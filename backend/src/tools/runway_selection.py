"""
Runway Selection Logic

Determines best runway based on wind direction/speed (true → magnetic),
runway magnetic headings, and max crosswind threshold.

Output example:
  "Runway 26 favored, 11 kt headwind, 3 kt crosswind"
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from decimal import Decimal, getcontext

from .magnetic import true_to_magnetic, load_variation
from .guardrails import calculate_crosswind_component


def runway_heading_from_designator(designator: str) -> Optional[float]:
    """
    Infer magnetic runway heading from designator (e.g., "26", "08", "17L").
    Uses tens-of-degrees rule: heading ≈ number * 10.
    """
    if not designator:
        return None
    try:
        # Strip letters (L/R/C) and parse number
        num = "".join(ch for ch in designator if ch.isdigit())
        if not num:
            return None
        hdg = int(num) * 10
        return hdg % 360
    except Exception:
        return None


def compute_components_for_runway(
    wind_direction_true: float,
    wind_speed: float,
    runway_heading_mag: float,
    magnetic_variation_deg: Optional[float],
) -> Dict[str, float]:
    """
    Convert wind to magnetic, compute crosswind and headwind vs runway.
    Headwind is signed: positive = headwind, negative = tailwind.
    """
    getcontext().prec = 10
    wind_dir_mag = true_to_magnetic(wind_direction_true, magnetic_variation_deg)
    res = calculate_crosswind_component(
        wind_speed=wind_speed,
        wind_direction=wind_dir_mag,
        runway_heading=runway_heading_mag,
    )
    # calculate_crosswind_component returns angle, crosswind (abs magnitude), headwind (signed by cos)
    return res


def select_best_runway(
    metar_data: Dict[str, Any],
    runways: List[Any],
    max_crosswind_threshold: float = 10.0,
    use_gust: bool = False,
    magnetic_variation_deg: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Select the best runway with lowest crosswind, prefer positive headwind.
    Accepts runway designators (e.g., "26", "08", "17L") or dicts with `heading_mag`.
    """
    wind_str = metar_data.get("wind", "")
    # Expect format "DDD @ SS" as provided by metar_real/tools
    try:
        wdir_true, wspeed = [float(x) for x in wind_str.split(" @ ")]
    except Exception:
        return {"error": f"Invalid wind format: {wind_str}"}

    gust = metar_data.get("wind_gust")
    speed_used = (gust if (use_gust and gust is not None) else wspeed)

    # Resolve variation
    if magnetic_variation_deg is None:
        magnetic_variation_deg = load_variation(metar_data.get("station"))

    candidates: List[Dict[str, Any]] = []

    for rwy in runways:
        if isinstance(rwy, str):
            heading_mag = runway_heading_from_designator(rwy)
            designator = rwy
        elif isinstance(rwy, dict):
            designator = rwy.get("designator") or rwy.get("name") or rwy.get("id")
            heading_mag = rwy.get("heading_mag") or runway_heading_from_designator(designator or "")
        else:
            continue
        if heading_mag is None:
            continue

        comps = compute_components_for_runway(
            wind_direction_true=wdir_true,
            wind_speed=speed_used,
            runway_heading_mag=heading_mag,
            magnetic_variation_deg=magnetic_variation_deg,
        )
        candidates.append({
            "designator": designator or f"HDG {heading_mag}",
            "heading_mag": heading_mag,
            "crosswind_kt": comps["crosswind_kt"],
            "headwind_kt": comps["headwind_kt"],
            "angle_deg": comps["angle_deg"],
        })

    if not candidates:
        return {"error": "No valid runways provided"}

    # Sort by absolute crosswind ascending, prefer higher (positive) headwind
    candidates.sort(key=lambda c: (abs(c["crosswind_kt"]), -c["headwind_kt"]))
    best = candidates[0]

    favored = best["designator"]
    headwind = best["headwind_kt"]
    crosswind = best["crosswind_kt"]

    exceeds = abs(crosswind) > max_crosswind_threshold

    phrase = (
        f"Runway {favored} favored, "
        f"{abs(round(headwind, 1))} kt {'headwind' if headwind >= 0 else 'tailwind'}, "
        f"{abs(round(crosswind, 1))} kt crosswind"
    )
    if exceeds:
        phrase += f" (exceeds {max_crosswind_threshold} kt limit)"

    return {
        "phrase": phrase,
        "best": best,
        "candidates": candidates,
        "used": {
            "wind_direction_true": wdir_true,
            "wind_speed": speed_used,
            "variation_deg": magnetic_variation_deg,
            "speed_source": ("gust" if (use_gust and gust is not None) else "sustained"),
        },
    }


if __name__ == "__main__":
    # Simple demo
    demo_metar = {"station": "KDEN", "wind": "260 @ 13", "wind_gust": None}
    print(select_best_runway(demo_metar, ["26", "08"], max_crosswind_threshold=10.0))
