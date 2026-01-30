# C-TRUST Setup Guide

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.9 or higher**
- **Node.js 16 or higher**
- **npm or yarn**
- **Git**
- **Groq API Key** (free at https://console.groq.com/keys) - **REQUIRED for AI features**

### About Groq API

C-TRUST uses **Groq** as its primary LLM provider for ultra-fast AI inference. Groq provides:
- **Free API access** with generous rate limits
- **Llama 3.3 70B** model for high-quality insights
- **Sub-second response times** for real-time analysis
- **No credit card required** for getting started

Get your free API key at: https://console.groq.com/keys

## Installation Steps

### 1. Clone the Repository

```bash
git clone <https://github.com/roybishal362/NEST_2.0_Hackthon/tree/main>
cd c-trust
```

### 2. Backend Setup

#### Create Virtual Environment

```bash
cd c_trust
python -m venv .venv
```

#### Activate Virtual Environment

**Windows:**
```bash
.venv\Scripts\activate
```

**macOS/Linux:**
```bash
source .venv/bin/activate
```

#### Install Python Dependencies

```bash
pip install -r requirements.txt
```

#### Configure Environment Variables

Create a `.env` file in the `c_trust` directory:

```bash
# Copy the example file
cp .env.example .env
```

Edit `.env` and add your configuration (see `.env.example` for all options):

**Minimum Required Configuration:**

```env
# Groq API Configuration (REQUIRED - get free key at https://console.groq.com/keys)
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Data Configuration
DATA_PATH=../norvatas/Data for problem Statement 1
```

**Important:** The `GROQ_API_KEY` is required for AI-powered features. Without it, the system will run in mock mode with template-based responses.

### 3. Frontend Setup

#### Navigate to Frontend Directory

```bash
cd frontend
```

#### Install Node Dependencies

```bash
npm install
# or
yarn install
```

#### Configure Frontend Environment

Create a `.env` file in the `frontend` directory:

```env
VITE_API_URL=http://localhost:8000
```

### 4. Verify Installation

#### Check Python Dependencies

```bash
cd c_trust
python -c "import fastapi, pandas, groq; print('All dependencies installed successfully')"
```

#### Check Node Dependencies

```bash
cd frontend
npm list react typescript
```

## Running the Application

### Start Backend Server

```bash
cd c_trust
python main.py
```

The backend API will be available at:
- API: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

### Start Frontend Development Server

In a new terminal:

```bash
cd c_trust/frontend
npm run dev
```

The frontend will be available at:
- Frontend: http://localhost:5173

## Running Tests

### Backend Tests

```bash
cd c_trust
pytest
```

Run with coverage:

```bash
pytest --cov=src --cov-report=html
```

### Frontend Tests

```bash
cd c_trust/frontend
npm test
```

## Data Setup

The application requires the NEST 2.0 dataset:

1. Ensure the dataset is in: `norvatas/Data for problem Statement 1/`
2. The dataset should contain Excel files for each study
3. Verify data path in `.env` file

## Troubleshooting

### Common Issues

#### 1. Groq API Key Error

**Error:** `Authentication error` or `API key not found`

**Solution:** 
1. Get a free API key from https://console.groq.com/keys
2. Add it to your `.env` file: `GROQ_API_KEY=your_key_here`
3. Restart the backend server

#### 2. Port Already in Use

**Error:** `Address already in use`

**Solution:** Change the port in `.env` or kill the process using the port

```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# macOS/Linux
lsof -ti:8000 | xargs kill -9
```

#### 3. Module Not Found

**Error:** `ModuleNotFoundError`

**Solution:** Ensure virtual environment is activated and dependencies are installed

```bash
pip install -r requirements.txt
```

#### 4. Frontend Build Errors

**Error:** `Cannot find module`

**Solution:** Delete node_modules and reinstall

```bash
rm -rf node_modules package-lock.json
npm install
```

### Getting Help

1. Check the [Technical Documentation](c_trust/TECHNICAL_DOCUMENTATION.md)
2. Review the [Simple Explanation](c_trust/SIMPLE_EXPLANATION.md)
3. Check API documentation at http://localhost:8000/docs

## Development Workflow

### Making Changes

1. Create a new branch
2. Make your changes
3. Run tests
4. Commit and push

### Code Quality

```bash
# Format Python code
black src/

# Lint Python code
flake8 src/

# Type check
mypy src/

# Format TypeScript code
cd frontend
npm run lint
npm run format
```

## Production Deployment

### Backend

```bash
# Install production dependencies
pip install -r requirements.txt

# Run with gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker src.api.main:app
```

### Frontend

```bash
cd frontend

# Build for production
npm run build

# Serve the build
npm run preview
```

## Environment Variables Reference

### Backend (.env)

| Variable | Description | Default |
|----------|-------------|---------|
| GROQ_API_KEY | Groq API key (free) | Required |
| GROQ_MODEL | Model to use | llama-3.3-70b-versatile |
| API_HOST | API host | 0.0.0.0 |
| API_PORT | API port | 8000 |
| DATA_PATH | Path to NEST data | ../norvatas/Data for problem Statement 1 |

### Frontend (.env)

| Variable | Description | Default |
|----------|-------------|---------|
| VITE_API_URL | Backend API URL | http://localhost:8000 |

## Next Steps

1. Review the [README](README.md) for project overview
2. Read the [Technical Documentation](c_trust/TECHNICAL_DOCUMENTATION.md)
3. Explore the [API Documentation](http://localhost:8000/docs)
4. Check the [Video Script](c_trust/VIDEO_SCRIPT.md) for feature walkthrough

## Support

For issues or questions:
- Check existing documentation
- Review test files for examples
- Consult the submission materials in `submission/`
