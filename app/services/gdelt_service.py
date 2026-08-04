from __future__ import annotations

import random
import threading
import time
from datetime import datetime, timezone
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


GDELT_DOC_API = "https://api.gdeltproject.org/api/v2/doc/doc"

GDELT_CONNECT_TIMEOUT_SECONDS = 12
GDELT_READ_TIMEOUT_SECONDS = 20
GDELT_MAX_ATTEMPTS = 3
GDELT_BACKOFF_BASE_SECONDS = 1.5

GDELT_CIRCUIT_FAILURE_THRESHOLD = 4
GDELT_CIRCUIT_COOLDOWN_SECONDS = 120

_retryable_status_codes = {
    429,
    500,
    502,
    503,
    504,
}

_circuit_lock = threading.Lock()
_consecutive_failures = 0
_circuit_open_until = 0.0


def is_url(text: Any) -> bool:
    return (
        isinstance(text, str)
        and text.startswith(("http://", "https://"))
    )


def _session() -> requests.Session:
    retry = Retry(
        total=0,
        connect=0,
        read=0,
        status=0,
        redirect=2,
        raise_on_status=False,
    )

    adapter = HTTPAdapter(
        max_retries=retry,
        pool_connections=10,
        pool_maxsize=10,
    )

    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    session.headers.update(
        {
            "User-Agent": (
                "Sovereign-Intelligence-SEWS/1.0 "
                "(GDELT intelligence collection)"
            ),
            "Accept": "application/json",
        }
    )

    return session


def _circuit_available() -> bool:
    with _circuit_lock:
        return time.monotonic() >= _circuit_open_until


def _record_success() -> None:
    global _consecutive_failures
    global _circuit_open_until

    with _circuit_lock:
        _consecutive_failures = 0
        _circuit_open_until = 0.0


def _record_failure() -> None:
    global _consecutive_failures
    global _circuit_open_until

    with _circuit_lock:
        _consecutive_failures += 1

        if (
            _consecutive_failures
            >= GDELT_CIRCUIT_FAILURE_THRESHOLD
        ):
            _circuit_open_until = (
                time.monotonic()
                + GDELT_CIRCUIT_COOLDOWN_SECONDS
            )


def _circuit_remaining_seconds() -> int:
    with _circuit_lock:
        remaining = _circuit_open_until - time.monotonic()

    return max(0, int(round(remaining)))


def _retry_delay(attempt: int) -> float:
    exponential = (
        GDELT_BACKOFF_BASE_SECONDS
        * (2 ** max(0, attempt - 1))
    )

    jitter = random.uniform(0.0, 0.5)

    return exponential + jitter


def _error_response(
    *,
    message: str,
    query: str,
    attempts: int,
    error_type: str,
    status_code: int | None = None,
) -> dict[str, Any]:
    return {
        "status": "error",
        "message": message,
        "error_type": error_type,
        "status_code": status_code,
        "query": query,
        "attempts": attempts,
        "fetched_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "articles": [],
        "article_count": 0,
    }


def fetch_gdelt_news(
    query: str = "China Taiwan",
    max_records: int = 10,
) -> dict[str, Any]:
    """
    Query the GDELT DOC API with retries, exponential backoff,
    and a process-level circuit breaker.

    Retryable conditions:
    - connection timeout
    - read timeout
    - connection errors
    - HTTP 429
    - temporary HTTP 5xx responses

    Non-retryable HTTP 4xx responses return immediately.
    """

    query = str(query or "").strip()

    if not query:
        return _error_response(
            message="GDELT query cannot be empty.",
            query=query,
            attempts=0,
            error_type="INVALID_QUERY",
        )

    if not _circuit_available():
        return _error_response(
            message=(
                "GDELT circuit breaker is open. "
                f"Retry in approximately "
                f"{_circuit_remaining_seconds()} seconds."
            ),
            query=query,
            attempts=0,
            error_type="CIRCUIT_OPEN",
        )

    max_records = max(
        1,
        min(int(max_records or 10), 250),
    )

    params = {
        "query": query,
        "mode": "ArtList",
        "maxrecords": max_records,
        "format": "json",
        "sort": "DateDesc",
    }

    last_error: Exception | None = None
    last_status_code: int | None = None
    session = _session()

    try:
        for attempt in range(1, GDELT_MAX_ATTEMPTS + 1):
            try:
                response = session.get(
                    GDELT_DOC_API,
                    params=params,
                    timeout=(
                        GDELT_CONNECT_TIMEOUT_SECONDS,
                        GDELT_READ_TIMEOUT_SECONDS,
                    ),
                )

                last_status_code = response.status_code

                if response.status_code == 200:
                    try:
                        data = response.json()
                    except ValueError as exc:
                        last_error = exc
                        _record_failure()

                        if attempt < GDELT_MAX_ATTEMPTS:
                            time.sleep(_retry_delay(attempt))
                            continue

                        return _error_response(
                            message=(
                                "GDELT returned an invalid JSON response."
                            ),
                            query=query,
                            attempts=attempt,
                            error_type="INVALID_JSON",
                            status_code=response.status_code,
                        )

                    articles = []

                    for article in data.get("articles", []):
                        title = article.get("title")
                        summary = (
                            article.get("socialimage")
                            or article.get("description")
                            or ""
                        )

                        articles.append(
                            {
                                "title": title,
                                "title_en": title,
                                "url": article.get("url"),
                                "source": article.get(
                                    "sourcecountry"
                                ),
                                "domain": article.get("domain"),
                                "language": article.get(
                                    "language"
                                ),
                                "seendate": article.get(
                                    "seendate"
                                ),
                                "summary": summary,
                                "summary_en": "",
                            }
                        )

                    _record_success()

                    return {
                        "status": "success",
                        "fetched_at": datetime.now(
                            timezone.utc
                        ).isoformat(),
                        "query": query,
                        "article_count": len(articles),
                        "articles": articles,
                        "attempts": attempt,
                    }

                if (
                    response.status_code
                    not in _retryable_status_codes
                ):
                    _record_failure()

                    return _error_response(
                        message=(
                            response.text[:1000]
                            or (
                                "GDELT returned HTTP "
                                f"{response.status_code}."
                            )
                        ),
                        query=query,
                        attempts=attempt,
                        error_type="HTTP_ERROR",
                        status_code=response.status_code,
                    )

                last_error = RuntimeError(
                    f"GDELT returned retryable HTTP "
                    f"{response.status_code}."
                )

            except (
                requests.ConnectTimeout,
                requests.ReadTimeout,
                requests.ConnectionError,
            ) as exc:
                last_error = exc

            except requests.RequestException as exc:
                last_error = exc

            _record_failure()

            if attempt < GDELT_MAX_ATTEMPTS:
                time.sleep(_retry_delay(attempt))

        return _error_response(
            message=(
                f"{type(last_error).__name__}: {last_error}"
                if last_error
                else "GDELT request failed."
            ),
            query=query,
            attempts=GDELT_MAX_ATTEMPTS,
            error_type=(
                type(last_error).__name__
                if last_error
                else "REQUEST_FAILED"
            ),
            status_code=last_status_code,
        )

    finally:
        session.close()


def search_gdelt(
    query: str = "China Taiwan",
    max_records: int = 10,
) -> dict[str, Any]:
    """
    Compatibility alias used by the SEWS source registry.
    """

    return fetch_gdelt_news(
        query=query,
        max_records=max_records,
    )
