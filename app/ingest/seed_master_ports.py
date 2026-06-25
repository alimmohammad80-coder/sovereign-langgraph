import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

ASIA_PACIFIC_PORTS = [
    {
        "port_name": "Port of Shanghai",
        "country": "China",
        "iso3": "CHN",
        "region": "Asia-Pacific",
        "latitude": 31.2304,
        "longitude": 121.4737,
        "port_type": "container",
        "strategic_importance": 98,
        "baseline_risk_score": 72,
        "risk_score": 72,
        "severity": "High",
        "dominant_driver": "High container throughput and Taiwan Strait exposure",
        "linked_chokepoints": ["Taiwan Strait", "Strait of Malacca"],
        "primary_commodities": ["Advanced Semiconductors", "Electronics", "Containerized Goods"]
    },
    {
        "port_name": "Port of Singapore",
        "country": "Singapore",
        "iso3": "SGP",
        "region": "Asia-Pacific",
        "latitude": 1.2644,
        "longitude": 103.8200,
        "port_type": "transshipment",
        "strategic_importance": 99,
        "baseline_risk_score": 76,
        "risk_score": 76,
        "severity": "High",
        "dominant_driver": "Global transshipment hub and Malacca chokepoint dependency",
        "linked_chokepoints": ["Strait of Malacca", "Singapore Strait"],
        "primary_commodities": ["Containerized Goods", "Crude Oil", "LNG", "Electronics"]
    },
    {
        "port_name": "Port of Ningbo-Zhoushan",
        "country": "China",
        "iso3": "CHN",
        "region": "Asia-Pacific",
        "latitude": 29.8683,
        "longitude": 121.5440,
        "port_type": "container/bulk",
        "strategic_importance": 96,
        "baseline_risk_score": 70,
        "risk_score": 70,
        "severity": "High",
        "dominant_driver": "China export concentration and East China Sea exposure",
        "linked_chokepoints": ["Taiwan Strait", "Strait of Malacca"],
        "primary_commodities": ["Containerized Goods", "Industrial Goods", "Chemicals"]
    },
    {
        "port_name": "Port of Shenzhen",
        "country": "China",
        "iso3": "CHN",
        "region": "Asia-Pacific",
        "latitude": 22.5431,
        "longitude": 114.0579,
        "port_type": "container",
        "strategic_importance": 95,
        "baseline_risk_score": 69,
        "risk_score": 69,
        "severity": "Elevated",
        "dominant_driver": "Electronics export concentration and South China Sea exposure",
        "linked_chokepoints": ["South China Sea", "Strait of Malacca"],
        "primary_commodities": ["Electronics", "Advanced Semiconductors", "Consumer Goods"]
    },
    {
        "port_name": "Port of Guangzhou",
        "country": "China",
        "iso3": "CHN",
        "region": "Asia-Pacific",
        "latitude": 23.1291,
        "longitude": 113.2644,
        "port_type": "container/bulk",
        "strategic_importance": 90,
        "baseline_risk_score": 66,
        "risk_score": 66,
        "severity": "Elevated",
        "dominant_driver": "Pearl River Delta manufacturing exposure",
        "linked_chokepoints": ["South China Sea", "Strait of Malacca"],
        "primary_commodities": ["Industrial Goods", "Consumer Goods", "Chemicals"]
    },
    {
        "port_name": "Port of Qingdao",
        "country": "China",
        "iso3": "CHN",
        "region": "Asia-Pacific",
        "latitude": 36.0671,
        "longitude": 120.3826,
        "port_type": "container/bulk",
        "strategic_importance": 89,
        "baseline_risk_score": 64,
        "risk_score": 64,
        "severity": "Elevated",
        "dominant_driver": "North China export and bulk commodity exposure",
        "linked_chokepoints": ["Yellow Sea", "Taiwan Strait"],
        "primary_commodities": ["Containerized Goods", "Iron Ore", "Chemicals"]
    },
    {
        "port_name": "Port of Tianjin",
        "country": "China",
        "iso3": "CHN",
        "region": "Asia-Pacific",
        "latitude": 39.0211,
        "longitude": 117.7382,
        "port_type": "container/bulk",
        "strategic_importance": 88,
        "baseline_risk_score": 63,
        "risk_score": 63,
        "severity": "Elevated",
        "dominant_driver": "Beijing-Tianjin industrial corridor exposure",
        "linked_chokepoints": ["Bohai Sea", "Yellow Sea"],
        "primary_commodities": ["Industrial Goods", "Automotive", "Steel"]
    },
    {
        "port_name": "Port of Busan",
        "country": "South Korea",
        "iso3": "KOR",
        "region": "Asia-Pacific",
        "latitude": 35.1028,
        "longitude": 129.0403,
        "port_type": "container",
        "strategic_importance": 94,
        "baseline_risk_score": 67,
        "risk_score": 67,
        "severity": "Elevated",
        "dominant_driver": "Korean export hub and Northeast Asia security exposure",
        "linked_chokepoints": ["Korea Strait", "Taiwan Strait"],
        "primary_commodities": ["Electronics", "Automotive", "Advanced Semiconductors"]
    },
    {
        "port_name": "Port of Kaohsiung",
        "country": "Taiwan",
        "iso3": "TWN",
        "region": "Asia-Pacific",
        "latitude": 22.6163,
        "longitude": 120.3133,
        "port_type": "container",
        "strategic_importance": 95,
        "baseline_risk_score": 78,
        "risk_score": 78,
        "severity": "High",
        "dominant_driver": "Taiwan semiconductor export exposure",
        "linked_chokepoints": ["Taiwan Strait"],
        "primary_commodities": ["Advanced Semiconductors", "Electronics", "Containerized Goods"]
    },
    {
        "port_name": "Port of Hong Kong",
        "country": "China",
        "iso3": "CHN",
        "region": "Asia-Pacific",
        "latitude": 22.3193,
        "longitude": 114.1694,
        "port_type": "container",
        "strategic_importance": 84,
        "baseline_risk_score": 62,
        "risk_score": 62,
        "severity": "Elevated",
        "dominant_driver": "Regional transshipment and South China Sea exposure",
        "linked_chokepoints": ["South China Sea", "Strait of Malacca"],
        "primary_commodities": ["Containerized Goods", "Electronics", "Consumer Goods"]
    },
    {
        "port_name": "Port of Tokyo",
        "country": "Japan",
        "iso3": "JPN",
        "region": "Asia-Pacific",
        "latitude": 35.6272,
        "longitude": 139.7767,
        "port_type": "container",
        "strategic_importance": 83,
        "baseline_risk_score": 58,
        "risk_score": 58,
        "severity": "Guarded",
        "dominant_driver": "Japanese industrial import/export exposure",
        "linked_chokepoints": ["Tokyo Bay", "Taiwan Strait"],
        "primary_commodities": ["Automotive", "Electronics", "Industrial Goods"]
    },
    {
        "port_name": "Port of Yokohama",
        "country": "Japan",
        "iso3": "JPN",
        "region": "Asia-Pacific",
        "latitude": 35.4437,
        "longitude": 139.6380,
        "port_type": "container",
        "strategic_importance": 82,
        "baseline_risk_score": 57,
        "risk_score": 57,
        "severity": "Guarded",
        "dominant_driver": "Automotive and industrial goods exposure",
        "linked_chokepoints": ["Tokyo Bay", "Taiwan Strait"],
        "primary_commodities": ["Automotive", "Industrial Goods", "Electronics"]
    },
    {
        "port_name": "Port of Laem Chabang",
        "country": "Thailand",
        "iso3": "THA",
        "region": "Asia-Pacific",
        "latitude": 13.0827,
        "longitude": 100.8830,
        "port_type": "container",
        "strategic_importance": 78,
        "baseline_risk_score": 56,
        "risk_score": 56,
        "severity": "Guarded",
        "dominant_driver": "Southeast Asia manufacturing and automotive exposure",
        "linked_chokepoints": ["Strait of Malacca", "South China Sea"],
        "primary_commodities": ["Automotive", "Electronics", "Containerized Goods"]
    },
    {
        "port_name": "Port Klang",
        "country": "Malaysia",
        "iso3": "MYS",
        "region": "Asia-Pacific",
        "latitude": 3.0000,
        "longitude": 101.4000,
        "port_type": "container",
        "strategic_importance": 87,
        "baseline_risk_score": 64,
        "risk_score": 64,
        "severity": "Elevated",
        "dominant_driver": "Malacca-adjacent container and energy exposure",
        "linked_chokepoints": ["Strait of Malacca"],
        "primary_commodities": ["Containerized Goods", "Electronics", "Crude Oil"]
    },
    {
        "port_name": "Tanjung Pelepas",
        "country": "Malaysia",
        "iso3": "MYS",
        "region": "Asia-Pacific",
        "latitude": 1.3644,
        "longitude": 103.5489,
        "port_type": "transshipment",
        "strategic_importance": 86,
        "baseline_risk_score": 65,
        "risk_score": 65,
        "severity": "Elevated",
        "dominant_driver": "Transshipment hub near Singapore and Malacca",
        "linked_chokepoints": ["Strait of Malacca", "Singapore Strait"],
        "primary_commodities": ["Containerized Goods", "Electronics", "Consumer Goods"]
    },
    {
        "port_name": "Tanjung Priok",
        "country": "Indonesia",
        "iso3": "IDN",
        "region": "Asia-Pacific",
        "latitude": -6.1045,
        "longitude": 106.8800,
        "port_type": "container",
        "strategic_importance": 79,
        "baseline_risk_score": 58,
        "risk_score": 58,
        "severity": "Guarded",
        "dominant_driver": "Indonesia import/export and archipelagic route exposure",
        "linked_chokepoints": ["Sunda Strait", "Lombok Strait", "Strait of Malacca"],
        "primary_commodities": ["Coal", "Palm Oil", "Containerized Goods"]
    },
    {
        "port_name": "Port of Manila",
        "country": "Philippines",
        "iso3": "PHL",
        "region": "Asia-Pacific",
        "latitude": 14.5833,
        "longitude": 120.9667,
        "port_type": "container",
        "strategic_importance": 75,
        "baseline_risk_score": 60,
        "risk_score": 60,
        "severity": "Elevated",
        "dominant_driver": "South China Sea exposure and island import dependency",
        "linked_chokepoints": ["South China Sea"],
        "primary_commodities": ["Containerized Goods", "Food", "Energy Products"]
    }
]

def seed_ports():
    result = supabase.table("sc_master_ports").upsert(
        ASIA_PACIFIC_PORTS,
        on_conflict="port_name"
    ).execute()

    print({
        "status": "success",
        "ports_seeded": len(ASIA_PACIFIC_PORTS)
    })

if __name__ == "__main__":
    seed_ports()

SOUTHEAST_ASIA_PORTS = [
    {
        "port_name": "Port Klang",
        "country": "Malaysia",
        "iso3": "MYS",
        "region": "Southeast Asia",
        "latitude": 3.0000,
        "longitude": 101.4000,
        "port_type": "container",
        "strategic_importance": 87,
        "baseline_risk_score": 64,
        "risk_score": 64,
        "severity": "Elevated",
        "dominant_driver": "Malacca-adjacent container and energy exposure",
        "linked_chokepoints": ["Strait of Malacca"],
        "primary_commodities": ["Containerized Goods", "Electronics", "Crude Oil"]
    },
    {
        "port_name": "Tanjung Pelepas",
        "country": "Malaysia",
        "iso3": "MYS",
        "region": "Southeast Asia",
        "latitude": 1.3644,
        "longitude": 103.5489,
        "port_type": "transshipment",
        "strategic_importance": 86,
        "baseline_risk_score": 65,
        "risk_score": 65,
        "severity": "Elevated",
        "dominant_driver": "Transshipment hub near Singapore and Malacca",
        "linked_chokepoints": ["Strait of Malacca", "Singapore Strait"],
        "primary_commodities": ["Containerized Goods", "Electronics", "Consumer Goods"]
    },
    {
        "port_name": "Tanjung Priok",
        "country": "Indonesia",
        "iso3": "IDN",
        "region": "Southeast Asia",
        "latitude": -6.1045,
        "longitude": 106.8800,
        "port_type": "container",
        "strategic_importance": 79,
        "baseline_risk_score": 58,
        "risk_score": 58,
        "severity": "Guarded",
        "dominant_driver": "Indonesia import/export and archipelagic route exposure",
        "linked_chokepoints": ["Sunda Strait", "Lombok Strait", "Strait of Malacca"],
        "primary_commodities": ["Coal", "Palm Oil", "Containerized Goods"]
    },
    {
        "port_name": "Port of Surabaya",
        "country": "Indonesia",
        "iso3": "IDN",
        "region": "Southeast Asia",
        "latitude": -7.2030,
        "longitude": 112.7340,
        "port_type": "container/bulk",
        "strategic_importance": 72,
        "baseline_risk_score": 55,
        "risk_score": 55,
        "severity": "Guarded",
        "dominant_driver": "Eastern Indonesia logistics and archipelagic route exposure",
        "linked_chokepoints": ["Lombok Strait", "Makassar Strait"],
        "primary_commodities": ["Containerized Goods", "Coal", "Food"]
    },
    {
        "port_name": "Port of Belawan",
        "country": "Indonesia",
        "iso3": "IDN",
        "region": "Southeast Asia",
        "latitude": 3.7857,
        "longitude": 98.6832,
        "port_type": "bulk/container",
        "strategic_importance": 68,
        "baseline_risk_score": 57,
        "risk_score": 57,
        "severity": "Guarded",
        "dominant_driver": "Sumatra export route near Malacca Strait",
        "linked_chokepoints": ["Strait of Malacca"],
        "primary_commodities": ["Palm Oil", "Rubber", "Containerized Goods"]
    },
    {
        "port_name": "Laem Chabang Port",
        "country": "Thailand",
        "iso3": "THA",
        "region": "Southeast Asia",
        "latitude": 13.0827,
        "longitude": 100.8830,
        "port_type": "container",
        "strategic_importance": 78,
        "baseline_risk_score": 56,
        "risk_score": 56,
        "severity": "Guarded",
        "dominant_driver": "Thailand manufacturing and automotive export exposure",
        "linked_chokepoints": ["Strait of Malacca", "South China Sea"],
        "primary_commodities": ["Automotive", "Electronics", "Containerized Goods"]
    },
    {
        "port_name": "Port of Ho Chi Minh City",
        "country": "Vietnam",
        "iso3": "VNM",
        "region": "Southeast Asia",
        "latitude": 10.7769,
        "longitude": 106.7009,
        "port_type": "container",
        "strategic_importance": 80,
        "baseline_risk_score": 59,
        "risk_score": 59,
        "severity": "Guarded",
        "dominant_driver": "Vietnam manufacturing export growth and South China Sea exposure",
        "linked_chokepoints": ["South China Sea", "Strait of Malacca"],
        "primary_commodities": ["Electronics", "Textiles", "Containerized Goods"]
    },
    {
        "port_name": "Port of Hai Phong",
        "country": "Vietnam",
        "iso3": "VNM",
        "region": "Southeast Asia",
        "latitude": 20.8449,
        "longitude": 106.6881,
        "port_type": "container",
        "strategic_importance": 76,
        "baseline_risk_score": 58,
        "risk_score": 58,
        "severity": "Guarded",
        "dominant_driver": "Northern Vietnam manufacturing and China-adjacent exposure",
        "linked_chokepoints": ["South China Sea"],
        "primary_commodities": ["Electronics", "Machinery", "Containerized Goods"]
    },
    {
        "port_name": "Port of Manila",
        "country": "Philippines",
        "iso3": "PHL",
        "region": "Southeast Asia",
        "latitude": 14.5833,
        "longitude": 120.9667,
        "port_type": "container",
        "strategic_importance": 75,
        "baseline_risk_score": 60,
        "risk_score": 60,
        "severity": "Elevated",
        "dominant_driver": "South China Sea exposure and island import dependency",
        "linked_chokepoints": ["South China Sea"],
        "primary_commodities": ["Containerized Goods", "Food", "Energy Products"]
    },
    {
        "port_name": "Port of Cebu",
        "country": "Philippines",
        "iso3": "PHL",
        "region": "Southeast Asia",
        "latitude": 10.3157,
        "longitude": 123.8854,
        "port_type": "container/passenger",
        "strategic_importance": 62,
        "baseline_risk_score": 54,
        "risk_score": 54,
        "severity": "Guarded",
        "dominant_driver": "Central Philippines logistics and island dependency",
        "linked_chokepoints": ["South China Sea"],
        "primary_commodities": ["Containerized Goods", "Food", "Consumer Goods"]
    }
]

def seed_southeast_asia_ports():
    supabase.table("sc_master_ports").upsert(
        SOUTHEAST_ASIA_PORTS,
        on_conflict="port_name"
    ).execute()
    print({
        "status": "success",
        "ports_seeded": len(SOUTHEAST_ASIA_PORTS),
        "region": "Southeast Asia"
    })

if __name__ == "__main__":
    seed_southeast_asia_ports()

MIDDLE_EAST_SOUTH_ASIA_PORTS = [
    {"port_name":"Jebel Ali Port","country":"United Arab Emirates","iso3":"ARE","region":"Middle East & South Asia","latitude":25.0118,"longitude":55.0611,"port_type":"container/free zone","strategic_importance":96,"baseline_risk_score":74,"risk_score":74,"severity":"High","dominant_driver":"Gulf transshipment hub and Hormuz exposure","linked_chokepoints":["Strait of Hormuz"],"primary_commodities":["Containerized Goods","Crude Oil","Electronics"]},
    {"port_name":"Khalifa Port","country":"United Arab Emirates","iso3":"ARE","region":"Middle East & South Asia","latitude":24.7994,"longitude":54.6492,"port_type":"container/industrial","strategic_importance":85,"baseline_risk_score":68,"risk_score":68,"severity":"Elevated","dominant_driver":"Abu Dhabi industrial and Gulf logistics exposure","linked_chokepoints":["Strait of Hormuz"],"primary_commodities":["Aluminum","Industrial Goods","Containerized Goods"]},
    {"port_name":"Port of Fujairah","country":"United Arab Emirates","iso3":"ARE","region":"Middle East & South Asia","latitude":25.1288,"longitude":56.3265,"port_type":"energy/bunkering","strategic_importance":90,"baseline_risk_score":72,"risk_score":72,"severity":"High","dominant_driver":"Energy bunkering hub outside Hormuz-facing Gulf routes","linked_chokepoints":["Strait of Hormuz","Arabian Sea"],"primary_commodities":["Crude Oil","Refined Products","LNG"]},

    {"port_name":"Jeddah Islamic Port","country":"Saudi Arabia","iso3":"SAU","region":"Middle East & South Asia","latitude":21.4858,"longitude":39.1925,"port_type":"container","strategic_importance":88,"baseline_risk_score":69,"risk_score":69,"severity":"Elevated","dominant_driver":"Red Sea container hub and Bab el-Mandeb exposure","linked_chokepoints":["Bab el-Mandeb","Suez Canal"],"primary_commodities":["Containerized Goods","Food","Consumer Goods"]},
    {"port_name":"King Abdulaziz Port","country":"Saudi Arabia","iso3":"SAU","region":"Middle East & South Asia","latitude":26.4476,"longitude":50.2007,"port_type":"container/energy","strategic_importance":84,"baseline_risk_score":70,"risk_score":70,"severity":"High","dominant_driver":"Eastern Province industrial exposure and Gulf route dependency","linked_chokepoints":["Strait of Hormuz"],"primary_commodities":["Petrochemicals","Crude Oil","Containerized Goods"]},
    {"port_name":"Yanbu Commercial Port","country":"Saudi Arabia","iso3":"SAU","region":"Middle East & South Asia","latitude":24.0889,"longitude":38.0618,"port_type":"energy/bulk","strategic_importance":80,"baseline_risk_score":66,"risk_score":66,"severity":"Elevated","dominant_driver":"Red Sea energy export and industrial corridor exposure","linked_chokepoints":["Bab el-Mandeb","Suez Canal"],"primary_commodities":["Crude Oil","Petrochemicals","Bulk Goods"]},

    {"port_name":"Hamad Port","country":"Qatar","iso3":"QAT","region":"Middle East & South Asia","latitude":25.0267,"longitude":51.6175,"port_type":"container","strategic_importance":82,"baseline_risk_score":68,"risk_score":68,"severity":"Elevated","dominant_driver":"Qatar import dependency and Gulf maritime exposure","linked_chokepoints":["Strait of Hormuz"],"primary_commodities":["Containerized Goods","LNG Equipment","Food"]},
    {"port_name":"Sohar Port","country":"Oman","iso3":"OMN","region":"Middle East & South Asia","latitude":24.5094,"longitude":56.6257,"port_type":"industrial/bulk","strategic_importance":78,"baseline_risk_score":64,"risk_score":64,"severity":"Elevated","dominant_driver":"Oman industrial gateway and Arabian Sea exposure","linked_chokepoints":["Strait of Hormuz","Arabian Sea"],"primary_commodities":["Metals","Petrochemicals","Bulk Goods"]},
    {"port_name":"Port of Salalah","country":"Oman","iso3":"OMN","region":"Middle East & South Asia","latitude":16.9569,"longitude":54.0083,"port_type":"transshipment","strategic_importance":86,"baseline_risk_score":67,"risk_score":67,"severity":"Elevated","dominant_driver":"Arabian Sea transshipment and Red Sea rerouting relevance","linked_chokepoints":["Bab el-Mandeb","Arabian Sea"],"primary_commodities":["Containerized Goods","Energy Products","Consumer Goods"]},
    {"port_name":"Port of Duqm","country":"Oman","iso3":"OMN","region":"Middle East & South Asia","latitude":19.6625,"longitude":57.7064,"port_type":"industrial/energy","strategic_importance":74,"baseline_risk_score":60,"risk_score":60,"severity":"Elevated","dominant_driver":"Emerging industrial hub with strategic Indian Ocean access","linked_chokepoints":["Arabian Sea"],"primary_commodities":["Energy Products","Industrial Goods","Bulk Goods"]},

    {"port_name":"Bandar Abbas","country":"Iran","iso3":"IRN","region":"Middle East & South Asia","latitude":27.1832,"longitude":56.2666,"port_type":"container/energy","strategic_importance":88,"baseline_risk_score":82,"risk_score":82,"severity":"Critical","dominant_driver":"Iranian Gulf gateway and sanctions/Hormuz exposure","linked_chokepoints":["Strait of Hormuz"],"primary_commodities":["Containerized Goods","Crude Oil","Industrial Goods"]},
    {"port_name":"Chabahar Port","country":"Iran","iso3":"IRN","region":"Middle East & South Asia","latitude":25.2919,"longitude":60.6430,"port_type":"container/strategic","strategic_importance":76,"baseline_risk_score":70,"risk_score":70,"severity":"High","dominant_driver":"Indian Ocean access point and sanctions exposure","linked_chokepoints":["Arabian Sea"],"primary_commodities":["Containerized Goods","Bulk Goods","Energy Products"]},

    {"port_name":"Port of Karachi","country":"Pakistan","iso3":"PAK","region":"Middle East & South Asia","latitude":24.8415,"longitude":66.9750,"port_type":"container","strategic_importance":78,"baseline_risk_score":64,"risk_score":64,"severity":"Elevated","dominant_driver":"Pakistan trade gateway and Arabian Sea exposure","linked_chokepoints":["Arabian Sea","Strait of Hormuz"],"primary_commodities":["Containerized Goods","Food","Energy Products"]},
    {"port_name":"Port Qasim","country":"Pakistan","iso3":"PAK","region":"Middle East & South Asia","latitude":24.7690,"longitude":67.3330,"port_type":"container/energy","strategic_importance":76,"baseline_risk_score":63,"risk_score":63,"severity":"Elevated","dominant_driver":"Energy and industrial import dependency","linked_chokepoints":["Arabian Sea","Strait of Hormuz"],"primary_commodities":["LNG","Coal","Containerized Goods"]},
    {"port_name":"Gwadar Port","country":"Pakistan","iso3":"PAK","region":"Middle East & South Asia","latitude":25.1264,"longitude":62.3225,"port_type":"strategic/deepwater","strategic_importance":72,"baseline_risk_score":68,"risk_score":68,"severity":"Elevated","dominant_driver":"Strategic corridor exposure and security risk","linked_chokepoints":["Arabian Sea","Strait of Hormuz"],"primary_commodities":["Energy Products","Containerized Goods","Bulk Goods"]},

    {"port_name":"Mundra Port","country":"India","iso3":"IND","region":"Middle East & South Asia","latitude":22.7350,"longitude":69.7050,"port_type":"container/bulk","strategic_importance":90,"baseline_risk_score":62,"risk_score":62,"severity":"Elevated","dominant_driver":"India private port concentration and Arabian Sea exposure","linked_chokepoints":["Arabian Sea","Strait of Hormuz"],"primary_commodities":["Containerized Goods","Coal","Crude Oil"]},
    {"port_name":"Jawaharlal Nehru Port","country":"India","iso3":"IND","region":"Middle East & South Asia","latitude":18.9490,"longitude":72.9510,"port_type":"container","strategic_importance":88,"baseline_risk_score":61,"risk_score":61,"severity":"Elevated","dominant_driver":"India container gateway and western corridor dependency","linked_chokepoints":["Arabian Sea","Suez Canal"],"primary_commodities":["Containerized Goods","Electronics","Machinery"]},
    {"port_name":"Port of Chennai","country":"India","iso3":"IND","region":"Middle East & South Asia","latitude":13.0827,"longitude":80.2707,"port_type":"container/automotive","strategic_importance":82,"baseline_risk_score":58,"risk_score":58,"severity":"Guarded","dominant_driver":"Automotive export and Bay of Bengal exposure","linked_chokepoints":["Bay of Bengal","Strait of Malacca"],"primary_commodities":["Automotive","Containerized Goods","Industrial Goods"]},
    {"port_name":"Visakhapatnam Port","country":"India","iso3":"IND","region":"Middle East & South Asia","latitude":17.6868,"longitude":83.2185,"port_type":"bulk/energy","strategic_importance":80,"baseline_risk_score":57,"risk_score":57,"severity":"Guarded","dominant_driver":"Bulk commodity and energy corridor exposure","linked_chokepoints":["Bay of Bengal","Strait of Malacca"],"primary_commodities":["Coal","Iron Ore","Crude Oil"]},
    {"port_name":"Port of Kochi","country":"India","iso3":"IND","region":"Middle East & South Asia","latitude":9.9679,"longitude":76.2441,"port_type":"container/energy","strategic_importance":72,"baseline_risk_score":56,"risk_score":56,"severity":"Guarded","dominant_driver":"Southwest India maritime and energy exposure","linked_chokepoints":["Arabian Sea","Strait of Malacca"],"primary_commodities":["Containerized Goods","Energy Products","Spices"]},
    {"port_name":"Deendayal Port","country":"India","iso3":"IND","region":"Middle East & South Asia","latitude":23.0333,"longitude":70.2167,"port_type":"bulk/container","strategic_importance":78,"baseline_risk_score":59,"risk_score":59,"severity":"Guarded","dominant_driver":"Gujarat bulk and energy import exposure","linked_chokepoints":["Arabian Sea","Strait of Hormuz"],"primary_commodities":["Crude Oil","Fertilizers","Coal"]},
    {"port_name":"Paradip Port","country":"India","iso3":"IND","region":"Middle East & South Asia","latitude":20.3167,"longitude":86.6167,"port_type":"bulk","strategic_importance":76,"baseline_risk_score":55,"risk_score":55,"severity":"Guarded","dominant_driver":"Eastern India bulk commodity corridor","linked_chokepoints":["Bay of Bengal","Strait of Malacca"],"primary_commodities":["Coal","Iron Ore","Fertilizers"]},

    {"port_name":"Port of Colombo","country":"Sri Lanka","iso3":"LKA","region":"Middle East & South Asia","latitude":6.9271,"longitude":79.8612,"port_type":"transshipment","strategic_importance":86,"baseline_risk_score":62,"risk_score":62,"severity":"Elevated","dominant_driver":"Indian Ocean transshipment hub and South Asia routing dependency","linked_chokepoints":["Strait of Malacca","Suez Canal","Arabian Sea"],"primary_commodities":["Containerized Goods","Textiles","Consumer Goods"]},
    {"port_name":"Hambantota Port","country":"Sri Lanka","iso3":"LKA","region":"Middle East & South Asia","latitude":6.1241,"longitude":81.1185,"port_type":"strategic/deepwater","strategic_importance":70,"baseline_risk_score":60,"risk_score":60,"severity":"Elevated","dominant_driver":"Strategic Indian Ocean location and debt/geopolitical exposure","linked_chokepoints":["Indian Ocean","Strait of Malacca"],"primary_commodities":["Bulk Goods","Energy Products","Vehicles"]},

    {"port_name":"Chittagong Port","country":"Bangladesh","iso3":"BGD","region":"Middle East & South Asia","latitude":22.3350,"longitude":91.8325,"port_type":"container","strategic_importance":78,"baseline_risk_score":60,"risk_score":60,"severity":"Elevated","dominant_driver":"Bangladesh export dependency and Bay of Bengal exposure","linked_chokepoints":["Bay of Bengal","Strait of Malacca"],"primary_commodities":["Textiles","Containerized Goods","Food"]},
    {"port_name":"Mongla Port","country":"Bangladesh","iso3":"BGD","region":"Middle East & South Asia","latitude":22.4886,"longitude":89.5925,"port_type":"bulk/container","strategic_importance":62,"baseline_risk_score":55,"risk_score":55,"severity":"Guarded","dominant_driver":"Secondary Bangladesh logistics and climate exposure","linked_chokepoints":["Bay of Bengal"],"primary_commodities":["Bulk Goods","Food","Containerized Goods"]}
]

def seed_middle_east_south_asia_ports():
    supabase.table("sc_master_ports").upsert(
        MIDDLE_EAST_SOUTH_ASIA_PORTS,
        on_conflict="port_name"
    ).execute()
    print({
        "status": "success",
        "ports_seeded": len(MIDDLE_EAST_SOUTH_ASIA_PORTS),
        "region": "Middle East & South Asia"
    })

if __name__ == "__main__":
    seed_middle_east_south_asia_ports()

EUROPE_PORTS = [
    {"port_name":"Port of Rotterdam","country":"Netherlands","iso3":"NLD","region":"Europe","latitude":51.9244,"longitude":4.4777,"port_type":"container/energy/bulk","strategic_importance":98,"baseline_risk_score":62,"risk_score":62,"severity":"Elevated","dominant_driver":"Europe gateway exposure and Suez/Bab el-Mandeb dependency","linked_chokepoints":["Suez Canal","Bab el-Mandeb","Dover Strait"],"primary_commodities":["Containerized Goods","Crude Oil","LNG","Chemicals"]},
    {"port_name":"Port of Antwerp-Bruges","country":"Belgium","iso3":"BEL","region":"Europe","latitude":51.2602,"longitude":4.4028,"port_type":"container/chemicals","strategic_importance":95,"baseline_risk_score":60,"risk_score":60,"severity":"Elevated","dominant_driver":"European chemicals and container gateway exposure","linked_chokepoints":["Dover Strait","Suez Canal"],"primary_commodities":["Chemicals","Containerized Goods","Automotive"]},
    {"port_name":"Port of Hamburg","country":"Germany","iso3":"DEU","region":"Europe","latitude":53.5511,"longitude":9.9937,"port_type":"container","strategic_importance":92,"baseline_risk_score":58,"risk_score":58,"severity":"Guarded","dominant_driver":"German industrial export gateway and North Sea dependency","linked_chokepoints":["Dover Strait","Danish Straits"],"primary_commodities":["Automotive","Machinery","Containerized Goods"]},
    {"port_name":"Bremerhaven Port","country":"Germany","iso3":"DEU","region":"Europe","latitude":53.5396,"longitude":8.5809,"port_type":"container/automotive","strategic_importance":88,"baseline_risk_score":56,"risk_score":56,"severity":"Guarded","dominant_driver":"Automotive export concentration and North Sea exposure","linked_chokepoints":["Dover Strait","Danish Straits"],"primary_commodities":["Automotive","Containerized Goods","Machinery"]},
    {"port_name":"Port of Felixstowe","country":"United Kingdom","iso3":"GBR","region":"Europe","latitude":51.9542,"longitude":1.3100,"port_type":"container","strategic_importance":84,"baseline_risk_score":57,"risk_score":57,"severity":"Guarded","dominant_driver":"UK container gateway and Dover Strait exposure","linked_chokepoints":["Dover Strait","English Channel"],"primary_commodities":["Containerized Goods","Consumer Goods","Food"]},
    {"port_name":"London Gateway","country":"United Kingdom","iso3":"GBR","region":"Europe","latitude":51.5079,"longitude":0.4977,"port_type":"container/logistics","strategic_importance":78,"baseline_risk_score":55,"risk_score":55,"severity":"Guarded","dominant_driver":"UK logistics hub and North Sea/Channel exposure","linked_chokepoints":["Dover Strait","English Channel"],"primary_commodities":["Containerized Goods","Consumer Goods","Retail Goods"]},
    {"port_name":"Port of Le Havre","country":"France","iso3":"FRA","region":"Europe","latitude":49.4944,"longitude":0.1079,"port_type":"container/energy","strategic_importance":82,"baseline_risk_score":56,"risk_score":56,"severity":"Guarded","dominant_driver":"French Atlantic gateway and Channel exposure","linked_chokepoints":["English Channel","Dover Strait"],"primary_commodities":["Containerized Goods","Crude Oil","Chemicals"]},
    {"port_name":"Marseille-Fos Port","country":"France","iso3":"FRA","region":"Europe","latitude":43.3522,"longitude":5.3095,"port_type":"energy/container","strategic_importance":86,"baseline_risk_score":59,"risk_score":59,"severity":"Guarded","dominant_driver":"Mediterranean energy and container gateway exposure","linked_chokepoints":["Suez Canal","Strait of Gibraltar"],"primary_commodities":["Crude Oil","LNG","Containerized Goods"]},
    {"port_name":"Port of Valencia","country":"Spain","iso3":"ESP","region":"Europe","latitude":39.4486,"longitude":-0.3166,"port_type":"container","strategic_importance":86,"baseline_risk_score":57,"risk_score":57,"severity":"Guarded","dominant_driver":"Western Mediterranean container hub and Suez/Gibraltar dependency","linked_chokepoints":["Strait of Gibraltar","Suez Canal"],"primary_commodities":["Containerized Goods","Automotive","Food"]},
    {"port_name":"Port of Algeciras","country":"Spain","iso3":"ESP","region":"Europe","latitude":36.1320,"longitude":-5.4400,"port_type":"transshipment/container","strategic_importance":90,"baseline_risk_score":61,"risk_score":61,"severity":"Elevated","dominant_driver":"Gibraltar gateway and Mediterranean-Atlantic transshipment exposure","linked_chokepoints":["Strait of Gibraltar","Suez Canal"],"primary_commodities":["Containerized Goods","Energy Products","Consumer Goods"]},
    {"port_name":"Port of Barcelona","country":"Spain","iso3":"ESP","region":"Europe","latitude":41.3525,"longitude":2.1587,"port_type":"container","strategic_importance":80,"baseline_risk_score":55,"risk_score":55,"severity":"Guarded","dominant_driver":"Mediterranean industrial and consumer goods exposure","linked_chokepoints":["Strait of Gibraltar","Suez Canal"],"primary_commodities":["Containerized Goods","Automotive","Chemicals"]},
    {"port_name":"Port of Genoa","country":"Italy","iso3":"ITA","region":"Europe","latitude":44.4056,"longitude":8.9463,"port_type":"container","strategic_importance":81,"baseline_risk_score":56,"risk_score":56,"severity":"Guarded","dominant_driver":"Northern Italy industrial gateway and Mediterranean exposure","linked_chokepoints":["Suez Canal","Strait of Gibraltar"],"primary_commodities":["Containerized Goods","Machinery","Automotive"]},
    {"port_name":"Port of Trieste","country":"Italy","iso3":"ITA","region":"Europe","latitude":45.6495,"longitude":13.7768,"port_type":"energy/container","strategic_importance":83,"baseline_risk_score":58,"risk_score":58,"severity":"Guarded","dominant_driver":"Adriatic gateway to Central Europe and energy corridor exposure","linked_chokepoints":["Suez Canal","Strait of Otranto"],"primary_commodities":["Crude Oil","Containerized Goods","Industrial Goods"]},
    {"port_name":"Gioia Tauro Port","country":"Italy","iso3":"ITA","region":"Europe","latitude":38.4250,"longitude":15.8980,"port_type":"transshipment/container","strategic_importance":78,"baseline_risk_score":57,"risk_score":57,"severity":"Guarded","dominant_driver":"Central Mediterranean transshipment exposure","linked_chokepoints":["Suez Canal","Strait of Gibraltar"],"primary_commodities":["Containerized Goods","Consumer Goods","Electronics"]},
    {"port_name":"Port of Piraeus","country":"Greece","iso3":"GRC","region":"Europe","latitude":37.9420,"longitude":23.6460,"port_type":"container/transshipment","strategic_importance":88,"baseline_risk_score":60,"risk_score":60,"severity":"Elevated","dominant_driver":"Eastern Mediterranean Asia-Europe gateway and Suez dependency","linked_chokepoints":["Suez Canal","Dardanelles"],"primary_commodities":["Containerized Goods","Electronics","Consumer Goods"]},
    {"port_name":"Port of Istanbul Ambarli","country":"Turkey","iso3":"TUR","region":"Europe","latitude":40.9670,"longitude":28.6800,"port_type":"container","strategic_importance":82,"baseline_risk_score":62,"risk_score":62,"severity":"Elevated","dominant_driver":"Turkish Straits and Black Sea gateway exposure","linked_chokepoints":["Bosporus","Dardanelles"],"primary_commodities":["Containerized Goods","Food","Industrial Goods"]},
    {"port_name":"Port of Constanta","country":"Romania","iso3":"ROU","region":"Europe","latitude":44.1598,"longitude":28.6348,"port_type":"bulk/container","strategic_importance":78,"baseline_risk_score":64,"risk_score":64,"severity":"Elevated","dominant_driver":"Black Sea grain and energy exposure","linked_chokepoints":["Bosporus","Dardanelles"],"primary_commodities":["Grain","Energy Products","Containerized Goods"]},
    {"port_name":"Port of Gdansk","country":"Poland","iso3":"POL","region":"Europe","latitude":54.3520,"longitude":18.6466,"port_type":"container/energy","strategic_importance":80,"baseline_risk_score":58,"risk_score":58,"severity":"Guarded","dominant_driver":"Baltic logistics and energy gateway exposure","linked_chokepoints":["Danish Straits","Kiel Canal"],"primary_commodities":["Containerized Goods","Coal","Energy Products"]},
    {"port_name":"Port of Klaipeda","country":"Lithuania","iso3":"LTU","region":"Europe","latitude":55.7033,"longitude":21.1443,"port_type":"bulk/container","strategic_importance":70,"baseline_risk_score":56,"risk_score":56,"severity":"Guarded","dominant_driver":"Baltic trade corridor and regional security exposure","linked_chokepoints":["Danish Straits"],"primary_commodities":["Fertilizers","Grain","Containerized Goods"]},
    {"port_name":"Port of Aarhus","country":"Denmark","iso3":"DNK","region":"Europe","latitude":56.1629,"longitude":10.2039,"port_type":"container","strategic_importance":68,"baseline_risk_score":53,"risk_score":53,"severity":"Guarded","dominant_driver":"Danish Straits regional logistics exposure","linked_chokepoints":["Danish Straits"],"primary_commodities":["Containerized Goods","Food","Industrial Goods"]},
    {"port_name":"Port of Gothenburg","country":"Sweden","iso3":"SWE","region":"Europe","latitude":57.7089,"longitude":11.9746,"port_type":"container/energy","strategic_importance":74,"baseline_risk_score":54,"risk_score":54,"severity":"Guarded","dominant_driver":"Nordic container and energy gateway exposure","linked_chokepoints":["Danish Straits"],"primary_commodities":["Containerized Goods","Automotive","Energy Products"]},
    {"port_name":"Port of Oslo","country":"Norway","iso3":"NOR","region":"Europe","latitude":59.9139,"longitude":10.7522,"port_type":"container","strategic_importance":62,"baseline_risk_score":50,"risk_score":50,"severity":"Guarded","dominant_driver":"Nordic import logistics and North Sea exposure","linked_chokepoints":["North Sea","Danish Straits"],"primary_commodities":["Containerized Goods","Food","Consumer Goods"]},
    {"port_name":"Port of Zeebrugge","country":"Belgium","iso3":"BEL","region":"Europe","latitude":51.3306,"longitude":3.2076,"port_type":"automotive/LNG/container","strategic_importance":82,"baseline_risk_score":57,"risk_score":57,"severity":"Guarded","dominant_driver":"LNG and automotive gateway exposure","linked_chokepoints":["Dover Strait","English Channel"],"primary_commodities":["LNG","Automotive","Containerized Goods"]},
    {"port_name":"Port of Bilbao","country":"Spain","iso3":"ESP","region":"Europe","latitude":43.2630,"longitude":-2.9340,"port_type":"bulk/container","strategic_importance":68,"baseline_risk_score":52,"risk_score":52,"severity":"Guarded","dominant_driver":"Atlantic industrial and energy exposure","linked_chokepoints":["Bay of Biscay","Strait of Gibraltar"],"primary_commodities":["Energy Products","Steel","Containerized Goods"]}
]

def seed_europe_ports():
    supabase.table("sc_master_ports").upsert(
        EUROPE_PORTS,
        on_conflict="port_name"
    ).execute()
    print({
        "status": "success",
        "ports_seeded": len(EUROPE_PORTS),
        "region": "Europe"
    })

if __name__ == "__main__":
    seed_europe_ports()

AFRICA_PORTS = [
    {"port_name":"Port Said","country":"Egypt","iso3":"EGY","region":"Africa","latitude":31.2653,"longitude":32.3019,"port_type":"container/transshipment","strategic_importance":90,"baseline_risk_score":68,"risk_score":68,"severity":"Elevated","dominant_driver":"Suez Canal gateway and Red Sea/Mediterranean exposure","linked_chokepoints":["Suez Canal","Bab el-Mandeb"],"primary_commodities":["Containerized Goods","Energy Products","Consumer Goods"]},
    {"port_name":"Port of Alexandria","country":"Egypt","iso3":"EGY","region":"Africa","latitude":31.2001,"longitude":29.9187,"port_type":"container/bulk","strategic_importance":82,"baseline_risk_score":60,"risk_score":60,"severity":"Elevated","dominant_driver":"Egypt import gateway and Mediterranean exposure","linked_chokepoints":["Suez Canal","Strait of Gibraltar"],"primary_commodities":["Grain","Containerized Goods","Energy Products"]},
    {"port_name":"Tanger Med","country":"Morocco","iso3":"MAR","region":"Africa","latitude":35.8840,"longitude":-5.5000,"port_type":"container/transshipment","strategic_importance":88,"baseline_risk_score":58,"risk_score":58,"severity":"Guarded","dominant_driver":"Gibraltar-adjacent transshipment and Europe-Africa logistics exposure","linked_chokepoints":["Strait of Gibraltar"],"primary_commodities":["Containerized Goods","Automotive","Textiles"]},
    {"port_name":"Port of Casablanca","country":"Morocco","iso3":"MAR","region":"Africa","latitude":33.5731,"longitude":-7.5898,"port_type":"container/bulk","strategic_importance":74,"baseline_risk_score":54,"risk_score":54,"severity":"Guarded","dominant_driver":"Morocco commercial gateway and Atlantic exposure","linked_chokepoints":["Strait of Gibraltar","Atlantic Corridor"],"primary_commodities":["Containerized Goods","Phosphates","Food"]},
    {"port_name":"Port of Algiers","country":"Algeria","iso3":"DZA","region":"Africa","latitude":36.7538,"longitude":3.0588,"port_type":"container/bulk","strategic_importance":70,"baseline_risk_score":56,"risk_score":56,"severity":"Guarded","dominant_driver":"Algerian import dependency and Mediterranean exposure","linked_chokepoints":["Strait of Gibraltar","Suez Canal"],"primary_commodities":["Containerized Goods","Food","Industrial Goods"]},
    {"port_name":"Port of Lagos Apapa","country":"Nigeria","iso3":"NGA","region":"Africa","latitude":6.4450,"longitude":3.3680,"port_type":"container","strategic_importance":82,"baseline_risk_score":66,"risk_score":66,"severity":"Elevated","dominant_driver":"West Africa container gateway and congestion exposure","linked_chokepoints":["Gulf of Guinea","Atlantic Corridor"],"primary_commodities":["Containerized Goods","Consumer Goods","Food"]},
    {"port_name":"Lekki Deep Sea Port","country":"Nigeria","iso3":"NGA","region":"Africa","latitude":6.4128,"longitude":4.0150,"port_type":"deepwater/container","strategic_importance":76,"baseline_risk_score":60,"risk_score":60,"severity":"Elevated","dominant_driver":"Emerging West Africa deepwater logistics hub","linked_chokepoints":["Gulf of Guinea","Atlantic Corridor"],"primary_commodities":["Containerized Goods","Consumer Goods","Industrial Goods"]},
    {"port_name":"Port of Durban","country":"South Africa","iso3":"ZAF","region":"Africa","latitude":-29.8688,"longitude":31.0610,"port_type":"container","strategic_importance":84,"baseline_risk_score":62,"risk_score":62,"severity":"Elevated","dominant_driver":"Southern Africa container gateway and Cape route exposure","linked_chokepoints":["Cape of Good Hope"],"primary_commodities":["Containerized Goods","Automotive","Minerals"]},
    {"port_name":"Port of Cape Town","country":"South Africa","iso3":"ZAF","region":"Africa","latitude":-33.9180,"longitude":18.4210,"port_type":"container/bulk","strategic_importance":74,"baseline_risk_score":58,"risk_score":58,"severity":"Guarded","dominant_driver":"Cape route logistics and weather exposure","linked_chokepoints":["Cape of Good Hope"],"primary_commodities":["Fruit","Containerized Goods","Energy Products"]},
    {"port_name":"Port of Ngqura","country":"South Africa","iso3":"ZAF","region":"Africa","latitude":-33.8000,"longitude":25.6833,"port_type":"deepwater/container","strategic_importance":70,"baseline_risk_score":56,"risk_score":56,"severity":"Guarded","dominant_driver":"Deepwater transshipment and Southern Africa logistics exposure","linked_chokepoints":["Cape of Good Hope"],"primary_commodities":["Containerized Goods","Automotive","Minerals"]},
    {"port_name":"Port of Mombasa","country":"Kenya","iso3":"KEN","region":"Africa","latitude":-4.0435,"longitude":39.6682,"port_type":"container/bulk","strategic_importance":78,"baseline_risk_score":60,"risk_score":60,"severity":"Elevated","dominant_driver":"East Africa gateway and Indian Ocean security exposure","linked_chokepoints":["Bab el-Mandeb","Indian Ocean"],"primary_commodities":["Containerized Goods","Tea","Fuel"]},
    {"port_name":"Port of Dar es Salaam","country":"Tanzania","iso3":"TZA","region":"Africa","latitude":-6.7924,"longitude":39.2083,"port_type":"container/bulk","strategic_importance":72,"baseline_risk_score":58,"risk_score":58,"severity":"Guarded","dominant_driver":"East/Central Africa corridor dependency","linked_chokepoints":["Indian Ocean","Mozambique Channel"],"primary_commodities":["Containerized Goods","Copper","Agricultural Goods"]},
    {"port_name":"Port of Djibouti","country":"Djibouti","iso3":"DJI","region":"Africa","latitude":11.5721,"longitude":43.1456,"port_type":"container/energy/strategic","strategic_importance":86,"baseline_risk_score":70,"risk_score":70,"severity":"High","dominant_driver":"Bab el-Mandeb gateway and military/geostrategic exposure","linked_chokepoints":["Bab el-Mandeb","Red Sea"],"primary_commodities":["Containerized Goods","Fuel","Food"]},
    {"port_name":"Port of Maputo","country":"Mozambique","iso3":"MOZ","region":"Africa","latitude":-25.9692,"longitude":32.5732,"port_type":"bulk/container","strategic_importance":68,"baseline_risk_score":56,"risk_score":56,"severity":"Guarded","dominant_driver":"Southern Africa bulk corridor and Mozambique Channel exposure","linked_chokepoints":["Mozambique Channel","Cape of Good Hope"],"primary_commodities":["Coal","Aluminum","Agricultural Goods"]},
    {"port_name":"Port of Beira","country":"Mozambique","iso3":"MOZ","region":"Africa","latitude":-19.8290,"longitude":34.8370,"port_type":"bulk/container","strategic_importance":64,"baseline_risk_score":57,"risk_score":57,"severity":"Guarded","dominant_driver":"Central Africa corridor and cyclone/weather exposure","linked_chokepoints":["Mozambique Channel"],"primary_commodities":["Coal","Agricultural Goods","Containerized Goods"]},
    {"port_name":"Port of Tema","country":"Ghana","iso3":"GHA","region":"Africa","latitude":5.6500,"longitude":0.0167,"port_type":"container","strategic_importance":70,"baseline_risk_score":55,"risk_score":55,"severity":"Guarded","dominant_driver":"Ghana import/export gateway and Gulf of Guinea exposure","linked_chokepoints":["Gulf of Guinea"],"primary_commodities":["Cocoa","Containerized Goods","Fuel"]},
    {"port_name":"Port of Abidjan","country":"Côte d’Ivoire","iso3":"CIV","region":"Africa","latitude":5.3167,"longitude":-4.0167,"port_type":"container/bulk","strategic_importance":72,"baseline_risk_score":56,"risk_score":56,"severity":"Guarded","dominant_driver":"West Africa cocoa/export corridor and Gulf of Guinea exposure","linked_chokepoints":["Gulf of Guinea"],"primary_commodities":["Cocoa","Cashew","Containerized Goods"]},
    {"port_name":"Port of Walvis Bay","country":"Namibia","iso3":"NAM","region":"Africa","latitude":-22.9575,"longitude":14.5053,"port_type":"container/bulk","strategic_importance":64,"baseline_risk_score":52,"risk_score":52,"severity":"Guarded","dominant_driver":"Southwest Africa corridor and Atlantic exposure","linked_chokepoints":["Atlantic Corridor","Cape of Good Hope"],"primary_commodities":["Minerals","Fish","Containerized Goods"]},
    {"port_name":"Port of Luanda","country":"Angola","iso3":"AGO","region":"Africa","latitude":-8.8390,"longitude":13.2894,"port_type":"container/energy","strategic_importance":70,"baseline_risk_score":57,"risk_score":57,"severity":"Guarded","dominant_driver":"Angola energy and import gateway exposure","linked_chokepoints":["Atlantic Corridor","Gulf of Guinea"],"primary_commodities":["Crude Oil","Containerized Goods","Food"]},
    {"port_name":"Port of Pointe-Noire","country":"Republic of the Congo","iso3":"COG","region":"Africa","latitude":-4.7692,"longitude":11.8664,"port_type":"container/energy","strategic_importance":66,"baseline_risk_score":55,"risk_score":55,"severity":"Guarded","dominant_driver":"Central Africa oil/logistics corridor exposure","linked_chokepoints":["Atlantic Corridor","Gulf of Guinea"],"primary_commodities":["Crude Oil","Timber","Containerized Goods"]}
]

def seed_africa_ports():
    supabase.table("sc_master_ports").upsert(
        AFRICA_PORTS,
        on_conflict="port_name"
    ).execute()
    print({
        "status": "success",
        "ports_seeded": len(AFRICA_PORTS),
        "region": "Africa"
    })

if __name__ == "__main__":
    seed_africa_ports()

NORTH_AMERICA_PORTS = [
    {"port_name":"Port of Los Angeles","country":"United States","iso3":"USA","region":"North America","latitude":33.7405,"longitude":-118.2775,"port_type":"container","strategic_importance":96,"baseline_risk_score":64,"risk_score":64,"severity":"Elevated","dominant_driver":"US Pacific gateway and Asia trade dependency","linked_chokepoints":["Panama Canal","Pacific Corridor"],"primary_commodities":["Containerized Goods","Electronics","Automotive"]},
    {"port_name":"Port of Long Beach","country":"United States","iso3":"USA","region":"North America","latitude":33.7542,"longitude":-118.2165,"port_type":"container","strategic_importance":95,"baseline_risk_score":64,"risk_score":64,"severity":"Elevated","dominant_driver":"High-volume trans-Pacific container exposure","linked_chokepoints":["Panama Canal","Pacific Corridor"],"primary_commodities":["Containerized Goods","Electronics","Consumer Goods"]},
    {"port_name":"Port of Oakland","country":"United States","iso3":"USA","region":"North America","latitude":37.7955,"longitude":-122.2790,"port_type":"container","strategic_importance":78,"baseline_risk_score":56,"risk_score":56,"severity":"Guarded","dominant_driver":"Northern California container and agriculture export exposure","linked_chokepoints":["Pacific Corridor"],"primary_commodities":["Agricultural Goods","Containerized Goods","Wine"]},
    {"port_name":"Port of Seattle","country":"United States","iso3":"USA","region":"North America","latitude":47.6062,"longitude":-122.3321,"port_type":"container","strategic_importance":78,"baseline_risk_score":55,"risk_score":55,"severity":"Guarded","dominant_driver":"Pacific Northwest Asia trade exposure","linked_chokepoints":["Pacific Corridor"],"primary_commodities":["Containerized Goods","Agricultural Goods","Machinery"]},
    {"port_name":"Port of Tacoma","country":"United States","iso3":"USA","region":"North America","latitude":47.2529,"longitude":-122.4443,"port_type":"container/automotive","strategic_importance":77,"baseline_risk_score":55,"risk_score":55,"severity":"Guarded","dominant_driver":"Pacific Northwest container and automotive logistics exposure","linked_chokepoints":["Pacific Corridor"],"primary_commodities":["Automotive","Containerized Goods","Industrial Goods"]},
    {"port_name":"Port of Houston","country":"United States","iso3":"USA","region":"North America","latitude":29.7604,"longitude":-95.3698,"port_type":"energy/container","strategic_importance":92,"baseline_risk_score":63,"risk_score":63,"severity":"Elevated","dominant_driver":"US energy, petrochemical, and Gulf Coast hurricane exposure","linked_chokepoints":["Gulf of Mexico","Panama Canal"],"primary_commodities":["Crude Oil","Petrochemicals","Containerized Goods"]},
    {"port_name":"Port of New Orleans","country":"United States","iso3":"USA","region":"North America","latitude":29.9511,"longitude":-90.0715,"port_type":"bulk/container","strategic_importance":82,"baseline_risk_score":61,"risk_score":61,"severity":"Elevated","dominant_driver":"Mississippi River grain and Gulf hurricane exposure","linked_chokepoints":["Gulf of Mexico","Mississippi River"],"primary_commodities":["Grain","Fertilizers","Containerized Goods"]},
    {"port_name":"Port of Savannah","country":"United States","iso3":"USA","region":"North America","latitude":32.0809,"longitude":-81.0912,"port_type":"container","strategic_importance":88,"baseline_risk_score":58,"risk_score":58,"severity":"Guarded","dominant_driver":"US Southeast container gateway and Atlantic storm exposure","linked_chokepoints":["Atlantic Corridor","Panama Canal"],"primary_commodities":["Containerized Goods","Automotive","Consumer Goods"]},
    {"port_name":"Port of Charleston","country":"United States","iso3":"USA","region":"North America","latitude":32.7765,"longitude":-79.9311,"port_type":"container","strategic_importance":82,"baseline_risk_score":57,"risk_score":57,"severity":"Guarded","dominant_driver":"Southeast US logistics and Atlantic hurricane exposure","linked_chokepoints":["Atlantic Corridor","Panama Canal"],"primary_commodities":["Containerized Goods","Automotive","Consumer Goods"]},
    {"port_name":"Port of Norfolk","country":"United States","iso3":"USA","region":"North America","latitude":36.8508,"longitude":-76.2859,"port_type":"container/naval","strategic_importance":84,"baseline_risk_score":58,"risk_score":58,"severity":"Guarded","dominant_driver":"US East Coast container and naval infrastructure exposure","linked_chokepoints":["Atlantic Corridor"],"primary_commodities":["Containerized Goods","Defense Logistics","Consumer Goods"]},
    {"port_name":"Port of New York and New Jersey","country":"United States","iso3":"USA","region":"North America","latitude":40.6681,"longitude":-74.0451,"port_type":"container","strategic_importance":94,"baseline_risk_score":61,"risk_score":61,"severity":"Elevated","dominant_driver":"Largest US East Coast gateway and urban logistics exposure","linked_chokepoints":["Atlantic Corridor","Panama Canal"],"primary_commodities":["Containerized Goods","Consumer Goods","Food"]},
    {"port_name":"Port of Miami","country":"United States","iso3":"USA","region":"North America","latitude":25.7781,"longitude":-80.1794,"port_type":"container/cruise","strategic_importance":72,"baseline_risk_score":56,"risk_score":56,"severity":"Guarded","dominant_driver":"Caribbean logistics and hurricane exposure","linked_chokepoints":["Caribbean Corridor","Panama Canal"],"primary_commodities":["Containerized Goods","Food","Consumer Goods"]},

    {"port_name":"Port of Vancouver","country":"Canada","iso3":"CAN","region":"North America","latitude":49.2827,"longitude":-123.1207,"port_type":"container/bulk/energy","strategic_importance":90,"baseline_risk_score":58,"risk_score":58,"severity":"Guarded","dominant_driver":"Canada Pacific gateway and Asia commodity export exposure","linked_chokepoints":["Pacific Corridor"],"primary_commodities":["Grain","Coal","Containerized Goods","Potash"]},
    {"port_name":"Port of Prince Rupert","country":"Canada","iso3":"CAN","region":"North America","latitude":54.3150,"longitude":-130.3208,"port_type":"container/bulk","strategic_importance":76,"baseline_risk_score":54,"risk_score":54,"severity":"Guarded","dominant_driver":"Northern Pacific gateway and rail corridor exposure","linked_chokepoints":["Pacific Corridor"],"primary_commodities":["Containerized Goods","Grain","Coal"]},
    {"port_name":"Port of Montreal","country":"Canada","iso3":"CAN","region":"North America","latitude":45.5017,"longitude":-73.5673,"port_type":"container","strategic_importance":78,"baseline_risk_score":54,"risk_score":54,"severity":"Guarded","dominant_driver":"St. Lawrence trade corridor and weather/ice exposure","linked_chokepoints":["St. Lawrence Seaway","Atlantic Corridor"],"primary_commodities":["Containerized Goods","Food","Machinery"]},
    {"port_name":"Port of Halifax","country":"Canada","iso3":"CAN","region":"North America","latitude":44.6488,"longitude":-63.5752,"port_type":"container","strategic_importance":72,"baseline_risk_score":52,"risk_score":52,"severity":"Guarded","dominant_driver":"Atlantic Canada container gateway and North Atlantic exposure","linked_chokepoints":["Atlantic Corridor"],"primary_commodities":["Containerized Goods","Seafood","Consumer Goods"]},

    {"port_name":"Port of Manzanillo Mexico","country":"Mexico","iso3":"MEX","region":"North America","latitude":19.0522,"longitude":-104.3158,"port_type":"container","strategic_importance":86,"baseline_risk_score":60,"risk_score":60,"severity":"Elevated","dominant_driver":"Mexico Pacific container gateway and Asia trade exposure","linked_chokepoints":["Pacific Corridor","Panama Canal"],"primary_commodities":["Containerized Goods","Automotive","Electronics"]},
    {"port_name":"Port of Lázaro Cárdenas","country":"Mexico","iso3":"MEX","region":"North America","latitude":17.9583,"longitude":-102.1944,"port_type":"container/bulk","strategic_importance":82,"baseline_risk_score":60,"risk_score":60,"severity":"Elevated","dominant_driver":"Mexico Pacific deepwater gateway and industrial corridor exposure","linked_chokepoints":["Pacific Corridor","Panama Canal"],"primary_commodities":["Containerized Goods","Steel","Automotive"]},
    {"port_name":"Port of Veracruz","country":"Mexico","iso3":"MEX","region":"North America","latitude":19.1738,"longitude":-96.1342,"port_type":"container/automotive","strategic_importance":78,"baseline_risk_score":57,"risk_score":57,"severity":"Guarded","dominant_driver":"Gulf of Mexico automotive and container gateway exposure","linked_chokepoints":["Gulf of Mexico"],"primary_commodities":["Automotive","Containerized Goods","Food"]},
    {"port_name":"Port of Altamira","country":"Mexico","iso3":"MEX","region":"North America","latitude":22.3921,"longitude":-97.9386,"port_type":"industrial/container","strategic_importance":72,"baseline_risk_score":56,"risk_score":56,"severity":"Guarded","dominant_driver":"Mexico Gulf industrial corridor and energy exposure","linked_chokepoints":["Gulf of Mexico"],"primary_commodities":["Chemicals","Containerized Goods","Industrial Goods"]}
]

def seed_north_america_ports():
    supabase.table("sc_master_ports").upsert(
        NORTH_AMERICA_PORTS,
        on_conflict="port_name"
    ).execute()
    print({
        "status": "success",
        "ports_seeded": len(NORTH_AMERICA_PORTS),
        "region": "North America"
    })

if __name__ == "__main__":
    seed_north_america_ports()

LATIN_AMERICA_PORTS = [
    {"port_name":"Port of Santos","country":"Brazil","iso3":"BRA","region":"Latin America","latitude":-23.9608,"longitude":-46.3336,"port_type":"container/bulk","strategic_importance":90,"baseline_risk_score":58,"risk_score":58,"severity":"Guarded","dominant_driver":"Brazil export gateway and agricultural/industrial concentration","linked_chokepoints":["Atlantic Corridor","Cape of Good Hope"],"primary_commodities":["Soybeans","Coffee","Containerized Goods","Steel"]},
    {"port_name":"Port of Paranaguá","country":"Brazil","iso3":"BRA","region":"Latin America","latitude":-25.5163,"longitude":-48.5095,"port_type":"bulk/container","strategic_importance":82,"baseline_risk_score":56,"risk_score":56,"severity":"Guarded","dominant_driver":"Agricultural export corridor and southern Brazil logistics exposure","linked_chokepoints":["Atlantic Corridor"],"primary_commodities":["Soybeans","Corn","Fertilizers","Containerized Goods"]},
    {"port_name":"Port of Rio de Janeiro","country":"Brazil","iso3":"BRA","region":"Latin America","latitude":-22.9068,"longitude":-43.1729,"port_type":"container/energy","strategic_importance":74,"baseline_risk_score":55,"risk_score":55,"severity":"Guarded","dominant_driver":"Brazil industrial and offshore energy logistics exposure","linked_chokepoints":["Atlantic Corridor"],"primary_commodities":["Containerized Goods","Crude Oil","Industrial Goods"]},
    {"port_name":"Port of Itajaí","country":"Brazil","iso3":"BRA","region":"Latin America","latitude":-26.9101,"longitude":-48.6705,"port_type":"container","strategic_importance":72,"baseline_risk_score":54,"risk_score":54,"severity":"Guarded","dominant_driver":"Southern Brazil container and food export exposure","linked_chokepoints":["Atlantic Corridor"],"primary_commodities":["Containerized Goods","Meat","Consumer Goods"]},

    {"port_name":"Port of Callao","country":"Peru","iso3":"PER","region":"Latin America","latitude":-12.0464,"longitude":-77.1428,"port_type":"container/bulk","strategic_importance":80,"baseline_risk_score":58,"risk_score":58,"severity":"Guarded","dominant_driver":"Peru trade gateway and Pacific commodity export exposure","linked_chokepoints":["Pacific Corridor","Panama Canal"],"primary_commodities":["Copper","Fishmeal","Containerized Goods"]},
    {"port_name":"Port of San Antonio","country":"Chile","iso3":"CHL","region":"Latin America","latitude":-33.5922,"longitude":-71.6217,"port_type":"container","strategic_importance":78,"baseline_risk_score":55,"risk_score":55,"severity":"Guarded","dominant_driver":"Chile container gateway and Pacific export corridor exposure","linked_chokepoints":["Pacific Corridor","Panama Canal"],"primary_commodities":["Copper","Fruit","Containerized Goods"]},
    {"port_name":"Port of Valparaíso","country":"Chile","iso3":"CHL","region":"Latin America","latitude":-33.0472,"longitude":-71.6127,"port_type":"container","strategic_importance":72,"baseline_risk_score":54,"risk_score":54,"severity":"Guarded","dominant_driver":"Central Chile logistics and Pacific trade exposure","linked_chokepoints":["Pacific Corridor","Panama Canal"],"primary_commodities":["Fruit","Wine","Containerized Goods"]},

    {"port_name":"Port of Cartagena Colombia","country":"Colombia","iso3":"COL","region":"Latin America","latitude":10.3910,"longitude":-75.4794,"port_type":"container/transshipment","strategic_importance":82,"baseline_risk_score":59,"risk_score":59,"severity":"Guarded","dominant_driver":"Caribbean transshipment and Panama Canal proximity","linked_chokepoints":["Panama Canal","Caribbean Corridor"],"primary_commodities":["Containerized Goods","Chemicals","Consumer Goods"]},
    {"port_name":"Port of Buenaventura","country":"Colombia","iso3":"COL","region":"Latin America","latitude":3.8801,"longitude":-77.0312,"port_type":"container/bulk","strategic_importance":76,"baseline_risk_score":61,"risk_score":61,"severity":"Elevated","dominant_driver":"Colombia Pacific gateway and internal logistics/security exposure","linked_chokepoints":["Pacific Corridor","Panama Canal"],"primary_commodities":["Containerized Goods","Coffee","Bulk Goods"]},

    {"port_name":"Port of Colón","country":"Panama","iso3":"PAN","region":"Latin America","latitude":9.3592,"longitude":-79.9014,"port_type":"container/transshipment","strategic_importance":88,"baseline_risk_score":66,"risk_score":66,"severity":"Elevated","dominant_driver":"Panama Canal Atlantic gateway and transshipment concentration","linked_chokepoints":["Panama Canal","Caribbean Corridor"],"primary_commodities":["Containerized Goods","Consumer Goods","Electronics"]},
    {"port_name":"Port of Balboa","country":"Panama","iso3":"PAN","region":"Latin America","latitude":8.9500,"longitude":-79.5667,"port_type":"container/transshipment","strategic_importance":86,"baseline_risk_score":66,"risk_score":66,"severity":"Elevated","dominant_driver":"Panama Canal Pacific gateway and transshipment concentration","linked_chokepoints":["Panama Canal","Pacific Corridor"],"primary_commodities":["Containerized Goods","Consumer Goods","Electronics"]},

    {"port_name":"Port of Buenos Aires","country":"Argentina","iso3":"ARG","region":"Latin America","latitude":-34.6037,"longitude":-58.3816,"port_type":"container/bulk","strategic_importance":76,"baseline_risk_score":57,"risk_score":57,"severity":"Guarded","dominant_driver":"Argentina trade gateway and macro/logistics exposure","linked_chokepoints":["Atlantic Corridor"],"primary_commodities":["Grain","Beef","Containerized Goods"]},
    {"port_name":"Port of Rosario","country":"Argentina","iso3":"ARG","region":"Latin America","latitude":-32.9442,"longitude":-60.6505,"port_type":"bulk/agricultural","strategic_importance":74,"baseline_risk_score":56,"risk_score":56,"severity":"Guarded","dominant_driver":"Paraná River agricultural export corridor exposure","linked_chokepoints":["Paraná River","Atlantic Corridor"],"primary_commodities":["Soybeans","Corn","Wheat"]},

    {"port_name":"Port of Guayaquil","country":"Ecuador","iso3":"ECU","region":"Latin America","latitude":-2.1894,"longitude":-79.8891,"port_type":"container/agricultural","strategic_importance":72,"baseline_risk_score":57,"risk_score":57,"severity":"Guarded","dominant_driver":"Ecuador export gateway and Pacific corridor exposure","linked_chokepoints":["Pacific Corridor","Panama Canal"],"primary_commodities":["Bananas","Shrimp","Containerized Goods"]},
    {"port_name":"Port of Montevideo","country":"Uruguay","iso3":"URY","region":"Latin America","latitude":-34.9011,"longitude":-56.1645,"port_type":"container/transshipment","strategic_importance":68,"baseline_risk_score":52,"risk_score":52,"severity":"Guarded","dominant_driver":"Southern Cone logistics and Atlantic exposure","linked_chokepoints":["Atlantic Corridor"],"primary_commodities":["Containerized Goods","Meat","Agricultural Goods"]},
    {"port_name":"Port of Kingston","country":"Jamaica","iso3":"JAM","region":"Latin America","latitude":17.9712,"longitude":-76.7936,"port_type":"container/transshipment","strategic_importance":70,"baseline_risk_score":55,"risk_score":55,"severity":"Guarded","dominant_driver":"Caribbean transshipment and hurricane exposure","linked_chokepoints":["Caribbean Corridor","Panama Canal"],"primary_commodities":["Containerized Goods","Consumer Goods","Food"]},
    {"port_name":"Port of Freeport Bahamas","country":"Bahamas","iso3":"BHS","region":"Latin America","latitude":26.5333,"longitude":-78.7000,"port_type":"container/transshipment","strategic_importance":68,"baseline_risk_score":55,"risk_score":55,"severity":"Guarded","dominant_driver":"Caribbean transshipment and hurricane exposure","linked_chokepoints":["Caribbean Corridor","Atlantic Corridor"],"primary_commodities":["Containerized Goods","Consumer Goods","Electronics"]},
    {"port_name":"Port of Caucedo","country":"Dominican Republic","iso3":"DOM","region":"Latin America","latitude":18.4260,"longitude":-69.6220,"port_type":"container/logistics","strategic_importance":68,"baseline_risk_score":54,"risk_score":54,"severity":"Guarded","dominant_driver":"Caribbean logistics hub and hurricane exposure","linked_chokepoints":["Caribbean Corridor","Panama Canal"],"primary_commodities":["Containerized Goods","Consumer Goods","Textiles"]}
]

def seed_latin_america_ports():
    supabase.table("sc_master_ports").upsert(
        LATIN_AMERICA_PORTS,
        on_conflict="port_name"
    ).execute()
    print({
        "status": "success",
        "ports_seeded": len(LATIN_AMERICA_PORTS),
        "region": "Latin America"
    })

if __name__ == "__main__":
    seed_latin_america_ports()

OCEANIA_PORTS = [
    {"port_name":"Port of Melbourne","country":"Australia","iso3":"AUS","region":"Oceania","latitude":-37.8136,"longitude":144.9631,"port_type":"container","strategic_importance":84,"baseline_risk_score":54,"risk_score":54,"severity":"Guarded","dominant_driver":"Australia container gateway and Asia-Pacific trade exposure","linked_chokepoints":["Pacific Corridor","Strait of Malacca"],"primary_commodities":["Containerized Goods","Consumer Goods","Food"]},
    {"port_name":"Port Botany","country":"Australia","iso3":"AUS","region":"Oceania","latitude":-33.9667,"longitude":151.2167,"port_type":"container","strategic_importance":82,"baseline_risk_score":54,"risk_score":54,"severity":"Guarded","dominant_driver":"Sydney import gateway and Pacific route exposure","linked_chokepoints":["Pacific Corridor"],"primary_commodities":["Containerized Goods","Consumer Goods","Electronics"]},
    {"port_name":"Port of Brisbane","country":"Australia","iso3":"AUS","region":"Oceania","latitude":-27.3810,"longitude":153.1670,"port_type":"container/bulk","strategic_importance":78,"baseline_risk_score":53,"risk_score":53,"severity":"Guarded","dominant_driver":"Queensland trade gateway and Pacific weather exposure","linked_chokepoints":["Pacific Corridor","Coral Sea"],"primary_commodities":["Containerized Goods","Coal","Agricultural Goods"]},
    {"port_name":"Port of Fremantle","country":"Australia","iso3":"AUS","region":"Oceania","latitude":-32.0569,"longitude":115.7439,"port_type":"container/bulk","strategic_importance":76,"baseline_risk_score":52,"risk_score":52,"severity":"Guarded","dominant_driver":"Western Australia Indian Ocean gateway exposure","linked_chokepoints":["Indian Ocean","Strait of Malacca"],"primary_commodities":["Containerized Goods","Iron Ore","Energy Products"]},
    {"port_name":"Port of Adelaide","country":"Australia","iso3":"AUS","region":"Oceania","latitude":-34.8450,"longitude":138.5060,"port_type":"container/bulk","strategic_importance":68,"baseline_risk_score":50,"risk_score":50,"severity":"Guarded","dominant_driver":"South Australia agricultural and industrial logistics exposure","linked_chokepoints":["Southern Ocean","Pacific Corridor"],"primary_commodities":["Grain","Wine","Containerized Goods"]},
    {"port_name":"Port Hedland","country":"Australia","iso3":"AUS","region":"Oceania","latitude":-20.3107,"longitude":118.5878,"port_type":"bulk/minerals","strategic_importance":88,"baseline_risk_score":56,"risk_score":56,"severity":"Guarded","dominant_driver":"Major iron ore export concentration and cyclone exposure","linked_chokepoints":["Indian Ocean","Strait of Malacca"],"primary_commodities":["Iron Ore","Lithium","Bulk Minerals"]},
    {"port_name":"Port of Dampier","country":"Australia","iso3":"AUS","region":"Oceania","latitude":-20.6610,"longitude":116.7060,"port_type":"energy/bulk","strategic_importance":82,"baseline_risk_score":55,"risk_score":55,"severity":"Guarded","dominant_driver":"LNG and iron ore export concentration with cyclone exposure","linked_chokepoints":["Indian Ocean","Strait of Malacca"],"primary_commodities":["LNG","Iron Ore","Energy Products"]},
    {"port_name":"Port of Darwin","country":"Australia","iso3":"AUS","region":"Oceania","latitude":-12.4634,"longitude":130.8456,"port_type":"energy/strategic","strategic_importance":74,"baseline_risk_score":57,"risk_score":57,"severity":"Guarded","dominant_driver":"Northern Australia strategic logistics and Indo-Pacific exposure","linked_chokepoints":["Timor Sea","Strait of Malacca"],"primary_commodities":["LNG","Defense Logistics","Containerized Goods"]},

    {"port_name":"Port of Auckland","country":"New Zealand","iso3":"NZL","region":"Oceania","latitude":-36.8436,"longitude":174.7669,"port_type":"container","strategic_importance":74,"baseline_risk_score":50,"risk_score":50,"severity":"Guarded","dominant_driver":"New Zealand import gateway and Pacific route exposure","linked_chokepoints":["Pacific Corridor"],"primary_commodities":["Containerized Goods","Food","Consumer Goods"]},
    {"port_name":"Port of Tauranga","country":"New Zealand","iso3":"NZL","region":"Oceania","latitude":-37.6550,"longitude":176.1830,"port_type":"container/bulk","strategic_importance":78,"baseline_risk_score":51,"risk_score":51,"severity":"Guarded","dominant_driver":"New Zealand export gateway and Pacific trade exposure","linked_chokepoints":["Pacific Corridor"],"primary_commodities":["Dairy","Timber","Containerized Goods"]},
    {"port_name":"Lyttelton Port","country":"New Zealand","iso3":"NZL","region":"Oceania","latitude":-43.6000,"longitude":172.7167,"port_type":"container/bulk","strategic_importance":64,"baseline_risk_score":49,"risk_score":49,"severity":"Guarded","dominant_driver":"South Island logistics and agricultural export exposure","linked_chokepoints":["Pacific Corridor"],"primary_commodities":["Dairy","Meat","Containerized Goods"]},

    {"port_name":"Port Moresby","country":"Papua New Guinea","iso3":"PNG","region":"Oceania","latitude":-9.4438,"longitude":147.1803,"port_type":"container/energy","strategic_importance":60,"baseline_risk_score":56,"risk_score":56,"severity":"Guarded","dominant_driver":"PNG import dependency and Pacific island logistics exposure","linked_chokepoints":["Coral Sea","Pacific Corridor"],"primary_commodities":["Containerized Goods","Energy Products","Food"]},
    {"port_name":"Lae Port","country":"Papua New Guinea","iso3":"PNG","region":"Oceania","latitude":-6.7333,"longitude":147.0000,"port_type":"container/bulk","strategic_importance":62,"baseline_risk_score":56,"risk_score":56,"severity":"Guarded","dominant_driver":"PNG commercial gateway and infrastructure exposure","linked_chokepoints":["Pacific Corridor","Coral Sea"],"primary_commodities":["Containerized Goods","Mining Inputs","Food"]},
    {"port_name":"Port of Suva","country":"Fiji","iso3":"FJI","region":"Oceania","latitude":-18.1248,"longitude":178.4501,"port_type":"container","strategic_importance":58,"baseline_risk_score":54,"risk_score":54,"severity":"Guarded","dominant_driver":"Pacific island transshipment and cyclone exposure","linked_chokepoints":["Pacific Corridor"],"primary_commodities":["Containerized Goods","Food","Consumer Goods"]}
]

def seed_oceania_ports():
    supabase.table("sc_master_ports").upsert(
        OCEANIA_PORTS,
        on_conflict="port_name"
    ).execute()
    print({
        "status": "success",
        "ports_seeded": len(OCEANIA_PORTS),
        "region": "Oceania"
    })

if __name__ == "__main__":
    seed_oceania_ports()
