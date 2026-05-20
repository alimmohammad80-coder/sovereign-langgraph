def extract_supply_chain_signals(live_data):
    articles = live_data.get("gdelt_news", [])

    signals = {
        "port_disruption": False,
        "military_escalation": False,
        "sanctions_expansion": False,
        "cyber_disruption": False,
        "price_spike": False,
        "insurance_premium_rise": False,
        "export_controls": False,
        "supplier_concentration": False
    }

    extracted = []

    keywords = {
        "port_disruption": ["port", "delay", "congestion", "blockade", "closure"],
        "military_escalation": ["military", "missile", "naval", "warship", "attack", "strike"],
        "sanctions_expansion": ["sanction", "blacklist", "restriction"],
        "cyber_disruption": ["cyber", "hack", "ransomware"],
        "price_spike": ["price", "surge", "spike", "shortage"],
        "insurance_premium_rise": ["insurance", "premium", "war risk"],
        "export_controls": ["export control", "ban", "license", "restriction"],
        "supplier_concentration": ["dependency", "shortage", "supplier", "bottleneck"]
    }

    for article in articles:
        text = f"{article.get('title', '')} {article.get('summary', '')}".lower()

        for signal_name, words in keywords.items():
            if any(word in text for word in words):
                signals[signal_name] = True
                extracted.append({
                    "signal_type": signal_name,
                    "source": article.get("source", "GDELT"),
                    "title": article.get("title"),
                    "url": article.get("url"),
                    "published_at": article.get("published_at"),
                    "confidence": "medium"
                })

    return {
        "signals": signals,
        "extracted_signals": extracted
    }
