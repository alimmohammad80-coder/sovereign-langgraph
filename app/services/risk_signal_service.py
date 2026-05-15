from app.services.supabase_service import supabase
from app.services.sifter_service import sift_article

KEYWORDS = {
    "security": [
        "military",
        "missile",
        "navy",
        "air force",
        "war",
        "taiwan",
        "iran",
        "china",
        "russia",
        "nuclear",
        "attack",
        "troops",
        "sanctions"
    ],
    "energy": [
        "oil",
        "gas",
        "pipeline",
        "hormuz",
        "energy",
        "shipping"
    ]
}


def calculate_severity(title):

    title_lower = title.lower()

    score = 20

    for category in KEYWORDS.values():
        for keyword in category:
            if keyword in title_lower:
                score += 10

    if score > 100:
        score = 100

    return score


def generate_risk_signals(limit=20):

    articles = (
        supabase
        .table("raw_gdelt")
        .select("*")
        .order("created_at", desc=True)
        .limit(100)
        .execute()
    )

    inserted = []

    for article in articles.data:

        title = article.get("title", "")

        severity = calculate_severity(title)
        
        signal = sift_article(article)        

        if signal["severity"] < 55:
            continue

        result = (
            supabase
            .table("risk_signals")
            .insert(signal)
            .execute()
        )

        inserted.append(result.data)

    return {
        "status": "success",
        "signals_created": len(inserted)
    }
