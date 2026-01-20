"""
ATC Phraseology Generator

Produces FAA/ICAO-standard radio phraseology using live METAR,
runway selection, and flight conditions.

Converts numbers to spoken words and generates realistic clearances.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


def number_to_words(num: int) -> str:
    """
    Convert a number to ATC-style spoken words.
    Examples:
    - 260 → "two six zero"
    - 13 → "one three"
    - 1 → "one"
    """
    ones = [
        "zero", "one", "two", "three", "four", "five",
        "six", "seven", "eight", "nine"
    ]
    digits = str(int(num))
    # Speak each digit individually
    return " ".join(ones[int(d)] for d in digits)


def wind_to_phrase(wind_direction: float, wind_speed: float, wind_gust: Optional[float] = None) -> str:
    """
    Convert METAR wind to ATC wind phrase.
    Examples:
    - 260, 13 → "wind two six zero at one three"
    - 260, 13, 20 → "wind two six zero at one three gusts two zero"
    """
    dir_words = number_to_words(int(wind_direction))
    spd_words = number_to_words(int(wind_speed))
    phrase = f"wind {dir_words} at {spd_words}"
    
    if wind_gust is not None:
        gust_words = number_to_words(int(wind_gust))
        phrase += f" gusts {gust_words}"
    
    return phrase


def runway_to_phrase(runway_designator: str) -> str:
    """
    Convert runway designator to ATC runway phrase.
    Examples:
    - "26" → "runway two six"
    - "17L" → "runway one seven left"
    - "08R" → "runway zero eight right"
    """
    # Parse number and suffix
    num_str = "".join(ch for ch in runway_designator if ch.isdigit())
    suffix = "".join(ch for ch in runway_designator if ch.isalpha()).upper()
    
    if not num_str:
        return ""
    
    suffix_words = {
        "L": "left",
        "R": "right",
        "C": "center",
    }
    
    rwy_words = number_to_words(int(num_str))
    phrase = f"runway {rwy_words}"
    
    if suffix:
        phrase += f" {suffix_words.get(suffix, suffix.lower())}"
    
    return phrase


def flight_condition_phrase(metar_data: Dict[str, Any]) -> str:
    """
    Generate phrase for flight conditions from METAR.
    Examples:
    - "VFR" for visual conditions
    - "MVFR" for marginal VFR
    - "IFR" for instrument conditions
    """
    flight_category = metar_data.get("flight_category", "UNKNOWN")
    
    abbrev_to_phrase = {
        "VFR": "visual flight rules",
        "MVFR": "marginal visual flight rules",
        "IFR": "instrument flight rules",
        "LIFR": "low instrument flight rules",
    }
    
    return abbrev_to_phrase.get(flight_category, flight_category.lower())


def generate_atc_phrase(
    metar_data: Dict[str, Any],
    runway_designator: str,
    phrase_type: str = "landing_clearance",
    station_callsign: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate ATC phraseology for common clearances and advisories.
    
    phrase_type options:
    - "landing_clearance": full landing clearance with wind/runway
    - "approach": expect ILS/approach on runway
    - "wind_advisory": just wind information
    - "runway_advisory": just runway information
    """
    
    wind_str = metar_data.get("wind", "")
    wind_gust = metar_data.get("wind_gust")
    
    # Parse wind
    try:
        wind_dir, wind_spd = [float(x) for x in wind_str.split(" @ ")]
    except Exception:
        return {"error": f"Invalid wind format: {wind_str}"}
    
    wind_phr = wind_to_phrase(wind_dir, wind_spd, wind_gust)
    runway_phr = runway_to_phrase(runway_designator)
    conditions_phr = flight_condition_phrase(metar_data)
    
    callsign = station_callsign or metar_data.get("station", "TOWER")
    
    phrases = {}
    
    if phrase_type == "landing_clearance":
        phrases["main"] = f"{wind_phr}, {runway_phr}, cleared to land"
        phrases["full"] = f"{callsign} {wind_phr}, {runway_phr}, cleared to land"
    elif phrase_type == "approach":
        phrases["main"] = f"expect {runway_phr}, conditions {conditions_phr}"
        phrases["full"] = f"{callsign} expect {runway_phr}, conditions {conditions_phr}"
    elif phrase_type == "wind_advisory":
        phrases["main"] = wind_phr
        phrases["full"] = f"{callsign} {wind_phr}"
    elif phrase_type == "runway_advisory":
        phrases["main"] = runway_phr
        phrases["full"] = f"{callsign} {runway_phr}"
    else:
        return {"error": f"Unknown phrase_type: {phrase_type}"}
    
    return {
        "phrase": phrases["main"],
        "full_transmission": phrases["full"],
        "components": {
            "wind": wind_phr,
            "runway": runway_phr,
            "conditions": conditions_phr,
            "callsign": callsign,
        },
    }


if __name__ == "__main__":
    # Demo
    demo_metar = {
        "station": "KDEN",
        "wind": "260 @ 13",
        "wind_gust": 18,
        "flight_category": "VFR",
    }
    
    result = generate_atc_phrase(
        metar_data=demo_metar,
        runway_designator="26",
        phrase_type="landing_clearance",
        station_callsign="Denver Tower",
    )
    
    print("Phrase:", result["phrase"])
    print("Full transmission:", result["full_transmission"])
    print("Components:", result["components"])
