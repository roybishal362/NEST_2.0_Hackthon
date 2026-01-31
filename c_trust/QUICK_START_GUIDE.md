# C-TRUST Quick Start Guide

## TL;DR - Get Running in 3 Steps

### 1. Setup Environment

```bash
# Install Python dependencies
cd c_trust
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Install Frontend dependencies
cd frontend
npm install
cd ..
```

### 2. Configure .env File

Create `c_trust/.env`:

```env
# REQUIRED: Point to your NEST data
DATA_ROOT_PATH=../norvatas/Data for problem Statement 1/NEST 2.0 Data files_Anonymized/QC Anonymized Study Files

# REQUIRED: Security key (any random string for dev)
SECRET_KEY=your_secret_key_here

# OPTIONAL: Groq API for AI insights (get free key at console.groq.com)
GROQ_API_KEY=your_groq_api_key_here

# Other settings (defaults are fine)
API_PORT=8000
CORS_ORIGINS=http://localhost:5173
```

### 3. Start the System

**Terminal 1 - Backend:**
```bash
cd c_trust
.venv\Scripts\activate
python -m uvicorn src.api.main:app --reload --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd c_trust/frontend
npm run dev
```

**Access Dashboard:**
- Frontend: http://localhost:5173
- API Docs: http://localhost:8000/api/docs

## First Run - Cache Generation

On first startup, the backend automatically generates the data cache:

```
============================================================
NO DATA CACHE FOUND - GENERATING NOW
This will take a few minutes on first startup...
============================================================
```

- **Duration**: 2-5 minutes (one-time only)
- **What it does**: Analyzes all 23 studies and caches results
- **Server status**: API starts immediately, cache generates in background
- **Subsequent runs**: Instant startup (cache exists)

## Manual Cache Regeneration

If you need to refresh the cache (e.g., after data updates):

```bash
cd c_trust
python scripts/update_dashboard_cache.py
```

## Troubleshooting

### Backend won't start - Missing environment variables

**Error:**
```
pydantic_core._pydantic_core.ValidationError: 3 validation errors for Settings
GROQ_API_KEY Field required
DATA_ROOT_PATH Field required
SECRET_KEY Field required
```

**Fix:** Create `.env` file with required variables (see step 2 above)

### Cache not generating

**Check:**
1. Is `DATA_ROOT_PATH` correct in `.env`?
2. Can you access the NEST data files?
3. Check backend logs for errors

**Manual generation:**
```bash
python scripts/update_dashboard_cache.py
```

### Frontend can't connect to backend

**Check:**
1. Is backend running on port 8000?
2. Check `frontend/.env` has correct API URL:
   ```
   VITE_API_BASE_URL=http://localhost:8000
   ```

### Port already in use

**Backend (8000):**
```bash
# Use different port
python -m uvicorn src.api.main:app --reload --port 8001
```

**Frontend (5173):**
```bash
# Vite will auto-increment to 5174 if 5173 is busy
npm run dev
```

## What's Next?

- **Explore Dashboard**: Navigate through Portfolio, AI Insights, Study Details
- **Check API Docs**: http://localhost:8000/api/docs
- **Read Full README**: [README.md](README.md)
- **Cache Details**: [CACHE_GENERATION.md](CACHE_GENERATION.md)
- **Run Tests**: `pytest tests/` (331 tests should pass)

## System Architecture

```
┌─────────────────┐
│   Frontend      │  React + TypeScript + Vite
│  (Port 5173)    │  Dashboard UI
└────────┬────────┘
         │ HTTP/REST
         ▼
┌─────────────────┐
│   Backend       │  FastAPI + Python
│  (Port 8000)    │  API Server
└────────┬────────┘
         │
         ├─► Data Ingestion (NEST 2.0 Excel files)
         ├─► Feature Extraction (Real data processing)
         ├─► 7 AI Agents (Multi-agent analysis)
         ├─► DQI Engine (Quality scoring)
         └─► Cache (data_cache.json)
```

## Key Files

- `c_trust/.env` - Configuration (you create this)
- `c_trust/data_cache.json` - Analysis cache (auto-generated)
- `c_trust/src/api/main.py` - Backend entry point
- `c_trust/frontend/src/App.tsx` - Frontend entry point
- `c_trust/scripts/update_dashboard_cache.py` - Manual cache generator

## Support

For issues or questions:
1. Check [README.md](README.md) for detailed documentation
2. Check [CACHE_GENERATION.md](CACHE_GENERATION.md) for cache issues
3. Review backend logs for error details
4. Check API health: http://localhost:8000/api/v1/health
