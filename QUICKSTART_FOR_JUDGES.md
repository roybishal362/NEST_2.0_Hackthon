# C-TRUST Quick Start for Judges

## 🎯 5-Minute Setup

### Prerequisites
- Python 3.9+
- Node.js 16+
- Groq API key (free at https://console.groq.com/keys)

### Setup Commands

```bash
# 1. Clone and navigate
git clone <repository-url>
cd c-trust/c_trust

# 2. Backend setup
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt

# 3. Configure
copy .env.example .env
# Edit .env and add: GROQ_API_KEY=your_key_here

# 4. Start backend
python main.py

# 5. Frontend setup (new terminal)
cd frontend
npm install
npm run dev
```

### Access
- **Frontend**: http://localhost:5173
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## 📚 Key Documents

### For Quick Understanding
1. **[SUBMISSION_GUIDE.md](SUBMISSION_GUIDE.md)** - Quick reference (5 min read)
2. **[c_trust/SIMPLE_EXPLANATION.md](c_trust/SIMPLE_EXPLANATION.md)** - High-level overview (10 min read)
3. **[c_trust/VIDEO_SCRIPT.md](c_trust/VIDEO_SCRIPT.md)** - Presentation script (5 min read)

### For Technical Review
1. **[c_trust/TECHNICAL_DOCUMENTATION.md](c_trust/TECHNICAL_DOCUMENTATION.md)** - Architecture (30 min read)
2. **[submission/C_TRUST_Technical_Whitepaper.md](submission/C_TRUST_Technical_Whitepaper.md)** - In-depth analysis (20 min read)

### For Submission Materials
1. **[submission/5_SLIDE_PPT_ABSTRACT.md](submission/5_SLIDE_PPT_ABSTRACT.md)** - 5-slide presentation
2. **[submission/FINAL_SUBMISSION_SLIDES.md](submission/FINAL_SUBMISSION_SLIDES.md)** - Complete slides

## 🎬 Demo Flow (10 Minutes)

### 1. Portfolio View (2 min)
- Navigate to http://localhost:5173
- See all 23 studies
- View DQI scores and risk levels
- Check enrollment progress

### 2. Study Dashboard (2 min)
- Click on any study (e.g., "STUDY01")
- View detailed metrics
- See site performance
- Check data quality indicators

### 3. AI Insights (3 min)
- Click "AI Insights" in navigation
- View 7 specialized agent analyses:
  - Enrollment Agent
  - Protocol Deviation Agent
  - Data Quality Agent
  - Temporal Drift Agent
  - Stability Agent
  - Coding Agent
  - EDC Quality Agent
- See Guardian Agent consensus
- Review risk assessments

### 4. Site Detail (2 min)
- Click on any site
- View site-specific metrics
- See patient list
- Check data completeness

### 5. Patient Dashboard (1 min)
- Click on any patient
- View patient timeline
- See visit history
- Check data quality

## 🏆 Key Differentiators

### 1. Multi-Agent Architecture
- 7 specialized AI agents
- Guardian meta-agent for consensus
- Explainable AI insights

### 2. Novel DQI Calculation
- Consensus-based scoring
- Agent-driven methodology
- Real-time updates

### 3. Production-Ready
- 331 automated tests
- Comprehensive documentation
- Deployment guides

### 4. Comprehensive Testing
- Unit tests
- Integration tests
- Property-based tests

## 📊 Quick Stats

- **Studies**: 23
- **Sites**: 100+
- **Patients**: 1000+
- **Tests**: 331
- **Response Time**: <2s
- **Code Coverage**: High

## 🧪 Run Tests

```bash
cd c_trust
pytest
```

Expected output:
```
331 passed in X.XXs
```

## 📖 Documentation Structure

```
Root Documentation (Quick Start)
├── README.md                    # Project overview
├── SUBMISSION_GUIDE.md          # Quick reference
└── SETUP.md                     # Setup instructions

C-TRUST Documentation (Detailed)
├── SIMPLE_EXPLANATION.md        # High-level (1775 lines)
├── TECHNICAL_DOCUMENTATION.md   # Technical (2592 lines)
└── VIDEO_SCRIPT.md              # Presentation

Submission Materials (Hackathon)
├── 5_SLIDE_PPT_ABSTRACT.md      # 5-slide PPT
├── FINAL_SUBMISSION_SLIDES.md   # Complete slides
└── C_TRUST_Technical_Whitepaper.md  # Whitepaper
```

## 💡 Key Features to Highlight

### Real-Time Monitoring
- Live DQI calculation
- Instant risk assessment
- Automated alerts

### Explainable AI
- Transparent agent reasoning
- Clear risk factors
- Actionable insights

### Comprehensive Coverage
- Portfolio-level overview
- Study-level details
- Site-level metrics
- Patient-level monitoring

### Production Quality
- Robust error handling
- Comprehensive testing
- Full documentation
- Deployment ready

## 🎯 Evaluation Criteria

### Innovation (30%)
- Novel multi-agent architecture
- Consensus-based DQI calculation
- Real-time risk assessment

### Technical Excellence (30%)
- Clean, modular code
- 331 automated tests
- Type-safe implementation
- Comprehensive error handling

### Usability (20%)
- Intuitive dashboard
- Clear visualizations
- Responsive design
- Easy navigation

### Documentation (20%)
- Comprehensive docs (10,000+ lines)
- Clear setup instructions
- Technical whitepaper
- Video script

## 🚀 If You Have Limited Time

### 5 Minutes
1. Read [SUBMISSION_GUIDE.md](SUBMISSION_GUIDE.md)
2. View screenshots in `images/`
3. Check [submission/5_SLIDE_PPT_ABSTRACT.md](submission/5_SLIDE_PPT_ABSTRACT.md)

### 15 Minutes
1. Read [c_trust/SIMPLE_EXPLANATION.md](c_trust/SIMPLE_EXPLANATION.md)
2. Read [c_trust/VIDEO_SCRIPT.md](c_trust/VIDEO_SCRIPT.md)
3. Browse code structure

### 30 Minutes
1. Follow setup instructions above
2. Run the application
3. Explore the dashboard
4. Review key documentation

### 1 Hour
1. Complete setup
2. Full demo walkthrough
3. Read technical documentation
4. Review code and tests

## 📞 Support

### Documentation
- **Quick Start**: This file
- **Setup**: [SETUP.md](SETUP.md)
- **Technical**: [c_trust/TECHNICAL_DOCUMENTATION.md](c_trust/TECHNICAL_DOCUMENTATION.md)

### API Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Code
- **Source**: `c_trust/src/`
- **Tests**: `c_trust/tests/`
- **Frontend**: `c_trust/frontend/`

## ✅ Verification

Before evaluating, verify setup:

```bash
# Backend health check
curl http://localhost:8000/health

# Frontend accessible
# Open http://localhost:5173 in browser

# Tests pass
cd c_trust
pytest
```

All should return success.

## 🎉 Ready to Evaluate!

The C-TRUST system is fully functional and ready for evaluation. All features are working, documentation is complete, and the system can be set up in under 5 minutes.

**Thank you for evaluating C-TRUST!**

---

**Need help?** Check [SETUP.md](SETUP.md) for detailed instructions or [SUBMISSION_GUIDE.md](SUBMISSION_GUIDE.md) for quick reference.
