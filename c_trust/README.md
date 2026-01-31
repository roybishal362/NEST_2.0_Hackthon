# C-TRUST: Clinical Trial Risk Understanding through Systematic Testing

**Production-Ready AI-Powered Clinical Trial Operations Platform**

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.3+-61DAFB.svg)](https://reactjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-3178C6.svg)](https://www.typescriptlang.org/)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)]()

---

## 📋 Table of Contents

- [What is C-TRUST?](#-what-is-c-trust)
- [Key Features](#-key-features)
- [System Requirements](#-system-requirements)
- [Quick Start](#-quick-start)
- [Running the System](#-running-the-system)
- [Usage Guide](#-usage-guide)
- [Configuration](#-configuration)
- [Troubleshooting](#-troubleshooting)
- [Project Structure](#-project-structure)
- [Development](#-development)
- [API Documentation](#-api-documentation)
- [Testing](#-testing)
- [License & Credits](#-license--credits)

---

## 🎯 What is C-TRUST?

C-TRUST (Clinical Trial Risk Understanding through Systematic Testing) is an enterprise-grade, AI-powered data quality intelligence system designed specifically for clinical trial operations. Built for the Novartis NEST 2.0 ecosystem, C-TRUST transforms how pharmaceutical companies monitor, assess, and improve data quality across their clinical trial portfolios.

### The Problem We Solve

Clinical trials generate massive amounts of data across multiple systems (EDC, SAE dashboards, coding reports, query systems), making it nearly impossible to:
- **Detect data quality issues early** before they impact regulatory submissions
- **Assess patient safety risks** from incomplete or delayed SAE reporting
- **Monitor portfolio-wide trends** across 20+ concurrent studies
- **Prioritize remediation efforts** based on actual risk levels
- **Maintain audit trails** for regulatory compliance

### Our Solution

C-TRUST employs a **multi-agent AI architecture** where 7 specialized agents independently analyze different aspects of data quality, then reach consensus through weighted voting. This approach provides:

✅ **Automated Risk Assessment**: Analyzes studies in ~300ms with transparent reasoning  
✅ **Real Data Processing**: Extracts features directly from NEST 2.0 files (no synthetic data)  
✅ **Agent-Driven DQI Scoring**: Data Quality Index calculated from actual agent assessments  
✅ **Guardian Oversight**: Meta-agent monitors system integrity and cross-agent consistency  
✅ **Production-Ready**: Comprehensive error handling, caching, logging, and 331 passing tests


---

## ✨ Key Features

### 1. Multi-Agent AI Architecture
- **7 Specialized Agents**: Safety & Compliance, Data Completeness, Coding Readiness, Query Quality, Temporal Drift, EDC Quality, Stability
- **Independent Analysis**: Each agent operates on isolated feature copies, preventing cascade failures
- **Weighted Consensus**: Safety Agent has 3.0x weight (patient safety first), others 1.2-1.5x
- **Graceful Degradation**: Agents abstain when data is insufficient rather than guessing

### 2. Agent-Driven DQI Calculation
- **Semantic Scoring**: DQI reflects actual data quality issues identified by agents
- **6 Dimensions**: Safety (35%), Completeness (20%), Accuracy (15%), Timeliness (15%), Conformance (10%), Consistency (5%)
- **Confidence-Weighted**: Agent confidence affects dimension scores
- **Consensus Modifier**: High-risk consensus reduces DQI by up to 20 points
- **Band Classification**: Green (85-100), Amber (65-84), Orange (40-64), Red (<40)

### 3. Real Data Extraction
- **No Fallbacks**: Features extracted directly from NEST 2.0 files without synthetic data
- **Multi-Row Header Support**: Handles complex EDC Metrics files with 3-row headers
- **Flexible Column Mapping**: Adapts to column name variations across studies
- **Transparent Limitations**: System explicitly states when data is unavailable

### 4. Guardian Meta-Agent
- **System Integrity Monitoring**: Validates cross-agent consistency
- **Semantic Checks**: Ensures DQI-consensus alignment
- **Staleness Detection**: Monitors data freshness
- **Anomaly Identification**: Catches unusual agent behavior

### 5. Comprehensive Dashboard
- **Portfolio Overview**: Executive view of all 23 studies with risk heatmap
- **AI Insights**: Agent status, recommendations, and confidence scores
- **Study Details**: Deep dive into individual study metrics and trends
- **Site & Patient Views**: Drill-down to site-level and patient-level data
- **Guardian Dashboard**: System health monitoring and alerts
- **Analytics**: Historical trends and performance metrics

### 6. Production-Ready Engineering
- **Multi-Layer Caching**: Backend file cache, React Query, localStorage (AI insights)
- **Comprehensive Error Handling**: Graceful failures with detailed logging
- **Property-Based Testing**: 331 tests including Hypothesis for algorithm correctness
- **Performance Optimized**: Parallel agent execution, efficient data processing
- **RESTful API**: FastAPI with automatic OpenAPI documentation


---

## 💻 System Requirements

### Minimum Requirements

#### Backend
- **Operating System**: Windows 10/11, macOS 10.15+, or Linux (Ubuntu 20.04+)
- **Python**: 3.10 or higher
- **RAM**: 4 GB minimum (8 GB recommended)
- **Disk Space**: 2 GB for application + data
- **CPU**: 2 cores minimum (4 cores recommended for parallel agent execution)

#### Frontend
- **Node.js**: 18.0 or higher
- **npm**: 9.0 or higher (comes with Node.js)
- **Modern Web Browser**: Chrome 90+, Firefox 88+, Safari 14+, or Edge 90+

### Recommended Specifications

For optimal performance when processing 23 studies:
- **RAM**: 16 GB
- **CPU**: 4+ cores (enables faster parallel agent execution)
- **SSD**: For faster file I/O operations
- **Network**: Stable internet connection for LLM API calls (Groq)

### Software Dependencies

#### Python Packages (automatically installed)
- FastAPI 0.104+ (REST API framework)
- Pandas 2.1+ (data manipulation)
- Pydantic 2.5+ (data validation)
- Openpyxl 3.1+ (Excel file reading)
- Uvicorn 0.24+ (ASGI server)
- Groq 0.4+ (LLM integration)
- Hypothesis 6.92+ (property-based testing)

#### Node.js Packages (automatically installed)
- React 18.3+ (UI framework)
- TypeScript 5.0+ (type safety)
- React Query 5.0+ (data fetching & caching)
- TailwindCSS 3.4+ (styling)
- Recharts 2.10+ (charts)
- Axios 1.6+ (HTTP client)

### External Services (Optional)

- **Groq API**: For AI-generated insights (free tier available)
  - Sign up at: https://console.groq.com
  - Free tier: 30 requests/minute
  - Required only for AI Insights page


---

## 🚀 Quick Start

Get C-TRUST running in 5 minutes with these simple steps.

### Prerequisites

Before you begin, ensure you have:

1. **Python 3.10+** installed
   ```bash
   python --version  # Should show 3.10 or higher
   ```

2. **Node.js 18+** installed
   ```bash
   node --version  # Should show 18.0 or higher
   npm --version   # Should show 9.0 or higher
   ```

3. **Git** (to clone the repository)
   ```bash
   git --version
   ```

4. **NEST 2.0 Data Files** (provided by Novartis)
   - Location: `norvatas/Data for problem Statement 1/NEST 2.0 Data files_Anonymized/QC Anonymized Study Files`
   - Contains 23 study folders with Excel files

### Installation Steps

#### Step 1: Clone the Repository

```bash
git clone @##################################
cd c_trust
```

#### Step 2: Set Up Python Backend

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

#### Step 3: Set Up Frontend

```bash
# Navigate to frontend directory
cd frontend

# Install Node.js dependencies
npm install

# Return to project root
cd ..
```

#### Step 4: Configure Environment

Create a `.env` file in the `c_trust` directory (or copy from `.env.example`):

```env
# Data Source
DATA_ROOT_PATH=..../Data for problem Statement 1/NEST 2.0 Data files_Anonymized/QC Anonymized Study Files

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# Groq API (Optional - for AI Insights)
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile

# Application Settings
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
```

**Important**: Update `DATA_ROOT_PATH` to point to your NEST 2.0 data location.

**Optional**: Get a free Groq API key at https://console.groq.com for AI-generated insights.


---

## 🎮 Running the System

C-TRUST can be run in two modes depending on your needs:

### Option 1: Frontend-Only Mode (Quick Demo)

**Best for**: Quick demonstrations, UI exploration, or when backend setup is not feasible.

**What you get**: Access to pre-processed data from all 23 studies via cached JSON file.

**Limitations**: No real-time data processing, no API calls, AI Insights may use cached data.

#### Using Cached Data

The system includes a pre-generated `data_cache.json` file with analysis results for all 23 studies. This allows you to run the frontend without the backend.

#### Starting Frontend

```bash
# Navigate to frontend directory (Note: Check first that you are in c_trust directory)
cd frontend

# Start development server
npm run dev
```

**Expected output**:
```
VITE v6.x.x  ready in xxx ms

➜  Local:   http://localhost:5173/
➜  Network: use --host to expose
```

#### Accessing Dashboard

Open your browser and navigate to:
```
http://localhost:5173
```

You should see the Portfolio Overview page with all 23 studies displayed.

#### Limitations of Frontend-Only Mode

- ❌ Cannot process new data or refresh analysis
- ❌ Cannot generate new predictions
- ❌ AI Insights may show cached responses (24-hour TTL)
- ❌ No access to API documentation
- ✅ Can explore all dashboard pages
- ✅ Can view historical data and trends
- ✅ Can test UI interactions

---

### Option 2: Full System Mode (Production)

**Best for**: Production use, development, testing, or when you need real-time data processing.

**What you get**: Complete functionality including data ingestion, agent analysis, and API access.

You'll need **two terminal windows** - one for backend, one for frontend.

#### Starting Backend

**Terminal 1** (Backend):

```bash
# Ensure you're in the c_trust directory
cd c_trust

# Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Start FastAPI server
python -m uvicorn src.api.main:app --reload --port 8000
```

**Expected output**:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

**Verify backend is running**:
- API: http://localhost:8000
- API Docs: http://localhost:8000/api/docs (interactive Swagger UI)
- Health Check: http://localhost:8000/api/v1/health

#### Generating Cache

On first run, or to refresh data, generate the cache:

```bash
# In a new terminal (with virtual environment activated)
python scripts/update_dashboard_cache.py
```

This will:
1. Discover all 23 studies in the NEST 2.0 dataset
2. Extract features from Excel files
3. Run 7 AI agents on each study
4. Calculate consensus and DQI scores
5. Save results to `data_cache.json`

**Expected duration**: 3-8 seconds per study (~2-3 minutes total for 23 studies)

#### Starting Frontend

**Terminal 2** (Frontend):

```bash
# Navigate to frontend directory (Note: Check first that you are in c_trust directory)
cd frontend

# Start development server
npm run dev
```

**Expected output**:
```
VITE v6.x.x  ready in xxx ms

➜  Local:   http://localhost:5173/
➜  Network: use --host to expose
```

#### Full Functionality

With both backend and frontend running, you have access to:

✅ **Real-time data processing**: Refresh analysis on demand  
✅ **Complete API access**: All endpoints available  
✅ **AI Insights**: Fresh LLM-generated recommendations  
✅ **Export functionality**: Generate CSV reports  
✅ **Guardian monitoring**: System integrity checks  
✅ **Developer tools**: API documentation, logs, debugging


---

## 📖 Usage Guide

### Dashboard Navigation

Once the system is running, you can access these pages:

#### 1. Portfolio Overview (`/`)
**Purpose**: Executive dashboard showing all 23 studies at a glance

**Key Metrics**:
- Total studies count
- Average DQI score across portfolio
- Risk distribution (Critical/High/Medium/Low)
- Study cards with DQI scores and risk indicators

**Actions**:
- Click any study card to view detailed analysis
- Filter studies by risk level
- Sort by DQI score, study ID, or enrollment

#### 2. AI Insights (`/insights`)
**Purpose**: View agent status and AI-generated recommendations

**Features**:
- Status of all 7 agents (active/abstained)
- Agent confidence scores
- Consensus risk level
- AI-generated insights (requires Groq API key)
- Guardian system status

**Use Cases**:
- Understand why a study received a specific DQI score
- See which agents identified issues
- Get actionable recommendations

#### 3. Study Details (`/study/:studyId`)
**Purpose**: Deep dive into individual study metrics

**Sections**:
- DQI gauge with band classification
- Agent signals breakdown
- Site-level metrics
- Patient enrollment data
- Temporal trends
- Export functionality

**Actions**:
- Drill down to site view
- Drill down to patient view
- Export study report as CSV

#### 4. Site View (`/study/:studyId/site/:siteId`)
**Purpose**: Site-level data quality analysis

**Metrics**:
- Site-specific DQI score
- Enrollment status
- Query backlog
- SAE discrepancies
- Form completion rate

#### 5. Patient View (`/study/:studyId/patient/:patientId`)
**Purpose**: Patient-level data exploration

**Information**:
- Patient demographics
- Visit completion status
- Form completion status
- Query history
- SAE records

#### 6. Guardian Dashboard (`/guardian`)
**Purpose**: System health monitoring

**Monitors**:
- Cross-agent consistency
- Data freshness
- System anomalies
- Event log

#### 7. Analytics (`/analytics`)
**Purpose**: Historical trends and performance metrics

**Charts**:
- DQI trends over time
- Risk distribution evolution
- Agent performance metrics
- Portfolio health indicators

### Understanding DQI Scores

**DQI (Data Quality Index)** is a 0-100 score calculated from agent assessments:

| Band | Score Range | Color | Meaning |
|------|-------------|-------|---------|
| **Green** | 85-100 | 🟢 | Analysis-ready, minimal issues |
| **Amber** | 65-84 | 🟡 | Minor issues, monitor closely |
| **Orange** | 40-64 | 🟠 | Attention needed, remediation required |
| **Red** | <40 | 🔴 | Not submission-ready, critical issues |

**DQI Dimensions** (weighted):
- Safety (35%): SAE reviews, fatal events
- Completeness (20%): Missing data, form completion
- Accuracy (15%): Coding quality, data entry errors
- Timeliness (15%): Query aging, data entry lag
- Conformance (10%): Protocol compliance
- Consistency (5%): Cross-source validation

### Understanding Agent Signals

Each agent provides a **risk signal** (Critical/High/Medium/Low) with:
- **Confidence Score**: 0-100% (how certain the agent is)
- **Evidence**: Specific metrics that drove the assessment
- **Reasoning**: Why the agent reached this conclusion

**Agent Types**:
1. **Safety & Compliance** (3.0x weight): Fatal SAEs, overdue reviews
2. **Data Completeness** (1.5x): Missing pages, incomplete forms
3. **Coding Readiness** (1.2x): Uncoded terms, coding backlog
4. **Query Quality** (1.5x): Open queries, query aging
5. **Temporal Drift** (1.2x): Data entry lag, visit delays
6. **EDC Quality** (1.2x): Form verification, data entry errors
7. **Stability** (1.2x): Visit completion, enrollment velocity

**Abstention**: An agent may abstain if it lacks sufficient data (e.g., no coding report available). This is normal and maintains system integrity.

### Exporting Data

Generate CSV reports for external analysis:

1. Navigate to Study Details page
2. Click "Export" button
3. Select export format:
   - Study summary
   - Site-level data
   - Patient-level data
   - Agent signals

Files are saved to `exports/` directory.


---

## ⚙️ Configuration

### Environment Variables

C-TRUST uses environment variables for configuration. Create a `.env` file in the `c_trust` directory:

#### Required Settings

```env
# Data Source (REQUIRED)
DATA_ROOT_PATH=path/to/NEST 2.0 Data files_Anonymized/QC Anonymized Study Files
```

#### API Configuration

```env
# API Server
API_HOST=0.0.0.0
API_PORT=8000
API_PREFIX=/api/v1

# CORS (for frontend access)
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

#### AI/ML Configuration

```env
# Groq API (Optional - for AI Insights)
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_TEMPERATURE=0.1
GROQ_MAX_TOKENS=2048

# LangChain (Optional - for tracing)
LANGCHAIN_TRACING=false
LANGCHAIN_API_KEY=your_langchain_api_key
```

#### DQI Engine Configuration

```env
# Dimension Weights (must sum to 100)
DQI_SAFETY_WEIGHT=35
DQI_COMPLIANCE_WEIGHT=25
DQI_COMPLETENESS_WEIGHT=25
DQI_OPERATIONS_WEIGHT=15

# Threshold Settings
DQI_CRITICAL_THRESHOLD=50
DQI_HIGH_THRESHOLD=70
DQI_MEDIUM_THRESHOLD=85
```

#### Agent Configuration

```env
# Agent Consensus Weights
AGENT_SAFETY_WEIGHT=30
AGENT_COMPLETENESS_WEIGHT=20
AGENT_COMPLIANCE_WEIGHT=20
AGENT_OPERATIONS_WEIGHT=15
AGENT_CODING_WEIGHT=10
AGENT_TIMELINE_WEIGHT=5

# Agent Behavior
AGENT_MIN_CONFIDENCE=0.6
AGENT_ABSTENTION_THRESHOLD=0.5
```

#### Guardian Configuration

```env
# Guardian System
GUARDIAN_ENABLED=true
GUARDIAN_CHECK_INTERVAL_HOURS=6
GUARDIAN_DRIFT_THRESHOLD=0.15
```

#### Application Settings

```env
# General
APP_NAME=C-TRUST
APP_VERSION=1.0.0
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Performance
BATCH_SIZE=10
MAX_WORKERS=4
```

### YAML Configuration Files

Additional configuration is available in `config/` directory:

#### `config/system_config.yaml`

Defines file type patterns for NEST 2.0 data:

```yaml
file_types:
  EDC_METRICS:
    patterns:
      - "*CPID_EDC_Metrics*.xlsx"
      - "*EDC_Metrics*.xlsx"
  SAE_DM:
    patterns:
      - "*eSAE Dashboard*.xlsx"
  MEDDRA:
    patterns:
      - "*GlobalCodingReport_MedDRA*.xlsx"
  # ... more file types
```

#### `config/settings.yaml`

Application-wide settings:

```yaml
app:
  name: "C-TRUST"
  version: "1.0.0"

agents:
  timeout_seconds: 30
  parallel_execution: true
  
cache:
  enabled: true
  ttl_hours: 24
```

### Frontend Configuration

Frontend configuration in `frontend/.env`:

```env
# API Endpoint
VITE_API_BASE_URL=http://localhost:8000

# Feature Flags
VITE_ENABLE_AI_INSIGHTS=true
VITE_ENABLE_GUARDIAN=true
VITE_ENABLE_EXPORT=true
```

### Customizing Agent Thresholds

To adjust agent risk thresholds, modify agent classes in `src/agents/signal_agents/`:

Example for Safety Agent (`safety_agent.py`):

```python
# Adjust these thresholds based on your organization's risk tolerance
CRITICAL_THRESHOLDS = {
    'fatal_sae_count': 0,  # Any fatal SAE = critical
    'sae_backlog_days': 14.0,  # 2 weeks
}

HIGH_THRESHOLDS = {
    'sae_backlog_days': 7.0,  # 1 week
}
```

### Logging Configuration

Logs are written to `logs/` directory:

- `logs/c_trust.log` - Application logs
- `logs/error.log` - Error logs only
- `logs/audit.log` - Audit trail

Configure log level in `.env`:
```env
LOG_LEVEL=INFO  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
```


---

## 🔧 Troubleshooting

### Common Issues and Solutions

#### Backend Issues

##### Issue: "ModuleNotFoundError: No module named 'src'"

**Cause**: Running the API from wrong directory or incorrect Python path.

**Solution**:
```bash
# Ensure you're in the c_trust directory
cd c_trust

# Use the correct command
python -m uvicorn src.api.main:app --reload --port 8000

# NOT: python src/api/main.py
```

##### Issue: "Port 8000 already in use"

**Cause**: Another process is using port 8000.

**Solution (Windows)**:
```powershell
# Find process using port 8000
netstat -ano | findstr :8000

# Kill the process (replace <PID> with actual process ID)
taskkill /PID <PID> /F
```

**Solution (macOS/Linux)**:
```bash
# Find and kill process
lsof -ti:8000 | xargs kill -9
```

##### Issue: "FileNotFoundError: NEST 2.0 data not found"

**Cause**: `DATA_ROOT_PATH` in `.env` is incorrect.

**Solution**:
1. Verify the path exists: `dir "path\to\NEST 2.0 Data files_Anonymized"`
2. Update `.env` with correct path (use forward slashes or escaped backslashes)
3. Restart backend

##### Issue: "No studies discovered"

**Cause**: Study folders don't match expected pattern.

**Solution**:
1. Check folder names match pattern: `study_01`, `Study 01`, `STUDY_01`, etc.
2. Verify folders contain Excel files
3. Check logs: `logs/c_trust.log` for details

##### Issue: "Agent abstention rate too high"

**Cause**: Missing required data files for agents.

**Solution**:
1. Check which files are missing: Review agent abstention reasons in logs
2. Ensure all file types are present:
   - EDC Metrics (required for most agents)
   - SAE Dashboard (required for Safety Agent)
   - Coding Reports (required for Coding Agent)
   - Query Reports (required for Query Agent)
3. If files are genuinely missing, this is expected behavior (agents abstain gracefully)

#### Frontend Issues

##### Issue: "npm install" fails with dependency errors

**Cause**: Node.js version incompatibility or corrupted cache.

**Solution**:
```bash
# Clear npm cache
npm cache clean --force

# Delete node_modules and package-lock.json
rm -rf node_modules package-lock.json

# Reinstall
npm install
```

##### Issue: "Port 5173 already in use"

**Cause**: Another Vite dev server is running.

**Solution (Windows)**:
```powershell
netstat -ano | findstr :5173
taskkill /PID <PID> /F
```

**Solution (macOS/Linux)**:
```bash
lsof -ti:5173 | xargs kill -9
```

##### Issue: Dashboard shows "Loading..." indefinitely

**Cause**: Backend not running or CORS issue.

**Solutions**:
1. **Verify backend is running**: Open http://localhost:8000/api/docs
2. **Check CORS settings**: Ensure `.env` has `CORS_ORIGINS=http://localhost:5173`
3. **Check browser console**: Look for CORS or network errors
4. **Hard refresh**: Press Ctrl+F5 (Windows) or Cmd+Shift+R (Mac)

##### Issue: "Failed to fetch" errors in console

**Cause**: Backend not running or wrong API URL.

**Solution**:
1. Verify backend is running: `curl http://localhost:8000/api/v1/health`
2. Check frontend `.env`: `VITE_API_BASE_URL=http://localhost:8000`
3. Restart frontend after changing `.env`

##### Issue: AI Insights page shows "No insights available"

**Cause**: Missing Groq API key or rate limit exceeded.

**Solutions**:
1. **Add API key**: Set `GROQ_API_KEY` in backend `.env`
2. **Check rate limits**: Free tier allows 30 requests/minute
3. **Check logs**: `logs/c_trust.log` for API errors
4. **Use cached insights**: System caches insights for 24 hours

#### Data Processing Issues

##### Issue: "Multi-row header detection failed"

**Cause**: EDC Metrics file has unexpected format.

**Solution**:
1. Verify file is EDC Metrics: Check filename contains "EDC_Metrics" or "CPID_EDC"
2. Open file manually: Ensure it has 3-row header
3. Check logs for specific error
4. If format is different, update `ExcelFileReader` in `src/data/ingestion.py`

##### Issue: "Column not found" errors

**Cause**: Column name variations not covered by FlexibleColumnMapper.

**Solution**:
1. Check actual column names in Excel file
2. Add pattern to `COLUMN_PATTERNS` in `src/data/column_mapper.py`:
   ```python
   COLUMN_PATTERNS = {
       'visit': [r'visit', r'visit\s+name', r'your_new_pattern'],
   }
   ```
3. Restart backend

##### Issue: DQI scores seem incorrect

**Cause**: Agent thresholds may not match your organization's standards.

**Solution**:
1. Review agent logic in `src/agents/signal_agents/`
2. Adjust thresholds in agent classes
3. Regenerate cache: `python scripts/update_dashboard_cache.py`

#### Performance Issues

##### Issue: Slow data processing

**Cause**: Large Excel files or limited system resources.

**Solutions**:
1. **Increase workers**: Set `MAX_WORKERS=8` in `.env` (if you have 8+ CPU cores)
2. **Reduce batch size**: Set `BATCH_SIZE=5` in `.env`
3. **Use SSD**: Move data to SSD for faster I/O
4. **Close other applications**: Free up RAM

##### Issue: High memory usage

**Cause**: Processing many large files simultaneously.

**Solutions**:
1. Reduce `MAX_WORKERS` in `.env`
2. Process studies in batches
3. Clear cache: Delete `data_cache.json` and regenerate

### Getting Help

If you encounter issues not covered here:

1. **Check logs**: `logs/c_trust.log` contains detailed error messages
2. **Enable debug mode**: Set `DEBUG=true` in `.env` for verbose logging
3. **Review API docs**: http://localhost:8000/api/docs for endpoint details
4. **Check GitHub issues**: Search for similar problems
5. **Contact support**: Provide logs and error messages

### Verification Commands

Test your setup with these commands:

```bash
# Backend health check
curl http://localhost:8000/api/v1/health

# List studies
curl http://localhost:8000/api/v1/studies

# Get study details
curl http://localhost:8000/api/v1/studies/STUDY_01

# Check agent status
curl http://localhost:8000/api/v1/agents

# Guardian status
curl http://localhost:8000/api/v1/guardian/status
```


---

## 📁 Project Structure

```
c_trust/
├── .env                          # Environment configuration
├── .venv/                        # Python virtual environment
├── requirements.txt              # Python dependencies
├── run.py                        # Backend entry point
├── data_cache.json              # Cached analysis results
│
├── config/                       # Configuration files
│   ├── system_config.yaml       # File type patterns
│   ├── settings.yaml            # Application settings
│   └── simulated_profiles.yaml  # Test data profiles
│
├── src/                         # Backend source code
│   ├── __init__.py
│   │
│   ├── api/                     # REST API
│   │   ├── main.py             # FastAPI application
│   │   ├── routes/             # API route handlers
│   │   └── export.py           # Export functionality
│   │
│   ├── agents/                  # AI Agents
│   │   └── signal_agents/      # 7 specialized agents
│   │       ├── safety_agent.py
│   │       ├── completeness_agent.py
│   │       ├── coding_agent.py
│   │       ├── query_agent.py
│   │       ├── temporal_drift_agent.py
│   │       ├── edc_quality_agent.py
│   │       └── stability_agent.py
│   │
│   ├── intelligence/            # Core AI logic
│   │   ├── base_agent.py       # Base agent class
│   │   ├── agent_pipeline.py   # Agent orchestration
│   │   ├── consensus.py        # Consensus engine
│   │   ├── dqi_engine_agent_driven.py  # DQI calculation
│   │   └── llm_client.py       # LLM integration
│   │
│   ├── data/                    # Data processing
│   │   ├── ingestion.py        # Excel file reading
│   │   ├── features.py         # Feature extraction
│   │   ├── features_real_extraction.py  # Real data extraction
│   │   ├── column_mapper.py    # Flexible column mapping
│   │   └── feature_validator.py  # Feature validation
│   │
│   ├── guardian/                # Guardian agent
│   │   └── guardian_agent.py   # System integrity monitoring
│   │
│   ├── core/                    # Core utilities
│   │   ├── models.py           # Data models
│   │   ├── enums.py            # Enumerations
│   │   └── config.py           # Configuration loader
│   │
│   └── notifications/           # Notification system
│       └── router.py           # Role-based routing
│
├── frontend/                    # React frontend
│   ├── package.json            # Node.js dependencies
│   ├── vite.config.ts          # Vite configuration
│   ├── tailwind.config.js      # TailwindCSS configuration
│   ├── tsconfig.json           # TypeScript configuration
│   │
│   └── src/
│       ├── main.tsx            # Application entry point
│       ├── App.tsx             # Root component
│       │
│       ├── pages/              # Page components
│       │   ├── Portfolio.tsx   # Portfolio overview
│       │   ├── AIInsights.tsx  # AI insights page
│       │   ├── StudyDetails.tsx  # Study details
│       │   ├── SiteView.tsx    # Site view
│       │   ├── PatientView.tsx # Patient view
│       │   ├── GuardianDashboard.tsx  # Guardian dashboard
│       │   └── Analytics.tsx   # Analytics page
│       │
│       ├── components/         # Reusable components
│       │   └── ui/            # UI components
│       │       ├── DQIDisplay.tsx
│       │       ├── EnrollmentDisplay.tsx
│       │       ├── ExportButton.tsx
│       │       └── ErrorBoundary.tsx
│       │
│       ├── hooks/              # Custom React hooks
│       │   ├── useStudyData.ts
│       │   ├── useAgentData.ts
│       │   ├── useGuardianData.ts
│       │   └── useReasoningData.ts
│       │
│       ├── api/                # API client
│       │   ├── client.ts       # Axios client
│       │   ├── data.ts         # Data endpoints
│       │   ├── agents.ts       # Agent endpoints
│       │   ├── guardian.ts     # Guardian endpoints
│       │   ├── reasoning.ts    # AI insights endpoints
│       │   └── export.ts       # Export endpoints
│       │
│       ├── utils/              # Utility functions
│       │   ├── colorContrast.ts
│       │   ├── AIInsightsCache.ts
│       │   └── AIInsightsErrorHandler.ts
│       │
│       └── providers/          # Context providers
│           └── QueryProvider.tsx  # React Query setup
│
├── tests/                       # Test suite
│   ├── unit/                   # Unit tests
│   ├── integration/            # Integration tests
│   ├── property/               # Property-based tests
│   ├── validation/             # Validation tests
│   ├── api/                    # API tests
│   └── guardian/               # Guardian tests
│
├── scripts/                     # Utility scripts
│   ├── update_dashboard_cache.py  # Regenerate cache
│   ├── generate_final_predictions.py  # Generate predictions
│   ├── run_agents_all_studies.py  # Run agents on all studies
│   └── validate_novartis_data.py  # Validate NEST data
│
├── data/                        # Data directory
│   ├── raw/                    # Raw NEST 2.0 files
│   ├── processed/              # Processed data
│   ├── simulated/              # Simulated test data
│   └── snapshots/              # Data snapshots
│
├── logs/                        # Log files
│   ├── c_trust.log            # Application logs
│   ├── error.log              # Error logs
│   └── audit.log              # Audit trail
│
├── exports/                     # Exported reports
│   └── *.csv                   # CSV exports
│
├── predictions/                 # Prediction outputs
│   ├── study_dqi_scores.csv
│   ├── site_risk_scores.csv
│   ├── patient_clean_status.csv
│   ├── agent_signals_summary.csv
│   └── escalation_flags.csv
│
└── docs/                        # Documentation
    ├── API_DOCUMENTATION.md
    ├── DEPLOYMENT_GUIDE.md
    └── TECHNICAL_DOCUMENTATION.md
```

### Key Directories Explained

#### `src/` - Backend Source Code
Contains all Python backend logic organized by functionality:
- **api/**: REST API endpoints and routing
- **agents/**: 7 specialized AI agents
- **intelligence/**: Core AI logic (consensus, DQI, LLM)
- **data/**: Data ingestion and feature extraction
- **guardian/**: System integrity monitoring
- **core/**: Shared utilities and models

#### `frontend/` - React Frontend
Modern React application with TypeScript:
- **pages/**: Top-level page components
- **components/**: Reusable UI components
- **hooks/**: Custom React hooks for data fetching
- **api/**: API client and endpoint wrappers
- **utils/**: Utility functions and helpers

#### `tests/` - Test Suite
Comprehensive testing with 331 tests:
- **unit/**: Component and function tests
- **integration/**: End-to-end workflow tests
- **property/**: Property-based tests (Hypothesis)
- **validation/**: Data validation tests

#### `config/` - Configuration
YAML configuration files for system behavior:
- **system_config.yaml**: File type patterns
- **settings.yaml**: Application settings
- **simulated_profiles.yaml**: Test data profiles

#### `scripts/` - Utility Scripts
Helper scripts for common tasks:
- Cache regeneration
- Prediction generation
- Data validation
- Batch processing


---

## 🛠️ Development

### Setting Up Development Environment

#### Backend Development

1. **Install development dependencies**:
```bash
pip install -r requirements.txt
pip install black flake8 mypy pytest-cov
```

2. **Enable debug mode**:
```env
# In .env
DEBUG=true
LOG_LEVEL=DEBUG
```

3. **Run with auto-reload**:
```bash
python -m uvicorn src.api.main:app --reload --port 8000
```

#### Frontend Development

1. **Install dependencies**:
```bash
cd frontend
npm install
```

2. **Run development server**:
```bash
npm run dev
```

3. **Enable hot module replacement**: Vite automatically reloads on file changes

### Code Style and Formatting

#### Python (Backend)

**Formatter**: Black
```bash
# Format all Python files
black src/ tests/

# Check formatting
black --check src/ tests/
```

**Linter**: Flake8
```bash
# Lint code
flake8 src/ tests/ --max-line-length=100
```

**Type Checker**: MyPy
```bash
# Type check
mypy src/ --ignore-missing-imports
```

#### TypeScript (Frontend)

**Linter**: ESLint
```bash
cd frontend

# Lint code
npm run lint

# Fix auto-fixable issues
npm run lint -- --fix
```

**Formatter**: Prettier (via ESLint)
```bash
# Format code
npm run format
```

### Running Tests

#### Backend Tests

**Run all tests**:
```bash
# From c_trust directory
pytest

# With coverage report
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_dqi_engine_agent_driven.py

# Run specific test
pytest tests/unit/test_dqi_engine_agent_driven.py::test_dqi_calculation
```

**Run property-based tests**:
```bash
# Property tests use Hypothesis
pytest tests/property/

# Increase test cases for thorough testing
pytest tests/property/ --hypothesis-seed=random
```

**Run integration tests**:
```bash
pytest tests/integration/
```

**Test categories**:
- `tests/unit/` - Unit tests (fast, isolated)
- `tests/integration/` - Integration tests (slower, end-to-end)
- `tests/property/` - Property-based tests (Hypothesis)
- `tests/validation/` - Data validation tests
- `tests/api/` - API endpoint tests
- `tests/guardian/` - Guardian agent tests

#### Frontend Tests

```bash
cd frontend

# Run all tests
npm test

# Run with coverage
npm test -- --coverage

# Run in watch mode
npm test -- --watch
```

### Adding New Features

#### Adding a New Agent

1. **Create agent class** in `src/agents/signal_agents/`:
```python
from src.intelligence.base_agent import BaseAgent, AgentSignal
from src.core.enums import AgentType, RiskSignal

class MyNewAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_type=AgentType.MY_NEW_AGENT,
            abstention_threshold=0.5
        )
    
    def analyze(self, features: Dict[str, Any], study_id: str) -> AgentSignal:
        # Implement analysis logic
        pass
```

2. **Register agent** in `src/intelligence/agent_pipeline.py`:
```python
from src.agents.signal_agents.my_new_agent import MyNewAgent

agents = {
    'my_new_agent': MyNewAgent(),
    # ... other agents
}
```

3. **Add tests** in `tests/unit/test_my_new_agent.py`

4. **Update DQI mapping** in `src/intelligence/dqi_engine_agent_driven.py`

#### Adding a New API Endpoint

1. **Create route handler** in `src/api/routes/`:
```python
from fastapi import APIRouter, HTTPException

router = APIRouter()

@router.get("/my-endpoint")
async def my_endpoint():
    return {"message": "Hello"}
```

2. **Register router** in `src/api/main.py`:
```python
from src.api.routes.my_routes import router as my_router

app.include_router(my_router, prefix="/api/v1")
```

3. **Add tests** in `tests/api/test_my_endpoint.py`

#### Adding a New Frontend Page

1. **Create page component** in `frontend/src/pages/`:
```tsx
import React from 'react';

export default function MyNewPage() {
  return (
    <div>
      <h1>My New Page</h1>
    </div>
  );
}
```

2. **Add route** in `frontend/src/App.tsx`:
```tsx
import MyNewPage from './pages/MyNewPage';

<Route path="/my-page" element={<MyNewPage />} />
```

3. **Add navigation link** in navigation component

### Debugging

#### Backend Debugging

**Using Python Debugger**:
```python
# Add breakpoint in code
import pdb; pdb.set_trace()

# Or use breakpoint() (Python 3.7+)
breakpoint()
```

**VS Code Launch Configuration** (`.vscode/launch.json`):
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "src.api.main:app",
        "--reload",
        "--port",
        "8000"
      ],
      "jinja": true
    }
  ]
}
```

**Check logs**:
```bash
# Tail application logs
tail -f logs/c_trust.log

# Tail error logs
tail -f logs/error.log

# Search logs
grep "ERROR" logs/c_trust.log
```

#### Frontend Debugging

**Browser DevTools**:
- Open Chrome DevTools (F12)
- Check Console for errors
- Use Network tab to inspect API calls
- Use React DevTools extension

**VS Code Debugger**:
```json
{
  "type": "chrome",
  "request": "launch",
  "name": "Launch Chrome",
  "url": "http://localhost:5173",
  "webRoot": "${workspaceFolder}/frontend/src"
}
```

### Performance Profiling

#### Backend Profiling

**Using cProfile**:
```python
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# Your code here

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)
```

**Memory profiling**:
```bash
pip install memory_profiler

# Add @profile decorator to functions
python -m memory_profiler your_script.py
```

#### Frontend Profiling

**React DevTools Profiler**:
1. Install React DevTools extension
2. Open Profiler tab
3. Record interaction
4. Analyze component render times

**Lighthouse**:
```bash
# Run Lighthouse audit
npm install -g lighthouse
lighthouse http://localhost:5173 --view
```

### Contributing Guidelines

1. **Create feature branch**:
```bash
git checkout -b feature/my-new-feature
```

2. **Make changes** following code style guidelines

3. **Write tests** for new functionality

4. **Run test suite**:
```bash
pytest  # Backend
npm test  # Frontend
```

5. **Format code**:
```bash
black src/ tests/  # Backend
npm run lint -- --fix  # Frontend
```

6. **Commit changes**:
```bash
git add .
git commit -m "feat: add my new feature"
```

7. **Push and create pull request**:
```bash
git push origin feature/my-new-feature
```

### Build for Production

#### Backend

```bash
# No build step required for Python
# Ensure all dependencies are in requirements.txt
pip freeze > requirements.txt
```

#### Frontend

```bash
cd frontend

# Build for production
npm run build

# Output in frontend/dist/
# Serve with any static file server
```


---

## 📚 API Documentation

### Interactive API Documentation

Once the backend is running, access interactive API documentation:

- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

### Key Endpoints

#### Health Check
```http
GET /api/v1/health
```
Returns system health status.

#### Studies

```http
GET /api/v1/studies
```
List all studies with DQI scores.

```http
GET /api/v1/studies/{study_id}
```
Get detailed study information.

```http
GET /api/v1/studies/{study_id}/dqi
```
Get DQI calculation details.

#### Agents

```http
GET /api/v1/agents
```
Get status of all agents.

```http
GET /api/v1/agents/{study_id}
```
Get agent signals for specific study.

#### Guardian

```http
GET /api/v1/guardian/status
```
Get Guardian system status.

```http
GET /api/v1/guardian/events
```
Get Guardian event log.

#### AI Insights

```http
GET /api/v1/reasoning/{study_id}
```
Get AI-generated insights for study.

#### Export

```http
POST /api/v1/export/study/{study_id}
```
Export study data as CSV.

For complete API documentation with request/response schemas, see http://localhost:8000/api/docs

---

## 🧪 Testing

### Test Coverage

C-TRUST includes 331 comprehensive tests:

- **Unit Tests**: 180+ tests for individual components
- **Integration Tests**: 50+ tests for end-to-end workflows
- **Property-Based Tests**: 40+ tests using Hypothesis
- **Validation Tests**: 30+ tests for data validation
- **API Tests**: 20+ tests for REST endpoints
- **Guardian Tests**: 11+ tests for system integrity

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test category
pytest tests/unit/
pytest tests/integration/
pytest tests/property/

# Run specific test file
pytest tests/unit/test_dqi_engine_agent_driven.py

# Run with verbose output
pytest -v

# Run with print statements
pytest -s
```

### Test Results

View coverage report:
```bash
# Generate HTML coverage report
pytest --cov=src --cov-report=html

# Open in browser
open htmlcov/index.html  # macOS
start htmlcov/index.html  # Windows
```

### Property-Based Testing

C-TRUST uses Hypothesis for property-based testing to ensure correctness across the input space:

```python
from hypothesis import given, strategies as st

@given(st.integers(min_value=0, max_value=100))
def test_dqi_score_range(score):
    """DQI scores must be between 0 and 100"""
    assert 0 <= score <= 100
```

Run property tests with more examples:
```bash
pytest tests/property/ --hypothesis-seed=random
```

---

## 📄 License & Credits

### License

**Proprietary Software**

Copyright © 2026 C-TRUST Development Team. All rights reserved.

This software is proprietary and confidential. Unauthorized copying, distribution, or use of this software, via any medium, is strictly prohibited.

### Built For

**Novartis NEST 2.0 Hackathon**

C-TRUST was developed as a solution for the Novartis NEST 2.0 Clinical Trial Data Quality Challenge.

### Technology Credits

C-TRUST is built with open-source technologies:

#### Backend
- **FastAPI** - Modern Python web framework
- **Pandas** - Data manipulation library
- **Pydantic** - Data validation
- **Uvicorn** - ASGI server
- **Hypothesis** - Property-based testing
- **Pytest** - Testing framework

#### Frontend
- **React** - UI library
- **TypeScript** - Type-safe JavaScript
- **Vite** - Build tool
- **TailwindCSS** - Utility-first CSS
- **React Query** - Data fetching & caching
- **Recharts** - Charting library
- **Axios** - HTTP client
- **Lucide React** - Icon library

#### AI/ML
- **Groq** - LLM API provider
- **LangChain** - LLM framework

### Acknowledgments

Special thanks to:
- **Novartis** for providing the NEST 2.0 dataset and problem statement
- **Open-source community** for the amazing tools and libraries
- **Clinical trial professionals** for domain expertise and feedback

### Contact

For questions, issues, or feedback:
- **Documentation**: See `docs/` directory
- **Technical Issues**: Check `logs/` for error details
- **API Questions**: See http://localhost:8000/api/docs

---

## 🎯 Quick Reference

### Essential Commands

```bash
# Backend
cd c_trust
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # macOS/Linux
python -m uvicorn src.api.main:app --reload --port 8000

# Frontend
cd frontend
npm run dev

# Regenerate cache
python scripts/update_dashboard_cache.py

# Run tests
pytest
npm test

# Check health
curl http://localhost:8000/api/v1/health
```

### Essential URLs

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/api/docs
- **Health Check**: http://localhost:8000/api/v1/health

### Essential Files

- **Backend Config**: `c_trust/.env`
- **Frontend Config**: `c_trust/frontend/.env`
- **Data Cache**: `c_trust/data_cache.json`
- **Logs**: `c_trust/logs/c_trust.log`
- **System Config**: `c_trust/config/system_config.yaml`

---

## 🚀 Next Steps

After getting C-TRUST running:

1. **Explore the Dashboard**: Navigate through all pages to understand the UI
2. **Review API Documentation**: Visit http://localhost:8000/api/docs
3. **Check Logs**: Review `logs/c_trust.log` to understand system behavior
4. **Read Technical Documentation**: See `TECHNICAL_DOCUMENTATION.md` for deep dive
5. **Run Tests**: Execute `pytest` to verify system integrity
6. **Customize Configuration**: Adjust thresholds in `.env` to match your needs
7. **Generate Predictions**: Run `python scripts/generate_final_predictions.py`

---

**C-TRUST: Transforming Clinical Trial Operations Through Intelligent Automation**

*Built with ❤️ for the pharmaceutical industry*

