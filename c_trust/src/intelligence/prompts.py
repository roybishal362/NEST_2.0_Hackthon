"""
LLM Prompt Templates for C-TRUST
================================
Structured prompts for Groq API calls.

Prompt Design Principles:
- Clinical trial domain context
- Structured output formatting
- Evidence-based reasoning
- Actionable recommendations
"""

# ========================================
# AGENT EXPLANATION PROMPT
# ========================================

AGENT_EXPLANATION_PROMPT = """
You are explaining a clinical trial monitoring AI's analysis to a study manager.

Agent Type: {agent_type}
Risk Level: {risk_level}
Confidence: {confidence:.1%}

Evidence:
{evidence}

Recommended Actions:
{recommendations}

Provide a clear, 2-3 sentence explanation of:
1. What the analysis found
2. Why this matters for the trial
3. What action should be taken

Keep the language professional but accessible. Focus on practical implications.
"""

# ========================================
# RECOMMENDATION PROMPT
# ========================================

RECOMMENDATION_PROMPT = """
You are a clinical trial operations expert providing prioritized recommendations.

Multiple AI agents have analyzed the study data:
{signal_summary}

Study Context:
{study_context}

Based on this analysis, provide 3-5 actionable recommendations in order of priority.
Format each as a numbered item starting with an action verb.
Consider regulatory timelines, patient safety, and data integrity.
"""

# ========================================
# STUDY SUMMARY PROMPT
# ========================================

STUDY_SUMMARY_PROMPT = """
Provide a concise executive summary of this clinical trial's current status.

Study ID: {study_id}
Data Quality Index (DQI): {dqi_score:.1f}%
Overall Risk Level: {risk_level}

Dimension Scores:
{dimension_scores}

Active Agent Signals: {agent_count}

Write a 3-4 sentence summary suitable for a study status report.
Include the key metrics, any concerns, and overall trajectory.
"""

# ========================================
# DQI EXPLANATION PROMPT
# ========================================

DQI_EXPLANATION_PROMPT = """
Explain the Data Quality Index (DQI) score to a clinical operations team member.

DQI Score: {dqi_score:.1f}%
DQI Band: {dqi_band}

Component Breakdown:
- Safety: {safety_score:.1f}% (weight: 35%)
- Compliance: {compliance_score:.1f}% (weight: 25%)
- Completeness: {completeness_score:.1f}% (weight: 20%)
- Operations: {operations_score:.1f}% (weight: 15%)

Explain:
1. What the DQI score means for trial readiness
2. Which component needs the most attention
3. What the trend suggests for database lock timeline
"""

# ========================================
# RISK ESCALATION PROMPT
# ========================================

RISK_ESCALATION_PROMPT = """
Generate an escalation summary for a critical risk finding.

Entity: {entity_type} {entity_id}
Risk Level: CRITICAL
Trigger: {trigger_description}

Agent Evidence:
{evidence}

Provide:
1. A brief (1 sentence) summary of the critical issue
2. Immediate actions required (bullet points)
3. Recommended escalation path
4. SLA expectation (e.g., "Resolve within 24 hours")
"""

# ========================================
# GUARDIAN ALERT PROMPT
# ========================================

GUARDIAN_ALERT_PROMPT = """
The Guardian System Integrity Agent has detected an anomaly.

Event Type: {event_type}
Severity: {severity}
Entity: {entity_id}

What was expected: {expected_behavior}
What actually occurred: {actual_behavior}

Provide a clear explanation of:
1. What this anomaly means
2. Potential causes
3. Recommended investigation steps

Keep the tone informative, not alarmist.
"""


__all__ = [
    "AGENT_EXPLANATION_PROMPT",
    "RECOMMENDATION_PROMPT",
    "STUDY_SUMMARY_PROMPT",
    "DQI_EXPLANATION_PROMPT",
    "RISK_ESCALATION_PROMPT",
    "GUARDIAN_ALERT_PROMPT",
]
