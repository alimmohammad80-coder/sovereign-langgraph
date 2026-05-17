from app.intelligence.entities.entity_mapper import (
    get_related_entities
)


def generate_cross_domain_impacts(entity: str):
    relationships = get_related_entities(entity)

    impacts = []

    for domain, related in relationships.items():

        impacts.append({
            "domain": domain,
            "related_entities": related,
            "impact_summary":
                f"{entity} developments may affect "
                f"{', '.join(related)}."
        })

    return impacts
