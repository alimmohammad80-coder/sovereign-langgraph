from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from .entity_master import CorporateEntityMaster
from .gleif import GLEIFCollector
from .sec_edgar import SECEdgarCollector


class CorporateUniverseService:
    """Search local strategic entities plus live SEC and GLEIF universes."""

    def __init__(
        self,
        entity_master: Optional[CorporateEntityMaster] = None,
        sec: Optional[SECEdgarCollector] = None,
        gleif: Optional[GLEIFCollector] = None,
        sec_cache_ttl_seconds: int = 21600,
    ) -> None:
        self.entity_master = entity_master or CorporateEntityMaster()
        self.sec = sec or SECEdgarCollector()
        self.gleif = gleif or GLEIFCollector()
        self.sec_cache_ttl_seconds = sec_cache_ttl_seconds
        self._sec_cache: List[Dict[str, Any]] = []
        self._sec_cache_loaded_at = 0.0

    def _sec_index(self) -> List[Dict[str, Any]]:
        now = time.monotonic()
        if self._sec_cache and now - self._sec_cache_loaded_at < self.sec_cache_ttl_seconds:
            return self._sec_cache
        self._sec_cache = self.sec.ticker_index()
        self._sec_cache_loaded_at = now
        return self._sec_cache

    def search_sec(self, query: str, limit: int = 25) -> List[Dict[str, Any]]:
        needle = query.strip().casefold()
        if not needle:
            return []

        scored: List[tuple[int, Dict[str, Any]]] = []
        for item in self._sec_index():
            ticker = str(item.get("ticker") or "")
            title = str(item.get("title") or "")
            ticker_key = ticker.casefold()
            title_key = title.casefold()
            score = None
            if needle == ticker_key:
                score = 0
            elif needle == title_key:
                score = 1
            elif ticker_key.startswith(needle):
                score = 2
            elif title_key.startswith(needle):
                score = 3
            elif needle in ticker_key:
                score = 4
            elif needle in title_key:
                score = 5
            if score is not None:
                scored.append((score, item))

        scored.sort(key=lambda entry: (entry[0], str(entry[1].get("title") or "")))
        return [
            {
                "provider": "sec_edgar",
                "entity_type": "public_company",
                "legal_name": item.get("title"),
                "ticker": item.get("ticker"),
                "identifiers": {"cik": item.get("cik")},
            }
            for _, item in scored[: max(1, min(100, int(limit)))]
        ]

    def search(
        self,
        query: str,
        country_iso2: Optional[str] = None,
        limit_per_provider: int = 15,
    ) -> Dict[str, Any]:
        local = self.entity_master.list_entities(query=query, limit=limit_per_provider)
        sec_results: List[Dict[str, Any]] = []
        gleif_results: List[Dict[str, Any]] = []
        warnings: List[str] = []

        if self.sec.configured:
            try:
                sec_results = self.search_sec(query, limit=limit_per_provider)
            except Exception as exc:
                warnings.append(f"SEC EDGAR: {exc}")
        else:
            warnings.append("SEC EDGAR disabled until SEC_USER_AGENT is configured")

        try:
            gleif_results = self.gleif.search_by_name(
                query,
                country=country_iso2,
                limit=limit_per_provider,
            )
        except Exception as exc:
            warnings.append(f"GLEIF: {exc}")

        return {
            "query": query,
            "local_strategic_entities": local,
            "sec_public_issuers": sec_results,
            "gleif_legal_entities": gleif_results,
            "counts": {
                "local": len(local),
                "sec": len(sec_results),
                "gleif": len(gleif_results),
            },
            "warnings": warnings,
        }
