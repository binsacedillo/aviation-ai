"""
Magnetic Variation Utilities

Provides helpers to convert headings between True and Magnetic, and to
load per-station magnetic variation (declination) from config.

Convention:
- Variation (declination) east is positive, west is negative
- Magnetic = True - variation
"""

from __future__ import annotations

import json
import os
from typing import Optional


def true_to_magnetic(true_heading: float, variation_deg: Optional[float]) -> float:
    """
    Convert true heading to magnetic heading using local variation.
    Magnetic = True - variation (east positive, west negative).
    If variation is None, returns original heading.
    """
    if variation_deg is None:
        return true_heading % 360
    return (true_heading - variation_deg) % 360


def magnetic_to_true(magnetic_heading: float, variation_deg: Optional[float]) -> float:
    """
    Convert magnetic heading to true heading using local variation.
    True = Magnetic + variation (east positive, west negative).
    If variation is None, returns original heading.
    """
    if variation_deg is None:
        return magnetic_heading % 360
    return (magnetic_heading + variation_deg) % 360


def load_variation(icao: Optional[str]) -> Optional[float]:
    """
    Load magnetic variation (declination) in degrees for an ICAO station
    from config/magnetic_variation.json. Returns None if unavailable.
    """
    if not icao:
        return None
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "magnetic_variation.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            val = data.get(icao.upper())
            if isinstance(val, (int, float)):
                return float(val)
            return None
    except Exception:
        return None


__all__ = [
    "true_to_magnetic",
    "magnetic_to_true",
    "load_variation",
]
