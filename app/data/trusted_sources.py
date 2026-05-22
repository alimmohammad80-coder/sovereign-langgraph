TIER1_SOURCES = [
    "reuters", "associated press", "ap news", "bbc", "financial times",
    "bloomberg", "wall street journal", "nikkei", "the economist",
    "al jazeera", "politico", "foreign policy"
]

TIER2_SOURCES = [
    "csis", "center for strategic and international studies",
    "council on foreign relations", "cfr", "institute for the study of war",
    "isw", "rand", "brookings", "carnegie", "rusi", "iiss",
    "defense one", "breaking defense", "war on the rocks",
    "maritime executive", "lloyd's list", "oilprice", "eia", "opec"
]

BLOCKED_SOURCES = [
    "hokanews", "specialeurasia", "dominotheory", "ntd news",
    "times of india", "blogspot", "substack"
]

TRUSTED_SOURCES = TIER1_SOURCES + TIER2_SOURCES

DOMAIN_KEYWORDS = {
    "chokepoint": ["hormuz", "bab el-mandeb", "suez", "taiwan strait", "malacca", "panama canal", "red sea"],
    "supply_chain": ["semiconductor", "chips", "shipping", "supply chain", "ports", "rare earth", "critical minerals"],
    "conflict": ["strike", "clash", "war", "missile", "military", "border", "attack", "mobilization", "drill", "exercise"],
    "energy": ["oil", "gas", "lng", "pipeline", "refinery", "opec", "energy", "tanker"],
    "strategic": ["sanctions", "cyberattack", "election", "coup", "diplomatic", "export controls"]
}
