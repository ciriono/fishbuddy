#!/usr/bin/env python3
import os, sys
if __package__ is None or __package__ == "":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import argparse
from typing import Optional, Dict, Any

if __package__:
    from .config import load_settings
    from .assistant import AssistantSession
else:
    from config import load_settings
    from assistant import AssistantSession

def prompt(label: str, cast=str, default: Optional[str] = None):
    raw = input(f"{label}" + (f" [{default}]" if default is not None else "") + ": ").strip()
    return cast(raw) if raw else (cast(default) if default is not None else None)

def main():
    parser = argparse.ArgumentParser(description="FischBuddy CLI (Schweizer Angelbegleiter)")
    parser.add_argument("--assistant-id", help="asst_...; if omitted, uses ASSISTANT_ID from .env/env")
    parser.add_argument("--place", type=str, help="Ort/Region (z.B. 'Zürichsee', 'Aare Bern')")
    parser.add_argument("--canton", type=str, help="Schweizer Kanton (z.B. ZH, BE, GE, TI)")
    parser.add_argument("--level", type=str, choices=["Beginner", "Intermediate", "Expert"], help="Erfahrungslevel")
    parser.add_argument("--waterbody", type=str, help="Fluss oder See")
    args = parser.parse_args()

    cfg = load_settings()
    api_key = os.getenv("OPENAI_API_KEY") or cfg.get("OPENAI_API_KEY")
    assistant_id = args.assistant_id or os.getenv("ASSISTANT_ID") or cfg.get("ASSISTANT_ID")

    if not api_key:
        print("Missing OPENAI_API_KEY. Put it in .env or your environment.")
        return
    if not assistant_id:
        assistant_id = prompt("Assistant ID (asst_...)", str)

    level = args.level or prompt("Level (Beginner/Intermediate/Expert)", str, "Beginner")
    waterbody = args.waterbody or prompt("Gewässer (z.B. Limmat, Thunersee)", str, "Unknown")
    place = args.place or prompt("Ort/Region (z.B. Zürich, Berner Oberland)", str, None)
    canton = args.canton or prompt("Kanton (z.B. ZH, BE, GE, TI) (optional)", str, None)

    # Build context for the Assistant (no stay_days for residents)
    context = {
        "level": level,
        "canton": canton or "unbekannt",
        "waterbody": waterbody,
        "place": place or "unbekannt",
        "user_type": "resident",  # always resident now
    }

    # Start Assistant session and interactive loop
    session = AssistantSession(api_key=api_key, assistant_id=assistant_id)
    print("\nFragen stellen (z.B. 'Welche Fische im Zürichsee?', 'Wetter jetzt?'); 'exit' zum Beenden.\n")

    while True:
        q = input("Du: ").strip()
        if not q:
            continue
        if q.lower() in ("exit", "quit", "q", "beenden"):
            break
        reply = session.ask(context=context, question=q)
        print("\nFischBuddy:\n" + reply + "\n")

if __name__ == "__main__":
    main()
