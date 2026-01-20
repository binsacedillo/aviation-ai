# 🚀 Quick Start - Full Stack

## One-Command Start (Docker Compose)

```bash
docker-compose up
```

This starts everything:
- Backend: http://localhost:8000
- Frontend: http://localhost:3000

## Manual Start (Development)

### Terminal 1: Backend
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Terminal 2: Frontend
```bash
cd frontend
npm install
npm run dev
```

### Terminal 3: Run Tests
```bash
python -m pytest tests/ -v
```

## Test the System

1. **Open Frontend**: http://localhost:3000
2. **Check Health**: See ✅ LIVE or 🔴 DISCONNECTED status
3. **Ask Question**: "What's the crosswind at KDEN runway 260?"
4. **Check Badge**:
   - ✅ LIVE = Response passed guardrails
   - ⚠️ FALLBACK = Response failed & was corrected

## What's New

### Frontend (Next.js)
- [frontend/README.md](frontend/README.md) - Frontend guide
- [FRONTEND_SETUP.md](FRONTEND_SETUP.md) - Detailed setup
- Components: HealthStatus, QueryInterface
- Styling: Vanilla CSS (no dependencies)
- Types: Full TypeScript support

### Backend Updates
- CORS enabled for frontend
- New `/query` endpoint (frontend-friendly)
- Health endpoint includes test status
- Guardrail status in responses

### Deployment
- [docker-compose.yml](docker-compose.yml) - One-command deployment
- [Dockerfile.backend](Dockerfile.backend) - Backend container
- [frontend/Dockerfile](frontend/Dockerfile) - Frontend container
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) - Full deployment guide

## Key Endpoints

```
GET  /health              → System status + test count
POST /query              → Query (frontend-friendly)
POST /query/legacy       → Original detailed format
POST /query/stream       → Real-time streaming
GET  /tools              → Available tools list
```

## Frontend Interface

**Left Column**: System Health
- Real-time status (5s polling)
- Guardrails active
- Test pass rate

**Right Column**: Query Interface
- Input question
- Get response with guardrail status
- See if live or fallback

**Bottom**: Information Panel
- Explains live vs fallback
- Explains verification status
- Technical details

## Troubleshooting

**Frontend won't load?**
```bash
cd frontend
npm install
npm run dev
```

**Backend won't connect?**
- Check: `curl http://localhost:8000/health`
- Verify CORS: Check `.env.local` has right URL

**Tests failing?**
```bash
python -m pytest tests/ -v --tb=short
```

**Port already in use?**
```bash
# Change port in frontend: edit frontend/package.json
# Change port in backend: edit --port 8000 to another port
```

## File Structure

```
flight-copilot-agent/
├── frontend/                    # Next.js UI
│   ├── app/                     # Pages & layout
│   ├── components/              # React components
│   ├── lib/api.ts              # API client
│   ├── styles/globals.css      # Styling
│   └── package.json
├── src/
│   ├── agent/agent.py          # AI agent + guardrails
│   ├── api/main.py             # FastAPI server
│   ├── database/               # Database layer
│   └── tools/                  # Tool implementations
├── tests/                       # Test suite (32 tests)
├── docs/
│   ├── TESTING.md              # Test guide
│   ├── DEPLOYMENT.md           # Deploy guide
├── docker-compose.yml          # Full-stack container
├── Dockerfile.backend          # Backend container
└── requirements.txt            # Backend dependencies
```

## Next Steps

1. ✅ Run with `docker-compose up`
2. ✅ Test at http://localhost:3000
3. ✅ Try test cases (see FRONTEND_SETUP.md)
4. ✅ Deploy with [DEPLOYMENT.md](docs/DEPLOYMENT.md)

## Help

- Backend questions? See [README.md](README.md)
- Frontend questions? See [frontend/README.md](frontend/README.md)
- Testing questions? See [docs/TESTING.md](docs/TESTING.md)
- Deployment questions? See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)

---

**Status**: ✅ Production Ready
- Backend: 3-layer guardrail protection ✅
- Frontend: Minimal UI with health & query ✅
- Tests: 32 tests passing ✅
- Docker: One-command deployment ✅
