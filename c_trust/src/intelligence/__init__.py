"""
C-TRUST Intelligence Module
===========================

Multi-agent intelligence system for clinical trial monitoring.

Components:
- BaseAgent: Abstract base class for all agents
- AgentRegistry: Central registry for agent management
- AgentOrchestrator: Coordinates multi-agent analysis
- ConsensusEngine: Weighted voting consensus algorithm
- RiskAssessmentEngine: Risk assessment and decision engine
- Signal Agents: Specialized analysis agents
"""

from src.intelligence.base_agent import (
    BaseAgent,
    AgentType,
    RiskSignal,
    FeatureEvidence,
    AgentSignal,
    AgentRegistry,
    AgentOrchestrator,
)

from src.intelligence.consensus import (
    ConsensusEngine,
    RiskAssessmentEngine,
    ConsensusDecision,
    AgentContribution,
    ConsensusRiskLevel,
    RecommendedAction,
)

__all__ = [
    # Base agent framework
    "BaseAgent",
    "AgentType",
    "RiskSignal",
    "FeatureEvidence",
    "AgentSignal",
    "AgentRegistry",
    "AgentOrchestrator",
    # Consensus engine
    "ConsensusEngine",
    "RiskAssessmentEngine",
    "ConsensusDecision",
    "AgentContribution",
    "ConsensusRiskLevel",
    "RecommendedAction",
]
