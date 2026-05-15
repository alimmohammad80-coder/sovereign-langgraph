STRATEGIC_KEYWORDS = {
    "security": [
        "military", "warship", "naval", "missile", "troops", "attack",
        "taiwan", "iran", "russia", "china", "hormuz", "conflict"
    ],
    "energy": [
        "oil", "gas", "pipeline", "hormuz", "energy", "brent", "shipping"
    ],
    "economic": [
        "tariff", "trade", "sanctions", "inflation", "markets", "supply chain"
    ],
    "cyber": [
        "cyber", "hack", "malware", "ransomware", "data breach"
    ]
}


def classify_domain(title: str):
    title_lower = title.lower()

    scores = {}

    for domain, keywords in STRATEGIC_KEYWORDS.items():
        scores[domain] = sum(1 for word in keywords if word in title_lower)

    best_domain = max(scores, key=scores.get)

    if scores[best_domain] == 0:
        return "geopolitical"

    return best_domain


def calculate_importance(title: str):
    title_lower = title.lower()

    score = 30

    for keywords in STRATEGIC_KEYWORDS.values():
        for word in keywords:
            if word in title_lower:
                score += 8

    if "taiwan" in title_lower and "china" in title_lower:
        score += 15

    if "hormuz" in title_lower or "iran" in title_lower:
        score += 15

    return min(score, 100)


def sift_article(article):

    title = article.get("title_en") or article.get("title") or ""

    domain = classify_domain(title)
    importance = calculate_importance(title)

    if importance >= 75:
        risk_level = "high"
    elif importance >= 55:
        risk_level = "medium"
    else:
        risk_level = "low"

    return {
        "title": title,
        "summary": article.get("summary_en") or article.get("summary"),
        "country": article.get("source_country"),
        "domain": domain,
        "category": "geopolitical",
        "severity": importance,
        "confidence": 70,
        "risk_level": risk_level,
        "source_url": article.get("url"),
        "source_provider": article.get("source_country") or article.get("domain"),
        "raw_article_id": article.get("id")
    }
