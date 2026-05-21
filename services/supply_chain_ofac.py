import requests
import csv
from io import StringIO
from datetime import datetime

OFAC_SDN_CSV = "https://www.treasury.gov/ofac/downloads/sdn.csv"


def fetch_ofac_sdn_matches(country=None, commodity=None, sector=None, limit=10):
    search_terms = [country, commodity, sector]
    search_terms = [str(x).lower() for x in search_terms if x]

    if not search_terms:
        return {
            "ofac_sanctions_signal": False,
            "sanctions_matches": [],
            "ofac_status": "no_search_terms"
        }

    try:
        response = requests.get(OFAC_SDN_CSV, timeout=20)
        response.raise_for_status()

        rows = csv.reader(StringIO(response.text))
        matches = []

        for row in rows:
            joined = " ".join(row).lower()

            if any(term in joined for term in search_terms):
                matches.append({
                    "raw_record": row[:8],
                    "matched_terms": [term for term in search_terms if term in joined]
                })

            if len(matches) >= limit:
                break

        return {
            "ofac_sanctions_signal": len(matches) > 0,
            "sanctions_matches": matches,
            "ofac_status": "connected",
            "checked_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        return {
            "ofac_sanctions_signal": False,
            "sanctions_matches": [],
            "ofac_status": f"error: {str(e)}",
            "checked_at": datetime.utcnow().isoformat()
        }
