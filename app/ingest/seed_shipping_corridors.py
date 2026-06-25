import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

CORRIDORS = [
    {
        "corridor_name": "Asia to Europe Corridor",
        "origin_region": "Asia-Pacific",
        "destination_region": "Europe",
        "primary_origin_ports": ["Port of Shanghai", "Port of Ningbo-Zhoushan", "Port of Singapore", "Port of Busan"],
        "primary_destination_ports": ["Port of Rotterdam", "Port of Hamburg", "Port of Antwerp-Bruges", "Port of Piraeus"],
        "transit_chokepoints": ["Strait of Malacca", "Bab el-Mandeb", "Suez Canal", "Dover Strait"],
        "primary_commodities": ["Containerized Goods", "Electronics", "Automotive", "Machinery"],
        "estimated_transit_days": 30,
        "annual_trade_value_usd": 1200000000000,
        "risk_score": 74,
        "severity": "High",
        "alternative_corridors": ["Cape of Good Hope Reroute"],
        "notes": "Core Asia-Europe container corridor exposed to Malacca, Red Sea, and Suez disruption."
    },
    {
        "corridor_name": "Gulf to Asia Energy Corridor",
        "origin_region": "Middle East & South Asia",
        "destination_region": "Asia-Pacific",
        "primary_origin_ports": ["Jebel Ali Port", "Port of Fujairah", "King Abdulaziz Port", "Hamad Port"],
        "primary_destination_ports": ["Port of Singapore", "Port of Shanghai", "Port of Busan", "Port of Tokyo"],
        "transit_chokepoints": ["Strait of Hormuz", "Strait of Malacca", "Singapore Strait"],
        "primary_commodities": ["Crude Oil", "LNG", "Refined Products", "Petrochemicals"],
        "estimated_transit_days": 18,
        "annual_trade_value_usd": 900000000000,
        "risk_score": 82,
        "severity": "Critical",
        "alternative_corridors": ["Cape of Good Hope Reroute", "Pipeline substitution limited"],
        "notes": "High-consequence energy corridor tied to Hormuz and Asian energy security."
    },
    {
        "corridor_name": "Gulf to Europe Energy Corridor",
        "origin_region": "Middle East & South Asia",
        "destination_region": "Europe",
        "primary_origin_ports": ["Port of Fujairah", "Jebel Ali Port", "Hamad Port", "Port of Salalah"],
        "primary_destination_ports": ["Port of Rotterdam", "Marseille-Fos Port", "Port of Trieste", "Port of Antwerp-Bruges"],
        "transit_chokepoints": ["Strait of Hormuz", "Bab el-Mandeb", "Suez Canal"],
        "primary_commodities": ["Crude Oil", "LNG", "Refined Products"],
        "estimated_transit_days": 22,
        "annual_trade_value_usd": 650000000000,
        "risk_score": 80,
        "severity": "Critical",
        "alternative_corridors": ["Cape of Good Hope Reroute"],
        "notes": "Energy corridor exposed to Hormuz, Red Sea security, and Suez transit constraints."
    },
    {
        "corridor_name": "China to US West Coast Corridor",
        "origin_region": "Asia-Pacific",
        "destination_region": "North America",
        "primary_origin_ports": ["Port of Shanghai", "Port of Shenzhen", "Port of Ningbo-Zhoushan", "Port of Busan"],
        "primary_destination_ports": ["Port of Los Angeles", "Port of Long Beach", "Port of Oakland", "Port of Seattle"],
        "transit_chokepoints": ["Pacific Corridor"],
        "primary_commodities": ["Containerized Goods", "Electronics", "Consumer Goods", "Automotive"],
        "estimated_transit_days": 14,
        "annual_trade_value_usd": 750000000000,
        "risk_score": 68,
        "severity": "Elevated",
        "alternative_corridors": ["Canada Pacific Gateway", "Mexico Pacific Gateway"],
        "notes": "Core trans-Pacific consumer goods and electronics corridor."
    },
    {
        "corridor_name": "Asia to US East Coast via Panama",
        "origin_region": "Asia-Pacific",
        "destination_region": "North America",
        "primary_origin_ports": ["Port of Shanghai", "Port of Singapore", "Port of Busan", "Port of Kaohsiung"],
        "primary_destination_ports": ["Port of New York and New Jersey", "Port of Savannah", "Port of Charleston", "Port of Norfolk"],
        "transit_chokepoints": ["Strait of Malacca", "Panama Canal", "Atlantic Corridor"],
        "primary_commodities": ["Containerized Goods", "Electronics", "Consumer Goods"],
        "estimated_transit_days": 32,
        "annual_trade_value_usd": 500000000000,
        "risk_score": 70,
        "severity": "High",
        "alternative_corridors": ["US West Coast + rail", "Suez route"],
        "notes": "US East Coast Asia trade corridor exposed to Panama Canal restrictions."
    },
    {
        "corridor_name": "Europe to North America Corridor",
        "origin_region": "Europe",
        "destination_region": "North America",
        "primary_origin_ports": ["Port of Rotterdam", "Port of Antwerp-Bruges", "Port of Hamburg", "Port of Valencia"],
        "primary_destination_ports": ["Port of New York and New Jersey", "Port of Norfolk", "Port of Savannah", "Port of Montreal"],
        "transit_chokepoints": ["Dover Strait", "Atlantic Corridor"],
        "primary_commodities": ["Containerized Goods", "Automotive", "Machinery", "Chemicals"],
        "estimated_transit_days": 12,
        "annual_trade_value_usd": 450000000000,
        "risk_score": 58,
        "severity": "Guarded",
        "alternative_corridors": ["Mediterranean to US Gulf", "Air cargo substitution"],
        "notes": "Mature transatlantic trade corridor with lower chokepoint risk but labor/weather exposure."
    },
    {
        "corridor_name": "South America to China Bulk Corridor",
        "origin_region": "Latin America",
        "destination_region": "Asia-Pacific",
        "primary_origin_ports": ["Port of Santos", "Port of Paranaguá", "Port of Rosario", "Port of Callao"],
        "primary_destination_ports": ["Port of Shanghai", "Port of Ningbo-Zhoushan", "Port of Guangzhou", "Port of Qingdao"],
        "transit_chokepoints": ["Cape of Good Hope", "Pacific Corridor"],
        "primary_commodities": ["Soybeans", "Iron Ore", "Copper", "Corn"],
        "estimated_transit_days": 35,
        "annual_trade_value_usd": 420000000000,
        "risk_score": 62,
        "severity": "Elevated",
        "alternative_corridors": ["Pacific direct routing", "Cape route"],
        "notes": "Bulk commodity corridor linking Latin American agriculture/mining to Chinese demand."
    },
    {
        "corridor_name": "Australia to China Bulk Corridor",
        "origin_region": "Oceania",
        "destination_region": "Asia-Pacific",
        "primary_origin_ports": ["Port Hedland", "Port of Dampier", "Port of Fremantle", "Port of Brisbane"],
        "primary_destination_ports": ["Port of Qingdao", "Port of Shanghai", "Port of Tianjin", "Port of Guangzhou"],
        "transit_chokepoints": ["Indian Ocean", "South China Sea"],
        "primary_commodities": ["Iron Ore", "LNG", "Coal", "Lithium"],
        "estimated_transit_days": 14,
        "annual_trade_value_usd": 380000000000,
        "risk_score": 60,
        "severity": "Elevated",
        "alternative_corridors": ["Japan/Korea diversion", "India diversion"],
        "notes": "Critical minerals and energy corridor connecting Australia to East Asian industry."
    },
    {
        "corridor_name": "Africa to Europe Corridor",
        "origin_region": "Africa",
        "destination_region": "Europe",
        "primary_origin_ports": ["Tanger Med", "Port of Lagos Apapa", "Port of Alexandria", "Port of Mombasa"],
        "primary_destination_ports": ["Port of Rotterdam", "Port of Antwerp-Bruges", "Port of Valencia", "Marseille-Fos Port"],
        "transit_chokepoints": ["Strait of Gibraltar", "Suez Canal", "Dover Strait"],
        "primary_commodities": ["Energy Products", "Agricultural Goods", "Containerized Goods", "Minerals"],
        "estimated_transit_days": 10,
        "annual_trade_value_usd": 250000000000,
        "risk_score": 62,
        "severity": "Elevated",
        "alternative_corridors": ["Atlantic direct routing"],
        "notes": "Africa-Europe trade corridor exposed to Mediterranean and Atlantic routing risks."
    },
    {
        "corridor_name": "Red Sea Corridor",
        "origin_region": "Middle East & South Asia",
        "destination_region": "Europe",
        "primary_origin_ports": ["Jeddah Islamic Port", "Port of Salalah", "Port of Djibouti", "Port Said"],
        "primary_destination_ports": ["Port of Piraeus", "Port of Rotterdam", "Port of Valencia", "Marseille-Fos Port"],
        "transit_chokepoints": ["Bab el-Mandeb", "Red Sea", "Suez Canal"],
        "primary_commodities": ["Containerized Goods", "Crude Oil", "LNG", "Consumer Goods"],
        "estimated_transit_days": 16,
        "annual_trade_value_usd": 1000000000000,
        "risk_score": 84,
        "severity": "Critical",
        "alternative_corridors": ["Cape of Good Hope Reroute"],
        "notes": "High-risk corridor where Red Sea security directly affects Asia-Europe flows."
    }
]

def seed_corridors():
    supabase.table("sc_shipping_corridors").upsert(
        CORRIDORS,
        on_conflict="corridor_name"
    ).execute()

    print({
        "status": "success",
        "corridors_seeded": len(CORRIDORS)
    })

if __name__ == "__main__":
    seed_corridors()
