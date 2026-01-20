# Flight Copilot Agent

AI assistant for aviation weather and runway analysis. Uses live METAR data from AVWX and real-time crosswind calculations with semantic verification.

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- Ollama (optional, for local LLM)

### Backend Setup

```bash
cd backend
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

Backend runs on: http://localhost:8000

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend runs on: http://localhost:3000

### Open in Browser

Visit **http://localhost:3000** and test queries:
- "metar KMCO" → Live weather data with flight category
- "crosswind landing at RPLL?" → Runway analysis with crosswind calculation
- "hello" → Text response with assistant intro

---

## 🏗️ Tech Stack

### Backend
- **Framework:** FastAPI (Python)
- **LLM:** Ollama (local) or OpenAI/Claude (optional)
- **Weather Data:** AVWX REST API (live METAR)
- **Verification:** Semantic guardrails with 3-knot crosswind threshold
- **Deployment:** Render.com

### Frontend
- **Framework:** Next.js 14 with TypeScript
- **Styling:** Tailwind CSS
- **Components:** React with structured data display
- **Deployment:** Vercel

---

## 📋 Features

✅ **Live METAR Integration**
- Real-time weather data for 8,000+ airports worldwide
- Structured JSON response with temperature, wind, flight category

✅ **Runway & Crosswind Analysis**
- Automatic runway selection based on wind direction
- Precise crosswind/headwind calculations using trigonometry
- Landing suitability assessment for aircraft

✅ **AI Reasoning Loop**
- Tool-calling agent with pattern-based decision logic
- ICAO airport code extraction from natural language
- Fallback responses for general questions

✅ **Safety Verification**
- Semantic guardrails check all responses against calculated math
- 3-knot tolerance rule for crosswind claims
- Safe-fail path if verification fails twice

✅ **Professional Formatting**
- Aviation-standard terminology (ignores casual phrasing)
- Color-coded flight categories (VFR/MVFR/IFR/LIFR)
- Live vs. fallback data indicators

---

## 🌐 Deployment

### Frontend → Vercel

1. Push to GitHub
2. Connect repo to [Vercel](https://vercel.com)
3. Add env var: `NEXT_PUBLIC_API_URL=<backend-url>`
4. Deploy (auto on push)

### Backend → Render

1. Push to GitHub
2. Create Web Service on [Render.com](https://render.com)
3. Configure:
   - **Runtime:** Python
   - **Build:** `pip install -r backend/requirements.txt`
   - **Start:** `gunicorn -w 4 -k uvicorn.workers.UvicornWorker backend.src.api.main:app`
   - **Env vars:** `AVWX_API_KEY=<your-key>`
4. Deploy and note the URL (e.g., `https://aviation-ai-backend.onrender.com`)
5. Add to Vercel env vars

---

## 🔑 Environment Variables

### Backend Setup

1. Copy the example file:
```bash
cp backend/.env.example backend/.env
```

2. Edit `backend/.env` and add your actual keys:
```env
AVWX_API_KEY=your_actual_api_key_here
OLLAMA_ENABLED=true
# ... other settings
```

### Frontend Setup

1. Copy the example file:
```bash
cp frontend/.env.example frontend/.env.local
```

2. Edit `frontend/.env.local`:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**⚠️ Important:** Never commit `.env` files! They're in `.gitignore` for security.

---

## 📊 Project Structure

```
flight-copilot-agent/
├── backend/
│   ├── src/
│   │   ├── agent/        # Core reasoning loop
│   │   ├── api/          # FastAPI endpoints
│   │   ├── tools/        # METAR fetching, runway selection, guardrails
│   │   └── database/     # Future PostgreSQL integration
│   ├── tests/            # pytest suite
│   ├── config/           # Settings and configuration
│   └── requirements.txt
│
├── frontend/
│   ├── app/              # Next.js pages
│   ├── components/       # React components (MetarDisplay, QueryInterface)
│   ├── lib/              # API client and utilities
│   └── package.json
│
├── .gitignore
├── .env.example
└── README.md
```

---

## 🧪 Testing

### Run Backend Tests

```bash
cd backend
python run_tests.py
```

### Run Specific Test

```bash
pytest tests/test_agent_integration.py -v
```

---

## 🛠️ Development

### Adding a New Tool

1. Create function in `backend/src/tools/tools.py`
2. Register in `TOOLS` dictionary
3. Agent automatically picks it up for tool-calling

### Modifying Guardrails

Edit `backend/src/tools/guardrails.py` to adjust:
- Crosswind threshold
- Verification logic
- Reflection prompts

### Updating Frontend Components

Components in `frontend/components/`:
- `MetarDisplay.tsx` — Weather card rendering
- `QueryInterface.tsx` — Query form and response display

---

## 📝 API Endpoints

### POST /query
Frontend-optimized endpoint. Returns structured METAR or text response.

**Request:**
```json
{
  "query": "metar KMCO"
}
```

**Response (METAR):**
```json
{
  "response_type": "metar",
  "metar": {
    "station": "KMCO",
    "raw": "METAR KMCO ...",
    "wind_direction": 90,
    "wind_speed": 8,
    "temperature_c": 28,
    "flight_category": "VFR"
  },
  "landing": {
    "runway_number": "09",
    "crosswind_kt": 3.5,
    "headwind_kt": 7.8
  },
  "guardrail_status": "passed",
  "is_fallback": false
}
```

---

## 🐛 Troubleshooting

**Backend won't start?**
- Check `AVWX_API_KEY` is set
- Ensure Python 3.10+ is installed
- Verify port 8000 is not in use

**Frontend can't reach backend?**
- Check `NEXT_PUBLIC_API_URL` in `.env.local`
- Ensure backend is running on correct port
- Check CORS settings in `src/api/main.py`

**METAR showing fallback data?**
- Verify `AVWX_API_KEY` is valid
- Check internet connection
- AVWX API might be down (check status)

---

## 📚 Resources

- [AVWX API Docs](https://avwx.rest/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Next.js Documentation](https://nextjs.org/docs)
- [Ollama](https://ollama.ai/)

---

## 📄 License

MIT License - see LICENSE file for details

---

**Built with ❤️ for aviation enthusiasts and developers**
