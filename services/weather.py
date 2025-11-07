# services/weather.py
import requests

def get_weather_by_place(place: str, language: str = "de", timeout: float = 10.0) -> dict:
    from .geocode import geocode_place
    g = geocode_place(place, language=language, timeout=timeout)
    if not g:
        return {"error": "geocode_failed"}
    url = "https://api.open-meteo.com/v1/icon"
    params = {
        "latitude": g["lat"], "longitude": g["lon"],
        "current": ["temperature_2m", "wind_speed_10m", "precipitation"],
        "timezone": "Europe/Zurich"
    }
    r = requests.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    cur = (r.json() or {}).get("current", {}) or {}
    return {"place": g["name"], "air_temp_c": cur.get("temperature_2m"),
            "wind_ms": cur.get("wind_speed_10m"), "precip_mm": cur.get("precipitation")}
