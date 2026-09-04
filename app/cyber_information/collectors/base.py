from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

import httpx


class CollectorError(RuntimeError):
    pass


class BaseCollector:
    source_name: str = "unknown"
    timeout_seconds: float = 20.0

    async def get_json(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        request_headers = {
            "Accept": "application/json",
            "User-Agent": "SovereignIntelligenceAI/1.0 cyber-information-collector",
            **(headers or {}),
        }
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds,
                follow_redirects=True,
            ) as client:
                response = await client.get(url, params=params, headers=request_headers)
                response.raise_for_status()
                return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise CollectorError(f"{self.source_name} collection failed: {exc}") from exc

    @staticmethod
    def collected_at() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def stable_hash(payload: Any) -> str:
        encoded = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()
