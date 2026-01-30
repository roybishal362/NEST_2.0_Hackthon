"""
C-TRUST Consensus Engine Module
==============================

Weighted voting and decision-making system that combines agent signals
into trusted, actionable insights.

**Validates: Requirements 2.4**
"""

from src.consensus.consensus_engine import (
    ConsensusEngine,
    ConsensusResult,
    ConsensusRiskLevel,
)
from src.consensus.risk_assessment import (
    RiskAssessmentEngine,
    RiskDecision,
    RecommendedAction,
    ActionPriority,
    ActionType,
)

__version__ = "1.0.0"

__all__ = [
    # Consensus Engine
    "ConsensusEngine",
    "ConsensusResult",
    "ConsensusRiskLevel",
    # Risk Assessment
    "RiskAssessmentEngine",
    "RiskDecision",
    "RecommendedAction",
    "ActionPriority",
    "ActionType",
]