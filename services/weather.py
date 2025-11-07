# services/weather.py
import requests
import json

def get_weather_by_place(name: str, language: str = "de", timeout: float = 10.0) -> dict:
    """
    Geocode then fetch current weather from Open-Meteo forecast API.
    Returns {"place", "air_temp_c", "wind_ms", "precip_mm"}.
    """
    from .geocode import geocode_place
    
    try:
        g = geocode_place(name, language=language, timeout=timeout)
        if "error" in g:
            return {"error": "geocode_failed", "place": name}
        
        # Use the main forecast endpoint (wider geographic coverage)
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": g["lat"],
            "longitude": g["lon"],
            "current": "temperature_2m,wind_speed_10m,precipitation",
            "timezone": "Europe/Zurich",
        }
        
        r = requests.get(url, params=params, timeout=timeout)
        r.raise_for_status()
        data = r.json() or {}
        cur = data.get("current", {}) or {}
        
        result = {
            "place": g.get("name"),
            "air_temp_c": cur.get("temperature_2m"),
            "wind_ms": cur.get("wind_speed_10m"),
            "precip_mm": cur.get("precipitation"),
        }
        
        # Return as JSON string for tool compatibility
        return json.dumps(result)
    
    except requests.exceptions.Timeout:
        return json.dumps({"error": "weather_api_timeout", "place": name})
    except requests.exceptions.RequestException as e:
        return json.dumps({"error": f"weather_api_error: {str(e)}", "place": name})
    except Exception as e:
        return json.dumps({"error": f"weather_failed: {str(e)}", "place": name})
