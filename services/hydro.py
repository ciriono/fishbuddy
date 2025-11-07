import math, requests

def get_water_data(place: str, language: str = "de", timeout: float = 10.0) -> dict:
    """
    Returns nearest station’s basic hydrology (water temperature, discharge) for the given place.
    Uses FOEN public hydrology endpoints available online (or a JSON proxy when needed).
    """
    from .geocode import geocode_place
    g = geocode_place(place, language=language, timeout=timeout)
    if not g:
        return {"error": "geocode_failed"}
    # Example approach: proxy with a public JSON that aggregates FOEN hydrodaten to simplify integration
    # Note: replace with your chosen official/open endpoint once you pick a stable dataset
    stations_url = "https://api.existenz.ch/hydro/locations"
    stations = requests.get(stations_url, timeout=timeout).json()
    # Find nearest by haversine (rough)
    def dkm(a,b): 
        import math
        return 2*6371*math.asin(math.sqrt(
            math.sin(math.radians((a["lat"]-b["lat"])/2))**2 +
            math.cos(math.radians(a["lat"]))*math.cos(math.radians(b["lat"]))*
            math.sin(math.radians((a["lon"]-b["lon"])/2))**2))
    target = {"lat": g["lat"], "lon": g["lon"]}
    nearest = min(stations, key=lambda s: dkm({"lat": s["lat"], "lon": s["lon"]}, target))
    latest = requests.get(f'https://api.existenz.ch/hydro/{nearest["id"]}', timeout=timeout).json()
    return {"place": g["name"], "station_id": nearest["id"], "station_name": nearest["name"],
            "water_temp_c": latest.get("water_temp_c"), "discharge_m3s": latest.get("discharge_m3s")}
