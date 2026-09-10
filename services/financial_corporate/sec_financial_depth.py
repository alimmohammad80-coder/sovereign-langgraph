from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from .sec_edgar import SEC_DATA_BASE, SECEdgarCollector


class SECFinancialDepthCollector:
    """Extract debt maturity schedules and annual financial history from SEC company facts."""

    HISTORY_CONCEPTS = {
        "revenue": ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet"],
        "net_income": ["NetIncomeLoss", "ProfitLoss"],
        "operating_income": ["OperatingIncomeLoss"],
        "operating_cash_flow": ["NetCashProvidedByUsedInOperatingActivities"],
        "long_term_debt": ["LongTermDebtNoncurrent", "LongTermDebt"],
    }

    MATURITY_CONCEPTS = {
        "year_1": [
            "LongTermDebtMaturitiesRepaymentsOfPrincipalInNextTwelveMonths",
            "LongTermDebtCurrent",
            "ShortTermBorrowings",
        ],
        "year_2": ["LongTermDebtMaturitiesRepaymentsOfPrincipalInYearTwo"],
        "year_3": ["LongTermDebtMaturitiesRepaymentsOfPrincipalInYearThree"],
        "year_4": ["LongTermDebtMaturitiesRepaymentsOfPrincipalInYearFour"],
        "year_5": ["LongTermDebtMaturitiesRepaymentsOfPrincipalInYearFive"],
        "thereafter": ["LongTermDebtMaturitiesRepaymentsOfPrincipalAfterYearFive"],
    }

    def __init__(self, sec: Optional[SECEdgarCollector] = None) -> None:
        self.sec = sec or SECEdgarCollector()

    @staticmethod
    def _candidate_rows(facts: Dict[str, Any], concepts: Iterable[str]) -> List[Dict[str, Any]]:
        us_gaap = facts.get("us-gaap") or {}
        rows: List[Dict[str, Any]] = []
        for concept in concepts:
            node = us_gaap.get(concept)
            if not isinstance(node, dict):
                continue
            for unit, observations in (node.get("units") or {}).items():
                if unit != "USD":
                    continue
                for item in observations or []:
                    if not isinstance(item, dict) or item.get("val") is None:
                        continue
                    rows.append({
                        "concept": concept,
                        "label": node.get("label"),
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
                    })
        return rows

    @classmethod
    def _latest_disclosed(cls, facts: Dict[str, Any], concepts: Iterable[str]) -> Optional[Dict[str, Any]]:
        rows = cls._candidate_rows(facts, concepts)
        if not rows:
            return None
        annual = [row for row in rows if row.get("form") == "10-K"]
        candidates = annual or rows
        candidates.sort(key=lambda row: (row.get("filed") or "", row.get("period_end") or ""), reverse=True)
        return candidates[0]

    @classmethod
    def _annual_history(cls, facts: Dict[str, Any], concepts: Iterable[str], limit: int = 5) -> List[Dict[str, Any]]:
        rows = [
            row for row in cls._candidate_rows(facts, concepts)
            if row.get("form") == "10-K" and row.get("fiscal_period") == "FY"
        ]
        concept_rank = {concept: index for index, concept in enumerate(concepts)}
        rows.sort(
            key=lambda row: (
                row.get("period_end") or "",
                -(concept_rank.get(row.get("concept"), 999)),
                row.get("filed") or "",
            )
        )
        by_period: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            period = row.get("period_end")
            if not period:
                continue
            existing = by_period.get(period)
            if existing is None or concept_rank.get(row.get("concept"), 999) < concept_rank.get(existing.get("concept"), 999):
                by_period[period] = row
            elif concept_rank.get(row.get("concept"), 999) == concept_rank.get(existing.get("concept"), 999) and (row.get("filed") or "") > (existing.get("filed") or ""):
                by_period[period] = row
        return [by_period[key] for key in sorted(by_period.keys())[-limit:]]

    def collect(self, cik: str | int) -> Dict[str, Any]:
        cik10 = self.sec.normalize_cik(cik)
        raw = self.sec._get_json(f"{SEC_DATA_BASE}/api/xbrl/companyfacts/CIK{cik10}.json")
        facts = raw.get("facts") or {}

        maturities = {
            key: self._latest_disclosed(facts, concepts)
            for key, concepts in self.MATURITY_CONCEPTS.items()
        }
        history = {
            key: self._annual_history(facts, concepts)
            for key, concepts in self.HISTORY_CONCEPTS.items()
        }

        return {
            "provider": "sec_edgar_xbrl",
            "cik": cik10,
            "entity_name": raw.get("entityName"),
            "debt_maturities": maturities,
            "financial_history": history,
            "maturity_buckets_observed": sum(1 for value in maturities.values() if value is not None),
            "history_metrics_observed": sum(1 for value in history.values() if len(value) >= 2),
            "source_url": f"{SEC_DATA_BASE}/api/xbrl/companyfacts/CIK{cik10}.json",
        }
