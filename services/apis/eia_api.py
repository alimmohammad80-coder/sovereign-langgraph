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

        data = r.json()

        if isinstance(data, dict):
            request_info = data.get("request")
            if isinstance(request_info, dict):
                params_info = request_info.get("params")
                if isinstance(params_info, dict) and "api_key" in params_info:
                    params_info["api_key"] = "REDACTED"

        return {
            "source": "EIA",
            "signal_type": "energy_market_signal",
            "severity_score": 7,
            "reliability_score": 9,
            "summary": "Energy price and petroleum market signal from EIA",
            "data": data
        }

    except Exception as e:
        return {
            "status": "error",
            "source": "EIA",
            "message": str(e)
        }
