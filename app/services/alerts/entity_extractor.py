COUNTRIES = [
    "China", "Taiwan", "Iran", "Israel", "Russia", "Ukraine", "United States",
    "India", "Pakistan", "Afghanistan", "Turkey", "Saudi Arabia", "Qatar",
    "UAE", "Japan", "South Korea", "North Korea", "Germany", "France",
    "United Kingdom"
]

CHOKEPOINTS = [
    "Taiwan Strait", "Strait of Hormuz", "Bab el-Mandeb", "Suez Canal",
    "Strait of Malacca", "South China Sea", "Black Sea", "Red Sea",
    "Panama Canal"
]

SECTORS = [
    "semiconductors", "energy", "shipping", "defense", "cyber",
    "oil", "gas", "LNG", "food", "rare earths", "finance"
]


def extract_entities(title: str, summary: str = "") -> dict:
    text = f"{title} {summary}".lower()

    countries = [c for c in COUNTRIES if c.lower() in text]
    chokepoints = [c for c in CHOKEPOINTS if c.lower() in text]
    sectors = [s for s in SECTORS if s.lower() in text]

    return {
        "countries": countries,
        "chokepoints": chokepoints,
        "sectors": sectors,
        "entities": list(set(countries + chokepoints + sectors)),
    }
