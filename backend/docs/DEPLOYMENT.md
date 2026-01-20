# Full-Stack Deployment Guide

## Overview

Complete instructions for deploying the Flight Copilot system with:
- Backend (FastAPI) on port 8000
- Frontend (Next.js) on port 3000
- PostgreSQL database (optional)
- Docker containerization

## Prerequisites

- Node.js 18+
- Python 3.10+
- Docker & Docker Compose (for containerized deployment)
- Git

## Quick Start (Local Development)

### 1. Backend Setup

```bash
cd flight-copilot-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run backend
python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at `http://localhost:8000`

Health check: `curl http://localhost:8000/health`

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure backend URL
cp .env.local.example .env.local
# Edit .env.local if backend is on different URL

# Run frontend
npm run dev
```

Frontend will be available at `http://localhost:3000`

## Docker Deployment

### Single Command (Docker Compose)

```bash
# In project root
docker-compose up
```

This starts:
- Backend on `http://localhost:8000`
- Frontend on `http://localhost:3000`

### Individual Docker Images

#### Backend Image

```bash
# Build
docker build -f Dockerfile.backend -t flight-copilot-backend .

# Run
docker run -p 8000:8000 \
  -e LOG_LEVEL=info \
  flight-copilot-backend
```

#### Frontend Image

```bash
# Build
docker build -f Dockerfile.frontend -t flight-copilot-frontend .

# Run
docker run -p 3000:3000 \
  -e NEXT_PUBLIC_API_URL=http://localhost:8000 \
  flight-copilot-frontend
```

## Production Deployment

### Environment Variables

#### Backend (.env)
```
LOG_LEVEL=warning
ENVIRONMENT=production
API_PORT=8000
CORS_ORIGINS=https://yourdomain.com
```

#### Frontend (.env.production)
```
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
```

### Deployment Platforms

#### Vercel (Frontend)

```bash
npm install -g vercel
cd frontend
vercel --prod
```

Configure environment variables in Vercel dashboard:
- `NEXT_PUBLIC_API_URL`: Your backend API URL

#### Railway (Backend + Frontend)

```bash
npm install -g railway
railway login
railway up
```

#### AWS EC2

```bash
# On EC2 instance
git clone <repo>
cd flight-copilot-agent

# Backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
nohup python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 &

# Frontend
cd frontend
npm install
npm run build
npm start &
```

Use Nginx as reverse proxy:

```nginx
upstream backend {
    server localhost:8000;
}

upstream frontend {
    server localhost:3000;
}

server {
    listen 80;
    server_name yourdomain.com;

    location /api {
        proxy_pass http://backend;
    }

    location / {
        proxy_pass http://frontend;
    }
}
```

### Kubernetes Deployment

See `k8s/` directory for Kubernetes manifests.

```bash
# Deploy
kubectl apply -f k8s/

# Check status
kubectl get pods
kubectl get services
```

## Database Setup (Optional)

### PostgreSQL

```bash
docker run -d \
  --name flight-copilot-db \
  -e POSTGRES_PASSWORD=secure_password \
  -p 5432:5432 \
  postgres:15
```

Connection string:
```
postgresql://postgres:secure_password@localhost:5432/flight_copilot
```

### Migrations

```bash
# From backend directory
python -m alembic upgrade head
```

## Monitoring

### Logs

```bash
# Backend
tail -f logs/trace.jsonl

# Frontend (check browser console)
# Open http://localhost:3000 and check DevTools
```

### Health Checks

```bash
# Backend health
curl http://localhost:8000/health

# Frontend health (check page loads)
curl http://localhost:3000
```

### Metrics (Future)

Coming soon:
- Guardrail pass/fail rates
- Response times
- API usage statistics
- Error tracking

## Troubleshooting

### Backend won't start

```bash
# Check Python version
python --version  # Should be 3.10+

# Check dependencies
pip list | grep fastapi

# Check port 8000 is available
lsof -i :8000
```

### Frontend won't connect to backend

1. Check `.env.local` has correct `NEXT_PUBLIC_API_URL`
2. Verify backend is running: `curl http://localhost:8000/health`
3. Check browser console for CORS errors
4. Ensure CORS is enabled in backend

### Tests failing after deployment

```bash
# Run tests locally
python -m pytest tests/ -v

# Check logs
cat logs/trace.jsonl
```

## SSL/HTTPS Setup

### Let's Encrypt with Certbot

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot certonly --nginx -d yourdomain.com
```

Update Nginx config:

```nginx
server {
    listen 443 ssl http2;
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    # ... rest of config
}
```

## Backup & Recovery

### Database Backup

```bash
# PostgreSQL backup
pg_dump flight_copilot > backup.sql

# Restore
psql flight_copilot < backup.sql
```

### Configuration Backup

```bash
# Backup environment files
cp .env .env.backup
cp frontend/.env.local frontend/.env.local.backup
```

## Performance Optimization

### Frontend

- Enable gzip compression in Nginx
- Use CDN for static assets
- Implement lazy loading for components

### Backend

- Use uvicorn workers: `--workers 4`
- Enable response caching
- Use connection pooling for database

### Both

- Enable HTTP/2
- Use SSL/TLS
- Monitor response times
- Implement rate limiting

## Security Checklist

- [ ] CORS configured for production domain only
- [ ] Environment variables not committed to git
- [ ] HTTPS/SSL enabled
- [ ] Database credentials in secure vault
- [ ] API rate limiting enabled
- [ ] Input validation on all endpoints
- [ ] Guardrails active and tested
- [ ] Audit logging enabled
- [ ] Regular security updates applied
- [ ] Backup strategy in place

## Support & Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Next.js Documentation](https://nextjs.org/docs)
- [Docker Documentation](https://docs.docker.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
