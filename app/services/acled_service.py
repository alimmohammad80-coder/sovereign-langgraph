import os
import requests
from dotenv import load_dotenv

load_dotenv(".env")

TOKEN_URL = "https://acleddata.com/oauth/token"
ACLED_READ_URL = "https://acleddata.com/api/acled/read?_format=json"

ACLED_EMAIL = os.getenv("ACLED_EMAIL")
ACLED_PASSWORD = os.getenv("ACLED_PASSWORD")

def get_acled_token():
    if not ACLED_EMAIL or not ACLED_PASSWORD:
        raise ValueError("ACLED_EMAIL or ACLED_PASSWORD missing in .env")

    resp = requests.post(
        TOKEN_URL,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "username": ACLED_EMAIL,
            "password": ACLED_PASSWORD,
            "grant_type": "password",
            "client_id": "acled",
        },
        timeout=60,
    )

    if not resp.ok:
        raise ValueError(f"ACLED token error {resp.status_code}: {resp.text}")

    data = resp.json()
    token = data.get("access_token")
    if not token:
        raise ValueError(f"No access_token in response: {data}")

    return token

def fetch_acled(country="Pakistan", limit=10):
    token = get_acled_token()

    resp = requests.get(
        ACLED_READ_URL,
        params={
            "country": country,
            "limit": limit,
            "fields": "event_id_cnty|event_date|event_type|sub_event_type|country|admin1|admin2|actor1|actor2|fatalities|latitude|longitude|source|notes"
        },
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        timeout=60,
    )

    if not resp.ok:
        raise ValueError(f"ACLED read error {resp.status_code}: {resp.text}")

    return resp.json()
