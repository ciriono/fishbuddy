# services/hydro.py
import requests
import json
import math
import os

def _haversine_km(lat1, lon1, lat2, lon2) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    return 2*R*math.asin(math.sqrt(a))

def get_water_data(name: str, language: str = "de", timeout: float = 10.0) -> dict:
    """
    Resolve place then return nearby hydrology (water temp/flow).
    Falls back gracefully if hydro proxy is unavailable.
    """
    from .geocode import geocode_place
    
    try:
        g = geocode_place(name, language=language, timeout=timeout)
        if "error" in g:
            return json.dumps({"error": "geocode_failed", "place": name})
        
        # Try to fetch hydro data from a proxy or fallback gracefully
        base = os.environ.get("FOEN_PROXY_BASE", "https://api.existenz.ch/hydro")
        
        try:
            stations = requests.get(f"{base}/locations", timeout=timeout).json()
            if not stations:
                return json.dumps({
                    "place": g.get("name"),
                    "note": "No hydrology data available; try again later."
                })
            
            tgt = min(stations, key=lambda s: _haversine_km(g["lat"], g["lon"], s.get("lat", 0), s.get("lon", 0)))
            latest = requests.get(f'{base}/{tgt["id"]}', timeout=timeout).json()
            
            result = {
                "place": g.get("name"),
                "station_id": tgt.get("id"),
                "station_name": tgt.get("name"),
                "water_temp_c": latest.get("water_temp_c"),
                "discharge_m3s": latest.get("discharge_m3s")
            }
            return json.dumps(result)
        
        except Exception as e:
            # Graceful fallback
            return json.dumps({
                "place": g.get("name"),
                "note": f"Water data unavailable ({e.__class__.__name__}); check FOEN station data manually."
            })
    
    except Exception as e:
        return json.dumps({"error": f"hydro_failed: {str(e)}", "place": name})
