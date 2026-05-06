import requests
import xml.etree.ElementTree as ET

OFAC_SDN_XML = "https://www.treasury.gov/ofac/downloads/sdn.xml"


def fetch_ofac_sanctions(limit: int = 25):
    try:
        r = requests.get(OFAC_SDN_XML, timeout=30)
        r.raise_for_status()

        root = ET.fromstring(r.content)
        results = []

        for entry in root.findall(".//{*}sdnEntry")[:limit]:
            first = entry.findtext(".//{*}firstName") or ""
            last = entry.findtext(".//{*}lastName") or ""
            sdn_type = entry.findtext(".//{*}sdnType")
            program = entry.findtext(".//{*}programList/{*}program")

            results.append({
                "source": "OFAC",
                "signal_type": "sanctions_exposure",
                "name": f"{first} {last}".strip() or "Unknown",
                "sdn_type": sdn_type,
                "program": program,
                "severity_score": 8,
                "reliability_score": 9,
                "summary": "OFAC sanctions exposure signal"
            })

        return results

    except Exception as e:
        return {
            "status": "error",
            "source": "OFAC",
            "message": str(e)
        }
