#!/usr/bin/env python3
import argparse
from typing import Optional
from config import load_settings
from models import Context
# Make cli.py runnable directly from inside the fishbuddy folder
import os, sys
if __package__ is None or __package__ == "":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # add current folder to sys.path

# Now import local modules without the package prefix
from config import load_settings
from assistant import AssistantSession
from services.weather import get_current_icon
from services.law import beginner_plan

def prompt(label: str, cast=str, default: Optional[str] = None):
    raw = input(f"{label}" + (f" [{default}]" if default is not None else "") + ": ").strip()
    return cast(raw) if raw else (cast(default) if default is not None else None)

def main():
    parser = argparse.ArgumentParser(description="FishBuddy CLI (interactive, Assistant-powered)")
    parser.add_argument("--assistant-id", help="asst_...; if omitted, uses ASSISTANT_ID from .env/env")
    parser.add_argument("--lat", type=float, help="Latitude for weather (optional)")
    parser.add_argument("--lon", type=float, help="Longitude for weather (optional)")
    parser.add_argument("--canton", type=str, help="Swiss canton code or name (e.g., ZH, BE, GE, TI)")
    parser.add_argument("--level", type=str, choices=["Beginner", "Intermediate", "Expert"], help="Experience level")
    parser.add_argument("--waterbody", type=str, help="Name of river or lake")
    parser.add_argument("--stay-days", type=int, help="Planned stay length in days")
    args = parser.parse_args()

    cfg = load_settings()
    api_key = cfg["OPENAI_API_KEY"]
    assistant_id = args.assistant_id or cfg["ASSISTANT_ID"]
    if not api_key:
        print("Missing OPENAI_API_KEY. Put it in .env or your environment.")
        return
    if not assistant_id:
        assistant_id = prompt("Assistant ID (asst_...)", str)

    # Interactive capture if fields omitted
    level = args.level or prompt("Level (Beginner/Intermediate/Expert)", str, "Beginner")
    canton = args.canton or prompt("Canton (e.g., ZH, BE, GE, TI)")
    waterbody = args.waterbody or prompt("Body of water (e.g., Limmat, Thunersee)", str, "Unknown")

    lat = args.lat if args.lat is not None else prompt("Latitude (empty to skip weather)", float, None)
    lon = args.lon if args.lon is not None else prompt("Longitude (empty to skip weather)", float, None)

    conditions = {"note": "No coordinates provided; skipping live weather."}
    if lat is not None and lon is not None:
        try:
            conditions = get_current_icon(lat, lon)
        except Exception as e:
            conditions = {"error": f"weather_unavailable: {e.__class__.__name__}"}

    stay_days = args.stay_days if args.stay_days is not None else prompt("Stay length (days)", int, 3)
    plan = beginner_plan(canton, stay_days)

    ctx = Context(
        level=level,
        canton=canton,
        waterbody=waterbody,
        location=(None if lat is None or lon is None else {"lat": lat, "lon": lon}),
        conditions=conditions,
        licence={"local_plan": plan, "stay_days": stay_days},
    )

    session = AssistantSession(api_key=api_key, assistant_id=assistant_id)
    print("\nType questions (e.g., 'What licence do I need?', 'What to bring?', 'Where to try now?'); type 'exit' to quit.\n")

    while True:
        q = input("You: ").strip()
        if not q:
            continue
        if q.lower() in ("exit", "quit", "q"):
            break
        reply = session.ask(context=ctx.__dict__, question=q)
        print("\nAssistant:\n" + reply + "\n")

if __name__ == "__main__":
    main()
