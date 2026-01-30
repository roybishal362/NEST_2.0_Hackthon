"""
C-TRUST Agents Module
====================

Multi-agent intelligence system with specialized agents for clinical trial monitoring.

Agent Types:
- Signal Agents: Primary analysis agents (Data Completeness, Safety, Query Quality, etc.)
- Context Agents: Meta-analysis agents (Temporal Drift, Cross Evidence)
- Guardian Agent: System integrity monitoring (separate module)

Signal Agents (MVP):
- DataCompletenessAgent: Missing data detection
- SafetyComplianceAgent: SAE monitoring (highest consensus weight)
- QueryQualityAgent: Query backlog analysis

Usage:
    from src.agents import (
        DataCompletenessAgent,
        SafetyComplianceAgent,
        QueryQualityAgent,
    )
    from src.intelligence import AgentRegistry, AgentOrchestrator
    
    # Setup multi-agent system
    registry = AgentRegistry()
    registry.register(DataCompletenessAgent(), weight=1.0)
    registry.register(SafetyComplianceAgent(), weight=3.0)
    registry.register(QueryQualityAgent(), weight=1.0)
    
    # Run analysis
    orchestrator = AgentOrchestrator(registry)
    signals = orchestrator.run_all_agents(features, study_id)
"""

__version__ = "1.0.0"

from src.agents.signal_agents import (
    DataCompletenessAgent,
    SafetyComplianceAgent,
    QueryQualityAgent,
)

__all__ = [
    "DataCompletenessAgent",
    "SafetyComplianceAgent",
    "QueryQualityAgent",
]
