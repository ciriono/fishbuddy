from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class Context:
    level: str
    canton: Optional[str]
    waterbody: Optional[str]
    location: Optional[Dict[str, float]]  # {"lat": float, "lon": float} or None
    conditions: Dict[str, Any]            # weather or note
    licence: Dict[str, Any]               # local plan scaffold
