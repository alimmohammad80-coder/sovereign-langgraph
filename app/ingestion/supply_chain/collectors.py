from __future__ import annotations

import asyncio
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import urlencode

import feedparser
import httpx

from app.ingestion.base_collector import BaseCollector
from app.ingestion.collection_result import CollectionResult
from app.ingestion.supply_chain.models import SupplyChainEvidence
from app.services.gdelt_service import fetch_gdelt_news


DEFAULT_TIMEOUT = httpx.Timeout(
    connect=12.0,
    read=45.0,
    write=15.0,
    pool=10.0,
)


def _iso(value: Any) -> str | None:
    if not value:
        return None
    text = str(value).strip()
    try:
        return datetime.fromisoformat(
            text.replace("Z", "+00:00")
        ).astimezone(timezone.utc).isoformat()
    except ValueError:
        try:
            return parsedate_to_datetime(text).astimezone(
                timezone.utc
            ).isoformat()
        except (TypeError, ValueError, OverflowError):
            return None


def _text(value: Any, limit: int = 6000) -> str:
    if value is None:
        return ""
    return re.sub(
        r"\s+",
        " ",
        re.sub(r"<[^>]+>", " ", str(value)),
    ).strip()[:limit]


def _result(
    source: str,
    records: list[SupplyChainEvidence],
    *,
    metadata: dict[str, Any] | None = None,
    errors: list[str] | None = None,
) -> tuple[list[dict[str, Any]], CollectionResult]:
    issues = errors or []
    result = CollectionResult(
        source_key=source,
        success=not issues,
        records_collected=len(records),
        errors=issues,
        metadata=metadata or {},
    )
    return [record.to_storage_row() for record in records], result


class GDELTSupplyChainCollector(BaseCollector):
    source_key = "GDELT"

    async def collect(
        self,
        context: dict[str, Any] | None = None,
    ) -> tuple[list[dict[str, Any]], CollectionResult]:
        context = context or {}
        query = context.get("query") or (
            '("supply chain" OR shipping OR port OR chokepoint OR '
            'freight OR semiconductor OR LNG) '
            '(disruption OR closure OR congestion OR strike OR sanctions)'
        )
        payload = await asyncio.to_thread(
            fetch_gdelt_news,
            query,
            min(int(context.get("max_records", 50)), 100),
        )
        if payload.get("status") != "success":
            return _result(
                self.source_key,
                [],
                metadata={"query": query},
                errors=[payload.get("message") or "GDELT request failed."],
            )

        records = [
            SupplyChainEvidence(
                source="GDELT",
                source_record_id=article.get("url") or (
                    f"{article.get('domain')}:{article.get('seendate')}:"
                    f"{article.get('title')}"
                ),
                evidence_type="event",
                title=_text(article.get("title"), 1000),
                summary=_text(article.get("summary")),
                url=article.get("url"),
                published_at=_iso(article.get("seendate")),
                event_type="reported_disruption",
                severity_score=55,
                confidence_score=55,
                raw_payload={
                    "domain": article.get("domain"),
                    "language": article.get("language"),
                    "query": query,
                },
            )
            for article in payload.get("articles", [])
            if article.get("title") and article.get("url")
        ]
        return _result(
            self.source_key,
            records,
            metadata={"query": query},
        )


class PortWatchCollector(BaseCollector):
    source_key = "IMF_PORTWATCH"

    async def collect(
        self,
        context: dict[str, Any] | None = None,
    ) -> tuple[list[dict[str, Any]], CollectionResult]:
        context = context or {}
        endpoint = (
            context.get("portwatch_url")
            or os.getenv("PORTWATCH_API_URL")
        )
        if not endpoint:
            return _result(
                self.source_key,
                [],
                errors=[
                    "PORTWATCH_API_URL is not configured; use an approved "
                    "IMF PortWatch export or API endpoint."
                ],
            )

        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            response = await client.get(
                endpoint,
                params=context.get("portwatch_params") or {},
            )
            response.raise_for_status()
            payload = response.json()

        rows = (
            payload.get("data", [])
            if isinstance(payload, dict)
            else payload
        )
        records: list[SupplyChainEvidence] = []
        for row in rows[: int(context.get("max_records", 250))]:
            if not isinstance(row, dict):
                continue
            name = (
                row.get("port_name")
                or row.get("port")
                or row.get("chokepoint")
                or row.get("name")
            )
            if not name:
                continue
            value = (
                row.get("trade_volume")
                or row.get("port_calls")
                or row.get("value")
            )
            try:
                metric_value = float(value)
            except (TypeError, ValueError):
                metric_value = None
            records.append(
                SupplyChainEvidence(
                    source="IMF PortWatch",
                    source_record_id=str(
                        row.get("id")
                        or f"{name}:{row.get('date') or row.get('period')}"
                    ),
                    evidence_type="observation",
                    title=f"PortWatch observation: {name}",
                    summary=_text(
                        row.get("description")
                        or row.get("summary")
                    ),
                    url=endpoint,
                    published_at=_iso(
                        row.get("date") or row.get("period")
                    ),
                    matched_port=(
                        str(name)
                        if row.get("port_name") or row.get("port")
                        else None
                    ),
                    matched_chokepoint=(
                        str(name) if row.get("chokepoint") else None
                    ),
                    metric_name=str(
                        row.get("metric") or "maritime_activity"
                    ),
                    metric_value=metric_value,
                    metric_unit=row.get("unit"),
                    confidence_score=85,
                    raw_payload=row,
                )
            )
        return _result(self.source_key, records)


class GDACSCollector(BaseCollector):
    source_key = "GDACS"
    feed_url = "https://www.gdacs.org/xml/rss.xml"

    async def collect(
        self,
        context: dict[str, Any] | None = None,
    ) -> tuple[list[dict[str, Any]], CollectionResult]:
        context = context or {}
        url = context.get("gdacs_url") or self.feed_url
        feed = await asyncio.to_thread(feedparser.parse, url)
        if getattr(feed, "bozo", False) and not feed.entries:
            return _result(
                self.source_key,
                [],
                errors=[str(getattr(feed, "bozo_exception", "Invalid feed"))],
            )
        records = [
            SupplyChainEvidence(
                source="GDACS",
                source_record_id=entry.get("id") or entry.get("link"),
                evidence_type="event",
                title=_text(entry.get("title"), 1000),
                summary=_text(
                    entry.get("summary") or entry.get("description")
                ),
                url=entry.get("link"),
                published_at=_iso(
                    entry.get("published") or entry.get("updated")
                ),
                country_iso3=entry.get("gdacs_country"),
                event_type="natural_hazard",
                severity_score=(
                    85
                    if "red" in _text(entry).lower()
                    else 70
                    if "orange" in _text(entry).lower()
                    else 55
                ),
                confidence_score=90,
                raw_payload={
                    "event_type": entry.get("gdacs_eventtype"),
                    "alert_level": entry.get("gdacs_alertlevel"),
                },
            )
            for entry in feed.entries[
                : int(context.get("max_records", 100))
            ]
            if entry.get("title") and entry.get("link")
        ]
        return _result(self.source_key, records)


class USGSEarthquakeCollector(BaseCollector):
    source_key = "USGS"
    feed_url = (
        "https://earthquake.usgs.gov/earthquakes/feed/v1.0/"
        "summary/4.5_day.geojson"
    )

    async def collect(
        self,
        context: dict[str, Any] | None = None,
    ) -> tuple[list[dict[str, Any]], CollectionResult]:
        context = context or {}
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            response = await client.get(
                context.get("usgs_url") or self.feed_url
            )
            response.raise_for_status()
            payload = response.json()

        records: list[SupplyChainEvidence] = []
        for feature in payload.get("features", [])[
            : int(context.get("max_records", 100))
        ]:
            properties = feature.get("properties") or {}
            magnitude = properties.get("mag")
            try:
                magnitude_value = float(magnitude)
            except (TypeError, ValueError):
                magnitude_value = None
            event_ms = properties.get("time")
            published = None
            if isinstance(event_ms, (int, float)):
                published = datetime.fromtimestamp(
                    event_ms / 1000,
                    timezone.utc,
                ).isoformat()
            records.append(
                SupplyChainEvidence(
                    source="USGS",
                    source_record_id=str(feature.get("id")),
                    evidence_type="event",
                    title=_text(properties.get("title"), 1000),
                    summary=_text(properties.get("place")),
                    url=properties.get("url"),
                    published_at=published,
                    event_type="earthquake",
                    severity_score=min(
                        100,
                        max(45, (magnitude_value or 4.5) * 12),
                    ),
                    confidence_score=95,
                    metric_name="magnitude",
                    metric_value=magnitude_value,
                    metric_unit="Mw",
                    raw_payload={
                        "geometry": feature.get("geometry"),
                        "tsunami": properties.get("tsunami"),
                        "felt": properties.get("felt"),
                    },
                )
            )
        return _result(self.source_key, records)


class UNComtradeCollector(BaseCollector):
    source_key = "UN_COMTRADE"
    endpoint = (
        "https://comtradeapi.un.org/public/v1/preview/C/A/HS"
    )

    async def collect(
        self,
        context: dict[str, Any] | None = None,
    ) -> tuple[list[dict[str, Any]], CollectionResult]:
        context = context or {}
        reporter_code = context.get("reporter_code")
        if not reporter_code:
            return _result(
                self.source_key,
                [],
                errors=["reporter_code is required for UN Comtrade."],
            )
        period = str(
            context.get("period")
            or datetime.now(timezone.utc).year - 1
        )
        params = {
            "reporterCode": reporter_code,
            "period": period,
            "partnerCode": context.get("partner_code", "0"),
            "partner2Code": "0",
            "cmdCode": context.get("commodity_code", "TOTAL"),
            "flowCode": context.get("flow_code", "X"),
            "maxRecords": min(
                int(context.get("max_records", 100)),
                500,
            ),
            "breakdownMode": "classic",
            "includeDesc": "true",
        }
        headers = {}
        api_key = os.getenv("UN_COMTRADE_API_KEY")
        if api_key:
            headers["Ocp-Apim-Subscription-Key"] = api_key
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            response = await client.get(
                self.endpoint,
                params=params,
                headers=headers,
            )
            response.raise_for_status()
            payload = response.json()

        records: list[SupplyChainEvidence] = []
        for index, row in enumerate(payload.get("data", [])):
            value = row.get("primaryValue")
            try:
                metric_value = float(value)
            except (TypeError, ValueError):
                metric_value = None
            commodity = row.get("cmdDesc")
            records.append(
                SupplyChainEvidence(
                    source="UN Comtrade",
                    source_record_id=str(
                        row.get("aggregateLevel")
                        or index
                    )
                    + ":"
                    + ":".join(
                        str(row.get(key) or "")
                        for key in (
                            "reporterCode",
                            "partnerCode",
                            "cmdCode",
                            "flowCode",
                            "period",
                        )
                    ),
                    evidence_type="trade",
                    title=(
                        f"{row.get('reporterDesc') or reporter_code} "
                        f"{row.get('flowDesc') or params['flowCode']}: "
                        f"{commodity or params['cmdCode']}"
                    ),
                    summary="UN Comtrade reported merchandise trade value.",
                    published_at=f"{period}-12-31T00:00:00+00:00",
                    country_iso3=context.get("country_iso3"),
                    matched_commodity=commodity,
                    metric_name="trade_value",
                    metric_value=metric_value,
                    metric_unit="USD",
                    confidence_score=90,
                    raw_payload=row,
                )
            )
        return _result(
            self.source_key,
            records,
            metadata={"params": params},
        )


class EIACollector(BaseCollector):
    source_key = "EIA"
    base_url = "https://api.eia.gov/v2"

    async def collect(
        self,
        context: dict[str, Any] | None = None,
    ) -> tuple[list[dict[str, Any]], CollectionResult]:
        context = context or {}
        api_key = os.getenv("EIA_API_KEY")
        route = str(context.get("eia_route") or "").strip("/")
        if not api_key or not route:
            return _result(
                self.source_key,
                [],
                errors=[
                    "EIA_API_KEY and context.eia_route are required."
                ],
            )
        params: list[tuple[str, str]] = [
            ("api_key", api_key),
            ("frequency", str(context.get("frequency", "monthly"))),
            ("length", str(min(int(context.get("max_records", 100)), 500))),
        ]
        for field in context.get("data_fields") or ["value"]:
            params.append(("data[]", str(field)))
        for key, values in (context.get("facets") or {}).items():
            for value in values if isinstance(values, list) else [values]:
                params.append((f"facets[{key}][]", str(value)))

        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            response = await client.get(
                f"{self.base_url}/{route}/data/",
                params=params,
            )
            response.raise_for_status()
            payload = response.json()

        rows = (payload.get("response") or {}).get("data", [])
        records: list[SupplyChainEvidence] = []
        for index, row in enumerate(rows):
            value = row.get("value")
            try:
                metric_value = float(value)
            except (TypeError, ValueError):
                metric_value = None
            commodity = (
                context.get("commodity")
                or row.get("product-name")
                or row.get("series-description")
            )
            records.append(
                SupplyChainEvidence(
                    source="U.S. EIA",
                    source_record_id=str(
                        row.get("series")
                        or row.get("seriesId")
                        or index
                    )
                    + ":"
                    + str(row.get("period") or ""),
                    evidence_type="energy",
                    title=_text(
                        row.get("series-description")
                        or row.get("product-name")
                        or commodity
                        or "EIA energy observation",
                        1000,
                    ),
                    summary=_text(row.get("area-name")),
                    published_at=_iso(row.get("period")),
                    matched_commodity=commodity,
                    metric_name=str(
                        context.get("metric_name") or "energy_value"
                    ),
                    metric_value=metric_value,
                    metric_unit=row.get("unit"),
                    confidence_score=95,
                    raw_payload=row,
                )
            )
        return _result(
            self.source_key,
            records,
            metadata={"route": route},
        )


class OFACCollector(BaseCollector):
    source_key = "OFAC"
    default_url = "https://www.treasury.gov/ofac/downloads/sdn.xml"

    async def collect(
        self,
        context: dict[str, Any] | None = None,
    ) -> tuple[list[dict[str, Any]], CollectionResult]:
        context = context or {}
        url = context.get("ofac_url") or self.default_url
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(120.0),
            follow_redirects=True,
        ) as client:
            response = await client.get(url)
            response.raise_for_status()

        root = ET.fromstring(response.content)
        records: list[SupplyChainEvidence] = []
        name_filter = _text(context.get("entity_query")).lower()
        for entry in root.findall(".//{*}sdnEntry"):
            uid = _text(entry.findtext("{*}uid"))
            first = _text(entry.findtext("{*}firstName"))
            last = _text(entry.findtext("{*}lastName"))
            name = " ".join(part for part in (first, last) if part)
            entry_type = _text(entry.findtext("{*}sdnType"))
            programs = [
                _text(node.text)
                for node in entry.findall(".//{*}program")
                if node.text
            ]
            if name_filter and name_filter not in name.lower():
                continue
            if not name_filter and entry_type.lower() not in {
                "entity",
                "vessel",
                "aircraft",
            }:
                continue
            records.append(
                SupplyChainEvidence(
                    source="OFAC",
                    source_record_id=uid or name,
                    evidence_type="sanctions",
                    title=f"OFAC designation: {name}",
                    summary=", ".join(programs),
                    url=url,
                    matched_company=(
                        name if entry_type.lower() == "entity" else None
                    ),
                    event_type="sanctions_designation",
                    severity_score=85,
                    confidence_score=100,
                    raw_payload={
                        "sdn_type": entry_type,
                        "programs": programs,
                    },
                )
            )
            if len(records) >= int(context.get("max_records", 250)):
                break
        return _result(self.source_key, records)


class SECEdgarCollector(BaseCollector):
    source_key = "SEC_EDGAR"

    async def collect(
        self,
        context: dict[str, Any] | None = None,
    ) -> tuple[list[dict[str, Any]], CollectionResult]:
        context = context or {}
        cik = re.sub(r"\D", "", str(context.get("company_cik") or ""))
        company = _text(context.get("company_name"))
        user_agent = os.getenv("SEC_USER_AGENT")
        if not cik or not user_agent:
            return _result(
                self.source_key,
                [],
                errors=[
                    "company_cik and SEC_USER_AGENT are required for EDGAR."
                ],
            )
        url = f"https://data.sec.gov/submissions/CIK{cik.zfill(10)}.json"
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            response = await client.get(
                url,
                headers={
                    "User-Agent": user_agent,
                    "Accept-Encoding": "gzip, deflate",
                },
            )
            response.raise_for_status()
            payload = response.json()

        recent = (payload.get("filings") or {}).get("recent") or {}
        forms = recent.get("form") or []
        records: list[SupplyChainEvidence] = []
        allowed = set(
            context.get("forms")
            or ["8-K", "10-K", "10-Q", "20-F", "6-K"]
        )
        for index, form in enumerate(forms):
            if form not in allowed:
                continue
            accession = recent.get("accessionNumber", [])[index]
            primary = recent.get("primaryDocument", [])[index]
            filing_date = recent.get("filingDate", [])[index]
            accession_path = accession.replace("-", "")
            filing_url = (
                f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
                f"{accession_path}/{primary}"
            )
            records.append(
                SupplyChainEvidence(
                    source="SEC EDGAR",
                    source_record_id=accession,
                    evidence_type="filing",
                    title=f"{company or payload.get('name')} {form} filing",
                    summary=(
                        "Company regulatory filing available for "
                        "supply-chain disclosure extraction."
                    ),
                    url=filing_url,
                    published_at=f"{filing_date}T00:00:00+00:00",
                    matched_company=company or payload.get("name"),
                    confidence_score=100,
                    raw_payload={
                        "form": form,
                        "filing_date": filing_date,
                        "primary_document": primary,
                    },
                )
            )
            if len(records) >= int(context.get("max_records", 30)):
                break
        return _result(self.source_key, records)


class GLEIFCollector(BaseCollector):
    source_key = "GLEIF"

    async def collect(
        self,
        context: dict[str, Any] | None = None,
    ) -> tuple[list[dict[str, Any]], CollectionResult]:
        context = context or {}
        company = _text(
            context.get("company_name") or context.get("entity_query")
        )
        if not company:
            return _result(
                self.source_key,
                [],
                errors=["company_name is required for GLEIF."],
            )
        params = {
            "filter[entity.legalName]": company,
            "page[size]": min(int(context.get("max_records", 10)), 50),
        }
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            response = await client.get(
                "https://api.gleif.org/api/v1/lei-records",
                params=params,
            )
            response.raise_for_status()
            payload = response.json()

        records: list[SupplyChainEvidence] = []
        for item in payload.get("data", []):
            attributes = item.get("attributes") or {}
            entity = attributes.get("entity") or {}
            legal_name = (
                (entity.get("legalName") or {}).get("name")
                or company
            )
            records.append(
                SupplyChainEvidence(
                    source="GLEIF",
                    source_record_id=str(item.get("id")),
                    evidence_type="entity_registry",
                    title=f"GLEIF entity record: {legal_name}",
                    summary=_text(
                        (entity.get("legalAddress") or {}).get("country")
                    ),
                    url=(item.get("links") or {}).get("self"),
                    matched_company=legal_name,
                    confidence_score=95,
                    raw_payload={
                        "lei": item.get("id"),
                        "entity_status": entity.get("status"),
                        "legal_address": entity.get("legalAddress"),
                        "headquarters_address": entity.get(
                            "headquartersAddress"
                        ),
                        "relationships": item.get("relationships"),
                    },
                )
            )
        return _result(self.source_key, records)


class OfficialFeedCollector(BaseCollector):
    source_key = "OFFICIAL_FEEDS"

    async def collect(
        self,
        context: dict[str, Any] | None = None,
    ) -> tuple[list[dict[str, Any]], CollectionResult]:
        context = context or {}
        feed_urls = context.get("official_feed_urls") or []
        if not feed_urls:
            return _result(
                self.source_key,
                [],
                errors=["official_feed_urls is required."],
            )
        records: list[SupplyChainEvidence] = []
        for feed_spec in feed_urls:
            if isinstance(feed_spec, str):
                url = feed_spec
                publisher = "Official source"
            else:
                url = feed_spec.get("url")
                publisher = feed_spec.get("name") or "Official source"
            if not url:
                continue
            feed = await asyncio.to_thread(feedparser.parse, url)
            for entry in feed.entries[
                : int(context.get("max_records_per_feed", 25))
            ]:
                link = entry.get("link")
                title = _text(entry.get("title"), 1000)
                if not link or not title:
                    continue
                records.append(
                    SupplyChainEvidence(
                        source=publisher,
                        source_record_id=entry.get("id") or link,
                        evidence_type="event",
                        title=title,
                        summary=_text(
                            entry.get("summary")
                            or entry.get("description")
                        ),
                        url=link,
                        published_at=_iso(
                            entry.get("published")
                            or entry.get("updated")
                        ),
                        event_type="official_notice",
                        severity_score=60,
                        confidence_score=95,
                        raw_payload={"feed_url": url},
                    )
                )
        return _result(self.source_key, records)
