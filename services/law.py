from typing import Dict

def beginner_plan(canton: str, stay_days: int) -> Dict:
    """
    Minimal scaffold: customize per canton as you collect official details.
    """
    plan = {"steps": [], "notes": []}
    c = (canton or "").strip().lower()

    if stay_days <= 7 and c in ("ti", "ticino"):
        plan["steps"].append("Short stay in Ticino: check tourist licence requirements with local authorities.")
    else:
        plan["steps"].append("Book the SaNa course/exam and obtain the SaNa certificate.")
        plan["steps"].append("Apply for your canton’s fishing licence per local process.")

    plan["notes"] = [
        "Carry required ID and documents per canton.",
        "Confirm waterbody-specific rules and closed seasons.",
    ]
    return plan
