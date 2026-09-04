import json

import pytest

from app.services.supply_chain_report_generator import (
    SupplyChainReportGenerationError,
    _attach_verified_citations,
    _build_source_register,
    _compact_value,
    _extract_json,
    _format_chicago_citation,
    _validate_report,
)


def _payload(analysis_words: int = 350, bluf_words: int = 80):
    return {
        "bluf": " ".join(["judgment"] * bluf_words),
        "complete_analysis": " ".join(["assessment"] * analysis_words),
        "confidence": "Moderate",
        "forecast": {
            "7_day": "Near-term monitoring continues.",
            "30_day": "Exposure remains elevated.",
            "90_day": "Mitigation may reduce concentration risk.",
        },
        "drivers": ["Concentration risk"],
        "sources": [{"name": "Live disruption feed", "title": "Observed signal"}],
    }


def test_validates_publication_length_and_metadata():
    report = _validate_report(_payload())

    assert report["analysis_word_count"] == 350
    assert report["confidence"] == "Moderate"
    assert report["sources"][0]["name"] == "Live disruption feed"


@pytest.mark.parametrize("word_count", [0, 299, 501])
def test_rejects_reports_outside_required_length(word_count):
    with pytest.raises(SupplyChainReportGenerationError):
        _validate_report(_payload(analysis_words=word_count))


def test_extracts_json_from_fenced_model_output():
    payload = _payload()
    fence = chr(96) * 3
    parsed = _extract_json(f"{fence}json\n{json.dumps(payload)}\n{fence}")

    assert parsed["confidence"] == "Moderate"


def test_compacts_large_context_without_losing_subject():
    context = {
        "companies": [
            {
                "entity_name": "TSMC",
                "company_profile": {"sector": "Semiconductors", "risk_score": 65},
                "signals": [{"title": f"Signal {index}"} for index in range(25)],
            }
        ]
    }

    compact = _compact_value(context)

    assert compact["companies"][0]["entity_name"] == "TSMC"
    assert len(compact["companies"][0]["signals"]) == 10


def test_formats_chicago_web_citation():
    citation = _format_chicago_citation(
        {
            "name": "GDACS",
            "title": "Flood Alert for Test Port",
            "published_at": "2026-09-04T10:30:00+00:00",
            "url": "https://example.test/alert",
        }
    )

    assert citation == (
        'GDACS. “Flood Alert for Test Port.” '
        "September 4, 2026. https://example.test/alert."
    )


def test_builds_deduplicated_verified_source_register():
    register = _build_source_register(
        {
            "external_evidence": [
                {
                    "source": "USGS",
                    "title": "Magnitude 6 Earthquake",
                    "published_at": "2026-09-04T10:30:00+00:00",
                    "url": "https://example.test/quake",
                },
                {
                    "source": "USGS",
                    "title": "Magnitude 6 Earthquake",
                    "published_at": "2026-09-04T10:30:00+00:00",
                    "url": "https://example.test/quake",
                },
            ]
        },
        "Port of Test",
    )

    assert [source["number"] for source in register] == [1, 2]
    assert register[0]["source_type"] == "internal"
    assert register[1]["name"] == "USGS"


def test_attaches_only_sources_cited_in_report():
    report = {
        "bluf": "Current conditions remain elevated.[1]",
        "complete_analysis": "An external hazard was recorded.[2]",
    }
    register = [
        {"number": 1, "citation": "Internal citation."},
        {"number": 2, "citation": "External citation."},
        {"number": 3, "citation": "Unused citation."},
    ]

    _attach_verified_citations(report, register)

    assert [source["number"] for source in report["sources"]] == [1, 2]
    assert report["citation_count"] == 2
    assert report["citation_style"].startswith("Chicago")


def test_rejects_unverified_source_number():
    report = {
        "bluf": "Current conditions remain elevated.[9]",
        "complete_analysis": "Assessment text.",
    }

    with pytest.raises(SupplyChainReportGenerationError):
        _attach_verified_citations(
            report,
            [{"number": 1, "citation": "Internal citation."}],
        )
