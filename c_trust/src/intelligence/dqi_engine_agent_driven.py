"""
C-TRUST Agent-Driven DQI Engine
================================
Calculates DQI scores directly from agent risk assessments.

This module implements the agent-driven DQI calculation that replaces
the placeholder DQI calculation. It maps agent signals to DQI dimensions
and applies consensus modifiers to produce final DQI scores.

Key Features:
- Agent-to-dimension mapping
- Consensus modifier application
- Confidence calculation based on agent participation
- Comprehensive logging for auditability

Design Philosophy:
- HIGH risk agents → LOW DQI scores
- LOW risk agents → HIGH DQI scores
- Agent consensus drives DQI calculation
- Transparent and auditable scoring
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import statistics

from src.core import get_logger
from src.intelligence.base_agent import AgentSignal, AgentType, RiskSignal
from src.intelligence.consensus import ConsensusDecision, ConsensusRiskLevel

logger = get_logger(__name__)


# ========================================
# DQI ENUMERATIONS
# ========================================

class DQIDimension(str, Enum):
    """DQI dimensions"""
    SAFETY = "safety"
    COMPLETENESS = "completeness"
    ACCURACY = "accuracy"
    TIMELINESS = "timeliness"
    CONFORMANCE = "conformance"
    CONSISTENCY = "consistency"


class DQIBand(str, Enum):
    """DQI score bands"""
    GREEN = "GREEN"      # 85-100: Ready for submission
    AMBER = "AMBER"      # 65-84: Minor issues
    ORANGE = "ORANGE"    # 40-64: Significant issues
    RED = "RED"          # 0-39: Critical issues


# ========================================
# DQI DATA STRUCTURES
# ========================================

@dataclass
class DimensionScore:
    """
    Score for a single DQI dimension.
    
    Attributes:
        dimension: Dimension name
        score: Dimension score (0-100)
        contributing_agents: List of agent types that contributed
        confidence: Confidence in this dimension score (0-1)
    """
    dimension: DQIDimension
    score: float
    contributing_agents: List[AgentType]
    confidence: float
    
    def __post_init__(self):
        """Validate score and confidence bounds"""
        if not 0 <= self.score <= 100:
            raise ValueError(f"Dimension score must be in [0, 100], got {self.score}")
        if not 0 <= self.confidence <= 1:
            raise ValueError(f"Confidence must be in [0, 1], got {self.confidence}")


@dataclass
class DQIResult:
    """
    Complete DQI calculation result.
    
    Attributes:
        score: Overall DQI score (0-100)
        band: DQI band classification
        confidence: Overall confidence (0-1)
        dimensions: Dimension scores
        consensus_modifier: Adjustment from consensus (-20 to 0)
        agent_driven: Flag indicating this is agent-driven calculation
        study_id: Study identifier
        timestamp: When calculation was performed
    """
    score: float
    band: DQIBand
    confidence: float
    dimensions: Dict[DQIDimension, DimensionScore]
    consensus_modifier: float
    agent_driven: bool = True
    study_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Validate score and confidence bounds"""
        if not 0 <= self.score <= 100:
            raise ValueError(f"DQI score must be in [0, 100], got {self.score}")
        if not 0 <= self.confidence <= 1:
            raise ValueError(f"Confidence must be in [0, 1], got {self.confidence}")
        if not -20 <= self.consensus_modifier <= 0:
            raise ValueError(f"Consensus modifier must be in [-20, 0], got {self.consensus_modifier}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "score": self.score,
            "band": self.band.value,
            "confidence": self.confidence,
            "dimensions": {
                dim.value: {
                    "score": dim_score.score,
                    "contributing_agents": [a.value for a in dim_score.contributing_agents],
                    "confidence": dim_score.confidence
                }
                for dim, dim_score in self.dimensions.items()
            },
            "consensus_modifier": self.consensus_modifier,
            "agent_driven": self.agent_driven,
            "study_id": self.study_id,
            "timestamp": self.timestamp.isoformat()
        }


# ========================================
# AGENT-TO-DIMENSION MAPPING
# ========================================

# Agent-to-dimension mapping as specified in requirements
AGENT_DIMENSION_MAP: Dict[AgentType, DQIDimension] = {
    AgentType.SAFETY: DQIDimension.SAFETY,
    AgentType.COMPLETENESS: DQIDimension.COMPLETENESS,
    AgentType.CODING: DQIDimension.ACCURACY,
    AgentType.QUERY_QUALITY: DQIDimension.TIMELINESS,
    AgentType.TEMPORAL_DRIFT: DQIDimension.TIMELINESS,
    AgentType.OPERATIONS: DQIDimension.CONFORMANCE,
    AgentType.STABILITY: DQIDimension.CONSISTENCY,
}

# Dimension weights (must sum to 1.0)
DIMENSION_WEIGHTS: Dict[DQIDimension, float] = {
    DQIDimension.SAFETY: 0.35,        # 35% - highest priority
    DQIDimension.COMPLETENESS: 0.20,  # 20%
    DQIDimension.ACCURACY: 0.15,      # 15%
    DQIDimension.TIMELINESS: 0.15,    # 15%
    DQIDimension.CONFORMANCE: 0.10,   # 10%
    DQIDimension.CONSISTENCY: 0.05,   # 5%
}


# ========================================
# DQI CALCULATION ENGINE
# ========================================

def risk_signal_to_score(risk_signal: RiskSignal) -> float:
    """
    Convert risk signal to DQI score.
    
    Key principle: HIGH risk → LOW DQI score
    
    Args:
        risk_signal: Agent risk signal
    
    Returns:
        DQI score (0-100)
    """
    mapping = {
        RiskSignal.CRITICAL: 20.0,  # Critical risk → Very low DQI
        RiskSignal.HIGH: 40.0,      # High risk → Low DQI
        RiskSignal.MEDIUM: 70.0,    # Medium risk → Moderate DQI
        RiskSignal.LOW: 90.0,       # Low risk → High DQI
        RiskSignal.UNKNOWN: 50.0,   # Unknown → Neutral DQI
    }
    return mapping.get(risk_signal, 50.0)


def calculate_dimension_score(
    dimension: DQIDimension,
    agent_signals: List[AgentSignal]
) -> Optional[DimensionScore]:
    """
    Calculate score for a single dimension from contributing agents.
    
    Args:
        dimension: Dimension to calculate
        agent_signals: All agent signals (will filter for this dimension)
    
    Returns:
        DimensionScore or None if no agents contribute to this dimension
    """
    # Find agents that contribute to this dimension
    contributing_signals = [
        signal for signal in agent_signals
        if not signal.abstained and AGENT_DIMENSION_MAP.get(signal.agent_type) == dimension
    ]
    
    if not contributing_signals:
        logger.debug(f"No agents contribute to dimension {dimension.value}")
        return None
    
    # Convert risk signals to DQI scores
    scores = []
    confidences = []
    contributing_agents = []
    
    for signal in contributing_signals:
        score = risk_signal_to_score(signal.risk_level)
        scores.append(score)
        confidences.append(signal.confidence)
        contributing_agents.append(signal.agent_type)
        
        logger.debug(
            f"Agent {signal.agent_type.value} → {dimension.value}: "
            f"risk={signal.risk_level.value}, score={score:.1f}, conf={signal.confidence:.2f}"
        )
    
    # Calculate weighted average score (weighted by confidence)
    total_weight = sum(confidences)
    if total_weight == 0:
        dimension_score = statistics.mean(scores)
        dimension_confidence = 0.0
    else:
        dimension_score = sum(s * c for s, c in zip(scores, confidences)) / total_weight
        dimension_confidence = statistics.mean(confidences)
    
    logger.info(
        f"Dimension {dimension.value}: score={dimension_score:.1f}, "
        f"confidence={dimension_confidence:.2f}, agents={len(contributing_signals)}"
    )
    
    return DimensionScore(
        dimension=dimension,
        score=dimension_score,
        contributing_agents=contributing_agents,
        confidence=dimension_confidence
    )


def calculate_consensus_modifier(consensus: ConsensusDecision) -> float:
    """
    Calculate DQI modifier based on consensus result.
    
    When agents disagree significantly (high risk consensus), reduce DQI.
    
    Args:
        consensus: Consensus decision from agents
    
    Returns:
        Modifier value (-20 to 0)
    """
    if consensus.risk_level == ConsensusRiskLevel.CRITICAL:
        # Critical consensus → maximum reduction
        modifier = -20.0
    elif consensus.risk_level == ConsensusRiskLevel.HIGH:
        # High consensus → significant reduction
        modifier = -15.0
    elif consensus.risk_level == ConsensusRiskLevel.MEDIUM:
        # Medium consensus → moderate reduction
        modifier = -10.0
    elif consensus.risk_level == ConsensusRiskLevel.LOW:
        # Low consensus → minimal reduction
        modifier = -5.0
    else:
        # Unknown → no modification
        modifier = 0.0
    
    # Adjust modifier based on confidence
    # Low confidence → less aggressive modification
    modifier = modifier * consensus.confidence
    
    logger.info(
        f"Consensus modifier: risk={consensus.risk_level.value}, "
        f"confidence={consensus.confidence:.2f}, modifier={modifier:.1f}"
    )
    
    return modifier


def calculate_overall_confidence(
    dimension_scores: Dict[DQIDimension, DimensionScore],
    agent_signals: List[AgentSignal],
    consensus: ConsensusDecision
) -> float:
    """
    Calculate overall confidence in DQI score.
    
    Factors:
    - Dimension coverage (how many dimensions have scores)
    - Average dimension confidence
    - Agent participation rate
    - Consensus confidence
    
    Args:
        dimension_scores: Calculated dimension scores
        agent_signals: All agent signals
        consensus: Consensus decision
    
    Returns:
        Overall confidence (0-1)
    """
    # Factor 1: Dimension coverage (how many dimensions have scores)
    total_dimensions = len(DIMENSION_WEIGHTS)
    covered_dimensions = len(dimension_scores)
    coverage_factor = covered_dimensions / total_dimensions
    
    # Factor 2: Average dimension confidence
    if dimension_scores:
        avg_dimension_confidence = statistics.mean(
            ds.confidence for ds in dimension_scores.values()
        )
    else:
        avg_dimension_confidence = 0.0
    
    # Factor 3: Agent participation rate
    total_agents = len(agent_signals)
    active_agents = len([s for s in agent_signals if not s.abstained])
    participation_rate = active_agents / total_agents if total_agents > 0 else 0.0
    
    # Factor 4: Consensus confidence
    consensus_confidence = consensus.confidence
    
    # Weighted combination
    overall_confidence = (
        coverage_factor * 0.25 +
        avg_dimension_confidence * 0.35 +
        participation_rate * 0.25 +
        consensus_confidence * 0.15
    )
    
    logger.info(
        f"Overall confidence: coverage={coverage_factor:.2f}, "
        f"dim_conf={avg_dimension_confidence:.2f}, "
        f"participation={participation_rate:.2f}, "
        f"consensus={consensus_confidence:.2f}, "
        f"overall={overall_confidence:.2f}"
    )
    
    return min(max(overall_confidence, 0.0), 1.0)


def classify_dqi_band(score: float) -> DQIBand:
    """
    Classify DQI score into band.
    
    Args:
        score: DQI score (0-100)
    
    Returns:
        DQI band
    """
    if score >= 85:
        return DQIBand.GREEN
    elif score >= 65:
        return DQIBand.AMBER
    elif score >= 40:
        return DQIBand.ORANGE
    else:
        return DQIBand.RED


def calculate_dqi_from_agents(
    agent_signals: List[AgentSignal],
    consensus: ConsensusDecision,
    study_id: Optional[str] = None
) -> DQIResult:
    """
    Calculate DQI score from agent signals and consensus.
    
    This is the main entry point for agent-driven DQI calculation.
    
    Algorithm:
    1. Map agent signals to dimensions
    2. Calculate dimension scores (weighted by agent confidence)
    3. Calculate weighted average across dimensions
    4. Apply consensus modifier
    5. Calculate overall confidence
    6. Classify into band
    
    Args:
        agent_signals: List of agent signals
        consensus: Consensus decision
        study_id: Optional study identifier
    
    Returns:
        DQIResult with complete calculation
    """
    logger.info(f"Calculating agent-driven DQI for study {study_id}")
    logger.info(
        f"Input: {len(agent_signals)} agent signals, "
        f"{len([s for s in agent_signals if not s.abstained])} active"
    )
    
    # Step 1: Calculate dimension scores
    dimension_scores = {}
    for dimension in DQIDimension:
        dim_score = calculate_dimension_score(dimension, agent_signals)
        if dim_score:
            dimension_scores[dimension] = dim_score
    
    if not dimension_scores:
        logger.warning(f"No dimension scores calculated for study {study_id}")
        # Return minimal DQI result
        return DQIResult(
            score=50.0,
            band=DQIBand.ORANGE,
            confidence=0.0,
            dimensions={},
            consensus_modifier=0.0,
            study_id=study_id
        )
    
    # Step 2: Calculate weighted average across dimensions
    total_weighted_score = 0.0
    total_weight = 0.0
    
    for dimension, dim_score in dimension_scores.items():
        weight = DIMENSION_WEIGHTS.get(dimension, 0.0)
        weighted_score = dim_score.score * weight
        total_weighted_score += weighted_score
        total_weight += weight
        
        logger.debug(
            f"Dimension {dimension.value}: score={dim_score.score:.1f}, "
            f"weight={weight:.2f}, weighted={weighted_score:.1f}"
        )
    
    # Normalize by actual weight (in case some dimensions are missing)
    if total_weight > 0:
        base_score = total_weighted_score / total_weight
    else:
        base_score = 50.0
    
    logger.info(f"Base DQI score (before consensus modifier): {base_score:.1f}")
    
    # Step 3: Apply consensus modifier
    consensus_modifier = calculate_consensus_modifier(consensus)
    final_score = base_score + consensus_modifier
    
    # Ensure score stays in bounds
    final_score = min(max(final_score, 0.0), 100.0)
    
    logger.info(
        f"Final DQI score: {final_score:.1f} "
        f"(base={base_score:.1f}, modifier={consensus_modifier:.1f})"
    )
    
    # Step 4: Calculate overall confidence
    overall_confidence = calculate_overall_confidence(
        dimension_scores, agent_signals, consensus
    )
    
    # Step 5: Classify into band
    band = classify_dqi_band(final_score)
    
    logger.info(
        f"DQI calculation complete for {study_id}: "
        f"score={final_score:.1f}, band={band.value}, confidence={overall_confidence:.2f}"
    )
    
    return DQIResult(
        score=final_score,
        band=band,
        confidence=overall_confidence,
        dimensions=dimension_scores,
        consensus_modifier=consensus_modifier,
        study_id=study_id
    )


# ========================================
# EXPORTS
# ========================================

__all__ = [
    "DQIDimension",
    "DQIBand",
    "DimensionScore",
    "DQIResult",
    "calculate_dqi_from_agents",
    "risk_signal_to_score",
    "calculate_dimension_score",
    "calculate_consensus_modifier",
    "calculate_overall_confidence",
    "classify_dqi_band",
]
