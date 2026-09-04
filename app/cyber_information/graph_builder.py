from __future__ import annotations

from uuid import uuid4

from .models import (
    EntityType,
    EvidenceStatus,
    IntelligenceEntity,
    IntelligenceRelationship,
    RelationshipType,
)
from .phase3_models import CyberIncident


class CyberGraphBuilder:
    """Convert Phase 3 intelligence objects into Phase 1 graph entities/relationships."""

    def incident_graph(self, incident: CyberIncident) -> dict:
        incident_entity = IntelligenceEntity(
            id=incident.id,
            entity_type=EntityType.INCIDENT,
            name=incident.title,
            attributes={
                "incident_type": incident.incident_type.value,
                "severity_score": incident.severity_score,
                "source": incident.source,
                "cves": incident.cves,
                "attack_techniques": incident.attack_techniques,
            },
        )
        entities = [incident_entity]
        relationships = []

        for cve in incident.cves:
            vuln = IntelligenceEntity(entity_type=EntityType.VULNERABILITY, name=cve)
            entities.append(vuln)
            relationships.append(IntelligenceRelationship(
                id=uuid4(),
                source_entity_id=incident.id,
                target_entity_id=vuln.id,
                relationship_type=RelationshipType.EXPLOITS,
                evidence_status=incident.evidence_status,
                confidence=incident.confidence,
                provenance=incident.provenance,
            ))

        for actor_name in incident.suspected_actors:
            actor = IntelligenceEntity(entity_type=EntityType.THREAT_ACTOR, name=actor_name)
            entities.append(actor)
            relationships.append(IntelligenceRelationship(
                id=uuid4(),
                source_entity_id=incident.id,
                target_entity_id=actor.id,
                relationship_type=RelationshipType.ATTRIBUTED_TO,
                evidence_status=EvidenceStatus.ASSESSED,
                confidence=incident.confidence,
                provenance=incident.provenance,
            ))

        for campaign_name in incident.campaign_names:
            campaign = IntelligenceEntity(entity_type=EntityType.CAMPAIGN, name=campaign_name)
            entities.append(campaign)
            relationships.append(IntelligenceRelationship(
                id=uuid4(),
                source_entity_id=incident.id,
                target_entity_id=campaign.id,
                relationship_type=RelationshipType.PART_OF,
                evidence_status=incident.evidence_status,
                confidence=incident.confidence,
                provenance=incident.provenance,
            ))

        for target_name in incident.target_names:
            target = IntelligenceEntity(entity_type=EntityType.INFRASTRUCTURE, name=target_name)
            entities.append(target)
            relationships.append(IntelligenceRelationship(
                id=uuid4(),
                source_entity_id=incident.id,
                target_entity_id=target.id,
                relationship_type=RelationshipType.AFFECTS,
                evidence_status=incident.evidence_status,
                confidence=incident.confidence,
                provenance=incident.provenance,
            ))

        return {
            "entities": [e.model_dump(mode="json") for e in entities],
            "relationships": [r.model_dump(mode="json") for r in relationships],
        }
