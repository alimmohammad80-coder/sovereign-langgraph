from app.ai_gateway.gateway import AIGateway
from app.ai_gateway.schemas import AITaskType
from app.ai_gateway.routing import DEFAULT_ROUTES

def test_default_strategic_review_route_prefers_nvidia():
    assert DEFAULT_ROUTES[AITaskType.STRATEGIC_REVIEW].providers[0] == "NVIDIA"

def test_empty_gateway_has_no_available_providers():
    assert AIGateway([]).available_providers() == []
