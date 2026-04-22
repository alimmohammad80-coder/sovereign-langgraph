import os
import requests
from dotenv import load_dotenv

load_dotenv(".env")

print("EMAIL:", os.getenv("ACLED_EMAIL"))
print("PASSWORD_LEN:", len(os.getenv("ACLED_PASSWORD") or ""))

resp = requests.post(
    "https://acleddata.com/oauth/token",
    headers={"Content-Type": "application/x-www-form-urlencoded"},
    data={
        "username": os.getenv("ACLED_EMAIL"),
        "password": os.getenv("ACLED_PASSWORD"),
        "grant_type": "password",
        "client_id": "acled",
    },
    timeout=60,
)

print(resp.status_code)
print(resp.text)
