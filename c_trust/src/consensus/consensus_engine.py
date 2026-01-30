"""
C-TRUST Consensus Engine
========================
Weighted voting and decision-making system that combines agent signals
into trusted, actionable insights.

Key Features:
- Weighted voting based on agent importance (Safety has highest weight)
- Confidence scoring based on agent agreement
- Risk level classification with configurable thresholds
- Support for agent abstention handling

**Validates: Requirements 2.4**

Design Principles:
1. Safety agent has highest weight (3.0x) due to critical nature
2. Stability agent has negative weight (-1.5x) to counter alert fatigue
3. Confidence increases when multiple agents agree
4. Abstained agents are excluded from voting
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import math

from src.intelligence.base_agent import AgentSignal, AgentType, RiskSignal
from src.core import get_logger

logger = get_logger(__name__)


class ConsensusRiskLevel(str, Enum):
    """Risk levels for consensus decisions"""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"


@dataclass
class ConsensusResult:
    """
    Result of consensus voting across all agents.
    
    Attributes:
        entity_id: Identifier for the entity being assessed
        risk_level: Final consensus risk level
        risk_score: Numerical risk score (0-100)
        confidence: Confidence in the consensus (0-1)
        contributing_agents: List of agents that contributed (non-abstained)
        abstained_agents: List of agents that abstained
        agent_signals: Original signals from all agents
        weighted_scores: Individual weighted scores per agent
        agreement_ratio: Ratio of agents agreeing on risk level
        timestamp: When consensus was calculated
    """
    entity_id: str
    risk_level: ConsensusRiskLevel
    risk_score: float
    confidence: float
    contributing_agents: List[str]
    abstained_agents: List[str]
    agent_signals: List[AgentSignal]
    weighted_scores: Dict[str, float] = field(default_factory=dict)
    agreement_ratio: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "entity_id": self.entity_id,
            "risk_level": self.risk_level.value,
            "risk_score": self.risk_score,
            "confidence": self.confidence,
            "contributing_agents": self.contributing_agents,
            "abstained_agents": self.abstained_agents,
            "weighted_scores": self.weighted_scores,
            "agreement_ratio": self.agreement_ratio,
            "timestamp": self.timestamp.isoformat(),
        }


class ConsensusEngine:
    """
    Weighted voting consensus engine for multi-agent decisions.
    
    Combines signals from multiple specialized agents using weighted voting
    to produce a single, trusted risk assessment.
    
    Weight Configuration (from design):
    - Safety Agent: 3.0x (highest priority - patient safety)
    - Data Completeness: 1.5x
    - Query Quality: 1.5x
    - Coding Readiness: 1.2x
    - Temporal Drift: 1.2x
    - Cross Evidence: 1.0x
    - Stability Agent: -1.5x (negative - counters alert fatigue)
    """
    
    # Default agent weights from design document
    DEFAULT_WEIGHTS: Dict[str, float] = {
        AgentType.SAFETY.value: 3.0,
        AgentType.COMPLETENESS.value: 1.5,
        AgentType.QUERY_QUALITY.value: 1.5,
        AgentType.CODING.value: 1.2,
        AgentType.TIMELINE.value: 1.2,
        AgentType.COMPLIANCE.value: 1.0,
        AgentType.OPERATIONS.value: 1.0,
    }
    
    # Risk signal to numerical score mapping
    RISK_SCORES: Dict[RiskSignal, float] = {
        RiskSignal.CRITICAL: 100.0,
        RiskSignal.HIGH: 75.0,
        RiskSignal.MEDIUM: 50.0,
        RiskSignal.LOW: 25.0,
        RiskSignal.UNKNOWN: 0.0,
    }
    
    # Risk level thresholds
    RISK_THRESHOLDS: Dict[str, float] = {
        "critical": 85.0,
        "high": 65.0,
        "medium": 40.0,
    }
    
    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        risk_thresholds: Optional[Dict[str, float]] = None
    ):
        """
        Initialize consensus engine.
        
        Args:
            weights: Custom agent weights (uses defaults if not provided)
            risk_thresholds: Custom risk thresholds (uses defaults if not provided)
        """
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()
        self.risk_thresholds = risk_thresholds or self.RISK_THRESHOLDS.copy()
        logger.info(f"ConsensusEngine initialized with {len(self.weights)} agent weights")
    
    def calculate_consensus(
        self,
        signals: List[AgentSignal],
        entity_id: str
    ) -> ConsensusResult:
        """
        Calculate weighted consensus from agent signals.
        
        Args:
            signals: List of AgentSignal from all agents
            entity_id: Identifier for the entity being assessed
        
        Returns:
            ConsensusResult with final risk assessment
        """
        logger.debug(f"Calculating consensus for {entity_id} with {len(signals)} signals")
        
        # Separate abstained and contributing signals
        contributing_signals = [s for s in signals if not s.abstained]
        abstained_signals = [s for s in signals if s.abstained]
        
        contributing_agents = [s.agent_type.value for s in contributing_signals]
        abstained_agents = [s.agent_type.value for s in abstained_signals]
        
        # Handle case where all agents abstained
        if not contributing_signals:
            logger.warning(f"All agents abstained for {entity_id}")
            return ConsensusResult(
                entity_id=entity_id,
                risk_level=ConsensusRiskLevel.UNKNOWN,
                risk_score=0.0,
                confidence=0.0,
                contributing_agents=[],
                abstained_agents=abstained_agents,
                agent_signals=signals,
                weighted_scores={},
                agreement_ratio=0.0,
            )
        
        # Calculate weighted scores
        weighted_scores = self._calculate_weighted_scores(contributing_signals)
        
        # Calculate final risk score
        risk_score = self._calculate_risk_score(weighted_scores, contributing_signals)
        
        # Determine risk level from score
        risk_level = self._classify_risk_level(risk_score)
        
        # Calculate confidence based on agent agreement
        confidence = self._calculate_confidence(contributing_signals, risk_level)
        
        # Calculate agreement ratio
        agreement_ratio = self._calculate_agreement_ratio(contributing_signals)
        
        logger.info(
            f"Consensus for {entity_id}: risk={risk_level.value}, "
            f"score={risk_score:.1f}, confidence={confidence:.2f}, "
            f"contributors={len(contributing_agents)}, abstained={len(abstained_agents)}"
        )
        
        return ConsensusResult(
            entity_id=entity_id,
            risk_level=risk_level,
            risk_score=risk_score,
            confidence=confidence,
            contributing_agents=contributing_agents,
            abstained_agents=abstained_agents,
            agent_signals=signals,
            weighted_scores=weighted_scores,
            agreement_ratio=agreement_ratio,
        )
    
    def _calculate_weighted_scores(
        self,
        signals: List[AgentSignal]
    ) -> Dict[str, float]:
        """
        Calculate weighted score for each agent signal.
        
        Args:
            signals: List of non-abstained agent signals
        
        Returns:
            Dictionary mapping agent type to weighted score
        """
        weighted_scores = {}
        
        for signal in signals:
            agent_key = signal.agent_type.value
            weight = self.weights.get(agent_key, 1.0)
            base_score = self.RISK_SCORES.get(signal.risk_level, 0.0)
            
            # Apply weight and confidence adjustment
            weighted_score = base_score * weight * signal.confidence
            weighted_scores[agent_key] = weighted_score
            
            logger.debug(
                f"Agent {agent_key}: base={base_score}, weight={weight}, "
                f"confidence={signal.confidence:.2f}, weighted={weighted_score:.2f}"
            )
        
        return weighted_scores
    
    def _calculate_risk_score(
        self,
        weighted_scores: Dict[str, float],
        signals: List[AgentSignal]
    ) -> float:
        """
        Calculate final risk score from weighted scores.
        
        Uses weighted average normalized by total weight.
        
        Args:
            weighted_scores: Dictionary of weighted scores per agent
            signals: Original signals for weight lookup
        
        Returns:
            Final risk score (0-100)
        """
        if not weighted_scores:
            return 0.0
        
        # Calculate total weight (absolute values for normalization)
        total_weight = sum(
            abs(self.weights.get(s.agent_type.value, 1.0)) * s.confidence
            for s in signals
        )
        
        if total_weight == 0:
            return 0.0
        
        # Sum of weighted scores
        total_score = sum(weighted_scores.values())
        
        # Normalize by total weight
        normalized_score = total_score / total_weight
        
        # Clamp to valid range
        return max(0.0, min(100.0, normalized_score))
    
    def _classify_risk_level(self, risk_score: float) -> ConsensusRiskLevel:
        """
        Classify risk score into risk level.
        
        Args:
            risk_score: Numerical risk score (0-100)
        
        Returns:
            ConsensusRiskLevel classification
        """
        if risk_score >= self.risk_thresholds["critical"]:
            return ConsensusRiskLevel.CRITICAL
        elif risk_score >= self.risk_thresholds["high"]:
            return ConsensusRiskLevel.HIGH
        elif risk_score >= self.risk_thresholds["medium"]:
            return ConsensusRiskLevel.MEDIUM
        else:
            return ConsensusRiskLevel.LOW
    
    def _calculate_confidence(
        self,
        signals: List[AgentSignal],
        consensus_risk: ConsensusRiskLevel
    ) -> float:
        """
        Calculate confidence in consensus based on agent agreement.
        
        Confidence factors:
        1. Number of contributing agents
        2. Agreement on risk level
        3. Individual agent confidences
        
        Args:
            signals: Contributing agent signals
            consensus_risk: Final consensus risk level
        
        Returns:
            Confidence score (0-1)
        """
        if not signals:
            return 0.0
        
        # Factor 1: Coverage - more agents = higher confidence
        coverage_factor = min(len(signals) / 5.0, 1.0)  # Max at 5 agents
        
        # Factor 2: Agreement - how many agents agree with consensus
        consensus_risk_signal = self._risk_level_to_signal(consensus_risk)
        agreeing_agents = sum(
            1 for s in signals
            if self._signals_agree(s.risk_level, consensus_risk_signal)
        )
        agreement_factor = agreeing_agents / len(signals)
        
        # Factor 3: Average agent confidence
        avg_confidence = sum(s.confidence for s in signals) / len(signals)
        
        # Combine factors with weights
        confidence = (
            coverage_factor * 0.3 +
            agreement_factor * 0.4 +
            avg_confidence * 0.3
        )
        
        return min(confidence, 1.0)
    
    def _calculate_agreement_ratio(self, signals: List[AgentSignal]) -> float:
        """
        Calculate ratio of agents agreeing on risk level.
        
        Args:
            signals: Contributing agent signals
        
        Returns:
            Agreement ratio (0-1)
        """
        if len(signals) <= 1:
            return 1.0
        
        # Count risk levels
        risk_counts: Dict[RiskSignal, int] = {}
        for signal in signals:
            risk_counts[signal.risk_level] = risk_counts.get(signal.risk_level, 0) + 1
        
        # Find most common risk level
        max_count = max(risk_counts.values())
        
        return max_count / len(signals)
    
    def _risk_level_to_signal(self, risk_level: ConsensusRiskLevel) -> RiskSignal:
        """Convert ConsensusRiskLevel to RiskSignal for comparison"""
        mapping = {
            ConsensusRiskLevel.CRITICAL: RiskSignal.CRITICAL,
            ConsensusRiskLevel.HIGH: RiskSignal.HIGH,
            ConsensusRiskLevel.MEDIUM: RiskSignal.MEDIUM,
            ConsensusRiskLevel.LOW: RiskSignal.LOW,
            ConsensusRiskLevel.UNKNOWN: RiskSignal.UNKNOWN,
        }
        return mapping.get(risk_level, RiskSignal.UNKNOWN)
    
    def _signals_agree(self, signal1: RiskSignal, signal2: RiskSignal) -> bool:
        """
        Check if two risk signals agree (same or adjacent levels).
        
        Args:
            signal1: First risk signal
            signal2: Second risk signal
        
        Returns:
            True if signals agree
        """
        # Exact match
        if signal1 == signal2:
            return True
        
        # Adjacent levels also count as agreement
        level_order = [RiskSignal.LOW, RiskSignal.MEDIUM, RiskSignal.HIGH, RiskSignal.CRITICAL]
        
        try:
            idx1 = level_order.index(signal1)
            idx2 = level_order.index(signal2)
            return abs(idx1 - idx2) <= 1
        except ValueError:
            return False
    
    def get_weight(self, agent_type: AgentType) -> float:
        """Get weight for an agent type"""
        return self.weights.get(agent_type.value, 1.0)
    
    def set_weight(self, agent_type: AgentType, weight: float) -> None:
        """Set weight for an agent type"""
        self.weights[agent_type.value] = weight
        logger.info(f"Updated weight for {agent_type.value}: {weight}")
    
    def set_risk_threshold(self, level: str, threshold: float) -> None:
        """Set risk threshold for a level"""
        if level in self.risk_thresholds:
            self.risk_thresholds[level] = threshold
            logger.info(f"Updated risk threshold for {level}: {threshold}")


__all__ = [
    "ConsensusEngine",
    "ConsensusResult",
    "ConsensusRiskLevel",
]
