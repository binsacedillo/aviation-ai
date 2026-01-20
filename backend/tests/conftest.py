"""
Pytest configuration and shared fixtures

Provides common test utilities and mock data.
"""

import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@pytest.fixture
def sample_metar_kden():
    """Sample METAR data for KDEN"""
    return {
        "station": "KDEN",
        "raw": "METAR KDEN 180953Z 26013KT 10SM FEW200 01/M13 A3006 RMK AO2 SLP181 T00111133",
        "time": "180953Z",
        "wind": "260 @ 13",
        "wind_gust": None,
        "temp_c": 1,
        "dewpoint_c": -13,
        "visibility_sm": "10",
        "altimeter": "A3006",
        "flight_category": "VFR",
        "summary": "Winds W-260 at 13kt, Vis 10sm, Temp 1°C, Dew -13°C, Alt 30.06 inHg, Few clouds at 20000ft"
    }


@pytest.fixture
def sample_metar_kbdu():
    """Sample METAR data for KBDU"""
    return {
        "station": "KBDU",
        "raw": "METAR KBDU 181035Z AUTO 26020G29KT 10SM CLR 06/M12 A3005 RMK AO2",
        "time": "181035Z",
        "wind": "260 @ 20",
        "wind_gust": 29,
        "temp_c": 6,
        "dewpoint_c": -12,
        "visibility_sm": "10",
        "altimeter": "A3005",
        "flight_category": "VFR",
        "summary": "Winds W-260 at 20kt gusting to 29kt, Vis 10sm, Temp 6°C, Dew -12°C, Alt 30.05 inHg, Sky clear"
    }


@pytest.fixture
def sample_runway_selection():
    """Sample runway selection result"""
    return {
        "selected_runway": "26",
        "runway_heading": 260,
        "candidates": [
            {
                "runway": "26",
                "heading": 260,
                "crosswind_kt": 1.7,
                "headwind_kt": 12.9,
                "score": 14.6
            },
            {
                "runway": "08",
                "heading": 80,
                "crosswind_kt": 1.7,
                "headwind_kt": -12.9,
                "score": -11.2
            }
        ],
        "phrase": "Runway 26 favored, 12.9 kt headwind, 1.7 kt crosswind"
    }


@pytest.fixture
def sample_aircraft_specs():
    """Sample aircraft specifications"""
    return {
        "type": "Cessna 172",
        "max_fuel": 53,
        "useful_load": 1100,
        "cruise_speed": 120,
        "max_range": 450
    }


@pytest.fixture(autouse=True)
def cleanup_logs():
    """Clean up test logs after each test"""
    yield
    # Cleanup can be added here if needed
    pass
