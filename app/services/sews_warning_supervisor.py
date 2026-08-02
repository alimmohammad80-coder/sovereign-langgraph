from __future__ import annotations
from datetime import datetime, timezone
from uuid import UUID
from supabase import Client

from app.schemas.sews_operations import EvidencePipelineResponse, IndicatorPipelineSummary, WarningSupervisorRunRequest
from app.sews_bridge.orchestrator import SEWSExistingSourcesBridge
from app.sews_bridge.schemas import BridgeRunRequest
from app.services.sews_deterministic_matcher import SEWSDeterministicIndicatorMatcher
from app.services.sews_evidence_service import (
    SEWSEvidenceService,
)
from app.services.sews_observation_service import SEWSObservationService
from app.services.sews_indicator_state_service import SEWSIndicatorStateService
from app.services.sews_warning_scoring_service import SEWSWarningScoringService
from app.services.sews_material_change_service import SEWSMaterialChangeService
from app.services.sews_ai_review_service import SEWSAIReviewService
from app.services.strategic_intelligence_product_service import StrategicIntelligenceProductService

from app.schemas.sews_evidence import (
    EvidenceNormalizeRequest,
    ObservationCreateRequest,
    ObservationEvidenceLinkInput,
    ObservationStatus,
    ObservationTrend,
    EvidencePolarity,
    IndicatorStateRecalculateRequest,
)
from app.schemas.sews_warning_scoring import WarningAssessmentRequest
from app.schemas.sews_ai_review import AIReviewRequest
from app.schemas.strategic_intelligence_product import ProductGenerationRequest

class SEWSWarningSupervisor:
    def __init__(self, db: Client):
        self.db = db
        self.matcher = SEWSDeterministicIndicatorMatcher()

    def _mappings(self, problem_key):
        result = (
            self.db.table("sews_warning_problem_indicators")
            .select("problem_key,indicator_key,indicator_class,weight,polarity,rationale,active,sews_indicator_definitions(*)")
            .eq("problem_key", problem_key)
            .eq("active", True)
            .range(0, 4999)
            .execute()
        )
        return result.data or []

    def _evidence(self, problem_key):
        result = (
            self.db.table("sews_raw_evidence")
            .select("*")
            .contains("metadata", {"warning_problem_key": problem_key})
            .is_("duplicate_of_id", "null")
            .order("collected_at", desc=True)
            .limit(500)
            .execute()
        )
        return result.data or []

    def _previous_assessment(self, problem_key):
        warning = self.db.table("sews_warning_problems").select("id").eq("problem_key", problem_key).limit(1).execute()
        if not warning.data:
            return None
        result = self.db.table("sews_assessments").select("*").eq("warning_problem_id", warning.data[0]["id"]).order("assessed_at", desc=True).limit(1).execute()
        return result.data[0] if result.data else None

    async def run(self, request: WarningSupervisorRunRequest) -> EvidencePipelineResponse:
        response = EvidencePipelineResponse(
            status="preview" if request.dry_run else "success",
            problem_key=request.problem_key,
        )

        bridge = await SEWSExistingSourcesBridge(self.db).run(
            BridgeRunRequest(
                problem_keys=[request.problem_key],
                source_keys=["GOOGLE_NEWS_RSS", "GDELT", "NEWSAPI"],
                limit_per_query=request.limit_per_query,
                persist=not request.dry_run,
                dry_run=request.dry_run,
            )
        )

        response.records_received = bridge.total_records_received
        response.records_persisted = bridge.total_records_persisted
        response.metadata["source_results"] = bridge.model_dump(mode="json")["source_results"]

        if request.dry_run:
            return response

        mappings = self._mappings(request.problem_key)
        response.indicators_considered = len(mappings)
        evidence_rows = self._evidence(request.problem_key)

        if not mappings:
            response.status = "blocked"
            response.errors.append("No active warning-to-indicator mappings.")
            return response

        if not evidence_rows:
            response.status = "blocked"
            response.errors.append("No persisted raw evidence for this warning.")
            return response

        evidence_service = SEWSEvidenceService(self.db)
        obs_service = SEWSObservationService(self.db)
        state_service = SEWSIndicatorStateService(self.db)
        matched = set()
        evidence_object_ids: dict[str, UUID] = {}

        # Rank indicators from the perspective of each evidence record.
        # One evidence item may affect no more than four indicators.
        selected_pairs: dict[
            str,
            list[tuple[dict, object]],
        ] = {}

        for evidence in evidence_rows:
            ranked_matches = self.matcher.rank_for_evidence(
                evidence=evidence,
                mappings=mappings,
                limit=4,
            )

            for selected_mapping, match in ranked_matches:
                selected_indicator_key = selected_mapping[
                    "indicator_key"
                ]

                selected_pairs.setdefault(
                    selected_indicator_key,
                    [],
                ).append(
                    (evidence, match)
                )

        for mapping in mappings:
            indicator = mapping.get("sews_indicator_definitions") or {}
            indicator_key = mapping["indicator_key"]
            item = IndicatorPipelineSummary(indicator_key=indicator_key)

            pairs = selected_pairs.get(
                indicator_key,
                [],
            )

            item.matched_evidence_count = len(pairs)
            if not pairs:
                response.indicator_results.append(item)
                continue

            matched.add(indicator_key)

            for evidence, match in pairs[:25]:
                try:
                    raw_evidence_id = UUID(
                        str(evidence["id"])
                    )

                    evidence_cache_key = str(raw_evidence_id)
                    evidence_object_id = evidence_object_ids.get(
                        evidence_cache_key
                    )

                    if evidence_object_id is None:
                        normalized = evidence_service.normalize(
                            EvidenceNormalizeRequest(
                                raw_evidence_id=raw_evidence_id,
                                evidence_type="OPEN_SOURCE_REPORT",
                                event_type=(
                                    evidence.get("metadata", {}).get(
                                        "event_type"
                                    )
                                    or "CURRENT_EVENT"
                                ),
                                summary=(
                                    evidence.get("title")
                                    or evidence.get("raw_text")
                                    or "SEWS evidence"
                                ),
                                normalized_text=(
                                    evidence.get("raw_text")
                                    or evidence.get("title")
                                ),
                                event_time=(
                                    evidence.get("observed_at")
                                    or evidence.get("published_at")
                                    or evidence.get("collected_at")
                                ),
                                country_iso3=evidence.get(
                                    "country_iso3"
                                ),
                                region_key=evidence.get(
                                    "region_key"
                                ),
                                polarity=EvidencePolarity.NEUTRAL,
                                source_reliability=float(
                                    indicator.get(
                                        "default_source_reliability",
                                        70,
                                    )
                                ),
                                extraction_confidence=min(
                                    95.0,
                                    max(
                                        40.0,
                                        50.0
                                        + match.score * 45.0,
                                    ),
                                ),
                                extractor_version=(
                                    "sews-deterministic-"
                                    "normalizer-v1"
                                ),
                                attributes={
                                    "warning_problem_key": (
                                        request.problem_key
                                    ),
                                    "indicator_key": indicator_key,
                                    "match_score": match.score,
                                    "matched_terms": (
                                        match.matched_terms
                                    ),
                                },
                            )
                        )

                        evidence_object_id = normalized.id
                        evidence_object_ids[
                            evidence_cache_key
                        ] = evidence_object_id

                    confidence = min(
                        95.0,
                        max(
                            40.0,
                            50.0 + match.score * 45.0,
                        ),
                    )

                    polarity = (
                        EvidencePolarity.SUPPORTING if match.polarity == "SUPPORTING"
                        else EvidencePolarity.CONTRADICTING if match.polarity == "CONTRADICTING"
                        else EvidencePolarity.NEUTRAL
                    )
                    trend = (
                        ObservationTrend.RISING if match.polarity == "SUPPORTING"
                        else ObservationTrend.FALLING if match.polarity == "CONTRADICTING"
                        else ObservationTrend.UNKNOWN
                    )

                    link = ObservationEvidenceLinkInput(
                        evidence_object_id=evidence_object_id,
                        polarity=polarity,
                        contribution_weight=min(
                            10.0,
                            max(
                                0.1,
                                float(mapping.get("weight") or 1.0)
                                * match.score,
                            ),
                        ),
                        confidence=confidence,
                        rationale=(
                            "Ranked deterministic evidence-to-indicator "
                            "match. Matched terms: "
                            + ", ".join(match.matched_terms)
                        ),
                    )

                    obs_service.create(
                        ObservationCreateRequest(
                            indicator_key=indicator_key,
                            warning_problem_key=request.problem_key,
                            title=evidence.get("title") or indicator.get("name") or indicator_key,
                            statement=evidence.get("raw_text") or evidence.get("title") or indicator_key,
                            normalized_value=round(match.score, 6),
                            polarity=polarity,
                            trend=trend,
                            confidence=min(95.0, max(40.0, 50.0 + match.score * 45.0)),
                            observed_at=evidence.get("observed_at") or evidence.get("published_at") or evidence.get("collected_at") or datetime.now(timezone.utc),
                            country_iso3=evidence.get("country_iso3"),
                            region_key=evidence.get("region_key"),
                            status=ObservationStatus.VALIDATED,
                            generation_method="RULE_BASED",
                            generator_version="sews-ranked-matcher-v2",
                            metadata={
                                "match_score": match.score,
                                "matched_terms": match.matched_terms,
                                "score_breakdown": match.score_breakdown,
                                "mapping_rationale": mapping.get("rationale"),
                                "ranking_version": "sews-hybrid-ranking-v1",
                                "duplicate_cluster_key": (
                                    evidence.get("metadata", {}).get(
                                        "duplicate_cluster_key"
                                    )
                                ),
                                "corroboration_count": (
                                    evidence.get("metadata", {}).get(
                                        "corroboration_count",
                                        1,
                                    )
                                ),
                                "source_diversity_count": (
                                    evidence.get("metadata", {}).get(
                                        "source_diversity_count",
                                        1,
                                    )
                                ),
                                "canonical_evidence_id": evidence.get("id"),
                            },
                            evidence_links=[link],
                        )
                    )
                    item.observations_created += 1
                    response.observations_created += 1
                except Exception as exc:
                    item.error = f"{type(exc).__name__}: {exc}"

            try:
                state = state_service.recalculate(
                    IndicatorStateRecalculateRequest(
                        indicator_key=indicator_key,
                        warning_problem_key=request.problem_key,
                        lookback_days=30,
                        stale_after_hours=72,
                        minimum_evidence=2,
                    )
                )
                item.state_recalculated = True
                item.state_status = str(state.status)
                item.current_value = state.current_value
                item.confidence = state.confidence
                response.states_recalculated += 1
            except Exception as exc:
                item.error = f"{type(exc).__name__}: {exc}"

            response.indicator_results.append(item)

        response.indicators_matched = len(matched)

        previous = self._previous_assessment(request.problem_key)

        try:
            assessment = SEWSWarningScoringService(self.db).assess(
                request.problem_key,
                WarningAssessmentRequest(
                    minimum_indicator_confidence=30,
                    minimum_indicator_count=2,
                    persist=True,
                ),
            )
            response.assessment_id = str(assessment.assessment_id) if assessment.assessment_id else None
            response.assessment_probability = assessment.probability
            response.assessment_confidence = assessment.confidence_score
            response.assessment_state = str(assessment.recommended_state)

            change = SEWSMaterialChangeService().evaluate(
                previous=previous,
                current=assessment.model_dump(mode="json"),
            )
            response.material_change = change.material_change
            response.material_change_reasons = change.reasons
        except Exception as exc:
            response.status = "partial"
            response.errors.append(f"Assessment failed: {type(exc).__name__}: {exc}")
            return response

        if response.material_change and response.assessment_id:
            try:
                review = SEWSAIReviewService(self.db).review(
                    request.problem_key,
                    AIReviewRequest(
                        assessment_id=UUID(response.assessment_id),
                        model_provider="NVIDIA",
                        persist=True,
                    ),
                )
                response.ai_review_id = str(review.id) if review.id else None
            except Exception as exc:
                response.status = "partial"
                response.errors.append(f"AI review failed: {type(exc).__name__}: {exc}")

            try:
                product = StrategicIntelligenceProductService(self.db).generate(
                    request.problem_key,
                    ProductGenerationRequest(
                        assessment_id=UUID(response.assessment_id),
                        ai_review_id=UUID(response.ai_review_id) if response.ai_review_id else None,
                        product_type="SEWS_WARNING",
                        audience="EXECUTIVE_ANALYST",
                        publish_to_ledger=True,
                        publish_product=False,
                        preferred_provider="NVIDIA",
                    ),
                )
                response.product_id = str(product.product_id) if product.product_id else None
            except Exception as exc:
                response.status = "partial"
                response.errors.append(f"Product generation failed: {type(exc).__name__}: {exc}")

        return response
