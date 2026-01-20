# 🛩️ Flight Copilot Agent

**Agentic AI System for Flight Planning & Assistance**

An advanced AI assistant powered by LangGraph that reasons, plans, and uses tools to help pilots with flight planning, weather analysis, fuel calculations, and safety checks.

## 📁 Project Structure

```
flight-copilot-agent/
├── src/
│   ├── agent/              # Agent reasoning loop (LangGraph)
│   │   └── agent.py
│   ├── tools/              # Tool definitions
│   │   └── tools.py
│   ├── api/                # FastAPI REST endpoints
│   │   └── main.py
│   └── database/           # PostgreSQL + pgvector (future)
├── config/                 # Configuration files
├── tests/                  # Unit & integration tests
├── docs/                   # Documentation
├── demo.py                 # Standalone demo script
└── requirements.txt        # Dependencies
```

## 🚀 Quick Start

### 1. Install the Package
```bash
# Install in editable mode (recommended for development)
pip install -e .

# Or install dependencies only
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
# Copy example environment file
cp .env.example .env

# Edit .env and add your API keys
# At minimum, add OPENAI_API_KEY for LLM integration
```

### 3. Run the Demo
```bash
python demo.py
```

### 4. Start FastAPI Server
```bash
python -m src.api.main
```

Then visit: `http://localhost:8000/docs`

### 5. (Optional) Use Free Local LLM with Ollama
```bash
# Install Ollama (one-time): https://ollama.com/download
ollama pull llama3.2

# Enable Ollama in .env
echo OLLAMA_ENABLED=true >> .env
echo OLLAMA_MODEL=llama3.2 >> .env
```
Run the demo again; responses will come from the local model instead of the simulated decision tree.

Troubleshooting (Ollama):
- First run may take 20–60s while the model loads; subsequent calls are faster.
- If it still feels slow, try a smaller model: `ollama pull mistral` then set `OLLAMA_MODEL=mistral`.
- To temporarily disable and use the simulated loop: set `OLLAMA_ENABLED=false`.

### Live Progress Streaming (No Waiting!)
You can stream progress events while the agent works—see each step in real-time!

**Quick Test (No API server needed):**
```bash
python test_streaming_direct.py
```

This shows you:
- 🤖 When LLM starts thinking (with Ollama enabled)
- 🔄 Each loop iteration (with simulated mode)
- 🔧 Each tool being called with arguments
- ✅ Results from each tool
- ✨ Final response

**Via API (with server running):**
```bash
# Start the API server first
python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000

# Then stream from another terminal
curl -N -X POST \
  -H "Content-Type: application/json" \
  -d '{"query":"Can I safely fly my Cessna 172 from Denver to Boulder?"}' \
  http://localhost:8000/query/stream
```

### LangGraph Tool-Calling Agent (LLM decides + executes tools)
Requires an LLM that supports tool-calling (OpenAI works best; Ollama may answer directly if tool-calls are unsupported by the model).

Quick CLI test:
```bash
cd "c:\Users\Owner\Documents\back end projects\flight-copilot-agent"
python - <<'PY'
from src.agent.tool_graph import run_tool_agent
result = run_tool_agent("Plan a safe VFR hop from KDEN to KBDU in a Cessna 172. Check weather and fuel.")
print(result["final_response"])
PY
```

To stream LangGraph steps programmatically:
```python
from src.agent.tool_graph import stream_tool_agent
for ev in stream_tool_agent("Check if I can fly KDEN to KBDU now"):
        print(ev)
```


## 🤖 How It Works

The agent executes in a **reasoning loop**:

```
User Query
    ↓
Think (Plan next action)
    ↓
Act (Call tools autonomously)
    ↓
Observe (Analyze results)
    ↓
Decide (More tools needed?)
    ├→ YES: Loop back to Act
    └→ NO: Respond to user
```

### Example Query
**User**: "Can I safely fly my Cessna 172 (N12345) from Denver to Boulder with current weather?"

**Agent's Action Sequence**:
1. `fetch_metar(KDEN)` → Get Denver weather
2. `fetch_metar(KBDU)` → Get Boulder weather
3. `fetch_aircraft_specs(N12345)` → Get aircraft fuel capacity
4. `calculate_fuel_burn(25nm, Cessna 172)` → Calculate fuel needed
5. **Respond**: "YES, safe to fly with X gallons fuel margin"

## 🛠️ Available Tools

| Tool | Purpose |
|------|---------|
| `fetch_metar()` | Real-time airport weather |
| `fetch_aircraft_specs()` | Aircraft data (fuel, range, weight) |
| `calculate_fuel_burn()` | Flight fuel consumption |
| `query_manual()` | Search flight manuals |
| `log_flight_event()` | Record flight events |

## 🔄 Technology Stack

- **Framework**: FastAPI + Uvicorn
- **Agent**: LangGraph (agentic orchestration)
- **Database**: PostgreSQL + pgvector (future)
- **LLM**: OpenAI / Claude (future integration)
- **Validation**: Pydantic V2
- **Testing**: pytest

## 📊 Roadmap

**Phase 1: Foundation** ✅
- [x] Project structure & package setup
- [x] Environment configuration
- [x] Mock tools & simulated agent

**Phase 2: Real Integrations** ✅ **COMPLETE**
- [x] Free local LLM with Ollama (no API costs)
- [x] Real METAR data via AVWX Engine (live aviation weather)
- [x] Streaming progress events (real-time feedback)
- [x] LangGraph tool-calling architecture (ready for OpenAI)
- [x] Trace audit testing (verify real data integration)
- [x] International airport support (any ICAO code worldwide 🌏)
- [x] Mathematical verification (crosswind calculations with real data)

> **DATA-DRIVEN MODE**: The agent now uses **real-time aviation weather data** from AVWX. When you ask "Can I fly from Denver to Boulder?", it fetches **actual current METAR** for KDEN and KBDU—not simulation!
>
> **Verify Real Integration (Three Methods):**
>
> **Method 1: Trace Audit** (The "Mind-Reading" Test)
> ```bash
> python test_trace_audit.py
> ```
> Shows three key handshakes that prove integration is real:
> 1. ✅ **Intent** - Agent decides to check weather
> 2. ✅ **Parameter** - Correct ICAO code passed to tool
> 3. ✅ **Observation** - Real numbers appear in tool results
>
> **Method 2: International Pivot** (The "Airports Never Seen" Test)
> ```bash
> python test_international_direct.py
> ```
> Tests Manila (RPLL) and Hong Kong (VHHH) - NOT in fallback data!
> - ✅ Shows tropical weather (29°C) - proves real AVWX API
> - ✅ Calculates 700nm distance - proves fuel tool integration
> - ✅ Works with any ICAO code worldwide 🌏
>
> **Method 3: Crosswind Verification** (The Mathematical Proof)
> ```bash
> python test_crosswind_verification.py
> ```
> Manually verify the math using real METAR data:
> - Fetches wind: 220° @ 10kt
> - Calculates: V_cross = 10 × sin(50°) = 7.66 kt
> - ✅ Proves integration is mathematically correct
> - Can verify ANY agent claim by hand!
>
> **More Tests:**
> ```bash
> # See real METAR for multiple airports
> python test_real_metar.py
> 
> # Agent using real METAR in decision-making
> python test_simulated_with_real_metar.py
> ```
>
> **Note on Tool Calling:**
> - **Simulated mode** (OLLAMA_ENABLED=false): Calls tools automatically with real METAR
> - **Ollama mode** (OLLAMA_ENABLED=true): Direct LLM response (Ollama doesn't support tool calling yet)
> - **OpenAI/Claude** (with API key): Full tool-calling capability via LangGraph

**Phase 3: Production Features**
- [ ] PostgreSQL + pgvector for semantic search
- [ ] User authentication & authorization
- [ ] Flight logging & history
- [ ] Implement MCP (Model Context Protocol)
- [ ] Comprehensive test suite
- [ ] Cloud deployment (AWS/GCP)

## 📝 License

MIT
