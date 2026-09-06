from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

import requests


SEC_DATA_BASE = "https://data.sec.gov"
SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"


class SECConfigurationError(RuntimeError):
    pass


class SECEdgarCollector:
    """SEC EDGAR submissions and XBRL company-facts collector.

    The SEC requires automated clients to identify themselves. Set SEC_USER_AGENT
    in the deployment environment before enabling live collection.
    """

    def __init__(self, user_agent: Optional[str] = None, timeout: int = 20) -> None:
        self.user_agent = (user_agent or os.getenv("SEC_USER_AGENT") or "").strip()
        self.timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self.user_agent)

    def _headers(self) -> Dict[str, str]:
        if not self.configured:
            raise SECConfigurationError(
                "SEC_USER_AGENT is required for SEC EDGAR automated access."
            )
        return {
            "User-Agent": self.user_agent,
            "Accept-Encoding": "gzip, deflate",
            "Accept": "application/json",
        }

    def _get_json(self, url: str) -> Dict[str, Any]:
        response = requests.get(url, headers=self._headers(), timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError(f"Unexpected SEC response type from {url}")
        return data

    @staticmethod
    def normalize_cik(cik: str | int) -> str:
        raw = str(cik).strip().upper().replace("CIK", "")
        if not raw.isdigit():
            raise ValueError("CIK must be numeric")
        return raw.zfill(10)

    def fetch_submissions(self, cik: str | int) -> Dict[str, Any]:
        cik10 = self.normalize_cik(cik)
        raw = self._get_json(f"{SEC_DATA_BASE}/submissions/CIK{cik10}.json")
        return self.normalize_submissions(raw)

    def fetch_company_facts(self, cik: str | int) -> Dict[str, Any]:
        cik10 = self.normalize_cik(cik)
        raw = self._get_json(f"{SEC_DATA_BASE}/api/xbrl/companyfacts/CIK{cik10}.json")
        return self.normalize_company_facts(raw)

    def ticker_index(self) -> List[Dict[str, Any]]:
        raw = self._get_json(SEC_TICKERS_URL)
        records: List[Dict[str, Any]] = []
        for item in raw.values():
            if not isinstance(item, dict):
                continue
            cik = item.get("cik_str")
            ticker = item.get("ticker")
            title = item.get("title")
            if cik is None or not ticker:
                continue
            records.append({
                "cik": self.normalize_cik(cik),
                "ticker": str(ticker).upper(),
                "title": title,
            })
        return records

    def resolve_ticker(self, ticker: str) -> Optional[Dict[str, Any]]:
        needle = ticker.strip().upper()
        if not needle:
            return None
        for item in self.ticker_index():
            if item["ticker"] == needle:
                return item
        return None

    @staticmethod
    def normalize_submissions(raw: Dict[str, Any]) -> Dict[str, Any]:
        recent = ((raw.get("filings") or {}).get("recent") or {})
        forms = recent.get("form") or []
        accessions = recent.get("accessionNumber") or []
        filed = recent.get("filingDate") or []
        primary_documents = recent.get("primaryDocument") or []

        filings: List[Dict[str, Any]] = []
        count = min(len(forms), len(accessions), len(filed))
        for index in range(count):
            filings.append({
                "form": forms[index],
                "accession_number": accessions[index],
                "filing_date": filed[index],
                "primary_document": primary_documents[index] if index < len(primary_documents) else None,
            })

        return {
            "provider": "sec_edgar",
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "identity": {
                "cik": str(raw.get("cik") or "").zfill(10) if raw.get("cik") is not None else None,
                "legal_name": raw.get("name"),
                "sic": raw.get("sic"),
                "sic_description": raw.get("sicDescription"),
                "tickers": raw.get("tickers") or [],
                "exchanges": raw.get("exchanges") or [],
                "ein": raw.get("ein"),
                "state_of_incorporation": raw.get("stateOfIncorporation"),
                "fiscal_year_end": raw.get("fiscalYearEnd"),
            },
            "recent_filings": filings,
            "source_url": f"{SEC_DATA_BASE}/submissions/CIK{str(raw.get('cik') or '').zfill(10)}.json",
        }

    @staticmethod
    def _latest_fact(
        facts: Dict[str, Any],
        concepts: Iterable[str],
        preferred_units: Iterable[str] = ("USD", "shares", "USD/shares", "pure"),
    ) -> Optional[Dict[str, Any]]:
        us_gaap = facts.get("us-gaap") or {}
        for concept in concepts:
            node = us_gaap.get(concept)
            if not isinstance(node, dict):
                continue
            units = node.get("units") or {}
            for unit in preferred_units:
                observations = units.get(unit)
                if not observations:
                    continue
                valid = [item for item in observations if isinstance(item, dict) and item.get("val") is not None]
                if not valid:
                    continue
                valid.sort(key=lambda item: (item.get("filed") or "", item.get("end") or ""), reverse=True)
                item = valid[0]
                return {
                    "concept": concept,
                    "label": node.get("label"),
                    "description": node.get("description"),
                    "value": item.get("val"),
                    "unit": unit,
                    "period_start": item.get("start"),
                    "period_end": item.get("end"),
                    "filed": item.get("filed"),
                    "form": item.get("form"),
                    "fiscal_year": item.get("fy"),
                    "fiscal_period": item.get("fp"),
                    "accession_number": item.get("accn"),
                    "frame": item.get("frame"),
                }
        return None

    @classmethod
    def normalize_company_facts(cls, raw: Dict[str, Any]) -> Dict[str, Any]:
        facts = raw.get("facts") or {}
        metrics = {
            "revenue": cls._latest_fact(facts, ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet"]),
            "net_income": cls._latest_fact(facts, ["NetIncomeLoss", "ProfitLoss"]),
            "operating_income": cls._latest_fact(facts, ["OperatingIncomeLoss"]),
            "assets": cls._latest_fact(facts, ["Assets"]),
            "liabilities": cls._latest_fact(facts, ["Liabilities"]),
            "equity": cls._latest_fact(facts, ["StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"]),
            "cash": cls._latest_fact(facts, ["CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"]),
            "current_assets": cls._latest_fact(facts, ["AssetsCurrent"]),
            "current_liabilities": cls._latest_fact(facts, ["LiabilitiesCurrent"]),
            "long_term_debt": cls._latest_fact(facts, ["LongTermDebtCurrent", "LongTermDebtNoncurrent", "LongTermDebt"]),
            "interest_expense": cls._latest_fact(facts, ["InterestExpenseNonOperating", "InterestExpense"]),
            "operating_cash_flow": cls._latest_fact(facts, ["NetCashProvidedByUsedInOperatingActivities"]),
        }
        cik10 = str(raw.get("cik") or "").zfill(10) if raw.get("cik") is not None else None
        return {
            "provider": "sec_edgar",
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "identity": {
                "cik": cik10,
                "legal_name": raw.get("entityName"),
            },
            "financial_observations": metrics,
            "source_url": f"{SEC_DATA_BASE}/api/xbrl/companyfacts/CIK{cik10}.json" if cik10 else None,
        }

    def company_snapshot(self, cik: str | int) -> Dict[str, Any]:
        submissions = self.fetch_submissions(cik)
        facts = self.fetch_company_facts(cik)
        return {
            "provider": "sec_edgar",
            "identity": submissions.get("identity"),
            "financial_observations": facts.get("financial_observations"),
            "recent_filings": submissions.get("recent_filings", []),
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "sources": [submissions.get("source_url"), facts.get("source_url")],
        }
