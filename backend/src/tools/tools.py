"""
Tool definitions for the Agentic AI system.
These are the "hands" the AI uses to interact with the world.
"""

import json
from typing import Any


# ============================================
# REAL-TIME DATA TOOLS (External APIs)
# ============================================

def fetch_metar(icao_code: str) -> dict[str, Any]:
    """
    Fetch real-time weather (METAR) for an airport.
    Uses live data from AVWX Engine when available, falls back to defaults.
    """
    # Try to use real METAR
    try:
        from .metar_real import fetch_metar_real
        return fetch_metar_real(icao_code)
    except Exception as e:
        # Fallback to mock data - align with metar_real structure for tracing
        metar_data = {
            "KDEN": {
                "station": "KDEN",
                "raw": "METAR KDEN ... (mock)",
                "wind": "180 @ 15",
                "wind_gust": 20,
                "temp_c": 5,
                "time": "180953Z",
                "visibility_sm": "10 SM",
                "flight_category": "VFR",
            },
            "KBDU": {
                "station": "KBDU",
                "raw": "METAR KBDU ... (mock)",
                "wind": "200 @ 12",
                "wind_gust": 18,
                "temp_c": 3,
                "time": "180955Z",
                "visibility_sm": "15 SM",
                "flight_category": "VFR",
            },
            "KJFK": {
                "station": "KJFK",
                "raw": "METAR KJFK ... (mock)",
                "wind": "230 @ 25",
                "wind_gust": 32,
                "temp_c": 2,
                "time": "180952Z",
                "visibility_sm": "8 SM",
                "flight_category": "MVFR",
            },
        }
        return metar_data.get(icao_code, {"station": icao_code, "error": f"No data for {icao_code}"})


def fetch_aircraft_specs(aircraft_id: str) -> dict[str, Any]:
    """
    Retrieve aircraft specifications from database.
    """
    specs = {
        "N12345": {
            "type": "Cessna 172",
            "max_fuel": 53,
            "useful_load": 1100,
            "cruise_speed": 120,
            "max_range": 450,
        },
        "N67890": {
            "type": "Piper Cherokee",
            "max_fuel": 48,
            "useful_load": 1050,
            "cruise_speed": 110,
            "max_range": 400,
        },
    }
    return specs.get(aircraft_id, {"error": f"Aircraft {aircraft_id} not found"})


# ============================================
# CALCULATION TOOLS (Logic)
# ============================================

def calculate_fuel_burn(distance_nm: float, aircraft_type: str, headwind_kt: float = 0) -> dict[str, Any]:
    """
    Calculate fuel consumption for a flight.
    Simple model: base_burn + headwind_penalty
    """
    # Fuel burn rates (gallons per hour) - simplified
    burn_rates = {
        "Cessna 172": 5.0,
        "Piper Cherokee": 5.5,
    }
    
    burn_rate = burn_rates.get(aircraft_type, 5.0)
    # Add 10% penalty per 10kt headwind
    headwind_penalty = (headwind_kt / 10) * 0.1
    adjusted_burn_rate = burn_rate * (1 + headwind_penalty)
    
    # Assume 100kt cruise speed
    flight_hours = distance_nm / 100
    total_fuel = flight_hours * adjusted_burn_rate
    
    return {
        "distance_nm": distance_nm,
        "flight_hours": round(flight_hours, 2),
        "burn_rate_gph": round(adjusted_burn_rate, 2),
        "total_fuel_gallons": round(total_fuel, 2),
    }


def query_manual(topic: str) -> dict[str, Any]:
    """
    Search flight manual for information.
    In production, this queries PostgreSQL + pgvector for semantic search.
    """
    manual_data = {
        "crosswind_limits": "Maximum crosswind: 12 knots for Cessna 172. Demonstrated crosswind: 15 knots.",
        "runway_requirements": "Minimum runway: 1500ft. Recommended: 2000ft for soft field operations.",
        "weight_balance": "Check weight and balance before every flight. Max GW: 2450 lbs.",
    }
    return {
        "topic": topic,
        "result": manual_data.get(topic, "Topic not found in manual"),
    }


# ============================================
# DATABASE TOOLS (Write Operations)
# ============================================

def log_flight_event(pilot_id: str, event_type: str, data: dict) -> dict[str, Any]:
    """
    Log a flight event to the database.
    In production, this writes to PostgreSQL.
    """
    return {
        "success": True,
        "pilot_id": pilot_id,
        "event_type": event_type,
        "data": data,
        "message": f"Flight event logged for pilot {pilot_id}",
    }


# ============================================
# TOOL REGISTRY (What LangGraph sees)
# ============================================

TOOLS = {
    "fetch_metar": {
        "function": fetch_metar,
        "description": "Fetch real-time weather (METAR) for an airport code. Returns wind, ceiling, visibility, temperature.",
        "parameters": {
            "type": "object",
            "properties": {
                "icao_code": {"type": "string", "description": "Airport ICAO code (e.g., KDEN, KJFK)"}
            },
            "required": ["icao_code"],
        },
    },
    "fetch_aircraft_specs": {
        "function": fetch_aircraft_specs,
        "description": "Get aircraft specifications from the database.",
        "parameters": {
            "type": "object",
            "properties": {
                "aircraft_id": {"type": "string", "description": "Aircraft tail number (e.g., N12345)"}
            },
            "required": ["aircraft_id"],
        },
    },
    "calculate_fuel_burn": {
        "function": calculate_fuel_burn,
        "description": "Calculate fuel consumption for a flight given distance, aircraft type, and wind.",
        "parameters": {
            "type": "object",
            "properties": {
                "distance_nm": {"type": "number", "description": "Distance in nautical miles"},
                "aircraft_type": {"type": "string", "description": "Aircraft type (e.g., Cessna 172)"},
                "headwind_kt": {"type": "number", "description": "Headwind in knots (default: 0)"},
            },
            "required": ["distance_nm", "aircraft_type"],
        },
    },
    "query_manual": {
        "function": query_manual,
        "description": "Search the flight manual for specific information.",
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "Topic to search (e.g., crosswind_limits, runway_requirements)"}
            },
            "required": ["topic"],
        },
    },
    "log_flight_event": {
        "function": log_flight_event,
        "description": "Log a flight event to the database.",
        "parameters": {
            "type": "object",
            "properties": {
                "pilot_id": {"type": "string", "description": "Pilot ID"},
                "event_type": {"type": "string", "description": "Type of event (e.g., flight_completed, maintenance_logged)"},
                "data": {"type": "object", "description": "Event data"},
            },
            "required": ["pilot_id", "event_type", "data"],
        },
    },
    "select_best_runway": {
        "function": None,  # placeholder set below
        "description": "Select best runway based on wind and crosswind limits.",
        "parameters": {
            "type": "object",
            "properties": {
                "metar_data": {"type": "object", "description": "METAR dict with wind and station"},
                "runways": {"type": "array", "description": "Runway designators or objects with heading_mag"},
                "max_crosswind_threshold": {"type": "number", "description": "Max allowable crosswind in kt"},
                "use_gust": {"type": "boolean", "description": "Use gust speed if available"},
                "magnetic_variation_deg": {"type": "number", "description": "Override declination (east +, west -)"}
            },
            "required": ["metar_data", "runways"],
        },
    },
    "generate_atc_phrase": {
        "function": None,  # placeholder set below
        "description": "Generate FAA/ICAO-standard ATC phraseology from METAR and runway.",
        "parameters": {
            "type": "object",
            "properties": {
                "metar_data": {"type": "object", "description": "METAR dict with wind and conditions"},
                "runway_designator": {"type": "string", "description": "Runway like '26' or '17L'"},
                "phrase_type": {"type": "string", "description": "landing_clearance, approach, wind_advisory, runway_advisory"},
                "station_callsign": {"type": "string", "description": "Optional station identifier (e.g., 'Denver Tower')"},
            },
            "required": ["metar_data", "runway_designator"],
        },
    },
}

# Wire tool functions (defined after TOOLS to avoid forward-ref issues)
from .runway_selection import select_best_runway as _select_best_runway
TOOLS["select_best_runway"]["function"] = _select_best_runway
from .atc_phraseology import generate_atc_phrase as _generate_atc_phrase
TOOLS["generate_atc_phrase"]["function"] = _generate_atc_phrase


def execute_tool(tool_name: str, **kwargs) -> Any:
    """Execute a tool by name with given arguments."""
    if tool_name not in TOOLS:
        return {"error": f"Tool '{tool_name}' not found"}
    
    tool = TOOLS[tool_name]
    try:
        result = tool["function"](**kwargs)
        return result
    except Exception as e:
        return {"error": str(e)}
