import requests

def get_current_icon(lat: float, lon: float, timeout: float = 10.0) -> dict:
    """
    Fetches current temperature (°C), wind (m/s), precipitation (mm) from the
    ICON model (MeteoSwiss via Open‑Meteo). No API key required.
    """
    url = "https://api.open-meteo.com/v1/icon"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": ["temperature_2m", "wind_speed_10m", "precipitation"],
        "timezone": "Europe/Zurich",
    }
    r = requests.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    cur = (r.json() or {}).get("current", {}) or {}
    return {
        "air_temp_c": cur.get("temperature_2m"),
        "wind_ms": cur.get("wind_speed_10m"),
        "precip_mm": cur.get("precipitation"),
    }
