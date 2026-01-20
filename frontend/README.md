# Flight Copilot Frontend

Modern Next.js frontend for the Flight Copilot Agent with real-time health status and guardrail verification display.

## Features

- **Health Status Dashboard**: Real-time connection status with 5-second polling
- **Query Interface**: Submit questions and get AI responses
- **Live vs Fallback Flagging**: Clear visual indicators for response type
  - ✅ **Live**: Response passed guardrail verification
  - ⚠️ **Fallback**: Response failed verification, using safe-fail mechanism
- **Guardrail Status Display**: Shows if response was verified against METAR data
- **Responsive Design**: Works on desktop and mobile
- **TypeScript**: Fully typed API client and components

## Quick Start

### Prerequisites
- Node.js 18+ and npm/yarn
- Backend running on `http://localhost:8000`

### Installation

```bash
cd frontend
npm install
```

### Development

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Build for Production

```bash
npm run build
npm start
```

### Type Checking

```bash
npm run type-check
```

## Environment Variables

Create `.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Change the URL if your backend is running elsewhere.

## Project Structure

```
frontend/
├── app/                 # Next.js app directory
│   ├── layout.tsx      # Root layout
│   └── page.tsx        # Home page
├── components/          # React components
│   ├── HealthStatus.tsx # System status display
│   └── QueryInterface.tsx # Query form and response
├── lib/
│   └── api.ts          # Axios API client
├── styles/
│   └── globals.css     # Global styles
├── package.json
├── tsconfig.json
├── next.config.js
└── README.md
```

## API Integration

The frontend calls these backend endpoints:

- `GET /health` - System health status
- `POST /query` - Submit a question
- `GET /status` - General status

See [lib/api.ts](lib/api.ts) for type definitions and API client.

## Guardrail Status Indicators

### Response Type

| Badge | Meaning | When It Happens |
|-------|---------|-----------------|
| ✅ Live | Response passed guardrails | Claim within 3-knot threshold of actual crosswind |
| ⚠️ Fallback | Response failed and was corrected | Claim exceeded threshold; agent reflected and corrected; or if still failing, safe-fail triggered |

### Verification Status

| Status | Meaning |
|--------|---------|
| ✅ Passed | Response verified accurate against real METAR data |
| ❌ Failed (Corrected) | Initial response failed, agent generated correction |
| ⊘ Skipped | No METAR or runway data available; verification not possible |

### Data Availability

- **METAR**: Wind and weather data fetched from AVWX
- **Runway**: Runway heading selected for the airport

## Styling

Built with vanilla CSS (no Tailwind/Bootstrap):
- Purple gradient background (`#667eea` to `#764ba2`)
- Clean, modern card-based layout
- Color-coded response indicators
- Mobile responsive
- Smooth transitions and animations

## Development Tips

### Testing the Guardrail System

1. **Live Response** (Accurate claim):
   ```
   Query: "What's the crosswind for KDEN runway 260?"
   Expected: Response claims 7.4 kt, LIVE badge appears
   ```

2. **Fallback Response** (Inaccurate claim):
   ```
   Query: "The crosswind is 20 kt at Denver, right?"
   Expected: Agent corrects to ~7.4 kt, FALLBACK badge appears
   ```

3. **Skipped Verification** (No METAR):
   ```
   Query: "Tell me about flying at NOWHERE"
   Expected: Response with ⊘ Skipped status
   ```

### Debugging

- Open DevTools Console to see API errors
- Health status shows guardrails active/inactive
- Response details expand to show technical info
- Backend logs available at `logs/trace.jsonl`

## Deployment

### Vercel (Recommended for Next.js)

```bash
npm install -g vercel
vercel
```

### Docker

Create `Dockerfile`:

```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
```

```bash
docker build -t flight-copilot-frontend .
docker run -p 3000:3000 -e NEXT_PUBLIC_API_URL=http://backend:8000 flight-copilot-frontend
```

### Environment Setup

For production, set `NEXT_PUBLIC_API_URL` to your backend URL:

```bash
export NEXT_PUBLIC_API_URL=https://api.example.com
npm run build
npm start
```

## Troubleshooting

### Backend Not Responding

- **Issue**: "DISCONNECTED" status badge
- **Fix**: Ensure backend is running on the URL in `.env.local`

```bash
# Check if backend is running
curl http://localhost:8000/health
```

### CORS Errors

- **Issue**: Browser console shows CORS errors
- **Fix**: Backend needs CORS headers enabled

Add to [src/api/main.py](../src/api/main.py):

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Type Errors

- **Issue**: `npm run type-check` fails
- **Fix**: Ensure all API types match backend responses

Update types in [lib/api.ts](lib/api.ts) to match backend.

## Next Steps

1. **Backend CORS**: Add CORS middleware to allow frontend
2. **Testing**: Write E2E tests with Playwright/Cypress
3. **Analytics**: Add guardrail success/failure metrics
4. **Dark Mode**: Toggle theme preference
5. **Chat History**: Store and replay past queries
6. **Map Integration**: Show airport locations and weather

## Resources

- [Next.js Documentation](https://nextjs.org/docs)
- [React Documentation](https://react.dev)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
- [Axios Documentation](https://axios-http.com/)
