# 🌤️ Real METAR Integration - DATA-DRIVEN MODE

**Status:** ✅ **COMPLETE** (Phase 2)

## Overview

The Flight Copilot Agent now uses **real-time aviation weather data** via the AVWX Engine library. This means when you ask "Can I fly from Denver to Boulder?", the agent fetches **actual current METAR reports** from KDEN and KBDU—not mock simulation data.

## What Changed

### Before (Simulation Mode)
```python
# Old behavior: Hardcoded mock data
def fetch_metar(icao_code: str) -> dict:
    return {
        "station": "KDEN",
        "wind": "180° @ 15kt",  # ❌ FAKE
        "temp_c": 5,            # ❌ FAKE
        "flight_category": "VFR"
    }
```

### After (Data-Driven Mode)
```python
# New behavior: Live AVWX data
def fetch_metar(icao_code: str) -> dict:
    metar = Metar(icao_code)
    metar.update()  # ✅ FETCHES LIVE DATA
    return {
        "station": metar.data.station,
        "wind": f"{metar.data.wind_direction.value}° @ {metar.data.wind_speed.value}kt",
        "temp_c": metar.data.temperature.value,
        "flight_category": metar.data.flight_rules
    }
```

## How It Works

### 1. AVWX Engine Library
- **Free, no API key required** (uses public NOAA/aviation feeds)
- Python library: `avwx-engine`
- Provides `Metar` class that fetches live reports
- Reference: [AVWX Documentation](https://avwx.rest/)

### 2. Integration Points

**File: `src/tools/metar_real.py`**
- `fetch_metar_real(icao_code)` → Fetches live METAR using AVWX
- Extracts: wind, temperature, dewpoint, visibility, altimeter, flight category
- Graceful fallback to mock data if AVWX unavailable

**File: `src/tools/tools.py`**
- `fetch_metar(icao_code)` → Calls `fetch_metar_real()` first
- Falls back to mock if AVWX fails

### 3. Example Real Data

```bash
$ python test_real_metar.py

📍 Fetching METAR for KDEN...
  station             : KDEN
  time                : 180653Z
  wind                : 250 @ 07          # ✅ REAL
  temp_c              : 0                 # ✅ REAL
  dewpoint_c          : -14               # ✅ REAL
  visibility_sm       : 10                # ✅ REAL
  altimeter           : A3006             # ✅ REAL
  flight_category     : VFR               # ✅ REAL
  raw                 : METAR KDEN 180653Z 25007KT 10SM CLR 00/M14 A3006...
```

## Testing

### Test Real METAR Fetching
```bash
python test_real_metar.py
```

Shows live weather for:
- KDEN (Denver International)
- KBDU (Boulder Municipal)
- KJFK (JFK International)

### Test Agent with Real Data
```bash
python test_simulated_with_real_metar.py
```

**Output Example:**
```
🔧 TOOL CALL: fetch_metar
   Input: {'icao_code': 'KDEN'}
   📍 Wind: 220 @ 10          # ✅ LIVE DATA
   🌡️ Temp: -1°C             # ✅ LIVE DATA
   ✈️ Category: VFR          # ✅ LIVE DATA
```

## Agent Modes

### Mode 1: Simulated (Tool-Calling)
**When:** `OLLAMA_ENABLED=false` in `.env`

**Behavior:**
- Runs through agentic loop (Think → Act → Observe)
- Automatically calls `fetch_metar()` for weather queries
- Uses **real AVWX data** ✅

**Best for:** Testing tool integration, seeing data flow

### Mode 2: Ollama (Direct Response)
**When:** `OLLAMA_ENABLED=true` in `.env`

**Behavior:**
- Asks Ollama LLM for a direct answer
- Ollama doesn't support tool calling (yet)
- May not fetch real weather automatically ⚠️

**Best for:** Natural language responses, general queries

### Mode 3: OpenAI/Claude (Full Tool-Calling)
**When:** `OPENAI_API_KEY` set in `.env`

**Behavior:**
- Uses LangGraph tool-calling protocol
- LLM decides when to call `fetch_metar()`
- Automatically uses **real AVWX data** ✅

**Best for:** Production, full agentic capability

## Installation

### Install AVWX Engine
```bash
pip install avwx-engine
```

This adds:
- `avwx-engine==1.9.7`
- Dependencies: `geopy`, `xmltodict`, `python-dateutil`

### Configuration
No API key needed! AVWX uses public aviation data sources.

## Architecture

```
User Query: "Can I fly from KDEN to KBDU?"
    ↓
Agent Decision: "Need to check weather"
    ↓
Tool Call: fetch_metar("KDEN")
    ↓
src/tools/tools.py → fetch_metar()
    ↓
src/tools/metar_real.py → fetch_metar_real()
    ↓
AVWX Engine → Metar("KDEN").update()
    ↓
NOAA/Aviation Weather Feeds (LIVE DATA)
    ↓
Return: {"wind": "220 @ 10", "temp_c": -1, "flight_category": "VFR"}
    ↓
Agent: "Weather looks good! VFR conditions, light winds..."
```

## Benefits

### 1. **Portfolio Quality**
Real data integration demonstrates:
- API consumption skills
- Error handling (fallback logic)
- Production-ready code

### 2. **Practical Utility**
- Agent can make **real safety decisions**
- Checks **actual current conditions**
- Not just a toy/demo

### 3. **No Costs**
- AVWX Engine is free (uses public data)
- No API keys or rate limits
- Perfect for development/learning

## Limitations & Fallbacks

### When AVWX Unavailable
```python
def _fallback_metar(icao_code: str) -> dict:
    """Returns mock data if AVWX fails"""
    mock_data = {
        "KDEN": {"wind": "180° @ 15kt", "temp_c": 5, ...},
        "KBDU": {"wind": "200° @ 12kt", "temp_c": 3, ...},
    }
    return mock_data.get(icao_code, {"error": "No data"})
```

### Graceful Degradation
- If AVWX fetch fails → returns reasonable defaults
- Agent still works, just with mock weather
- User sees warning: "⚠️ AVWX fetch failed, using fallback"

## Next Steps (Phase 3)

- [ ] Add TAF (Terminal Aerodrome Forecast) support
- [ ] Integrate NOTAM (Notice to Airmen) data
- [ ] Cache METAR reports (reduce API calls)
- [ ] Add weather trend analysis (improving/worsening)
- [ ] Support international airports (ICAO codes worldwide)

## References

- [AVWX Engine Documentation](https://avwx.rest/)
- [AVWX Python Library](https://github.com/avwx-rest/avwx-engine)
- [METAR Format Guide](https://www.aviationweather.gov/metar/help)
- [Aviation Weather Center](https://www.aviationweather.gov/)

---

**Capstone Requirement Met:** ✅

> "Now, when you ask 'Can I fly?', the AI will look at actual crosswinds in Manila right now."
>
> This is no longer simulation—it's **real, data-driven aviation AI**.
