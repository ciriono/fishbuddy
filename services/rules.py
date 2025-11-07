import json, os
from datetime import date

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "rules.json")

def load_rules() -> dict:
    if not os.path.exists(DATA_PATH):
        return {"cantons": {}}
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def check_rules(canton: str, species: str, method: str, date_iso: str) -> dict:
    rules = load_rules()
    c = (canton or "").strip().lower()
    s = (species or "").strip().lower()
    m = (method or "").strip().lower()
    day = date.fromisoformat(date_iso)
    entry = (rules.get("cantons", {}).get(c, {}).get("species", {}).get(s, {}))
    closed_ranges = entry.get("closed_seasons", [])
    min_size = entry.get("min_size_cm")
    bag = entry.get("bag_limit")
    closed = any(r["from"] <= date_iso <= r["to"] for r in closed_ranges)
    legal = not closed and (method in entry.get("methods_allowed", []) if entry.get("methods_allowed") else True)
    return {"legal": legal, "closed": closed, "min_size_cm": min_size, "bag_limit": bag}
