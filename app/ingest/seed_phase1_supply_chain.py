import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

COMMODITIES = [
    ("CRUDE_OIL", "Crude Oil", "Energy", 95),
    ("LNG", "LNG", "Energy", 90),
    ("REFINED_PETROLEUM", "Refined Petroleum", "Energy", 85),
    ("URANIUM", "Uranium", "Energy", 85),
    ("COAL", "Coal", "Energy", 70),
    ("LITHIUM", "Lithium", "Critical Minerals", 92),
    ("COBALT", "Cobalt", "Critical Minerals", 88),
    ("NICKEL", "Nickel", "Critical Minerals", 86),
    ("GRAPHITE", "Graphite", "Critical Minerals", 84),
    ("RARE_EARTHS", "Rare Earth Elements", "Critical Minerals", 95),
    ("COPPER", "Copper", "Critical Minerals", 88),
    ("ALUMINUM", "Aluminum", "Industrial Materials", 79),
    ("STEEL", "Steel", "Industrial Materials", 78),
    ("CHEMICALS", "Chemicals", "Industrial Materials", 81),
    ("PLASTICS", "Plastics", "Industrial Materials", 70),
    ("WHEAT", "Wheat", "Agriculture", 80),
    ("RICE", "Rice", "Agriculture", 75),
    ("CORN", "Corn", "Agriculture", 74),
    ("SOYBEANS", "Soybeans", "Agriculture", 74),
    ("FERTILIZERS", "Fertilizers", "Agriculture", 83),
    ("SEMICONDUCTORS", "Advanced Semiconductors", "Technology", 100),
    ("MEMORY_CHIPS", "Memory Chips", "Technology", 90),
    ("SILICON_WAFERS", "Silicon Wafers", "Technology", 88),
    ("PCBS", "Printed Circuit Boards", "Technology", 82),
    ("BATTERIES", "Lithium-ion Batteries", "Energy Transition", 92),
    ("APIS", "Active Pharmaceutical Ingredients", "Healthcare", 91),
    ("MEDICAL_DEVICES", "Medical Devices", "Healthcare", 85),
    ("TITANIUM", "Titanium", "Defense", 87),
]

COMPANIES = [
    ("Apple", "Technology", "United States", "AAPL", 95),
    ("Nvidia", "Technology", "United States", "NVDA", 96),
    ("TSMC", "Technology", "Taiwan", "TSM", 100),
    ("Samsung Electronics", "Technology", "South Korea", "005930", 98),
    ("Intel", "Technology", "United States", "INTC", 88),
    ("ASML", "Technology", "Netherlands", "ASML", 94),
    ("ExxonMobil", "Energy", "United States", "XOM", 92),
    ("Chevron", "Energy", "United States", "CVX", 88),
    ("Shell", "Energy", "United Kingdom", "SHEL", 90),
    ("Saudi Aramco", "Energy", "Saudi Arabia", None, 98),
    ("QatarEnergy", "Energy", "Qatar", None, 90),
    ("Maersk", "Shipping", "Denmark", "MAERSK-B", 94),
    ("MSC", "Shipping", "Switzerland", None, 92),
    ("CMA CGM", "Shipping", "France", None, 90),
    ("COSCO", "Shipping", "China", None, 88),
    ("Hapag-Lloyd", "Shipping", "Germany", "HLAG", 85),
    ("BHP", "Mining", "Australia", "BHP", 89),
    ("Rio Tinto", "Mining", "United Kingdom", "RIO", 87),
    ("Vale", "Mining", "Brazil", "VALE", 84),
    ("Glencore", "Mining", "Switzerland", "GLEN", 90),
    ("Tesla", "Automotive", "United States", "TSLA", 85),
    ("Toyota", "Automotive", "Japan", "TM", 87),
    ("Volkswagen", "Automotive", "Germany", "VWAGY", 84),
    ("Walmart", "Retail", "United States", "WMT", 82),
    ("Amazon", "Retail", "United States", "AMZN", 85),
    ("Lockheed Martin", "Defense", "United States", "LMT", 89),
    ("RTX", "Defense", "United States", "RTX", 84),
    ("Northrop Grumman", "Defense", "United States", "NOC", 83),
]

PORTS = [
    ("Port of Singapore", "Singapore", "SGP", 1.2644, 103.8200, 98),
    ("Port of Shanghai", "China", "CHN", 31.2304, 121.4737, 96),
    ("Port of Rotterdam", "Netherlands", "NLD", 51.9244, 4.4777, 92),
    ("Jebel Ali Port", "United Arab Emirates", "ARE", 25.0118, 55.0611, 90),
    ("Port of Los Angeles", "United States", "USA", 33.7405, -118.2775, 88),
    ("Port of Kaohsiung", "Taiwan", "TWN", 22.6163, 120.3133, 91),
    ("Port of Busan", "South Korea", "KOR", 35.1028, 129.0403, 89),
    ("Port of Ningbo-Zhoushan", "China", "CHN", 29.8683, 121.5440, 93),
    ("Port of Antwerp-Bruges", "Belgium", "BEL", 51.2600, 4.4000, 87),
    ("Port of Hamburg", "Germany", "DEU", 53.5461, 9.9661, 86),
    ("Port of Shenzhen", "China", "CHN", 22.5431, 114.0579, 92),
    ("Port of Qingdao", "China", "CHN", 36.0671, 120.3826, 88),
    ("Port of Dubai", "United Arab Emirates", "ARE", 25.2048, 55.2708, 85),
    ("Port of Long Beach", "United States", "USA", 33.7701, -118.1937, 87),
    ("Port of Felixstowe", "United Kingdom", "GBR", 51.9617, 1.3511, 80),
]

def upsert_commodities():
    rows = [
        {
            "commodity_code": code,
            "commodity_name": name,
            "category": category,
            "strategic_importance": importance,
        }
        for code, name, category, importance in COMMODITIES
    ]
    supabase.table("sc_commodities").upsert(rows, on_conflict="commodity_code").execute()
    return len(rows)

def upsert_companies():
    rows = [
        {
            "company_name": name,
            "sector": sector,
            "headquarters_country": country,
            "ticker": ticker,
            "strategic_importance": importance,
        }
        for name, sector, country, ticker, importance in COMPANIES
    ]
    supabase.table("sc_companies").upsert(rows, on_conflict="company_name").execute()
    return len(rows)

def upsert_ports():
    rows = [
        {
            "port_name": name,
            "country": country,
            "iso3": iso3,
            "latitude": lat,
            "longitude": lng,
            "strategic_importance": importance,
        }
        for name, country, iso3, lat, lng, importance in PORTS
    ]
    supabase.table("sc_ports").upsert(rows, on_conflict="port_name").execute()
    return len(rows)

if __name__ == "__main__":
    print({
        "commodities": upsert_commodities(),
        "companies": upsert_companies(),
        "ports": upsert_ports(),
        "status": "phase_1_seed_complete"
    })
