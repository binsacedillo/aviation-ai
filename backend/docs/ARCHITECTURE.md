# System Architecture

## Full Stack Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     USER BROWSER (localhost:3000)               │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │              FLIGHT COPILOT FRONTEND (Next.js)             │ │
│  ├────────────────────────────────────────────────────────────┤ │
│  │                                                              │ │
│  │  ┌─────────────────┐        ┌──────────────────────────┐  │ │
│  │  │ Health Status   │        │ Query Interface          │  │ │
│  │  ├─────────────────┤        ├──────────────────────────┤  │ │
│  │  │ • Live/Offline  │        │ • Question input         │  │ │
│  │  │ • Guardrails ✓  │        │ • Get response           │  │ │
│  │  │ • Tests: 32/32  │        │ • Show live/fallback     │  │ │
│  │  │ • Polling 5s    │        │ • Verify status          │  │ │
│  │  └─────────────────┘        │ • Show details           │  │ │
│  │                              └──────────────────────────┘  │ │
│  │                                                              │ │
│  │  ┌────────────────────────────────────────────────────────┐ │
│  │  │            API Client (Axios + TypeScript)             │ │
│  │  │  • GET  /health                                        │ │
│  │  │  • POST /query                                         │ │
│  │  │  • Error handling & CORS                               │ │
│  │  └────────────────────────────────────────────────────────┘ │
│  │                                                              │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
                            ▼ HTTP
        ┌───────────────────────────────────────────┐
        │   CORS Middleware (FastAPI)               │
        │   Allow: localhost:3000                   │
        └───────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│              BACKEND API (FastAPI - localhost:8000)              │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Router / Endpoint Handler                    │   │
│  │  ┌────────────┬─────────────┬──────────────────┐         │   │
│  │  │ /health    │ /query      │ /query/stream    │         │   │
│  │  │ (sync)     │ (JSON)      │ (NDJSON)         │         │   │
│  │  └────────────┴─────────────┴──────────────────┘         │   │
│  └──────────────────────────────────────────────────────────┘   │
│                            ▼                                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │         Flight Assistant Agent (Agentic Loop)            │   │
│  │                                                            │   │
│  │  1. Parse query & context                                │   │
│  │  2. Call LLM (or simulated for testing)                  │   │
│  │  3. Extract tool calls                                   │   │
│  │  4. Execute tools (fetch_metar, select_runway, etc.)    │   │
│  │  5. Build context for next iteration                     │   │
│  │  6. Loop until done_reasoning=true                       │   │
│  │                                                            │   │
│  └──────────────────────────────────────────────────────────┘   │
│                            ▼                                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │            TRIPLE-LAYER GUARDRAIL SYSTEM                 │   │
│  ├──────────────────────────────────────────────────────────┤   │
│  │                                                            │   │
│  │  LAYER 1: SEMANTIC VERIFICATION                          │   │
│  │  ────────────────────────────────────────────            │   │
│  │  • Extract crosswind claim from response                 │   │
│  │  • Get METAR data (wind, heading)                        │   │
│  │  • Get runway heading (from tool tracking)               │   │
│  │  • Calculate actual crosswind                            │   │
│  │  • Check: |claim - actual| ≤ 3.0 knots?                │   │
│  │                                                            │   │
│  │  ✅ PASSED → Return response as-is (LIVE)               │   │
│  │  ❌ FAILED → Go to Layer 2                               │   │
│  │  ⊘ SKIPPED → Return response (no data)                 │   │
│  │                                                            │   │
│  │  LAYER 2: REFLECTION & CORRECTION                        │   │
│  │  ──────────────────────────────────                       │   │
│  │  • Build prompt with:                                    │   │
│  │    - Original response                                   │   │
│  │    - Verification failure reason                         │   │
│  │    - Correct calculation                                 │   │
│  │  • Call LLM for corrected response                       │   │
│  │  • Re-verify the corrected response                      │   │
│  │                                                            │   │
│  │  ✅ PASSED → Return corrected (LIVE)                     │   │
│  │  ❌ FAILED → Go to Layer 3                               │   │
│  │                                                            │   │
│  │  LAYER 3: SAFE-FAIL FALLBACK                             │   │
│  │  ────────────────────────────────                         │   │
│  │  • Generate conservative response:                       │   │
│  │    "I need accurate METAR data to answer..."             │   │
│  │  • Log audit trail to logs/trace.jsonl                   │   │
│  │  • Return fallback (FALLBACK)                            │   │
│  │                                                            │   │
│  │  Final Response: {                                       │   │
│  │    response: "...",                                      │   │
│  │    guardrail_status: "passed|failed|skipped",            │   │
│  │    is_fallback: true/false,                              │   │
│  │    metar_available: true/false,                          │   │
│  │    runway_available: true/false                          │   │
│  │  }                                                        │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │               Audit & Logging                             │   │
│  │  • logs/trace.jsonl (guardrail events)                   │   │
│  │  • logs/agent.log (debug info)                           │   │
│  │  • Test results                                          │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
                            ▼ (As needed)
        ┌───────────────────────────────────────────┐
        │   External Tools & Services               │
        ├───────────────────────────────────────────┤
        │  • AVWX (Weather data)                    │
        │  • Aircraft specs database                │
        │  • Runway/airport database                │
        └───────────────────────────────────────────┘
```

## Request/Response Flow

```
USER QUERY: "What's the crosswind at KDEN runway 260?"
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│ Frontend sends: POST /query                              │
│ {query: "What's the crosswind at KDEN runway 260?"}    │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│ Backend Agent Loop:                                      │
│ 1. LLM: "I need to fetch weather for KDEN"            │
│ 2. Tool Call: fetch_metar(KDEN)                         │
│    ▼ Agent tracks METAR in self.metar_data              │
│ 3. Tool Result: {wind: 220@10, temp: 15, ...}          │
│ 4. LLM: "Runway 260, wind 220@10... crosswind..."      │
│ 5. Tool Call: select_best_runway(KDEN)                 │
│    ▼ Agent tracks runway_heading=260                    │
│ 6. Tool Result: {best_runway: 260}                      │
│ 7. LLM: "The crosswind is approximately 7.4 knots"     │
│ 8. Done: done_reasoning=true                            │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│ Guardrail Verification:                                  │
│ Extract claim: "7.4 knots"                              │
│ Has METAR: YES (220@10)                                 │
│ Has runway: YES (260°)                                  │
│ Calculate: wind_angle = 220 - 260 = -40°               │
│ Crosswind = 10 * sin(40°) = 6.43 kt                    │
│ Check: |7.4 - 6.43| = 0.97 ≤ 3.0? YES ✅              │
│ Status: PASSED                                          │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│ Frontend receives:                                       │
│ {                                                        │
│   response: "The crosswind is approximately 7.4 knots" │
│   guardrail_status: "passed",                           │
│   is_fallback: false,                                   │
│   metar_available: true,                                │
│   runway_available: true                                │
│ }                                                        │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│ Frontend Displays:                                       │
│                                                          │
│ ✅ LIVE (green badge)                                  │
│ ✅ Passed verification                                 │
│ "The crosswind is approximately 7.4 knots"            │
│ METAR: ✅ Available                                    │
│ Runway: ✅ Available                                   │
└─────────────────────────────────────────────────────────┘
```

## Data Flow Diagram

```
MEMORY TRACKING DURING AGENT LOOP
──────────────────────────────────

Agent Start:
  metar_data = None
  runway_heading = None
  
Loop Iteration 1:
  Tool Call: fetch_metar("KDEN")
  ▼ _track_metar_and_runway() called
  ▼ Finds "METAR": {...} in tool result
  metar_data = {wind: "220@10", ...}

Loop Iteration 2:
  Tool Call: select_best_runway("KDEN")
  ▼ _track_metar_and_runway() called
  ▼ Finds "heading": 260 in tool result
  runway_heading = 260

Loop End:
  final_response = "The crosswind is 7.4 knots"
  ▼ verify_response() called
  ▼ extract_claim("7.4 knots")
  ▼ calculate_crosswind(wind=220@10, runway=260)
  ▼ check_threshold(7.4, 6.43, threshold=3.0)
  ✅ PASSED
```

## Component Dependencies

```
Frontend:
  page.tsx
  ├── HealthStatus.tsx
  │   └── lib/api.ts (getHealth)
  └── QueryInterface.tsx
      └── lib/api.ts (submitQuery)
  
Backend:
  main.py (FastAPI)
  ├── CORS Middleware
  ├── /health endpoint
  ├── /query endpoint
  │   └── agent.py (FlightAssistantAgent)
  │       ├── run() method
  │       │   ├── _track_metar_and_runway()
  │       │   ├── verify_response()
  │       │   ├── reflect_and_correct()
  │       │   └── _safe_fail_response()
  │       └── guardrails.py (CrosswindGuardrail)
  │           ├── verify()
  │           ├── extract_claim()
  │           └── calculate_crosswind()
  └── /query/stream endpoint
      └── run_stream() generator
```

## Testing Architecture

```
Test Suite (32 tests)
├── test_guardrails_unit.py (19 tests)
│   ├── TestWindParsing (3)
│   ├── TestCrosswindCalculation (3)
│   ├── TestClaimExtraction (5)
│   ├── TestGuardrailVerification (4)
│   ├── TestGuardrailWithDetails (3)
│   └── TestMagneticCorrection (1)
└── test_agent_integration.py (13 tests)
    ├── TestAgentGuardrailIntegration (3)
    ├── TestAgentVerification (3)
    ├── TestAgentReflection (2)
    ├── TestAgentSafeFail (2)
    ├── TestAgentFullPipeline (1)
    └── TestAgentStreamingWithGuardrails (2)

conftest.py
├── Mock METAR fixtures
├── Mock tool responses
└── Test configuration
```

## Deployment Topology

```
Production Deployment
─────────────────────

┌──────────────────────────────────────────────┐
│           CloudFlare / CDN                    │
│        (Static assets + caching)              │
└──────────────────────────────────────────────┘
              ▼
┌──────────────────────────────────────────────┐
│     Reverse Proxy (Nginx)                    │
│     • SSL/TLS termination                    │
│     • Load balancing                         │
│     • Static file serving                    │
└──────────────────────────────────────────────┘
    ▼                                ▼
┌─────────────────────┐  ┌───────────────────┐
│  Frontend Container │  │ Backend Container │
│  (Next.js)          │  │ (FastAPI)         │
│  Port 3000          │  │ Port 8000         │
│                     │  │                   │
│  Build: npm build   │  │ Build: Python env │
│  Run: npm start     │  │ Run: uvicorn      │
└─────────────────────┘  └───────────────────┘
                             ▼
                    ┌──────────────────┐
                    │  Database        │
                    │  (PostgreSQL)    │
                    │  (Optional)      │
                    └──────────────────┘
```

---

**Last Updated**: January 18, 2026  
**Status**: Production Ready ✈️
