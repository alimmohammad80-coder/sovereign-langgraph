import os
import requests
from dotenv import load_dotenv

load_dotenv()

EIA_API_KEY = os.getenv("EIA_API_KEY")


def fetch_eia_energy_signals():
    if not EIA_API_KEY:
        return {
            "status": "missing_api_key",
            "source": "EIA",
            "message": "EIA_API_KEY is missing."
        }

    url = "https://api.eia.gov/v2/petroleum/pri/spt/data/"

    params = {
        "api_key": EIA_API_KEY,
        "frequency": "weekly",
        "data[0]": "value",
        "sort[0][column]": "period",
        "sort[0][direction]": "desc",
        "offset": 0,
        "length": 10
    }

    try:
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()

        return {
            "source": "EIA",
            "signal_type": "energy_market_signal",
            "severity_score": 7,
            "reliability_score": 9,
            "summary": "Energy price and petroleum market signal from EIA",
            "data": r.json()
        }

    except Exception as e:
        return {
            "status": "error",
            "source": "EIA",
            "message": str(e)
        }
