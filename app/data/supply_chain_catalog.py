SECTORS = {
    "energy": ["oil", "gas", "lng", "refinery", "pipeline", "electricity"],
    "semiconductors": ["chips", "advanced chips", "fabs", "packaging", "rare gases"],
    "critical_minerals": ["lithium", "cobalt", "nickel", "rare earths", "copper"],
    "food_security": ["grain", "fertilizer", "wheat", "corn", "rice"],
    "maritime": ["shipping", "ports", "tankers", "containers", "insurance"],
    "pharmaceuticals": ["active pharmaceutical ingredients", "medical devices"],
    "defense_industrial_base": ["munitions", "microelectronics", "dual-use components"]
}

CHOKEPOINTS = {
    "Strait of Hormuz": {"region": "Middle East", "base_risk": 28, "sectors": ["energy", "maritime"]},
    "Bab el-Mandeb": {"region": "Red Sea", "base_risk": 25, "sectors": ["energy", "maritime", "food_security"]},
    "Suez Canal": {"region": "Egypt/Red Sea", "base_risk": 22, "sectors": ["maritime", "energy", "food_security"]},
    "Taiwan Strait": {"region": "Indo-Pacific", "base_risk": 30, "sectors": ["semiconductors", "maritime", "defense_industrial_base"]},
    "South China Sea": {"region": "Indo-Pacific", "base_risk": 24, "sectors": ["maritime", "energy", "semiconductors"]},
    "Malacca Strait": {"region": "Southeast Asia", "base_risk": 20, "sectors": ["energy", "maritime"]},
    "Black Sea": {"region": "Europe/Eurasia", "base_risk": 26, "sectors": ["food_security", "energy", "maritime"]},
    "Panama Canal": {"region": "Americas", "base_risk": 18, "sectors": ["maritime", "food_security"]}
}

COUNTRY_EXPOSURE = {
    "China": {"sanctions": 12, "geopolitical": 18, "manufacturing_dependency": 25},
    "Taiwan": {"sanctions": 5, "geopolitical": 28, "manufacturing_dependency": 30},
    "Russia": {"sanctions": 25, "geopolitical": 22, "manufacturing_dependency": 10},
    "Iran": {"sanctions": 25, "geopolitical": 24, "manufacturing_dependency": 8},
    "United States": {"sanctions": 5, "geopolitical": 8, "manufacturing_dependency": 12},
    "India": {"sanctions": 5, "geopolitical": 12, "manufacturing_dependency": 16},
    "Saudi Arabia": {"sanctions": 4, "geopolitical": 16, "manufacturing_dependency": 12},
    "Ukraine": {"sanctions": 8, "geopolitical": 26, "manufacturing_dependency": 10}
}
