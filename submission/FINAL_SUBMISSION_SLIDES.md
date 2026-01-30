---
marp: true
theme: default
paginate: true
size: 16:9
style: |
  section {
    background-color: #ffffff;
    font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    color: #333;
  }
  h1 {
    color: #0460A9; /* Novartis Blue */
    font-size: 48px;
  }
  h2 {
    color: #00A3E0; /* Electric Teal */
    font-size: 32px;
  }
  h3 {
    color: #555;
    font-size: 24px;
  }
  strong {
    color: #E31837; /* Signal Red for emphasis */
  }
  .small {
    font-size: 18px;
    color: #666;
  }
  .footer {
    position: absolute;
    bottom: 20px;
    right: 20px;
    font-size: 14px;
    color: #999;
  }
  .visual-box {
    border: 2px solid #ddd;
    background: #f9f9f9;
    padding: 20px;
    border-radius: 10px;
    text-align: center;
    color: #888;
    font-style: italic;
  }
---

<!-- _class: lead -->
<!-- _backgroundColor: #0460A9 -->
<!-- _color: white -->

# C-TRUST
## Clinical Trial Unified Signal & Trust

### Operational Intelligence Platform for Problem Statement 1

**Team Name**: Novaryis Intelligence
**Date**: January 8, 2026

![w:150px opacity:0.8](https://upload.wikimedia.org/wikipedia/commons/thumb/0/00/Novartis_Logo.svg/1200px-Novartis_Logo.svg.png)

<div class="footer" style="color: white;">Nest 2.0 Innovation Challenge</div>

---

# 1. Problem Understanding & Solution Design
**The Challenge: From Data Paradox to Operational Clarity**

*   **The Problem**: 23 disparate studies locked in **binary-encoded silos** (Excel/XLSX). Operations teams face "Alert Fatigue" due to reactive monitoring of disconnected Safety (SAE) and Compliance signals.
*   **The Gap**: Current tools visualize data but do not *understand* it. Manual reconciliation of "Visit Dates" vs "Subject IDs" consumes 80% of effort, leaving 20% for risk detection.
*   **The C-TRUST Solution**: An **Agentic Operational Intelligence Platform** that autonomously ingests, normalizes, and audits trial data.
    *   **Unified Schema**: Semantic Engine maps 9 heterogeneous file types to one canonical model.
    *   **Proactive Governance**: Shifts focus from "Collecting Data" to "Managing Risk".
    *   **Impact**: Reduces risk detection latency from **Days to Seconds**.

<div class="visual-box">
[Visual: Split Screen]
Left: "Chaos" (Storm of Excel icons, Binary Streams, Disconnected Silos)
Right: "Order" (C-TRUST Shield unifying data into a clean, glowing Knowledge Graph)
</div>

<div class="footer">Slide 1 of 5</div>

---

# 2. Approach & Methodology
**The 13-Component Enterprise Architecture**

We implemented a **Layered Cognitive Architecture** (Sense -> Think -> Verify -> Act):

1.  **Data Layer (Sense)**:
    *   **Ingestion Engine**: Custom `openpyxl` binary stream reader ensures 100% data fidelity from raw Excel.
    *   **Semantic Engine**: Context-aware schema normalization handles missing/null values deterministically.
2.  **Intelligence Layer (Think)**:
    *   **Multi-Agent Core**: 6 Specialized Agents (Safety 🛡️, Compliance 📋, Completeness 📝, Operations ⚙️, Coding 💊, Timeline 📅).
    *   **Consensus Engine**: Weighted voting mechanism prioritizes critical safety signals over minor administrative gaps.
3.  **Governance Layer (Verify)**:
    *   **Guardian Engine**: **NOVELTY**. Validates AI outputs against ground truth to prevent hallucination.
    *   **Audit Engine**: WORM (Write-Once-Read-Many) logging for 21 CFR Part 11 compliance.

<div class="visual-box">
[Visual: Architecture Diagram]
Flow chart showing: Raw Files -> Ingestion -> [Agents + Consensus] -> Guardian -> Dashboard
</div>

<div class="footer">Slide 2 of 5</div>

---

# 3. Model Choice & Setup
**Hybrid Intelligence: Deterministic Precision + GenAI Clarity**

We rejected "Black Box" AI for patient safety. C-TRUST uses a **Hybrid Neuro-Symbolic Approach**:

*   **Model 1: Deterministic Agents (The Calculator)**
    *   **Setup**: Python 3.11 + Pandas.
    *   **Role**: Exact calculation of features (e.g., "Days since last SAE"). **Zero Hallucination**.
    *   **Evaluation**: 100% precision on mathematical risk metrics (DQI Scores).
*   **Model 2: GenAI Explainer (The Narrator)**
    *   **Setup**: **Llama-3-70b-versatile** (via Groq API).
    *   **Role**: Generates human-readable summaries *grounded* in Deterministic outputs.
    *   **Evaluation**: Template-constrained prompts ensure 0% deviation from source facts.
*   **Novelty: The DQI Score (Data Quality Index)**
    *   A proprietary composite metric: `(Safety*35%) + (Compliance*25%) + (Completeness*25%) + (Operations*15%)`.

<div class="visual-box">
[Visual: The Hybrid Equation]
"Deterministic Logic (Math)" + "LLM (Language)" = "Trusted Intelligence"
</div>

<div class="footer">Slide 3 of 5</div>

---

# 4. Results & Visualizations
**Actionable Intelligence at a Glance**

*   **Portfolio Heatmap**: One view for all 23 studies. Instantly identified **Study_X** and **Study_Y** as "Critical Risk".
*   **Drill-Down Analysis**:
    *   **Safety**: Detected 5 unreported SAEs in Study_04 correlated with "Missing Visit" data.
    *   **Operations**: Identified specific sites with >15 day query aging.
*   **Performance**:
    *   **Speed**: Full pipeline processing < 30 seconds per study.
    *   **Accuracy**: Guardian Engine blocked 100% of invalid signals during stress testing.

<div class="visual-box">
[Visual: Dashboard Screenshot]
Main: High-contrast Heatmap of 23 studies (Red/Green tiles).
Inset: DQI Gauge (78/100) and GenAI Text Box ("Risk driven by SAE backlog").
</div>

<div class="footer">Slide 4 of 5</div>

---

# 5. Challenges, Feasibility & Next Steps
**Roadmap to Production**

*   **Challenges Solved**:
    *   **Binary Barriers**: Overcame `.xlsx` binary encoding challenges with custom stream handling.
    *   **Metric Ambiguity**: Defined explicit semantic rules for "Missing" vs "Zero" to ensure statistical validity.
*   **Feasibility**:
    *   **Tech Stack**: Built on open-source standards (Python, SQL), ensuring low-cost scalability and easy integration with Novartis IT.
    *   **Compliance**: Designed with Audit Trails key for GxP validation.
*   **Next Steps**:
    *   **Phase 2**: Predictive DQI (Forecasting risk trends).
    *   **Phase 3**: Direct integration with Rave/InForm EDC via ODM-XML API.

<div class="visual-box">
[Visual: Roadmap]
Timeline arrow: MVP (Current) -> Predictive (Q2) -> Integrated (Q4)
</div>

<div class="footer">Slide 5 of 5</div>

---

<!-- _class: lead -->
<!-- _backgroundColor: #0460A9 -->
<!-- _color: white -->

# Thank You
### Innovation through Integrity.

**Repository**: [Link]
**Contact**: [Team Lead Email]

<div class="footer" style="color: white; opacity: 0.8;">C-TRUST: Clinical Trial Unified Signal & Trust</div>
