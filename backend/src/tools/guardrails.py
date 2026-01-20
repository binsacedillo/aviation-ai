"""
Semantic Guardrails - Automated Verification System

This module provides guardrails that verify agent claims before they reach users.
If discrepancies are detected, the system triggers a reflection/re-evaluation loop.

Pattern: "Feedback Loop with Self-Auditing"
"""

import math
from decimal import Decimal, getcontext
from typing import Dict, Any, Optional, Tuple
from .tracing import TraceLogger
from .magnetic import true_to_magnetic, load_variation


def parse_wind_from_string(wind_str: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Parse wind direction and speed from string like "220 @ 10".
    
    Returns:
        (wind_direction, wind_speed) or (None, None) if parsing fails
    """
    if not wind_str or ' @ ' not in wind_str:
        return None, None
    
    try:
        parts = wind_str.split(' @ ')
        direction = float(parts[0])
        speed = float(parts[1])
        return direction, speed
    except (ValueError, IndexError):
        return None, None


def calculate_crosswind_component(
    wind_speed: float,
    wind_direction: float,
    runway_heading: float
) -> Dict[str, float]:
    """
    Calculate crosswind and headwind components using aviation math.
    
    Args:
        wind_speed: Wind speed in knots
        wind_direction: Wind direction in degrees (where it's FROM)
        runway_heading: Runway heading in degrees
    
    Returns:
        dict with crosswind_kt, headwind_kt, angle_deg
    """
    # Calculate angle between wind and runway
    angle = abs(wind_direction - runway_heading)
    
    # Normalize to 0-180 range
    if angle > 180:
        angle = 360 - angle
    
    # Convert to radians for trigonometry
    angle_rad = math.radians(angle)
    # Use Decimal for final results to avoid rounding drift
    getcontext().prec = 10
    crosswind = Decimal(wind_speed) * Decimal(math.sin(angle_rad))
    headwind = Decimal(wind_speed) * Decimal(math.cos(angle_rad))
    
    return {
        "crosswind_kt": float(crosswind.quantize(Decimal("0.01"))),
        "headwind_kt": float(headwind.quantize(Decimal("0.01"))),
        "angle_deg": round(angle, 1),
    }


def apply_magnetic_correction(wind_direction_true: float, magnetic_variation_deg: Optional[float]) -> float:
    """
    Convert wind direction from True to Magnetic using local declination.
    Magnetic = True - declination (east positive, west negative).
    If declination is None, returns original direction.
    """
    if magnetic_variation_deg is None:
        return wind_direction_true
    corrected = wind_direction_true - magnetic_variation_deg
    corrected %= 360
    return corrected


def extract_crosswind_claim_from_response(response: str) -> Optional[float]:
    """
    Extract crosswind value from agent's response text.
    
    Looks for patterns like:
    - "crosswind is 5 knots"
    - "5kt crosswind"
    - "crosswind: 7.66 kt"
    - "crosswind at KDEN Runway 17L is 7.7 kt"
    
    Returns:
        Crosswind value in knots, or None if not found
    """
    import re
    
    # Pattern: "crosswind" followed by number and "kt" or "knot"
    # Allow anything between "crosswind" and number
    patterns = [
        r'crosswind\s+.*?(\d+(?:\.\d+)?)\s*(?:kt|knots?)',  # "crosswind...7.7 kt"
        r'(\d+(?:\.\d+)?)\s*(?:kt|knots?)\s+crosswind',  # "7.7 kt crosswind"
    ]
    
    response_lower = response.lower()
    
    for pattern in patterns:
        match = re.search(pattern, response_lower)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                continue
    
    return None


class CrosswindGuardrail:
    """
    Semantic Guardrail: Verify crosswind calculations before sending to user.
    
    The 3-Knot Rule:
        If |V_agent - V_math| > 3 kt, trigger re-evaluation
    
    Usage:
        guardrail = CrosswindGuardrail(threshold_kt=3.0)
        result = guardrail.verify(agent_response, metar_data, runway_heading)
        
        if not result["passed"]:
            # Trigger reflection/re-evaluation
            agent.reflect_and_correct(result["issue"])
    """
    
    def __init__(self, threshold_kt: float = 3.0):
        """
        Initialize guardrail with threshold for acceptable discrepancy.
        
        Args:
            threshold_kt: Maximum allowed difference in knots (default: 3.0)
        """
        self.threshold_kt = threshold_kt
    
    def verify(
        self,
        agent_response: str,
        metar_data: Dict[str, Any],
        runway_heading: float,
        use_gust: bool = False,
        magnetic_variation_deg: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Verify agent's crosswind claim against mathematical truth.
        
        Args:
            agent_response: Agent's text response to user
            metar_data: METAR data dict with 'wind' field
            runway_heading: Runway heading in degrees
        
        Returns:
            dict with:
                - passed: bool (True if verification passed)
                - agent_claim: float or None
                - mathematical_truth: float or None
                - discrepancy: float or None
                - issue: str (description if failed)
                - recommendation: str (what to do)
        """
        # Extract agent's crosswind claim
        agent_claim = extract_crosswind_claim_from_response(agent_response)
        
        if agent_claim is None:
            # Agent didn't make a crosswind claim - that's fine
            return {
                "passed": True,
                "agent_claim": None,
                "mathematical_truth": None,
                "discrepancy": None,
                "issue": "No crosswind claim detected in response",
                "recommendation": "No verification needed",
            }
        
        # Parse wind from METAR
        wind_str = metar_data.get('wind', '')
        wind_direction, wind_speed = parse_wind_from_string(wind_str)
        gust = metar_data.get('wind_gust')
        # Resolve magnetic variation: prefer provided, else load from config
        if magnetic_variation_deg is None:
            magnetic_variation_deg = load_variation(metar_data.get('station'))
        # Apply magnetic correction if direction available
        wind_direction_mag = true_to_magnetic(wind_direction, magnetic_variation_deg) if wind_direction is not None else None
        
        if wind_direction_mag is None or wind_speed is None:
            return {
                "passed": False,
                "agent_claim": agent_claim,
                "mathematical_truth": None,
                "discrepancy": None,
                "issue": f"Could not parse wind data: {wind_str}",
                "recommendation": "Re-fetch METAR data",
            }
        
        # Calculate mathematical truth
        # Choose sustained vs gust speed
        speed_used = gust if (use_gust and gust is not None) else wind_speed

        math_result = calculate_crosswind_component(
            wind_speed=speed_used,
            wind_direction=wind_direction_mag,
            runway_heading=runway_heading
        )
        
        mathematical_truth = math_result["crosswind_kt"]
        
        # Calculate discrepancy
        # Use Decimal for discrepancy
        discrepancy = float((Decimal(agent_claim) - Decimal(mathematical_truth)).copy_abs())
        
        # Apply the 3-Knot Rule
        passed = discrepancy <= self.threshold_kt
        
        if passed:
            return {
                "passed": True,
                "agent_claim": agent_claim,
                "mathematical_truth": mathematical_truth,
                "discrepancy": discrepancy,
                "issue": None,
                "recommendation": "Verification passed - safe to send to user",
            }
        else:
            return {
                "passed": False,
                "agent_claim": agent_claim,
                "mathematical_truth": mathematical_truth,
                "discrepancy": discrepancy,
                "issue": f"Crosswind discrepancy: Agent claimed {agent_claim} kt, "
                        f"but math shows {mathematical_truth} kt "
                        f"(difference: {discrepancy:.2f} kt > threshold: {self.threshold_kt} kt)",
                "recommendation": "TRIGGER REFLECTION: Re-read METAR and runway heading, "
                                 "recalculate crosswind component",
            }
    
    def verify_with_details(
        self,
        agent_response: str,
        metar_data: Dict[str, Any],
        runway_heading: float,
        use_gust: bool = False,
        magnetic_variation_deg: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Extended verification with detailed breakdown for debugging.
        
        Returns additional fields:
            - wind_data: parsed wind
            - calculation_details: step-by-step math
            - explanation: human-readable explanation
        """
        # Initialize tracer for introspective logging
        tracer = TraceLogger(category="crosswind")
        tracer.set_context(
            airport=metar_data.get("station"),
            runway_heading=runway_heading,
        )

        result = self.verify(
            agent_response,
            metar_data,
            runway_heading,
            use_gust=use_gust,
            magnetic_variation_deg=magnetic_variation_deg,
        )
        
        # Add detailed breakdown
        raw_metar = metar_data.get('raw')
        wind_str = metar_data.get('wind', '')
        tracer.log_input(raw_metar=raw_metar, wind_str=wind_str)
        wind_direction, wind_speed = parse_wind_from_string(wind_str)
        gust = metar_data.get('wind_gust')
        if magnetic_variation_deg is None:
            magnetic_variation_deg = load_variation(metar_data.get('station'))
        wind_direction_mag = true_to_magnetic(wind_direction, magnetic_variation_deg) if wind_direction is not None else None
        
        result["wind_data"] = {
            "raw": wind_str,
            "direction": wind_direction,
            "direction_magnetic": wind_direction_mag,
            "speed": wind_speed,
            "gust": gust,
            "speed_used": (gust if (use_gust and gust is not None) else wind_speed),
            "speed_source": ("gust" if (use_gust and gust is not None) else "sustained"),
        }
        tracer.log_transformation(wind_direction=wind_direction, wind_speed=wind_speed)
        
        if wind_direction is not None and wind_speed is not None:
            angle = abs((wind_direction_mag if wind_direction_mag is not None else wind_direction) - runway_heading)
            if angle > 180:
                angle = 360 - angle
            
            math_truth = result.get('mathematical_truth', 0) or 0
            
            result["calculation_details"] = {
                "wind_direction_true": wind_direction,
                "wind_direction_magnetic": wind_direction_mag,
                "runway_heading": runway_heading,
                "angle": angle,
                "formula": f"{result['wind_data']['speed_used']} × sin({angle}°)",
                "result": f"{result['wind_data']['speed_used']} × {math.sin(math.radians(angle)):.4f} = "
                         f"{math_truth:.2f} kt",
                "temporal": metar_data.get('time'),
                "magnetic_variation_deg": magnetic_variation_deg,
                "speed_source": result['wind_data']['speed_source'],
            }
            tracer.log_operation(function="sin", angle_deg=angle, expression=f"{result['wind_data']['speed_used']} × sin({angle}°)")
            # Also log headwind if available via recalculation
            # Recompute components to get headwind
            angle_rad = math.radians(angle)
            crosswind = (result['wind_data']['speed_used']) * math.sin(angle_rad)
            headwind = (result['wind_data']['speed_used']) * math.cos(angle_rad)
            tracer.log_result(crosswind_kt=round(crosswind, 2), headwind_kt=round(headwind, 2))
        
        # Add explanation
        if result["passed"]:
            if result["agent_claim"] is None:
                result["explanation"] = "ℹ️ No crosswind claim detected - verification not applicable."
            else:
                result["explanation"] = (
                    f"✅ VERIFIED: Agent's claim ({result['agent_claim']} kt) is within "
                    f"{self.threshold_kt} kt of mathematical truth ({result['mathematical_truth']} kt). "
                    f"Discrepancy: {result['discrepancy']:.2f} kt. Using {result['wind_data']['speed_source']} speed."
                )
        else:
            result["explanation"] = (
                f"❌ FAILED: Agent's claim ({result['agent_claim']} kt) differs from "
                f"mathematical truth ({result['mathematical_truth']} kt) by "
                f"{result['discrepancy']:.2f} kt, which exceeds threshold of {self.threshold_kt} kt. "
                f"TRIGGER REFLECTION. Using {result['wind_data']['speed_source']} speed."
            )
        
        # Attach trace and emit to file for observability
        result["trace"] = tracer.to_json()
        tracer.emit()

        return result


# Convenience function for quick verification
def verify_crosswind_claim(
    agent_response: str,
    metar_data: Dict[str, Any],
    runway_heading: float,
    threshold_kt: float = 3.0
) -> bool:
    """
    Quick verification: Returns True if passed, False if failed.
    
    Args:
        agent_response: Agent's text response
        metar_data: METAR data dict
        runway_heading: Runway heading in degrees
        threshold_kt: Acceptable discrepancy threshold
    
    Returns:
        True if verification passed, False if failed
    """
    guardrail = CrosswindGuardrail(threshold_kt=threshold_kt)
    result = guardrail.verify(agent_response, metar_data, runway_heading)
    return result["passed"]


# Example usage:
if __name__ == "__main__":
    # Test the guardrail
    guardrail = CrosswindGuardrail(threshold_kt=3.0)
    
    # Example 1: Correct claim
    metar = {"wind": "220 @ 10"}
    response = "The crosswind at KDEN Runway 17L is 7.7 kt, which is safe."
    result = guardrail.verify_with_details(response, metar, runway_heading=170)
    
    print("Example 1: Correct Claim")
    print(f"  Passed: {result['passed']}")
    print(f"  Explanation: {result['explanation']}")
    print()
    
    # Example 2: Incorrect claim (should trigger reflection)
    response_wrong = "The crosswind at KDEN Runway 17L is 15 kt - DANGEROUS!"
    result_wrong = guardrail.verify_with_details(response_wrong, metar, runway_heading=170)
    
    print("Example 2: Incorrect Claim")
    print(f"  Passed: {result_wrong['passed']}")
    print(f"  Explanation: {result_wrong['explanation']}")
    print(f"  Recommendation: {result_wrong['recommendation']}")
