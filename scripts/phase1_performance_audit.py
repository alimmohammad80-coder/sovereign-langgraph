from __future__ import annotations

import argparse
import json
import math
import statistics
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


DEFAULT_BASE_URL = "https://sovereign-langgraph.onrender.com"
DEFAULT_PATHS = (
    "/",
    "/health",
    "/api/platform/health",
    "/api/global/risk",
)
FRESHNESS_KEYS = (
    "updated_at",
    "generated_at",
    "processed_at",
    "observed_at",
    "source_updated_at",
    "timestamp",
    "as_of",
)


@dataclass
class Sample:
    status: int | None
    elapsed_ms: float
    size_bytes: int
    error: str | None
    payload: Any = None


def percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * p
    lo = math.floor(position)
    hi = math.ceil(position)
    if lo == hi:
        return ordered[lo]
    weight = position - lo
    return ordered[lo] * (1 - weight) + ordered[hi] * weight


def parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def collect_freshness(payload: Any, prefix: str = "") -> list[tuple[str, datetime]]:
    found: list[tuple[str, datetime]] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            path = f"{prefix}.{key}" if prefix else key
            if key.lower() in FRESHNESS_KEYS:
                parsed = parse_datetime(value)
                if parsed:
                    found.append((path, parsed))
            if isinstance(value, (dict, list)):
                found.extend(collect_freshness(value, path))
    elif isinstance(payload, list):
        # Sample only a small prefix so a very large response does not make the
        # diagnostic itself expensive.
        for index, value in enumerate(payload[:25]):
            found.extend(collect_freshness(value, f"{prefix}[{index}]"))
    return found


def fetch(url: str, timeout: float) -> Sample:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "sovereign-phase1-performance-audit/1.0",
        },
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
            elapsed_ms = (time.perf_counter() - started) * 1000
            payload: Any = None
            content_type = response.headers.get("content-type", "")
            if "json" in content_type.lower() and body:
                try:
                    payload = json.loads(body)
                except json.JSONDecodeError:
                    payload = None
            return Sample(
                status=response.status,
                elapsed_ms=elapsed_ms,
                size_bytes=len(body),
                error=None,
                payload=payload,
            )
    except urllib.error.HTTPError as exc:
        elapsed_ms = (time.perf_counter() - started) * 1000
        body = exc.read()
        return Sample(exc.code, elapsed_ms, len(body), f"HTTP {exc.code}")
    except Exception as exc:  # diagnostic script: preserve the concrete failure
        elapsed_ms = (time.perf_counter() - started) * 1000
        return Sample(None, elapsed_ms, 0, str(exc))


def audit_path(base_url: str, path: str, runs: int, timeout: float) -> dict[str, Any]:
    url = base_url.rstrip("/") + "/" + path.lstrip("/")
    samples = [fetch(url, timeout) for _ in range(runs)]
    successful = [sample for sample in samples if sample.status and 200 <= sample.status < 400]
    timings = [sample.elapsed_ms for sample in successful]
    sizes = [sample.size_bytes for sample in successful]

    freshest: tuple[str, datetime] | None = None
    oldest: tuple[str, datetime] | None = None
    for sample in successful:
        for item in collect_freshness(sample.payload):
            if freshest is None or item[1] > freshest[1]:
                freshest = item
            if oldest is None or item[1] < oldest[1]:
                oldest = item

    now = datetime.now(timezone.utc)
    return {
        "path": path,
        "url": url,
        "runs": runs,
        "successful_runs": len(successful),
        "statuses": [sample.status for sample in samples],
        "errors": [sample.error for sample in samples if sample.error],
        "latency_ms": {
            "min": round(min(timings), 1) if timings else None,
            "median": round(statistics.median(timings), 1) if timings else None,
            "p95": round(percentile(timings, 0.95), 1) if timings else None,
            "max": round(max(timings), 1) if timings else None,
        },
        "payload_bytes": {
            "median": int(statistics.median(sizes)) if sizes else None,
            "max": max(sizes) if sizes else None,
        },
        "freshness": {
            "freshest_field": freshest[0] if freshest else None,
            "freshest_at": freshest[1].isoformat() if freshest else None,
            "freshest_age_seconds": round((now - freshest[1]).total_seconds(), 1) if freshest else None,
            "oldest_field": oldest[0] if oldest else None,
            "oldest_at": oldest[1].isoformat() if oldest else None,
            "oldest_age_seconds": round((now - oldest[1]).total_seconds(), 1) if oldest else None,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Measure Sovereign Intelligence API latency, payload size, and visible freshness metadata."
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument(
        "--path",
        action="append",
        dest="paths",
        help="GET path to audit. Repeat for multiple endpoints. Defaults to safe platform endpoints.",
    )
    args = parser.parse_args()

    paths = tuple(args.paths) if args.paths else DEFAULT_PATHS
    report = {
        "base_url": args.base_url,
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "runs_per_path": args.runs,
        "results": [
            audit_path(args.base_url, path, args.runs, args.timeout)
            for path in paths
        ],
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
