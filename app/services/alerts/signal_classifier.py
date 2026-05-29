def classify_signal(title: str, summary: str = "") -> list[str]:
    text = f"{title} {summary}".lower()
    domains = []

    rules = {
        "conflict": [
            "war", "military", "missile", "drill", "troop", "border",
            "attack", "airstrike", "naval", "carrier", "invasion", "clash"
        ],
        "supply_chain": [
            "shipping", "port", "semiconductor", "supply chain", "strait",
            "chokepoint", "container", "logistics", "export delay", "reroute"
        ],
        "energy": [
            "oil", "gas", "lng", "energy", "pipeline", "opec", "refinery",
            "hormuz", "tanker"
        ],
        "cyber": [
            "cyber", "hack", "malware", "ransomware", "data breach",
            "ddos", "espionage"
        ],
        "geoeconomic": [
            "sanction", "tariff", "export control", "trade restriction",
            "capital control", "de-dollarization"
        ],
        "political_risk": [
            "election", "coup", "protest", "unrest", "parliament",
            "government collapse", "regime", "crisis"
        ],
    }

    for domain, keywords in rules.items():
        if any(k in text for k in keywords):
            domains.append(domain)

    return list(set(domains)) or ["geopolitical"]
