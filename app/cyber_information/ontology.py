from __future__ import annotations

from .models import EntityType, RelationshipType


ONTOLOGY_VERSION = "cyber-info-ontology-v1"

ENTITY_DEFINITIONS = {
    EntityType.STATE: "Recognized state or governing authority relevant to an operation.",
    EntityType.THREAT_ACTOR: "Named or tracked cyber/information threat actor or cluster.",
    EntityType.ORGANIZATION: "Public, private, military, civil-society, or other organization.",
    EntityType.PERSON: "Person relevant to a campaign, incident, narrative, or attribution.",
    EntityType.CAMPAIGN: "Linked set of cyber, information, or hybrid activities.",
    EntityType.MALWARE: "Malware family, tool, implant, or malicious software capability.",
    EntityType.VULNERABILITY: "Tracked software or hardware vulnerability.",
    EntityType.INFRASTRUCTURE: "Physical or digital infrastructure asset or system.",
    EntityType.SECTOR: "Economic or critical-infrastructure sector.",
    EntityType.NARRATIVE: "Claim, theme, frame, or narrative cluster under observation.",
    EntityType.PLATFORM: "Information or communications platform relevant to propagation.",
    EntityType.LOCATION: "Geographic location relevant to observed activity.",
    EntityType.INCIDENT: "Discrete cyber, information, or hybrid operational event.",
}

RELATIONSHIP_DEFINITIONS = {
    RelationshipType.ATTRIBUTED_TO: "Analytic attribution; must carry evidence status and confidence.",
    RelationshipType.TARGETS: "Actor, campaign, malware, or narrative targets an entity or sector.",
    RelationshipType.USES: "Actor or campaign uses a capability, infrastructure, technique, or narrative.",
    RelationshipType.EXPLOITS: "Actor, campaign, or malware exploits a vulnerability.",
    RelationshipType.AMPLIFIES: "Entity increases distribution or visibility of a narrative.",
    RelationshipType.ORIGINATES_FROM: "Observed or assessed origin relationship.",
    RelationshipType.AFFECTS: "Activity materially affects an entity, location, sector, or system.",
    RelationshipType.PART_OF: "Entity or incident is part of a larger campaign or operation.",
    RelationshipType.CORRELATED_WITH: "Evidence-supported correlation without asserting causation.",
    RelationshipType.SUPPORTS: "Evidence or entity supports an analytic proposition.",
    RelationshipType.CONTRADICTS: "Evidence or entity contradicts an analytic proposition.",
}


def ontology_manifest() -> dict:
    return {
        "version": ONTOLOGY_VERSION,
        "entity_types": {key.value: value for key, value in ENTITY_DEFINITIONS.items()},
        "relationship_types": {key.value: value for key, value in RELATIONSHIP_DEFINITIONS.items()},
        "analytic_rules": [
            "Observed facts, inference, and assessment must remain distinguishable.",
            "Attribution requires explicit confidence and provenance.",
            "Confidence must not be substituted for severity or forecast probability.",
            "Correlation must not be represented as causation without supporting evidence.",
            "Every material analytic object must retain source provenance.",
        ],
    }
