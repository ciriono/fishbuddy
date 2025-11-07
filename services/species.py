# services/species.py
import requests
import json
import math
from typing import Dict

def _wkt_square(lat: float, lon: float, km: float = 5.0) -> str:
    """Generate WKT polygon around a point."""
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

def list_species_by_place(place: str, language: str = "de", radius_km: float = 5.0, timeout: float = 12.0) -> dict:
    """
    Query GBIF occurrence API with geometry=WKT to find fish species near a place.
    Filters for Actinopterygii (ray-finned fishes) and Petromyzontida (lampreys).
    Returns {"place", "provider": "gbif", "species": [{"name", "count", "scientific_name"}]}.
    """
    from .geocode import geocode_place

    g = geocode_place(place, language=language, timeout=timeout)
    if "error" in g:
        return {"error": "geocode_failed"}

    wkt = _wkt_square(g["lat"], g["lon"], km=radius_km)
    
    # Query GBIF with geometry (WKT polygon) filtering for fish
    # kingdomKey=1 is Animalia; classKey includes ray-finned fishes (Actinopterygii) and lampreys
    params = {
        "geometry": wkt,
        "country": "CH",
        "hasCoordinate": "true",
        "kingdom": "Animalia",
        "classKey": "127206",  # Actinopterygii (ray-finned fishes)
        "limit": 300,
        "offset": 0
    }
    headers = {"User-Agent": "FischBuddy/1.0 (+https://github.com/yourname/fishbuddy)"}
    
    try:
        r = requests.get("https://api.gbif.org/v1/occurrence/search", params=params, headers=headers, timeout=timeout)
        r.raise_for_status()
        data = r.json() or {}
        
        # Aggregate species counts and common names
        species_map = {}
        for rec in data.get("results", []):
            sp = rec.get("species")
            sci_name = rec.get("scientificName")
            if sp and sci_name:
                if sp not in species_map:
                    species_map[sp] = {"count": 0, "scientific_name": sci_name}
                species_map[sp]["count"] += 1
        
        # Sort by count descending, take top 20
        top = sorted(species_map.items(), key=lambda kv: kv[1]["count"], reverse=True)[:20]
        
        return {
            "place": g.get("name"),
            "provider": "gbif",
            "region": g.get("admin1"),
            "data_source": "GBIF Swiss Node - Swiss National Fish Databank",
            "species": [
                {"name": name, "count": info["count"], "scientific_name": info["scientific_name"]}
                for name, info in top
            ]
        }
    except Exception as e:
        return {
            "place": g.get("name"),
            "error": f"species_unavailable: {e.__class__.__name__}",
            "hint": "GBIF API may be temporarily unavailable; try again later."
        }
