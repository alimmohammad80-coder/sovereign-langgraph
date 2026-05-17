ENTITY_RELATIONSHIPS = {
    "Taiwan": {
        "supply_chain": [
            "Semiconductors",
            "TSMC",
            "Shipping",
            "Electronics"
        ],
        "financial_risk": [
            "Asian Markets",
            "Global Equities",
            "Insurance"
        ],
        "military": [
            "PLA",
            "USINDOPACOM",
            "Japan"
        ],
        "cyber": [
            "Telecom",
            "Critical Infrastructure"
        ]
    },

    "Red Sea": {
        "supply_chain": [
            "Suez Canal",
            "Shipping",
            "Energy Transit"
        ],
        "financial_risk": [
            "Oil Markets",
            "Freight Costs"
        ],
        "military": [
            "CENTCOM",
            "Houthis",
            "Iran"
        ]
    }
}


def get_related_entities(entity: str):
    return ENTITY_RELATIONSHIPS.get(entity, {})
