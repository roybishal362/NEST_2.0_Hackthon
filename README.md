# C-TRUST

## 🎯 Overview

C-TRUST is an AI-powered clinical trial monitoring system that provides real-time risk assessment and data quality insights for clinical trials. Built for the Novartis NEST 2.0 Hackathon, it addresses critical challenges in clinical trial oversight through intelligent agent-based analysis.

## 🏆 Key Features

- **7 Specialized AI Agents**: Analyze different aspects of trial data (enrollment, protocol deviations, data quality, temporal drift, stability, coding, and EDC quality)
- **Groq-Powered AI**: Ultra-fast LLM inference using Llama 3.3 70B via Groq API for real-time insights
- **Guardian Agent**: Meta-agent that synthesizes insights from all agents
- **Real-time DQI Scoring**: Data Quality Index calculation based on agent consensus
- **Interactive Dashboard**: React-based frontend for portfolio, study, site, and patient-level views
- **Export Capabilities**: Generate comprehensive reports for stakeholders

## 📁 Project Structure

```
c_trust/
├── src/                    # Core application code
│   ├── agents/            # 7 specialized AI agents
│   ├── data/              # Data ingestion and processing
│   ├── intelligence/      # LLM client and DQI engine
│   └── api/               # FastAPI backend
├── frontend/              # React/TypeScript dashboard
├── tests/                 # Comprehensive test suite (331 tests)
├── scripts/               # Utility scripts
├── config/                # Configuration files
└── docs/                  # Documentation

submission/                # Submission materials
├── 5_SLIDE_PPT_ABSTRACT.md
├── C_TRUST_Technical_Whitepaper.md
└── FINAL_SUBMISSION_SLIDES.md

norvatas/                  # NEST 2.0 dataset
└── Data for problem Statement 1/
```

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Node.js 16+
- **Groq API key** (free at https://console.groq.com/keys) - **REQUIRED**

### Why Groq?

C-TRUST uses Groq for ultra-fast LLM inference:
- ⚡ **Sub-second response times** for real-time analysis
- 🆓 **Free API access** with generous rate limits
- 🧠 **Llama 3.3 70B** model for high-quality insights
- 🚀 **No credit card required** to get started

### Backend Setup

```bash
cd c_trust

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env and add your GROQ_API_KEY

# Run the backend
python main.py
```

### Frontend Setup

```bash
cd c_trust/frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### Access the Application

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## 📊 System Architecture

C-TRUST uses a multi-agent architecture:

1. **Data Ingestion Layer**: Processes NEST 2.0 Excel files
2. **Feature Extraction**: Extracts 50+ features from trial data
3. **Agent Analysis**: 7 specialized agents analyze different aspects
4. **Guardian Synthesis**: Meta-agent creates consensus view
5. **DQI Calculation**: Computes Data Quality Index from agent insights
6. **Visualization**: Interactive dashboard for stakeholders

## 🧪 Testing

```bash
# Run all tests
cd c_trust
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test suite
pytest tests/unit/
pytest tests/integration/
pytest tests/property/
```

## 📖 Documentation

- **[Simple Explanation](c_trust/SIMPLE_EXPLANATION.md)**: High-level overview for non-technical stakeholders
- **[Technical Documentation](c_trust/TECHNICAL_DOCUMENTATION.md)**: Detailed technical architecture
- **[Video Script](c_trust/VIDEO_SCRIPT.md)**: Presentation script
- **[Integration Guide](C_TRUST_COMPLETE_INTEGRATION_GUIDE.md)**: Setup and integration instructions

## 🎓 Key Technologies

- **Backend**: Python, FastAPI, Pandas
- **AI/LLM**: Groq API (Llama 3.3 70B), LangChain, Multi-agent architecture
- **Frontend**: React, TypeScript, TailwindCSS, Recharts
- **Testing**: Pytest, Hypothesis (property-based testing)
- **Data Processing**: Pandas, NumPy, OpenPyXL

## 📈 Performance

- Processes 23 clinical studies
- Analyzes 100+ sites
- Monitors 1000+ patients
- 331 automated tests
- <2s average response time

## 🤝 Contributing

This project was developed for the Novartis NEST 2.0 Hackathon. For questions or collaboration:

- Review the technical documentation
- Check the test suite for examples
- See submission materials for detailed explanations

## 📄 License

Proprietary - Developed for Novartis NEST 2.0 Hackathon

## 🙏 Acknowledgments

- Novartis for the NEST 2.0 dataset and problem statement
- Groq for ultra-fast LLM inference with Llama 3.3 70B
- The clinical trial community for domain expertise

---

**Built with ❤️ for better clinical trial oversight**
