# tools.py
import json

def geocode_place(name: str, language: str = "de") -> str:
    """Geocode a place name to coordinates."""
    try:
        from services.geocode import geocode_place as _geocode_place
        result = _geocode_place(name, language=language)
        if isinstance(result, dict):
            return json.dumps(result)
        return result
    except Exception as e:
        return json.dumps({"error": f"geocode_tool_failed: {str(e)}"})

def canton_from_place(name: str, language: str = "de") -> str:
    """Get canton from a place name."""
    try:
        from services.geocode import canton_from_place as _canton_from_place
        result = _canton_from_place(name, language=language)
        if isinstance(result, dict):
            return json.dumps(result)
        return result
    except Exception as e:
        return json.dumps({"error": f"canton_tool_failed: {str(e)}"})

def get_weather_by_place(name: str, language: str = "de") -> str:
    """Get current weather for a place."""
    try:
        from services.weather import get_weather_by_place as _get_weather
        result = _get_weather(name, language=language)
        if isinstance(result, dict):
            return json.dumps(result)
        return result
    except Exception as e:
        return json.dumps({"error": f"weather_tool_failed: {str(e)}"})

def get_water_data(name: str, language: str = "de") -> str:
    """Get water temperature and flow data for a place."""
    try:
        from services.hydro import get_water_data as _get_hydro
        result = _get_hydro(name, language=language)
        if isinstance(result, dict):
            return json.dumps(result)
        return result
    except Exception as e:
        return json.dumps({"error": f"hydro_tool_failed: {str(e)}"})

def list_species_by_place(name: str, language: str = "de") -> str:
    """List fish species found near a place."""
    try:
        from services.species import list_species_by_place as _list_species
        result = _list_species(name, language=language)
        if isinstance(result, dict):
            return json.dumps(result)
        return result
    except Exception as e:
        return json.dumps({"error": f"species_tool_failed: {str(e)}"})

def check_rules(canton: str, species: str = "", language: str = "de") -> str:
    """Check fishing rules for a canton and species."""
    try:
        from services.rules import check_rules as _check_rules
        result = _check_rules(canton, species=species, language=language)
        if isinstance(result, dict):
            return json.dumps(result)
        return result
    except Exception as e:
        return json.dumps({"error": f"rules_tool_failed: {str(e)}"})
