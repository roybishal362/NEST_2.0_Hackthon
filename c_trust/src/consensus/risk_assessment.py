"""
C-TRUST Risk Assessment and Decision Engine
============================================
Implements risk thresholds, decision matrix, and confidence-based
action recommendations.

Key Features:
- Risk threshold configuration
- Decision matrix for action recommendations
- Confidence-based action prioritization
- Structured decision output format

**Validates: Requirements 2.4**

Decision Matrix (from design):
Risk Level    | Confidence | Action
High         | High       | Immediate Escalation
High         | Low        | Human Review Required
Medium       | High       | Prioritize for Action
Medium       | Low        | Monitor Closely
Low          | Any        | Routine Monitoring
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from src.consensus.consensus_engine import ConsensusResult, ConsensusRiskLevel
from src.intelligence.base_agent import AgentSignal, RiskSignal
from src.core import get_logger

logger = get_logger(__name__)


class ActionPriority(str, Enum):
    """Priority levels for recommended actions"""
    IMMEDIATE = "IMMEDIATE"      # Requires immediate attention
    HIGH = "HIGH"                # Should be addressed soon
    MEDIUM = "MEDIUM"            # Schedule for review
    LOW = "LOW"                  # Routine monitoring
    INFORMATIONAL = "INFORMATIONAL"  # No action required


class ActionType(str, Enum):
    """Types of recommended actions"""
    ESCALATE = "ESCALATE"
    REVIEW = "REVIEW"
    MONITOR = "MONITOR"
    INVESTIGATE = "INVESTIGATE"
    ACKNOWLEDGE = "ACKNOWLEDGE"
    NO_ACTION = "NO_ACTION"


@dataclass
class RecommendedAction:
    """
    A recommended action based on risk assessment.
    
    Attributes:
        action_type: Type of action to take
        priority: Priority level of the action
        description: Human-readable description
        target_role: Role responsible for this action
        due_within_hours: Suggested timeframe for action
        evidence_summary: Summary of evidence supporting this action
    """
    action_type: ActionType
    priority: ActionPriority
    description: str
    target_role: str = "DATA_MANAGER"
    due_within_hours: Optional[int] = None
    evidence_summary: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "action_type": self.action_type.value,
            "priority": self.priority.value,
            "description": self.description,
            "target_role": self.target_role,
            "due_within_hours": self.due_within_hours,
            "evidence_summary": self.evidence_summary,
        }


@dataclass
class RiskDecision:
    """
    Final risk decision with recommended actions.
    
    Attributes:
        entity_id: Identifier for the entity being assessed
        entity_type: Type of entity (STUDY, SITE, SUBJECT)
        risk_level: Final risk level
        risk_score: Numerical risk score (0-100)
        confidence: Confidence in the assessment
        recommended_actions: List of recommended actions
        decision_rationale: Explanation of the decision
        contributing_factors: Key factors that influenced the decision
        consensus_result: Original consensus result
        timestamp: When decision was made
    """
    entity_id: str
    entity_type: str
    risk_level: ConsensusRiskLevel
    risk_score: float
    confidence: float
    recommended_actions: List[RecommendedAction]
    decision_rationale: str
    contributing_factors: List[str]
    consensus_result: Optional[ConsensusResult] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "risk_level": self.risk_level.value,
            "risk_score": self.risk_score,
            "confidence": self.confidence,
            "recommended_actions": [a.to_dict() for a in self.recommended_actions],
            "decision_rationale": self.decision_rationale,
            "contributing_factors": self.contributing_factors,
            "timestamp": self.timestamp.isoformat(),
        }


class RiskAssessmentEngine:
    """
    Risk assessment and decision engine.
    
    Transforms consensus results into actionable decisions with
    prioritized recommendations based on risk level and confidence.
    
    Decision Matrix:
    - CRITICAL + High Confidence → Immediate Escalation
    - CRITICAL + Low Confidence → Urgent Human Review
    - HIGH + High Confidence → Prioritize for Action
    - HIGH + Low Confidence → Human Review Required
    - MEDIUM + High Confidence → Schedule Review
    - MEDIUM + Low Confidence → Monitor Closely
    - LOW + Any → Routine Monitoring
    """
    
    # Confidence thresholds
    HIGH_CONFIDENCE_THRESHOLD = 0.7
    MEDIUM_CONFIDENCE_THRESHOLD = 0.4
    
    # Due within hours by priority
    DUE_WITHIN_HOURS = {
        ActionPriority.IMMEDIATE: 4,
        ActionPriority.HIGH: 24,
        ActionPriority.MEDIUM: 72,
        ActionPriority.LOW: 168,  # 1 week
        ActionPriority.INFORMATIONAL: None,
    }
    
    # Role assignments by risk type
    ROLE_ASSIGNMENTS = {
        "safety": "STUDY_LEAD",
        "compliance": "DATA_MANAGER",
        "completeness": "CRA",
        "operations": "CRA",
        "default": "DATA_MANAGER",
    }
    
    def __init__(
        self,
        high_confidence_threshold: float = 0.7,
        medium_confidence_threshold: float = 0.4
    ):
        """
        Initialize risk assessment engine.
        
        Args:
            high_confidence_threshold: Threshold for high confidence
            medium_confidence_threshold: Threshold for medium confidence
        """
        self.high_confidence_threshold = high_confidence_threshold
        self.medium_confidence_threshold = medium_confidence_threshold
        logger.info("RiskAssessmentEngine initialized")
    
    def assess_risk(
        self,
        consensus_result: ConsensusResult,
        entity_type: str = "SITE"
    ) -> RiskDecision:
        """
        Assess risk and generate decision with recommendations.
        
        Args:
            consensus_result: Result from consensus engine
            entity_type: Type of entity (STUDY, SITE, SUBJECT)
        
        Returns:
            RiskDecision with recommended actions
        """
        logger.debug(f"Assessing risk for {consensus_result.entity_id}")
        
        # Determine confidence level
        confidence_level = self._classify_confidence(consensus_result.confidence)
        
        # Generate recommended actions based on decision matrix
        actions = self._generate_actions(
            consensus_result.risk_level,
            confidence_level,
            consensus_result
        )
        
        # Generate decision rationale
        rationale = self._generate_rationale(
            consensus_result.risk_level,
            confidence_level,
            consensus_result
        )
        
        # Extract contributing factors
        factors = self._extract_contributing_factors(consensus_result)
        
        decision = RiskDecision(
            entity_id=consensus_result.entity_id,
            entity_type=entity_type,
            risk_level=consensus_result.risk_level,
            risk_score=consensus_result.risk_score,
            confidence=consensus_result.confidence,
            recommended_actions=actions,
            decision_rationale=rationale,
            contributing_factors=factors,
            consensus_result=consensus_result,
        )
        
        logger.info(
            f"Risk decision for {consensus_result.entity_id}: "
            f"risk={decision.risk_level.value}, "
            f"actions={len(actions)}, "
            f"top_priority={actions[0].priority.value if actions else 'NONE'}"
        )
        
        return decision
    
    def _classify_confidence(self, confidence: float) -> str:
        """Classify confidence level"""
        if confidence >= self.high_confidence_threshold:
            return "HIGH"
        elif confidence >= self.medium_confidence_threshold:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _generate_actions(
        self,
        risk_level: ConsensusRiskLevel,
        confidence_level: str,
        consensus: ConsensusResult
    ) -> List[RecommendedAction]:
        """
        Generate recommended actions based on decision matrix.
        
        Args:
            risk_level: Consensus risk level
            confidence_level: HIGH, MEDIUM, or LOW
            consensus: Full consensus result for context
        
        Returns:
            List of recommended actions
        """
        actions = []
        
        # Decision matrix implementation
        if risk_level == ConsensusRiskLevel.CRITICAL:
            if confidence_level == "HIGH":
                actions.append(RecommendedAction(
                    action_type=ActionType.ESCALATE,
                    priority=ActionPriority.IMMEDIATE,
                    description="CRITICAL risk detected with high confidence. Immediate escalation required.",
                    target_role="STUDY_LEAD",
                    due_within_hours=self.DUE_WITHIN_HOURS[ActionPriority.IMMEDIATE],
                    evidence_summary=self._summarize_evidence(consensus),
                ))
            else:
                actions.append(RecommendedAction(
                    action_type=ActionType.REVIEW,
                    priority=ActionPriority.IMMEDIATE,
                    description="CRITICAL risk detected but confidence is low. Urgent human review required to validate findings.",
                    target_role="STUDY_LEAD",
                    due_within_hours=self.DUE_WITHIN_HOURS[ActionPriority.IMMEDIATE],
                    evidence_summary=self._summarize_evidence(consensus),
                ))
        
        elif risk_level == ConsensusRiskLevel.HIGH:
            if confidence_level == "HIGH":
                actions.append(RecommendedAction(
                    action_type=ActionType.INVESTIGATE,
                    priority=ActionPriority.HIGH,
                    description="HIGH risk detected with high confidence. Prioritize for investigation and action.",
                    target_role="DATA_MANAGER",
                    due_within_hours=self.DUE_WITHIN_HOURS[ActionPriority.HIGH],
                    evidence_summary=self._summarize_evidence(consensus),
                ))
            else:
                actions.append(RecommendedAction(
                    action_type=ActionType.REVIEW,
                    priority=ActionPriority.HIGH,
                    description="HIGH risk detected but confidence is low. Human review required to validate assessment.",
                    target_role="DATA_MANAGER",
                    due_within_hours=self.DUE_WITHIN_HOURS[ActionPriority.HIGH],
                    evidence_summary=self._summarize_evidence(consensus),
                ))
        
        elif risk_level == ConsensusRiskLevel.MEDIUM:
            if confidence_level == "HIGH":
                actions.append(RecommendedAction(
                    action_type=ActionType.INVESTIGATE,
                    priority=ActionPriority.MEDIUM,
                    description="MEDIUM risk detected. Schedule for review and potential action.",
                    target_role="CRA",
                    due_within_hours=self.DUE_WITHIN_HOURS[ActionPriority.MEDIUM],
                    evidence_summary=self._summarize_evidence(consensus),
                ))
            else:
                actions.append(RecommendedAction(
                    action_type=ActionType.MONITOR,
                    priority=ActionPriority.MEDIUM,
                    description="MEDIUM risk detected with low confidence. Monitor closely for changes.",
                    target_role="CRA",
                    due_within_hours=self.DUE_WITHIN_HOURS[ActionPriority.MEDIUM],
                    evidence_summary=self._summarize_evidence(consensus),
                ))
        
        elif risk_level == ConsensusRiskLevel.LOW:
            actions.append(RecommendedAction(
                action_type=ActionType.MONITOR,
                priority=ActionPriority.LOW,
                description="LOW risk. Continue routine monitoring.",
                target_role="CRA",
                due_within_hours=self.DUE_WITHIN_HOURS[ActionPriority.LOW],
                evidence_summary="No significant issues detected.",
            ))
        
        else:  # UNKNOWN
            actions.append(RecommendedAction(
                action_type=ActionType.REVIEW,
                priority=ActionPriority.MEDIUM,
                description="Unable to assess risk due to insufficient data. Review data availability.",
                target_role="DATA_MANAGER",
                due_within_hours=self.DUE_WITHIN_HOURS[ActionPriority.MEDIUM],
                evidence_summary="Insufficient data for risk assessment.",
            ))
        
        # Add agent-specific actions based on contributing signals
        agent_actions = self._generate_agent_specific_actions(consensus)
        actions.extend(agent_actions)
        
        return actions
    
    def _generate_agent_specific_actions(
        self,
        consensus: ConsensusResult
    ) -> List[RecommendedAction]:
        """Generate actions based on specific agent findings"""
        actions = []
        
        for signal in consensus.agent_signals:
            if signal.abstained:
                continue
            
            # Only add specific actions for HIGH or CRITICAL signals
            if signal.risk_level not in [RiskSignal.HIGH, RiskSignal.CRITICAL]:
                continue
            
            agent_type = signal.agent_type.value
            target_role = self.ROLE_ASSIGNMENTS.get(agent_type, "DATA_MANAGER")
            
            # Generate action based on agent type
            if agent_type == "safety":
                if signal.risk_level == RiskSignal.CRITICAL:
                    actions.append(RecommendedAction(
                        action_type=ActionType.ESCALATE,
                        priority=ActionPriority.IMMEDIATE,
                        description=f"Safety agent detected CRITICAL issue. Review SAE backlog and compliance.",
                        target_role="STUDY_LEAD",
                        due_within_hours=4,
                        evidence_summary=self._format_agent_evidence(signal),
                    ))
            
            elif agent_type == "completeness":
                actions.append(RecommendedAction(
                    action_type=ActionType.INVESTIGATE,
                    priority=ActionPriority.HIGH if signal.risk_level == RiskSignal.CRITICAL else ActionPriority.MEDIUM,
                    description=f"Data completeness issues detected. Review missing data and form completion.",
                    target_role="CRA",
                    due_within_hours=24 if signal.risk_level == RiskSignal.CRITICAL else 72,
                    evidence_summary=self._format_agent_evidence(signal),
                ))
            
            elif agent_type == "query_quality":
                actions.append(RecommendedAction(
                    action_type=ActionType.INVESTIGATE,
                    priority=ActionPriority.HIGH if signal.risk_level == RiskSignal.CRITICAL else ActionPriority.MEDIUM,
                    description=f"Query quality issues detected. Review query backlog and aging.",
                    target_role="DATA_MANAGER",
                    due_within_hours=24 if signal.risk_level == RiskSignal.CRITICAL else 72,
                    evidence_summary=self._format_agent_evidence(signal),
                ))
        
        return actions
    
    def _generate_rationale(
        self,
        risk_level: ConsensusRiskLevel,
        confidence_level: str,
        consensus: ConsensusResult
    ) -> str:
        """Generate human-readable decision rationale"""
        parts = []
        
        # Risk level explanation
        parts.append(f"Risk level assessed as {risk_level.value} (score: {consensus.risk_score:.1f}/100).")
        
        # Confidence explanation
        parts.append(f"Confidence in assessment is {confidence_level.lower()} ({consensus.confidence:.0%}).")
        
        # Contributing agents
        if consensus.contributing_agents:
            parts.append(f"Assessment based on {len(consensus.contributing_agents)} agent(s): {', '.join(consensus.contributing_agents)}.")
        
        # Abstained agents
        if consensus.abstained_agents:
            parts.append(f"Note: {len(consensus.abstained_agents)} agent(s) abstained due to insufficient data.")
        
        # Agreement
        if consensus.agreement_ratio < 0.5:
            parts.append("Warning: Low agreement among agents - consider additional review.")
        elif consensus.agreement_ratio >= 0.8:
            parts.append("High agreement among agents supports this assessment.")
        
        return " ".join(parts)
    
    def _extract_contributing_factors(
        self,
        consensus: ConsensusResult
    ) -> List[str]:
        """Extract key contributing factors from consensus"""
        factors = []
        
        for signal in consensus.agent_signals:
            if signal.abstained:
                continue
            
            if signal.risk_level in [RiskSignal.HIGH, RiskSignal.CRITICAL]:
                factors.append(
                    f"{signal.agent_type.value}: {signal.risk_level.value} risk "
                    f"(confidence: {signal.confidence:.0%})"
                )
        
        if not factors:
            factors.append("No significant risk factors identified")
        
        return factors
    
    def _summarize_evidence(self, consensus: ConsensusResult) -> str:
        """Summarize evidence from consensus"""
        summaries = []
        
        for signal in consensus.agent_signals:
            if signal.abstained:
                continue
            
            if signal.evidence:
                for evidence in signal.evidence[:2]:  # Limit to top 2 per agent
                    summaries.append(evidence.description)
        
        if summaries:
            return "; ".join(summaries[:5])  # Limit total to 5
        
        return "See detailed agent signals for evidence."
    
    def _format_agent_evidence(self, signal: AgentSignal) -> str:
        """Format evidence from a single agent signal"""
        if signal.evidence:
            descriptions = [e.description for e in signal.evidence[:3]]
            return "; ".join(descriptions)
        return "No specific evidence recorded."


__all__ = [
    "RiskAssessmentEngine",
    "RiskDecision",
    "RecommendedAction",
    "ActionPriority",
    "ActionType",
]
