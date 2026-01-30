"""
Signal Agents Module
===================

Primary analysis agents for clinical trial monitoring.
Each agent specializes in a specific aspect of data quality assessment.

Agents:
- DataCompletenessAgent: Missing data detection and completeness scoring
- SafetyComplianceAgent: SAE monitoring and safety compliance (highest weight)
- QueryQualityAgent: Query backlog analysis and resolution tracking
- CodingReadinessAgent: MedDRA and WHODD coding completion monitoring
- StabilityAgent: Enrollment velocity and site performance tracking
- TemporalDriftAgent: Data entry lag patterns and trend analysis
- CrossEvidenceAgent: Multi-source data validation and consistency

Usage:
    from src.agents.signal_agents import (
        DataCompletenessAgent,
        SafetyComplianceAgent,
        QueryQualityAgent,
        CodingReadinessAgent,
        StabilityAgent,
        TemporalDriftAgent,
        CrossEvidenceAgent,
    )
    
    # Create and register all 7 agents
    registry = AgentRegistry()
    registry.register(DataCompletenessAgent(), weight=1.5)
    registry.register(SafetyComplianceAgent(), weight=3.0)  # Highest priority
    registry.register(QueryQualityAgent(), weight=1.5)
    registry.register(CodingReadinessAgent(), weight=1.2)
    registry.register(StabilityAgent(), weight=-1.5)  # Negative evidence
    registry.register(TemporalDriftAgent(), weight=1.2)
    registry.register(CrossEvidenceAgent(), weight=1.5)
"""

from src.agents.signal_agents.completeness_agent import DataCompletenessAgent
from src.agents.signal_agents.safety_agent import SafetyComplianceAgent
from src.agents.signal_agents.query_agent import QueryQualityAgent
from src.agents.signal_agents.coding_agent import CodingReadinessAgent
from src.agents.signal_agents.temporal_drift_agent import TemporalDriftAgent
from src.agents.signal_agents.edc_quality_agent import EDCQualityAgent
from src.agents.signal_agents.stability_agent import StabilityAgent
from src.agents.signal_agents.cross_evidence_agent import CrossEvidenceAgent

__all__ = [
    "DataCompletenessAgent",
    "SafetyComplianceAgent",
    "QueryQualityAgent",
    "CodingReadinessAgent",
    "TemporalDriftAgent",
    "EDCQualityAgent",
    "StabilityAgent",
    "CrossEvidenceAgent",
]

