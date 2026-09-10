from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from supabase import Client

from app.schemas.sews_operations import PortfolioSupervisorRunRequest
from app.schemas.strategic_intelligence_product import ProductGenerationRequest
from app.sews_bridge.orchestrator import SEWSExistingSourcesBridge
from app.sews_bridge.schemas import BridgeRunRequest
from app.services.evidence_grounded_strategic_product_service import (
    EvidenceGroundedStrategicIntelligenceProductService,
)
from app.services.sews_evidence_context_service import SEWSEvidenceContextService
from app.services.sews_portfolio_supervisor import SEWSPortfolioSupervisor


REFRESH_VERSION = "sews-portfolio-refresh-v2.0.0"


class SEWSPortfolioRefreshService:
    """Refresh SEWS evidence, assessments, and OA/2.0 products coherently.

    The legacy warning supervisor remains responsible for deterministic matching,
    observation/state recalculation, and scoring. This coordinator broadens source
    collection before that run and then creates the canonical evidence-grounded
    Official Assessment after scoring. An Official Assessment is never generated
    when the warning has no canonical evidence context.
    """

    def __init__(self, db: Client):
        self.db = db

    def active_problem_keys(self) -> list[str]:
        result = (
            self.db.table("sews_warning_problems")
            .select("problem_key")
            .eq("active", True)
            .order("problem_key")
            .range(0, 4999)
            .execute()
        )
        return [str(row["problem_key"]) for row in (result.data or [])]

    async def refresh(
        self,
        *,
        problem_keys: list[str] | None = None,
        concurrency: int = 2,
        limit_per_query: int = 5,
    ) -> dict[str, Any]:
        keys = problem_keys or self.active_problem_keys()
        started_at = datetime.now(timezone.utc)

        # First collect across every discoverable source family. The bridge's
        # per-warning source policy decides which families are relevant. Source
        # adapters that cannot serve a warning are isolated in their own errors.
        bridge = await SEWSExistingSourcesBridge(self.db).run(
            BridgeRunRequest(
                problem_keys=keys,
                source_keys=None,
                limit_per_query=max(1, min(limit_per_query, 20)),
                persist=True,
                dry_run=False,
            )
        )

        portfolio = await SEWSPortfolioSupervisor(self.db).run(
            PortfolioSupervisorRunRequest(
                problem_keys=keys,
                dry_run=False,
                concurrency=max(1, min(concurrency, 4)),
                limit_per_query=max(1, min(limit_per_query, 20)),
            )
        )

        evidence_service = SEWSEvidenceContextService(self.db)
        product_service = EvidenceGroundedStrategicIntelligenceProductService(self.db)

        products_generated = 0
        products_blocked_no_evidence = 0
        product_errors: list[dict[str, str]] = []
        coverage: list[dict[str, Any]] = []

        for result in portfolio.results:
            key = result.problem_key
            context = evidence_service.build(key, limit=100)
            documents = context.get("documents") or []
            unique_sources = (context.get("quality") or {}).get("unique_source_count") or 0

            item = {
                "problem_key": key,
                "status": result.status,
                "records_received": result.records_received,
                "records_persisted": result.records_persisted,
                "observations_created": result.observations_created,
                "states_recalculated": result.states_recalculated,
                "assessment_id": result.assessment_id,
                "canonical_evidence_count": len(documents),
                "unique_source_count": unique_sources,
                "official_assessment_generated": False,
            }

            if not result.assessment_id:
                coverage.append(item)
                continue

            # Citation integrity gate: an Official Assessment must have at least
            # one canonical evidence document. Low diversity is reported through
            # confidence/quality metadata; zero evidence blocks publication.
            if not documents:
                products_blocked_no_evidence += 1
                item["official_assessment_blocked"] = "NO_CANONICAL_EVIDENCE"
                coverage.append(item)
                continue

            try:
                product = product_service.generate(
                    key,
                    ProductGenerationRequest(
                        assessment_id=UUID(str(result.assessment_id)),
                        ai_review_id=(
                            UUID(str(result.ai_review_id))
                            if result.ai_review_id
                            else None
                        ),
                        product_type="SEWS_OFFICIAL_ASSESSMENT",
                        audience="EXECUTIVE_ANALYST",
                        publish_to_ledger=True,
                        publish_product=True,
                        preferred_provider="NVIDIA",
                    ),
                )
                products_generated += 1
                item["official_assessment_generated"] = True
                item["product_id"] = str(product.product_id)
            except Exception as exc:
                product_errors.append(
                    {
                        "problem_key": key,
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )
                item["official_assessment_error"] = f"{type(exc).__name__}: {exc}"

            coverage.append(item)

        finished_at = datetime.now(timezone.utc)
        return {
            "status": "success" if not product_errors and portfolio.failed == 0 else "partial",
            "refresh_version": REFRESH_VERSION,
            "started_at": started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            "warning_problem_count": len(keys),
            "bridge": bridge.model_dump(mode="json"),
            "portfolio": portfolio.model_dump(mode="json"),
            "products_generated": products_generated,
            "products_blocked_no_evidence": products_blocked_no_evidence,
            "product_errors": product_errors,
            "coverage": coverage,
        }
