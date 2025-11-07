# tools.py
import json
import math
import os
from datetime import date
import requests

# ---------------- Geocoding & Canton inference ----------------

def geocode_place(name: str, language: str = "de", timeout: float = 10.0) -> str:
    """
    Open-Meteo Geocoding API; returns {"lat","lon","name","admin1","country_code"} as JSON string.
    """
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {"name": name, "count": 1, "language": language, "format": "json"}
    r = requests.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    data = r.json() or {}
    results = data.get("results") or []
    if not results:
        return json.dumps({"error": "not_found"})
    top = results[0]
    return json.dumps({
        "lat": top.get("latitude"),
        "lon": top.get("longitude"),
        "name": top.get("name"),
        "admin1": top.get("admin1"),
        "country_code": top.get("country_code"),
    })
# Open‑Meteo Geocoding is free and key‑less, ideal for user place input. [web:448]

def canton_from_place(name: str, language: str = "de", timeout: float = 10.0) -> str:
    """
    Geocode then resolve canton with GeoAdmin identify layer; returns {"place","canton"} as JSON.
    """
    g = json.loads(geocode_place(name, language=language, timeout=timeout))
    if "error" in g:
        return json.dumps({"error": "geocode_failed"})
    lat, lon = g.get("lat"), g.get("lon")
    url = "https://api3.geo.admin.ch/rest/services/api/MapServer/identify"
    params = {
        "geometryType": "esriGeometryPoint",
        "geometry": f"{lon},{lat}",
        "mapExtent": f"{lon-0.01},{lat-0.01},{lon+0.01},{lat+0.01}",
        "tolerance": 0,
        "layers": "all:ch.swisstopo.swissboundaries3d-kanton-flaeche.fill",
        "returnGeometry": "false",
        "imageDisplay": "400,400,96",
        "lang": language
    }
    r = requests.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    results = (r.json() or {}).get("results") or []
    if not results:
        return json.dumps({"place": g.get("name"), "canton": None})
    attrs = results[0].get("attributes") or {}
    canton = attrs.get("kt_kz") or attrs.get("name")
    return json.dumps({"place": g.get("name"), "canton": canton})
# GeoAdmin identify can resolve the canton polygon at a point reliably. [web:279]

# ---------------- Weather by place (ICON, key‑free) ----------------

def get_weather_by_place(name: str, language: str = "de", timeout: float = 10.0) -> str:
    """
    Geocode then fetch current ICON weather: air_temp_c, wind_ms, precip_mm; returns JSON.
    """
    g = json.loads(geocode_place(name, language=language, timeout=timeout))
    if "error" in g:
        return json.dumps({"error": "geocode_failed"})
    url = "https://api.open-meteo.com/v1/icon"
    params = {
        "latitude": g["lat"],
        "longitude": g["lon"],
        "current": ["temperature_2m", "wind_speed_10m", "precipitation"],
        "timezone": "Europe/Zurich",
    }
    r = requests.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    cur = (r.json() or {}).get("current", {}) or {}
    return json.dumps({
        "place": g.get("name"),
        "air_temp_c": cur.get("temperature_2m"),
        "wind_ms": cur.get("wind_speed_10m"),
        "precip_mm": cur.get("precipitation"),
    })
# The ICON endpoint is a good, key‑less current weather source for Swiss fishing context. [web:462][web:28]

# ---------------- FOEN hydrology (stable endpoint or proxy) ----------------

def _haversine_km(lat1, lon1, lat2, lon2) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1); dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    return 2*R*math.asin(math.sqrt(a))

def get_water_data(name: str, language: str = "de", timeout: float = 10.0) -> str:
    """
    Resolve place then return nearby hydrology (water temp/flow) via your chosen FOEN endpoint or a proxy; returns JSON.
    """
    g = json.loads(geocode_place(name, language=language, timeout=timeout))
    if "error" in g:
        return json.dumps({"error": "geocode_failed"})
    # Option A (recommended once finalized): FOEN/Hydrodaten official JSON or OGC API endpoint listing stations + latest values. [web:484][web:493]
    # Option B (quick start): use an existing proxy that aggregates FOEN stations and latest readings.
    base = os.environ.get("FOEN_PROXY_BASE", "https://api.existenz.ch/hydro")
    try:
        stations = requests.get(f"{base}/locations", timeout=timeout).json()
        tgt = min(stations, key=lambda s: _haversine_km(g["lat"], g["lon"], s["lat"], s["lon"]))
        latest = requests.get(f'{base}/{tgt["id"]}', timeout=timeout).json()
        return json.dumps({
            "place": g.get("name"),
            "station_id": tgt["id"],
            "station_name": tgt.get("name"),
            "water_temp_c": latest.get("water_temp_c"),
            "discharge_m3s": latest.get("discharge_m3s")
        })
    except Exception as e:
        return json.dumps({"place": g.get("name"), "error": f"hydro_unavailable:{e.__class__.__name__}"})
# FOEN hosts the authoritative hydrology data; you can start with a proxy while you finalize the official endpoint selection. [web:484][web:482][web:493]

# ---------------- Species near place (Info Fauna with GBIF fallback) ----------------

def _wkt_square(lat: float, lon: float, km: float = 5.0) -> str:
    # ~0.009 degrees lat per km; adjust lon by cos(lat)
    dlat = km * 0.009
    dlon = km * 0.009 / max(0.1, math.cos(math.radians(lat)))
    pts = [
        (lon - dlon, lat - dlat),
        (lon + dlon, lat - dlat),
        (lon + dlon, lat + dlat),
        (lon - dlon, lat + dlat),
        (lon - dlon, lat - dlat),
    ]
    return "POLYGON((" + ", ".join(f"{x} {y}" for x,y in pts) + "))"

def list_species_by_place(name: str, language: str = "de", radius_km: float = 5.0, timeout: float = 12.0) -> str:
    """
    Query GBIF for fish species near a place; returns JSON.
    """
    from services.species import list_species_by_place as _list_species
    import json
    result = _list_species(name, language=language, radius_km=radius_km, timeout=timeout)
    return json.dumps(result)


# ---------------- Canton rules (data‑driven with sources) ----------------

_RULES_PATH = os.path.join(os.path.dirname(__file__), "data", "rules.json")

def _load_rules() -> dict:
    if not os.path.exists(_RULES_PATH):
        return {"cantons": {}}
    with open(_RULES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def check_rules(canton: str, species: str, method: str, date_iso: str) -> str:
    """
    Look up rules from data/rules.json; returns legality, closed, min size, bag limit, and sources; returns JSON.
    """
    rules = _load_rules()
    c = (canton or "").strip().lower()
    s = (species or "").strip().lower()
    m = (method or "").strip().lower()
    # Validate date format
    _ = date.fromisoformat(date_iso)

    entry = rules.get("cantons", {}).get(c, {}).get("species", {}).get(s, {}) or {}
    closed_ranges = entry.get("closed_seasons", [])
    min_size = entry.get("min_size_cm")
    bag = entry.get("bag_limit")
    sources = entry.get("sources", [])
    methods_allowed = entry.get("methods_allowed")

    closed = any(r["from"] <= date_iso <= r["to"] for r in closed_ranges)
    legal = (not closed) and (m in methods_allowed if methods_allowed else True)

    return json.dumps({
        "legal": legal,
        "closed": closed,
        "min_size_cm": min_size,
        "bag_limit": bag,
        "sources": sources
    })
# Keeping rules in JSON with per‑entry sources allows updates and traceability to authoritative canton publications. [web:489]
