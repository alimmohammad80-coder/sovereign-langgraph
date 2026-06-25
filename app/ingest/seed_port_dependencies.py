import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

PORT_CHOKEPOINT_DEPENDENCIES = [
    # Asia-Pacific
    ("Port of Shanghai", "Taiwan Strait", 70, "East Asia export route"),
    ("Port of Shanghai", "Strait of Malacca", 45, "Asia-Europe / Asia-Middle East routing"),
    ("Port of Singapore", "Strait of Malacca", 95, "Core transshipment dependency"),
    ("Port of Singapore", "Singapore Strait", 95, "Immediate port approach"),
    ("Port of Ningbo-Zhoushan", "Taiwan Strait", 65, "East China Sea route exposure"),
    ("Port of Shenzhen", "South China Sea", 80, "South China export corridor"),
    ("Port of Guangzhou", "South China Sea", 75, "Pearl River Delta export exposure"),
    ("Port of Busan", "Korea Strait", 75, "Northeast Asia route exposure"),
    ("Port of Kaohsiung", "Taiwan Strait", 95, "Taiwan export route exposure"),
    ("Port Klang", "Strait of Malacca", 90, "Malaysia container corridor"),
    ("Tanjung Pelepas", "Strait of Malacca", 95, "Transshipment dependency"),
    ("Tanjung Priok", "Strait of Malacca", 60, "Indonesia-Europe/Asia routing"),
    ("Laem Chabang Port", "Strait of Malacca", 65, "Thailand export routing"),
    ("Port of Ho Chi Minh City", "South China Sea", 80, "Vietnam export exposure"),
    ("Port of Manila", "South China Sea", 85, "Philippines import dependency"),

    # Middle East & South Asia
    ("Jebel Ali Port", "Strait of Hormuz", 95, "Gulf transshipment and energy exposure"),
    ("Khalifa Port", "Strait of Hormuz", 85, "UAE industrial and container route"),
    ("Port of Fujairah", "Strait of Hormuz", 70, "Energy logistics and bunkering exposure"),
    ("Jeddah Islamic Port", "Bab el-Mandeb", 75, "Red Sea route exposure"),
    ("Jeddah Islamic Port", "Suez Canal", 70, "Asia-Europe route exposure"),
    ("King Abdulaziz Port", "Strait of Hormuz", 85, "Saudi Gulf route dependency"),
    ("Hamad Port", "Strait of Hormuz", 90, "Qatar maritime dependency"),
    ("Port of Salalah", "Bab el-Mandeb", 65, "Red Sea rerouting relevance"),
    ("Bandar Abbas", "Strait of Hormuz", 95, "Iranian Gulf gateway"),
    ("Chabahar Port", "Arabian Sea", 70, "Indian Ocean access"),
    ("Port of Karachi", "Arabian Sea", 75, "Pakistan trade gateway"),
    ("Port Qasim", "Arabian Sea", 75, "Pakistan energy and industrial corridor"),
    ("Gwadar Port", "Arabian Sea", 80, "Strategic corridor exposure"),
    ("Mundra Port", "Strait of Hormuz", 55, "Energy import exposure"),
    ("Jawaharlal Nehru Port", "Suez Canal", 55, "India-Europe container routing"),
    ("Port of Colombo", "Strait of Malacca", 65, "Indian Ocean transshipment"),
    ("Port of Colombo", "Suez Canal", 55, "Asia-Europe routing"),

    # Europe
    ("Port of Rotterdam", "Suez Canal", 60, "Asia-Europe container and energy route"),
    ("Port of Rotterdam", "Bab el-Mandeb", 45, "Red Sea exposure"),
    ("Port of Rotterdam", "Dover Strait", 70, "Northwest Europe gateway"),
    ("Port of Antwerp-Bruges", "Dover Strait", 65, "Northwest Europe gateway"),
    ("Port of Antwerp-Bruges", "Suez Canal", 50, "Asia-Europe trade route"),
    ("Port of Hamburg", "Danish Straits", 55, "Baltic/North Sea route exposure"),
    ("Port of Felixstowe", "Dover Strait", 80, "UK Channel route exposure"),
    ("Marseille-Fos Port", "Suez Canal", 55, "Mediterranean-Asia route"),
    ("Port of Valencia", "Strait of Gibraltar", 60, "Mediterranean-Atlantic routing"),
    ("Port of Algeciras", "Strait of Gibraltar", 90, "Immediate chokepoint exposure"),
    ("Port of Piraeus", "Suez Canal", 70, "Eastern Mediterranean Asia-Europe gateway"),
    ("Port of Istanbul Ambarli", "Bosporus", 90, "Turkish Straits dependency"),
    ("Port of Constanta", "Bosporus", 85, "Black Sea access"),
    ("Port of Gdansk", "Danish Straits", 65, "Baltic access"),

    # Africa
    ("Port Said", "Suez Canal", 95, "Immediate Suez gateway"),
    ("Port Said", "Bab el-Mandeb", 60, "Red Sea exposure"),
    ("Tanger Med", "Strait of Gibraltar", 90, "Immediate Gibraltar exposure"),
    ("Port of Lagos Apapa", "Gulf of Guinea", 80, "West Africa security and congestion exposure"),
    ("Port of Durban", "Cape of Good Hope", 75, "Southern Africa route exposure"),
    ("Port of Cape Town", "Cape of Good Hope", 85, "Immediate Cape route exposure"),
    ("Port of Mombasa", "Bab el-Mandeb", 55, "East Africa-Red Sea routing"),
    ("Port of Djibouti", "Bab el-Mandeb", 95, "Immediate chokepoint exposure"),
    ("Port of Maputo", "Mozambique Channel", 70, "Southern Africa corridor"),

    # North America
    ("Port of Los Angeles", "Pacific Corridor", 85, "Trans-Pacific trade route"),
    ("Port of Long Beach", "Pacific Corridor", 85, "Trans-Pacific trade route"),
    ("Port of Houston", "Gulf of Mexico", 80, "Gulf Coast energy corridor"),
    ("Port of New Orleans", "Mississippi River", 90, "Inland grain/export corridor"),
    ("Port of New York and New Jersey", "Atlantic Corridor", 75, "East Coast trade route"),
    ("Port of Savannah", "Panama Canal", 55, "Asia-US East Coast route"),
    ("Port of Vancouver", "Pacific Corridor", 80, "Canada-Asia commodity route"),
    ("Port of Manzanillo Mexico", "Pacific Corridor", 75, "Mexico-Asia route"),
    ("Port of Veracruz", "Gulf of Mexico", 70, "Mexico Gulf route"),

    # Latin America
    ("Port of Santos", "Atlantic Corridor", 70, "Brazil export corridor"),
    ("Port of Callao", "Pacific Corridor", 75, "Peru Pacific export route"),
    ("Port of Cartagena Colombia", "Panama Canal", 70, "Caribbean/Panama proximity"),
    ("Port of Colón", "Panama Canal", 95, "Immediate canal dependency"),
    ("Port of Balboa", "Panama Canal", 95, "Immediate canal dependency"),
    ("Port of Buenos Aires", "Atlantic Corridor", 70, "Argentina export corridor"),

    # Oceania
    ("Port of Melbourne", "Pacific Corridor", 75, "Australia-Asia container route"),
    ("Port Botany", "Pacific Corridor", 75, "Australia-Asia container route"),
    ("Port Hedland", "Indian Ocean", 80, "Iron ore export route"),
    ("Port of Dampier", "Indian Ocean", 80, "LNG and iron ore route"),
    ("Port of Tauranga", "Pacific Corridor", 70, "New Zealand export route"),
]

def seed_dependencies():
    rows = [
        {
            "port_name": port,
            "dependency_type": "chokepoint",
            "dependency_name": chokepoint,
            "dependency_weight": weight,
            "category": "maritime_route",
            "notes": notes,
        }
        for port, chokepoint, weight, notes in PORT_CHOKEPOINT_DEPENDENCIES
    ]

    supabase.table("sc_port_dependencies").upsert(
        rows,
        on_conflict="port_name,dependency_type,dependency_name"
    ).execute()

    print({
        "status": "success",
        "dependencies_seeded": len(rows)
    })

if __name__ == "__main__":
    seed_dependencies()
