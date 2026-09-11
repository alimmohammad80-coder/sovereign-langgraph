from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests


class FinancialHistoryStore:
    """Fail-open PostgREST persistence for Financial Risk Command history."""

    def __init__(self, timeout: int = 10) -> None:
        self.url = (os.getenv("SUPABASE_URL") or os.getenv("SUPABASE_PROJECT_URL") or "").rstrip("/")
        self.key = (
            os.getenv("SUPABASE_SECRET_KEY")
            or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            or os.getenv("SUPABASE_KEY")
            or ""
        ).strip()
        self.timeout = timeout
        self.snapshot_table = os.getenv("FINANCIAL_SNAPSHOT_HISTORY_TABLE", "financial_risk_snapshots")
        self.report_table = os.getenv("FINANCIAL_REPORT_HISTORY_TABLE", "financial_risk_reports")

    @property
    def configured(self) -> bool:
        return bool(self.url and self.key)

    def _headers(self) -> Dict[str, str]:
        return {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    def _post(self, table: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.configured:
            return {"status": "disabled", "persisted": False}
        try:
            response = requests.post(
                f"{self.url}/rest/v1/{table}",
                headers=self._headers(),
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json() if response.content else []
            return {"status": "success", "persisted": True, "data": data}
        except Exception as exc:
            return {"status": "error", "persisted": False, "error": str(exc)}

    def save_snapshot(self, symbol: str, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        overall = snapshot.get("overall") or {}
        return self._post(
            self.snapshot_table,
            {
                "symbol": symbol.upper(),
                "captured_at": datetime.now(timezone.utc).isoformat(),
                "risk_score": overall.get("risk_score"),
                "risk_level": overall.get("risk_level"),
                "confidence_score": overall.get("confidence_score"),
                "methodology": snapshot.get("methodology"),
                "snapshot_json": snapshot,
            },
        )

    def save_report(self, report_id: str, symbol: str, report: Dict[str, Any]) -> Dict[str, Any]:
        return self._post(
            self.report_table,
            {
                "report_id": report_id,
                "symbol": symbol.upper(),
                "generated_at": report.get("generated_at") or datetime.now(timezone.utc).isoformat(),
                "risk_score": ((report.get("executive_summary") or {}).get("risk_score") if isinstance(report.get("executive_summary"), dict) else None),
                "methodology": report.get("methodology"),
                "report_json": report,
            },
        )

    @staticmethod
    def _history_item(row: Dict[str, Any]) -> Dict[str, Any]:
        snapshot = row.get("snapshot_json") if isinstance(row.get("snapshot_json"), dict) else {}
        dimensions = snapshot.get("dimensions") if isinstance(snapshot.get("dimensions"), list) else []
        dimension_scores = {
            str(item.get("key")): item.get("score")
            for item in dimensions
            if isinstance(item, dict) and item.get("key")
        }
        explanation = snapshot.get("explanation") if isinstance(snapshot.get("explanation"), dict) else {}
        largest_pressure = explanation.get("largest_pressure") if isinstance(explanation.get("largest_pressure"), dict) else {}
        freshness = snapshot.get("freshness") if isinstance(snapshot.get("freshness"), dict) else {}
        return {
            "id": row.get("id"),
            "symbol": row.get("symbol"),
            "captured_at": row.get("captured_at"),
            "risk_score": row.get("risk_score"),
            "risk_level": row.get("risk_level"),
            "confidence_score": row.get("confidence_score"),
            "methodology": row.get("methodology"),
            "dimensions": dimension_scores,
            "largest_pressure": {
                "key": largest_pressure.get("key"),
                "label": largest_pressure.get("label"),
                "score": largest_pressure.get("score"),
            } if largest_pressure else None,
            "freshness_status": freshness.get("overall_status"),
        }

    def list_snapshots(self, symbol: str, limit: int = 30) -> Dict[str, Any]:
        if not self.configured:
            return {"status": "disabled", "items": []}
        try:
            response = requests.get(
                f"{self.url}/rest/v1/{self.snapshot_table}",
                headers={**self._headers(), "Prefer": ""},
                params={
                    "symbol": f"eq.{symbol.upper()}",
                    "select": "id,symbol,captured_at,risk_score,risk_level,confidence_score,methodology,snapshot_json",
                    "order": "captured_at.desc",
                    "limit": max(1, min(200, int(limit))),
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            rows = data if isinstance(data, list) else []
            return {"status": "success", "items": [self._history_item(row) for row in rows]}
        except Exception as exc:
            return {"status": "error", "items": [], "error": str(exc)}

    def get_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        if not self.configured:
            return None
        try:
            response = requests.get(
                f"{self.url}/rest/v1/{self.report_table}",
                headers={**self._headers(), "Prefer": ""},
                params={"report_id": f"eq.{report_id}", "select": "report_json", "limit": 1},
                timeout=self.timeout,
            )
            response.raise_for_status()
            rows: List[Dict[str, Any]] = response.json()
            if rows and isinstance(rows[0].get("report_json"), dict):
                return rows[0]["report_json"]
        except Exception:
            return None
        return None
