"""
C-TRUST Consensus Engine - Component 3
======================================
Weighted voting consensus algorithm for multi-agent decision making.

Philosophy:
- WEIGHTED VOTING: Safety Agent has highest priority (3.0x)
- CONFIDENCE SCORING: Based on agent agreement and data quality
- RISK ASSESSMENT: Configurable thresholds for regulatory criticality
- TRANSPARENCY: Full audit trail of consensus decisions

Consensus Logic:
- Safety Agent: 3.0x weight (highest priority)
- Compliance Agent: 1.5x weight
- Completeness Agent: 1.0x weight
- Query Quality Agent: 1.0x weight
- Stability Agent: -1.5x weight (negative evidence)

Decision Matrix:
| Risk Level | Confidence | Action                    |
|------------|------------|---------------------------|
| High       | High       | Immediate Escalation      |
| High       | Low        | Human Review Required     |
| Medium     | High       | Prioritize for Action     |
| Medium     | Low        | Monitor Closely           |
| Low        | Any        | Routine Monitoring        |
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import statistics

from src.core import get_logger
from src.intelligence.base_agent import (
    AgentSignal,
    AgentType,
    RiskSignal,
    AgentRegistry,
)

logger = get_logger(__name__)


# ========================================
# CONSENSUS ENUMERATIONS
# ========================================

class ConsensusRiskLevel(str, Enum):
    """Risk levels for consensus decisions"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class RecommendedAction(str, Enum):
    """Recommended actions based on consensus"""
    IMMEDIATE_ESCALATION = "immediate_escalation"
    HUMAN_REVIEW_REQUIRED = "human_review_required"
    PRIORITIZE_FOR_ACTION = "prioritize_for_action"
    MONITOR_CLOSELY = "monitor_closely"
    ROUTINE_MONITORING = "routine_monitoring"


# ========================================
# CONSENSUS DATA STRUCTURES
# ========================================

@dataclass
class AgentContribution:
    """
    Contribution of a single agent to consensus.
    
    Attributes:
        agent_type: Type of agent
        raw_signal: Original risk signal
        weight: Agent weight in consensus
        weighted_score: Score after weight applied
        confidence: Agent's confidence in its signal
    """
    agent_type: AgentType
    raw_signal: RiskSignal
    weight: float
    weighted_score: float
    confidence: float
    abstained: bool = False


@dataclass
class ConsensusDecision:
    """
    Output of consensus engine.
    
    Attributes:
        risk_level: Final assessed risk level
        confidence: Confidence in consensus (0-1)
        risk_score: Numerical risk score (0-100)
        contributing_agents: List of agent contributions
        recommended_action: Suggested action based on risk/confidence
        explanation: Human-readable explanation
        timestamp: When decision was made
    """
    risk_level: ConsensusRiskLevel
    confidence: float
    risk_score: float
    contributing_agents: List[AgentContribution]
    recommended_action: RecommendedAction
    explanation: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Metadata
    total_agents: int = 0
    abstained_agents: int = 0
    study_id: Optional[str] = None
    
    def __post_init__(self):
        """Validate confidence is in [0, 1]"""
        if not 0 <= self.confidence <= 1:
            raise ValueError("Confidence must be between 0 and 1")
        if not 0 <= self.risk_score <= 100:
            raise ValueError("Risk score must be between 0 and 100")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "risk_level": self.risk_level.value,
            "confidence": self.confidence,
            "risk_score": self.risk_score,
            "contributing_agents": [
                {
                    "agent_type": c.agent_type.value,
                    "raw_signal": c.raw_signal.value,
                    "weight": c.weight,
                    "weighted_score": c.weighted_score,
                    "confidence": c.confidence,
                    "abstained": c.abstained,
                }
                for c in self.contributing_agents
            ],
            "recommended_action": self.recommended_action.value,
            "explanation": self.explanation,
            "timestamp": self.timestamp.isoformat(),
            "total_agents": self.total_agents,
            "abstained_agents": self.abstained_agents,
            "study_id": self.study_id,
        }


# ========================================
# CONSENSUS ENGINE
# ========================================

class ConsensusEngine:
    """
    Weighted voting consensus engine for multi-agent decisions.
    
    Implements:
    - Weighted voting with configurable agent weights
    - Confidence scoring based on agent agreement
    - Risk level classification
    - Action recommendations based on risk/confidence matrix
    
    Default Weights (from design):
    - Safety Agent: 3.0x (highest priority)
    - Compliance Agent: 1.5x
    - Completeness Agent: 1.0x
    - Query Quality Agent: 1.0x
    - Stability Agent: -1.5x (negative evidence)
    """
    
    # Default agent weights
    DEFAULT_WEIGHTS: Dict[AgentType, float] = {
        AgentType.SAFETY: 3.0,
        AgentType.COMPLIANCE: 1.5,
        AgentType.COMPLETENESS: 1.0,
        AgentType.QUERY_QUALITY: 1.0,
        AgentType.OPERATIONS: 1.0,
        AgentType.CODING: 1.0,
        AgentType.TIMELINE: 1.0,
    }
    
    # Risk signal to numeric score mapping
    RISK_SCORES: Dict[RiskSignal, float] = {
        RiskSignal.CRITICAL: 100.0,
        RiskSignal.HIGH: 75.0,
        RiskSignal.MEDIUM: 50.0,
        RiskSignal.LOW: 25.0,
        RiskSignal.UNKNOWN: 0.0,  # Abstained agents don't contribute
    }
    
    # Risk thresholds for classification
    RISK_THRESHOLDS: Dict[str, float] = {
        "critical": 85.0,
        "high": 65.0,
        "medium": 40.0,
    }
    
    def __init__(
        self,
        custom_weights: Optional[Dict[AgentType, float]] = None,
        custom_thresholds: Optional[Dict[str, float]] = None,
    ):
        """
        Initialize consensus engine.
        
        Args:
            custom_weights: Override default agent weights
            custom_thresholds: Override default risk thresholds
        """
        self.weights = {**self.DEFAULT_WEIGHTS}
        if custom_weights:
            self.weights.update(custom_weights)
        
        self.thresholds = {**self.RISK_THRESHOLDS}
        if custom_thresholds:
            self.thresholds.update(custom_thresholds)
        
        logger.info("ConsensusEngine initialized with weights: %s", self.weights)
    
    def calculate_consensus(
        self,
        signals: List[AgentSignal],
        study_id: Optional[str] = None,
    ) -> ConsensusDecision:
        """
        Calculate weighted consensus from agent signals with enhanced abstention handling.
        
        This enhanced version:
        1. Separates active signals from abstentions
        2. Requires minimum 3 active agents for consensus
        3. Adjusts confidence based on participation rate
        4. Includes abstention information in explanation
        
        Args:
            signals: List of agent signals
            study_id: Optional study identifier
        
        Returns:
            ConsensusDecision with risk assessment
        """
        if not signals:
            logger.warning("No signals provided for consensus")
            return self._create_unknown_decision(study_id)
        
        # Separate abstained and active signals
        active_signals = [s for s in signals if not s.abstained]
        abstained_signals = [s for s in signals if s.abstained]
        
        # Log abstention information
        if abstained_signals:
            abstained_names = [s.agent_type.value for s in abstained_signals]
            logger.info(
                f"Study {study_id}: {len(abstained_signals)}/{len(signals)} agents abstained: "
                f"{', '.join(abstained_names)}"
            )
        
        # Require minimum 3 active agents for reliable consensus
        if len(active_signals) < 3:
            logger.warning(
                f"Study {study_id}: Only {len(active_signals)} active agents, "
                f"minimum 3 required for consensus"
            )
            return self._create_insufficient_data_decision(
                signals, active_signals, abstained_signals, study_id
            )
        
        # Calculate weighted risk score
        contributions = []
        total_weighted_score = 0.0
        total_weight = 0.0
        
        for signal in active_signals:
            weight = self.weights.get(signal.agent_type, 1.0)
            raw_score = self.RISK_SCORES.get(signal.risk_level, 0.0)
            
            # Apply confidence to weight
            effective_weight = weight * signal.confidence
            weighted_score = raw_score * effective_weight
            
            contributions.append(AgentContribution(
                agent_type=signal.agent_type,
                raw_signal=signal.risk_level,
                weight=weight,
                weighted_score=weighted_score,
                confidence=signal.confidence,
                abstained=False,
            ))
            
            total_weighted_score += weighted_score
            total_weight += effective_weight
        
        # Add abstained agents to contributions for transparency
        for signal in abstained_signals:
            contributions.append(AgentContribution(
                agent_type=signal.agent_type,
                raw_signal=signal.risk_level,
                weight=self.weights.get(signal.agent_type, 1.0),
                weighted_score=0.0,
                confidence=0.0,
                abstained=True,
            ))
        
        # Calculate final risk score
        risk_score = total_weighted_score / total_weight if total_weight > 0 else 0.0
        
        # Calculate consensus confidence
        base_confidence = self._calculate_confidence(active_signals)
        
        # Adjust confidence based on participation rate
        participation_rate = len(active_signals) / len(signals)
        adjusted_confidence = base_confidence * participation_rate
        
        # Log confidence adjustment
        logger.debug(
            f"Study {study_id}: Base confidence={base_confidence:.2f}, "
            f"Participation={participation_rate:.2f}, "
            f"Adjusted confidence={adjusted_confidence:.2f}"
        )
        
        # Classify risk level
        risk_level = self._classify_risk(risk_score)
        
        # Determine recommended action
        action = self._determine_action(risk_level, adjusted_confidence)
        
        # Generate explanation with abstention information
        explanation = self._generate_explanation_with_abstentions(
            risk_level, adjusted_confidence, contributions, risk_score,
            active_signals, abstained_signals
        )
        
        decision = ConsensusDecision(
            risk_level=risk_level,
            confidence=adjusted_confidence,
            risk_score=risk_score,
            contributing_agents=contributions,
            recommended_action=action,
            explanation=explanation,
            total_agents=len(signals),
            abstained_agents=len(abstained_signals),
            study_id=study_id,
        )
        
        logger.info(
            f"Consensus for {study_id}: risk={risk_level.value}, "
            f"score={risk_score:.1f}, confidence={adjusted_confidence:.2f}, "
            f"active_agents={len(active_signals)}/{len(signals)}"
        )
        
        return decision
    
    def _calculate_confidence(self, signals: List[AgentSignal]) -> float:
        """
        Calculate confidence based on agent agreement.
        
        Factors:
        - Agreement between agents (variance in risk levels)
        - Individual agent confidences
        - Number of contributing agents
        
        Returns:
            Confidence score between 0 and 1
        """
        if not signals:
            return 0.0
        
        if len(signals) == 1:
            return signals[0].confidence
        
        # Factor 1: Average agent confidence
        avg_confidence = statistics.mean(s.confidence for s in signals)
        
        # Factor 2: Agreement (inverse of variance in risk scores)
        risk_scores = [self.RISK_SCORES.get(s.risk_level, 0) for s in signals]
        
        if len(set(risk_scores)) == 1:
            # Perfect agreement
            agreement_factor = 1.0
        else:
            # Calculate normalized variance
            variance = statistics.variance(risk_scores)
            max_variance = 1875.0  # Max variance for [0, 25, 50, 75, 100]
            agreement_factor = 1.0 - min(variance / max_variance, 1.0)
        
        # Factor 3: Coverage (more agents = higher confidence)
        coverage_factor = min(len(signals) / 3.0, 1.0)  # Max at 3 agents
        
        # Weighted combination
        confidence = (
            avg_confidence * 0.4 +
            agreement_factor * 0.4 +
            coverage_factor * 0.2
        )
        
        return min(max(confidence, 0.0), 1.0)
    
    def _classify_risk(self, risk_score: float) -> ConsensusRiskLevel:
        """
        Classify risk score into risk level.
        
        Args:
            risk_score: Numerical risk score (0-100)
        
        Returns:
            ConsensusRiskLevel
        """
        if risk_score >= self.thresholds["critical"]:
            return ConsensusRiskLevel.CRITICAL
        elif risk_score >= self.thresholds["high"]:
            return ConsensusRiskLevel.HIGH
        elif risk_score >= self.thresholds["medium"]:
            return ConsensusRiskLevel.MEDIUM
        else:
            return ConsensusRiskLevel.LOW
    
    def _determine_action(
        self,
        risk_level: ConsensusRiskLevel,
        confidence: float,
    ) -> RecommendedAction:
        """
        Determine recommended action based on risk/confidence matrix.
        
        Decision Matrix:
        | Risk Level | Confidence | Action                    |
        |------------|------------|---------------------------|
        | Critical   | Any        | Immediate Escalation      |
        | High       | High       | Immediate Escalation      |
        | High       | Low        | Human Review Required     |
        | Medium     | High       | Prioritize for Action     |
        | Medium     | Low        | Monitor Closely           |
        | Low        | Any        | Routine Monitoring        |
        """
        high_confidence = confidence >= 0.7
        
        if risk_level == ConsensusRiskLevel.CRITICAL:
            return RecommendedAction.IMMEDIATE_ESCALATION
        
        elif risk_level == ConsensusRiskLevel.HIGH:
            if high_confidence:
                return RecommendedAction.IMMEDIATE_ESCALATION
            else:
                return RecommendedAction.HUMAN_REVIEW_REQUIRED
        
        elif risk_level == ConsensusRiskLevel.MEDIUM:
            if high_confidence:
                return RecommendedAction.PRIORITIZE_FOR_ACTION
            else:
                return RecommendedAction.MONITOR_CLOSELY
        
        else:  # LOW or UNKNOWN
            return RecommendedAction.ROUTINE_MONITORING
    
    def _generate_explanation(
        self,
        risk_level: ConsensusRiskLevel,
        confidence: float,
        contributions: List[AgentContribution],
        risk_score: float,
    ) -> str:
        """Generate human-readable explanation of consensus decision."""
        active = [c for c in contributions if not c.abstained]
        abstained = [c for c in contributions if c.abstained]
        
        # Build explanation
        parts = [
            f"Risk Level: {risk_level.value.upper()} (score: {risk_score:.1f}/100)",
            f"Confidence: {confidence:.0%}",
        ]
        
        if active:
            agent_summary = ", ".join(
                f"{c.agent_type.value}={c.raw_signal.value}"
                for c in active
            )
            parts.append(f"Contributing agents: {agent_summary}")
        
        if abstained:
            abstained_names = ", ".join(c.agent_type.value for c in abstained)
            parts.append(f"Abstained agents: {abstained_names}")
        
        # Highlight highest risk contributor
        if active:
            highest = max(active, key=lambda c: c.weighted_score)
            if highest.weighted_score > 0:
                parts.append(
                    f"Primary risk driver: {highest.agent_type.value} "
                    f"(weight: {highest.weight}x)"
                )
        
        return " | ".join(parts)
    
    def _generate_explanation_with_abstentions(
        self,
        risk_level: ConsensusRiskLevel,
        confidence: float,
        contributions: List[AgentContribution],
        risk_score: float,
        active_signals: List[AgentSignal],
        abstained_signals: List[AgentSignal],
    ) -> str:
        """
        Generate enhanced explanation including abstention details.
        
        This provides more context about why agents abstained and how
        that affected the consensus decision.
        """
        active = [c for c in contributions if not c.abstained]
        abstained = [c for c in contributions if c.abstained]
        
        # Build explanation
        parts = [
            f"Risk Level: {risk_level.value.upper()} (score: {risk_score:.1f}/100)",
            f"Confidence: {confidence:.0%}",
            f"Active Agents: {len(active)}/{len(contributions)}",
        ]
        
        if active:
            agent_summary = ", ".join(
                f"{c.agent_type.value}={c.raw_signal.value}"
                for c in active
            )
            parts.append(f"Signals: {agent_summary}")
        
        if abstained:
            abstained_names = ", ".join(c.agent_type.value for c in abstained)
            parts.append(f"Abstained: {abstained_names}")
            
            # Add abstention reasons if available
            if abstained_signals:
                reasons = []
                for signal in abstained_signals[:2]:  # Show first 2 reasons
                    if signal.abstention_reason:
                        short_reason = signal.abstention_reason.split('.')[0][:50]
                        reasons.append(f"{signal.agent_type.value}: {short_reason}")
                if reasons:
                    parts.append(f"Reasons: {'; '.join(reasons)}")
        
        # Highlight highest risk contributor
        if active:
            highest = max(active, key=lambda c: c.weighted_score)
            if highest.weighted_score > 0:
                parts.append(
                    f"Primary driver: {highest.agent_type.value} "
                    f"(weight: {highest.weight}x, conf: {highest.confidence:.0%})"
                )
        
        return " | ".join(parts)
    
    def _create_insufficient_data_decision(
        self,
        all_signals: List[AgentSignal],
        active_signals: List[AgentSignal],
        abstained_signals: List[AgentSignal],
        study_id: Optional[str],
    ) -> ConsensusDecision:
        """
        Create decision when insufficient active agents (< 3).
        
        This is different from all agents abstaining - some agents provided
        signals but not enough for reliable consensus.
        """
        contributions = []
        
        # Add active agents
        for signal in active_signals:
            contributions.append(AgentContribution(
                agent_type=signal.agent_type,
                raw_signal=signal.risk_level,
                weight=self.weights.get(signal.agent_type, 1.0),
                weighted_score=0.0,
                confidence=signal.confidence,
                abstained=False,
            ))
        
        # Add abstained agents
        for signal in abstained_signals:
            contributions.append(AgentContribution(
                agent_type=signal.agent_type,
                raw_signal=signal.risk_level,
                weight=self.weights.get(signal.agent_type, 1.0),
                weighted_score=0.0,
                confidence=0.0,
                abstained=True,
            ))
        
        active_names = [s.agent_type.value for s in active_signals]
        abstained_names = [s.agent_type.value for s in abstained_signals]
        
        explanation = (
            f"Insufficient data for consensus: Only {len(active_signals)} of {len(all_signals)} "
            f"agents provided signals (minimum 3 required). "
            f"Active: {', '.join(active_names)}. "
            f"Abstained: {', '.join(abstained_names)}."
        )
        
        return ConsensusDecision(
            risk_level=ConsensusRiskLevel.UNKNOWN,
            confidence=0.0,
            risk_score=0.0,
            contributing_agents=contributions,
            recommended_action=RecommendedAction.HUMAN_REVIEW_REQUIRED,
            explanation=explanation,
            total_agents=len(all_signals),
            abstained_agents=len(abstained_signals),
            study_id=study_id,
        )
    
    def _create_unknown_decision(
        self,
        study_id: Optional[str],
    ) -> ConsensusDecision:
        """Create decision when no signals available."""
        return ConsensusDecision(
            risk_level=ConsensusRiskLevel.UNKNOWN,
            confidence=0.0,
            risk_score=0.0,
            contributing_agents=[],
            recommended_action=RecommendedAction.HUMAN_REVIEW_REQUIRED,
            explanation="No agent signals available for consensus",
            total_agents=0,
            abstained_agents=0,
            study_id=study_id,
        )
    
    def _create_abstained_decision(
        self,
        signals: List[AgentSignal],
        study_id: Optional[str],
    ) -> ConsensusDecision:
        """Create decision when all agents abstained."""
        contributions = [
            AgentContribution(
                agent_type=s.agent_type,
                raw_signal=s.risk_level,
                weight=self.weights.get(s.agent_type, 1.0),
                weighted_score=0.0,
                confidence=0.0,
                abstained=True,
            )
            for s in signals
        ]
        
        return ConsensusDecision(
            risk_level=ConsensusRiskLevel.UNKNOWN,
            confidence=0.0,
            risk_score=0.0,
            contributing_agents=contributions,
            recommended_action=RecommendedAction.HUMAN_REVIEW_REQUIRED,
            explanation="All agents abstained due to insufficient data",
            total_agents=len(signals),
            abstained_agents=len(signals),
            study_id=study_id,
        )
    
    def get_weight(self, agent_type: AgentType) -> float:
        """Get weight for an agent type."""
        return self.weights.get(agent_type, 1.0)
    
    def set_weight(self, agent_type: AgentType, weight: float) -> None:
        """Set weight for an agent type."""
        self.weights[agent_type] = weight
        logger.info(f"Updated weight for {agent_type.value}: {weight}")


# ========================================
# RISK ASSESSMENT ENGINE
# ========================================

class RiskAssessmentEngine:
    """
    Risk assessment and decision engine.
    
    Provides:
    - Risk threshold management
    - Decision matrix application
    - Structured decision output
    - Confidence-based action recommendations
    """
    
    def __init__(
        self,
        consensus_engine: Optional[ConsensusEngine] = None,
    ):
        """
        Initialize risk assessment engine.
        
        Args:
            consensus_engine: Consensus engine to use (creates default if None)
        """
        self.consensus = consensus_engine or ConsensusEngine()
        logger.info("RiskAssessmentEngine initialized")
    
    def assess_study_risk(
        self,
        signals: List[AgentSignal],
        study_id: str,
    ) -> ConsensusDecision:
        """
        Assess overall risk for a study.
        
        Args:
            signals: Agent signals for the study
            study_id: Study identifier
        
        Returns:
            ConsensusDecision with risk assessment
        """
        return self.consensus.calculate_consensus(signals, study_id)
    
    def assess_site_risk(
        self,
        signals: List[AgentSignal],
        study_id: str,
        site_id: str,
    ) -> ConsensusDecision:
        """
        Assess risk for a specific site.
        
        Args:
            signals: Agent signals for the site
            study_id: Study identifier
            site_id: Site identifier
        
        Returns:
            ConsensusDecision with risk assessment
        """
        decision = self.consensus.calculate_consensus(
            signals, f"{study_id}/{site_id}"
        )
        return decision
    
    def prioritize_risks(
        self,
        decisions: List[ConsensusDecision],
    ) -> List[ConsensusDecision]:
        """
        Prioritize multiple risk decisions.
        
        Sorting criteria:
        1. Risk level (critical > high > medium > low)
        2. Confidence (higher confidence first)
        3. Risk score (higher score first)
        
        Args:
            decisions: List of consensus decisions
        
        Returns:
            Sorted list with highest priority first
        """
        risk_order = {
            ConsensusRiskLevel.CRITICAL: 4,
            ConsensusRiskLevel.HIGH: 3,
            ConsensusRiskLevel.MEDIUM: 2,
            ConsensusRiskLevel.LOW: 1,
            ConsensusRiskLevel.UNKNOWN: 0,
        }
        
        return sorted(
            decisions,
            key=lambda d: (
                risk_order.get(d.risk_level, 0),
                d.confidence,
                d.risk_score,
            ),
            reverse=True,
        )
    
    def get_action_summary(
        self,
        decisions: List[ConsensusDecision],
    ) -> Dict[RecommendedAction, int]:
        """
        Get summary of recommended actions.
        
        Args:
            decisions: List of consensus decisions
        
        Returns:
            Dictionary mapping actions to counts
        """
        summary: Dict[RecommendedAction, int] = {}
        for decision in decisions:
            action = decision.recommended_action
            summary[action] = summary.get(action, 0) + 1
        return summary


# ========================================
# EXPORTS
# ========================================

__all__ = [
    "ConsensusEngine",
    "RiskAssessmentEngine",
    "ConsensusDecision",
    "AgentContribution",
    "ConsensusRiskLevel",
    "RecommendedAction",
]
