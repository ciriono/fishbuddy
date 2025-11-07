# services/geocode.py
import requests

def geocode_place(name: str, count: int = 1, language: str = "de", timeout: float = 10.0) -> dict:
    url = "https://geocoding-api.open-meteo.com/v1/search"
    r = requests.get(url, params={"name": name, "count": count, "language": language, "format": "json"}, timeout=timeout)
    r.raise_for_status()
    res = (r.json() or {}).get("results") or []
    if not res:
        return {}
    top = res[0]
    return {"lat": top.get("latitude"), "lon": top.get("longitude"), "name": top.get("name"),
            "admin1": top.get("admin1"), "country_code": top.get("country_code")}

def canton_from_coords(lat: float, lon: float, timeout: float = 10.0) -> str | None:
    url = "https://api3.geo.admin.ch/rest/services/api/MapServer/identify"
    params = {
        "geometryType": "esriGeometryPoint",
        "geometry": f"{lon},{lat}",
        "mapExtent": f"{lon-0.01},{lat-0.01},{lon+0.01},{lat+0.01}",
        "tolerance": 0,
        "layers": "all:ch.swisstopo.swissboundaries3d-kanton-flaeche.fill",
        "returnGeometry": "false",
        "imageDisplay": "400,400,96",
        "lang": "de"
    }
    r = requests.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    results = (r.json() or {}).get("results") or []
    attrs = results[0].get("attributes") if results else None
    return (attrs.get("kt_kz") or attrs.get("name")) if attrs else None

