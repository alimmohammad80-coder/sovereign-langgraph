def filter_relevant_articles(articles=None, country=None, sector=None, chokepoint=None, commodity=None):
    articles = articles or []

    required_terms = [
        country,
        sector,
        chokepoint,
        commodity,
        "supply chain",
        "shipping",
        "port",
        "export",
        "shortage",
        "disruption",
        "sanction",
        "semiconductor",
        "energy",
        "commodity",
        "chokepoint"
    ]

    required_terms = [str(t).lower() for t in required_terms if t]

    filtered = []

    for article in articles:
        text = " ".join([
            str(article.get("title", "")),
            str(article.get("summary", "")),
            str(article.get("domain", "")),
            str(article.get("source", ""))
        ]).lower()

        score = sum(1 for term in required_terms if term in text)

        if score >= 1:
            article["article_relevance_score"] = score
            filtered.append(article)

    return sorted(filtered, key=lambda x: x.get("article_relevance_score", 0), reverse=True)
