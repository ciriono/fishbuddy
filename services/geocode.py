# services/geocode.py
import requests
import json

def geocode_place(name: str, language: str = "de", timeout: float = 10.0) -> dict:
    """
    Geocode a place name to lat/lon using Open-Meteo Geocoding API.
    Returns {"name", "lat", "lon"} or {"error": "..."}
    """
    try:
        url = "https://geocoding-api.open-meteo.com/v1/search"
        params = {
            "name": name,
            "language": language,
            "count": 1,
            "format": "json"
        }
        
        r = requests.get(url, params=params, timeout=timeout)
        r.raise_for_status()
        data = r.json() or {}
        
        results = data.get("results", [])
        if not results:
            return {"error": f"no_results_for_{name}"}
        
        result = results[0]
        return {
            "name": result.get("name", name),
            "lat": result.get("latitude"),
            "lon": result.get("longitude"),
            "country": result.get("country"),
            "admin1": result.get("admin1"),  # Canton/State
        }
    except requests.exceptions.Timeout:
        return {"error": "geocode_timeout"}
    except requests.exceptions.RequestException as e:
        return {"error": f"geocode_request_failed: {str(e)}"}
    except Exception as e:
        return {"error": f"geocode_failed: {str(e)}"}

def canton_from_place(name: str, language: str = "de", timeout: float = 10.0) -> dict:
    """
    Extract canton/state from a place name using geocoding.
    Returns {"place", "canton"} or {"error": "..."}
    """
    try:
        g = geocode_place(name, language=language, timeout=timeout)
        
        if "error" in g:
            return {"error": g["error"], "place": name}
        
        # Map Swiss cantons
        admin1 = g.get("admin1", "").upper()
        canton_map = {
            "ZURICH": "ZH",
            "BERN": "BE",
            "LUCERNE": "LU",
            "URI": "UR",
            "SCHWYZ": "SZ",
            "OBWALDEN": "OW",
            "NIDWALDEN": "NW",
            "GLARUS": "GL",
            "ZUG": "ZG",
            "FRIBOURG": "FR",
            "SOLOTHURN": "SO",
            "BASEL-STADT": "BS",
            "BASEL-LANDSCHAFT": "BL",
            "SCHAFFHAUSEN": "SH",
            "APPENZELL AUSSERRHODEN": "AR",
            "APPENZELL INNERRHODEN": "AI",
            "ST. GALLEN": "SG",
            "GRAUBUNDEN": "GR",
            "AARGAU": "AG",
            "THURGAU": "TG",
            "TICINO": "TI",
            "VAUD": "VD",
            "VALAIS": "VS",
            "NEUCHATEL": "NE",
            "JURA": "JU",
            "GENEVA": "GE",
        }
        
        canton = canton_map.get(admin1, "UNKNOWN")
        
        return {
            "place": g.get("name"),
            "canton": canton,
            "admin1": admin1
        }
    
    except Exception as e:
        return {"error": f"canton_extraction_failed: {str(e)}", "place": name}
