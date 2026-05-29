import requests


def fetch_marine_weather_signal(
    latitude: float = 26.5667,
    longitude: float = 56.2500,
    location_name: str = "Strait of Hormuz"
):
    """
    Fetch marine weather/wave risk signal for a chokepoint.
    Default coordinates are for the Strait of Hormuz.
    """

    url = "https://marine-api.open-meteo.com/v1/marine"

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": "wave_height,wave_direction,wave_period,wind_wave_height,swell_wave_height",
        "forecast_days": 3,
        "timezone": "auto"
    }

    try:
        r = requests.get(url, params=params, timeout=25)
        r.raise_for_status()
        data = r.json()

        hourly = data.get("hourly", {})
        wave_heights = hourly.get("wave_height", []) or []
        max_wave_height = max(wave_heights) if wave_heights else None

        if max_wave_height is None:
            severity = "Unknown"
            severity_score = 3
        elif max_wave_height >= 4:
            severity = "High"
            severity_score = 8
        elif max_wave_height >= 2.5:
            severity = "Moderate"
            severity_score = 6
        else:
            severity = "Low"
            severity_score = 3

        return {
            "source": "Open-Meteo Marine Weather",
            "signal_type": "marine_weather_disruption",
            "location_name": location_name,
            "latitude": latitude,
            "longitude": longitude,
            "max_wave_height_m": max_wave_height,
            "severity": severity,
            "severity_score": severity_score,
            "reliability_score": 7,
            "summary": f"Marine weather signal for {location_name}. Maximum forecast wave height: {max_wave_height}m.",
            "data": data
        }

    except Exception as e:
        return {
            "status": "error",
            "source": "Open-Meteo Marine Weather",
            "message": str(e)
        }
