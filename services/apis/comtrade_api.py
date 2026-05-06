import os
import requests
from dotenv import load_dotenv

load_dotenv()

UN_COMTRADE_API_KEY = os.getenv("UN_COMTRADE_API_KEY")


def fetch_comtrade_trade_signals(
    reporter_code: str = "156",
    partner_code: str = "0",
    commodity_code: str = "TOTAL",
    period: str = "2023"
):
    if not UN_COMTRADE_API_KEY:
        return {
            "status": "missing_api_key",
            "source": "UN Comtrade",
            "message": "UN_COMTRADE_API_KEY is missing."
        }

    url = "https://comtradeapi.un.org/data/v1/get/C/A/HS"

    params = {
        "reporterCode": reporter_code,
        "partnerCode": partner_code,
        "cmdCode": commodity_code,
        "flowCode": "X",
        "period": period
    }

    headers = {
        "Ocp-Apim-Subscription-Key": UN_COMTRADE_API_KEY
    }

    try:
        r = requests.get(url, params=params, headers=headers, timeout=30)
        r.raise_for_status()

        return {
            "source": "UN Comtrade",
            "signal_type": "trade_dependency_signal",
            "severity_score": 6,
            "reliability_score": 8,
            "summary": "Trade-flow dependency signal from UN Comtrade",
            "data": r.json()
        }

    except Exception as e:
        return {
            "status": "error",
            "source": "UN Comtrade",
            "message": str(e)
        }
