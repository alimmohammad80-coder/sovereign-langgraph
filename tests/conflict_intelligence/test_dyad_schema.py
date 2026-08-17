from datetime import datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.conflict_intelligence.common import ConfidenceGrade, ReviewStatus
from app.schemas.conflict_intelligence.ontology import BorderDyad


def base_payload():
    now = datetime.utcnow()
    return {
        "id": uuid4(),
        "created_at": now,
        "updated_at": now,
        "dyad_id": "DYAD-CHN-IND-LAND",
        "country_a_iso3": "CHN",
        "country_b_iso3": "IND",
        "dyad_type": "land",
        "source": "test",
        "confidence_grade": ConfidenceGrade.HIGH,
        "review_status": ReviewStatus.VALIDATED,
    }


def test_canonical_dyad():
    model = BorderDyad(**base_payload())
    assert model.dyad_id == "DYAD-CHN-IND-LAND"


def test_rejects_reversed_dyad():
    payload = base_payload()
    payload["country_a_iso3"] = "IND"
    payload["country_b_iso3"] = "CHN"
    payload["dyad_id"] = "DYAD-IND-CHN-LAND"
    with pytest.raises(ValidationError):
        BorderDyad(**payload)
