from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from typing import Any

from openai import OpenAI


MIN_ANALYSIS_WORDS = 300
MAX_ANALYSIS_WORDS = 500
MIN_BLUF_WORDS = 60
MAX_BLUF_WORDS = 140


class SupplyChainReportGenerationError(RuntimeError):
    """Raised when no publication-quality report can be produced."""


def _word_count(value: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", value or ""))


def _compact_value(value: Any, depth: int = 0) -> Any:
    """Bound live context without discarding entity-specific evidence."""
    if depth >= 7:
        return None
    if isinstance(value, dict):
        compact: dict[str, Any] = {}
        for key, item in list(value.items())[:45]:
            normalized = _compact_value(item, depth + 1)
            if normalized not in (None, "", [], {}):
                compact[str(key)] = normalized
        return compact
    if isinstance(value, list):
        return [
            normalized
            for item in value[:10]
            if (normalized := _compact_value(item, depth + 1)) not in (None, "", [], {})
        ]
    if isinstance(value, str):
        return value.strip()[:1800]
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return str(value)[:500]


def _extract_json(content: str) -> dict[str, Any]:
    text = (content or "").strip()
    fence = chr(96) * 3
    if text.startswith(fence):
        text = re.sub(r"^\x60{3}(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*\x60{3}$", "", text)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            raise SupplyChainReportGenerationError("The report model did not return JSON.")
        try:
            parsed = json.loads(text[start : end + 1])
        except json.JSONDecodeError as exc:
            raise SupplyChainReportGenerationError("The report model returned malformed JSON.") from exc
    if not isinstance(parsed, dict):
        raise SupplyChainReportGenerationError("The report payload is not an object.")
    return parsed


def _string_list(value: Any, limit: int = 8) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        if isinstance(item, str):
            text = item.strip()
        elif isinstance(item, dict):
            text = str(
                item.get("text")
                or item.get("title")
                or item.get("name")
                or item.get("action")
                or item.get("indicator")
                or ""
            ).strip()
        else:
            text = ""
        if text and text not in result:
            result.append(text)
        if len(result) >= limit:
            break
    return result


def _sources(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    result: list[dict[str, Any]] = []
    for item in value[:12]:
        if isinstance(item, str) and item.strip():
            result.append({"name": item.strip()})
        elif isinstance(item, dict):
            name = str(item.get("name") or item.get("source") or item.get("publisher") or "").strip()
            if name:
                result.append(
                    {
                        "name": name,
                        "title": item.get("title"),
                        "published_at": item.get("published_at") or item.get("date"),
                        "url": item.get("url"),
                    }
                )
    return result


def _source_key(value: str) -> str:
    return re.sub(r"\b(rss|feed|api)\b|[^a-z0-9]+", "", value.lower())


def _known_source_tokens(value: Any) -> set[str]:
    known: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if key.lower() in {"source", "publisher", "provider"} and isinstance(item, str):
                token = _source_key(item)
                if token:
                    known.add(token)
            known.update(_known_source_tokens(item))
    elif isinstance(value, list):
        for item in value:
            known.update(_known_source_tokens(item))
    return known


def _filter_verified_sources(
    sources: list[dict[str, Any]],
    evidence: Any,
) -> list[dict[str, Any]]:
    known = _known_source_tokens(evidence)
    if not known:
        return []
    return [
        source
        for source in sources
        if _source_key(str(source.get("name") or "")) in known
    ]


def _validate_report(payload: dict[str, Any]) -> dict[str, Any]:
    bluf = str(payload.get("bluf") or "").strip()
    analysis = str(
        payload.get("complete_analysis")
        or payload.get("complete_intelligence_analysis")
        or ""
    ).strip()

    errors: list[str] = []
    bluf_words = _word_count(bluf)
    analysis_words = _word_count(analysis)
    if not MIN_BLUF_WORDS <= bluf_words <= MAX_BLUF_WORDS:
        errors.append(
            f"BLUF must contain {MIN_BLUF_WORDS}-{MAX_BLUF_WORDS} words; received {bluf_words}."
        )
    if not MIN_ANALYSIS_WORDS <= analysis_words <= MAX_ANALYSIS_WORDS:
        errors.append(
            f"Complete analysis must contain {MIN_ANALYSIS_WORDS}-{MAX_ANALYSIS_WORDS} words; "
            f"received {analysis_words}."
        )
    if not str(payload.get("confidence") or "").strip():
        errors.append("Confidence is required.")
    if errors:
        raise SupplyChainReportGenerationError(" ".join(errors))

    forecast = payload.get("forecast") if isinstance(payload.get("forecast"), dict) else {}
    return {
        "bluf": bluf,
        "complete_analysis": analysis,
        "strategic_assessment": str(payload.get("strategic_assessment") or "").strip() or None,
        "simulation_assessment": str(payload.get("simulation_assessment") or "").strip() or None,
        "key_judgments": _string_list(payload.get("key_judgments"), 6),
        "drivers": _string_list(payload.get("drivers"), 8),
        "early_warning_indicators": _string_list(payload.get("early_warning_indicators"), 8),
        "recommended_actions": _string_list(payload.get("recommended_actions"), 8),
        "second_order_effects": _string_list(payload.get("second_order_effects"), 8),
        "goods_impact": _string_list(payload.get("goods_impact"), 8),
        "commodity_impact": _string_list(payload.get("commodity_impact"), 8),
        "company_impact": _string_list(payload.get("company_impact"), 8),
        "market_impact": str(payload.get("market_impact") or "").strip() or None,
        "supply_chain_impact": str(payload.get("supply_chain_impact") or "").strip() or None,
        "forecast": {
            "7_day": str(forecast.get("7_day") or "").strip() or None,
            "30_day": str(forecast.get("30_day") or "").strip() or None,
            "90_day": str(forecast.get("90_day") or "").strip() or None,
            "180_day": str(forecast.get("180_day") or "").strip() or None,
        },
        "confidence": str(payload.get("confidence") or "").strip(),
        "confidence_rationale": str(payload.get("confidence_rationale") or "").strip() or None,
        "intelligence_gaps": _string_list(payload.get("intelligence_gaps"), 6),
        "sources": _sources(payload.get("sources")),
        "analysis_word_count": analysis_words,
    }


def _provider_timeout_seconds() -> float:
    """Allow long-form report generation without an unbounded provider wait."""
    raw = os.getenv("SUPPLY_CHAIN_REPORT_TIMEOUT_SECONDS", "240")
    try:
        timeout = float(raw)
    except (TypeError, ValueError):
        timeout = 240.0
    return min(max(timeout, 60.0), 600.0)


def _client_config() -> tuple[OpenAI, str]:
    timeout = _provider_timeout_seconds()
    nvidia_key = os.getenv("NVIDIA_API_KEY") or os.getenv("NVIDIA_NIM_API_KEY")
    if nvidia_key:
        base_url = os.getenv("NVIDIA_BASE_URL") or "https://integrate.api.nvidia.com/v1"
        model = (
            os.getenv("SUPPLY_CHAIN_REPORT_MODEL")
            or os.getenv("NVIDIA_MODEL")
            or os.getenv("NEMOTRON_MODEL")
            or "nvidia/llama-3.1-nemotron-ultra-253b-v1"
        )
        return OpenAI(api_key=nvidia_key, base_url=base_url, timeout=timeout, max_retries=1), model

    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        base_url = os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1"
        model = (
            os.getenv("SUPPLY_CHAIN_REPORT_MODEL")
            or os.getenv("OPENAI_MODEL")
            or "gpt-4.1-mini"
        )
        return OpenAI(api_key=openai_key, base_url=base_url, timeout=timeout, max_retries=1), model

    raise SupplyChainReportGenerationError("No report-generation provider is configured.")


SYSTEM_PROMPT = """You are the senior supply-chain intelligence analyst for Sovereign Intelligence AI.
Produce publication-quality current intelligence for executives, risk officers, government analysts,
and strategic planners. Use only the supplied context. Never invent events, dependencies, statistics,
sources, or company exposures. Clearly separate observed evidence from analytic judgment. If the
evidence is thin, state the gap and lower confidence rather than filling it with generic claims.

Return only valid JSON. The BLUF must be 60-140 words. The complete_analysis must be 300-500 words
of coherent, entity-specific prose. It must explain current conditions, causal drivers, exposure
pathways, operational and market implications, alternative explanations, and the 7/30/90-day outlook.
Do not use markdown inside JSON strings. Avoid generic boilerplate and comma-joined fragments.

Use exactly these top-level keys:
bluf, complete_analysis, strategic_assessment, simulation_assessment, key_judgments, drivers,
goods_impact, commodity_impact, company_impact, market_impact, supply_chain_impact,
second_order_effects, forecast, early_warning_indicators, recommended_actions, confidence,
confidence_rationale, intelligence_gaps, sources.

forecast is an object with 7_day, 30_day, 90_day, and 180_day. Arrays contain concise standalone
items. sources contains only sources present in the supplied evidence, using objects with name,
title, published_at, and url where available."""


def generate_professional_supply_chain_report(
    entity_type: str,
    entity_name: str,
    question: str,
    context: dict[str, Any],
) -> dict[str, Any]:
    client, model = _client_config()
    provider = "NVIDIA" if model.lower().startswith("nvidia/") else "OpenAI"
    evidence = _compact_value(context)
    user_payload = {
        "report_subject": {
            "entity_type": entity_type,
            "entity_name": entity_name,
        },
        "analytic_requirement": question,
        "evidence_context": evidence,
    }
    messages: list[dict[str, str]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(user_payload, default=str)},
    ]

    last_error: Exception | None = None
    for attempt in range(2):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.1,
                max_tokens=3200,
            )
        except Exception as exc:
            detail = str(exc).lower()
            if "timeout" in type(exc).__name__.lower() or "timed out" in detail:
                message = (
                    "The report provider exceeded the configured "
                    f"{int(_provider_timeout_seconds())}-second generation window."
                )
            else:
                message = "The configured report provider did not complete the request."
            raise SupplyChainReportGenerationError(message) from exc
        content = response.choices[0].message.content or ""
        try:
            report = _validate_report(_extract_json(content))
            if (
                entity_type != "multi_entity_investigation"
                and entity_name.lower() not in (
                    report["bluf"] + " " + report["complete_analysis"]
                ).lower()
            ):
                raise SupplyChainReportGenerationError(
                    "The analysis does not identify the requested report subject."
                )
            report["sources"] = _filter_verified_sources(report["sources"], evidence)
            report.update(
                {
                    "entity_type": entity_type,
                    "entity_name": entity_name,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "provider": provider,
                    "model": model,
                    "generation_status": "validated",
                }
            )
            return report
        except SupplyChainReportGenerationError as exc:
            last_error = exc
            if attempt == 0:
                messages.extend(
                    [
                        {"role": "assistant", "content": content[:12000]},
                        {
                            "role": "user",
                            "content": (
                                "The draft failed publication quality control: "
                                f"{exc} Rewrite the full JSON report now. Preserve only evidence-grounded "
                                "judgments and satisfy every required field and word-count constraint."
                            ),
                        },
                    ]
                )

    raise SupplyChainReportGenerationError(
        f"No publication-quality report was produced after validation: {last_error}"
    )
