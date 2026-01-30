"""
Coding Readiness Agent
======================
Specialized agent for detecting coding delays, backlog, and uncoded events.

Responsibilities:
- Monitor coding completion rates
- Track coding backlog duration
- Identify uncoded SAEs (critical safety events)
- Assess coding readiness for analysis

Key Features:
- Coding completion rate analysis
- Backlog aging detection
- Uncoded SAE monitoring
- Coding velocity tracking

**Validates: Requirements 2.2**
"""

from typing import Any, Dict, List, Optional
from datetime import datetime

from src.intelligence.base_agent import (
    BaseAgent,
    AgentType,
    RiskSignal,
    FeatureEvidence,
    AgentSignal,
)
from src.core import get_logger

logger = get_logger(__name__)


class CodingReadinessAgent(BaseAgent):
    """
    Agent specialized in detecting coding delays and readiness issues.
    
    Analyzes:
    - Coding completion rate
    - Coding backlog duration
    - Uncoded SAE count
    - Coding velocity trends
    
    Risk Assessment:
    - CRITICAL: <70% completion or >30 days backlog or uncoded SAEs
    - HIGH: <85% completion or >15 days backlog
    - MEDIUM: <95% completion or >7 days backlog
    - LOW: ≥95% completion and ≤7 days backlog
    """
    
    # Required features for analysis
    REQUIRED_FEATURES = [
        "coding_completion_rate",
        "coding_backlog_days",
    ]
    
    # Optional features that enhance analysis
    OPTIONAL_FEATURES = [
        "uncoded_sae_count",
        "coding_velocity",
        "pending_queries_coding",
    ]
    
    # Risk thresholds
    THRESHOLDS = {
        "coding_completion_rate": {
            "critical": 70.0,  # Below this is critical
            "high": 85.0,
            "medium": 95.0,
        },
        "coding_backlog_days": {
            "critical": 30.0,
            "high": 15.0,
            "medium": 7.0,
        },
        "uncoded_sae_count": {
            "critical": 1.0,  # Any uncoded SAE is critical
            "high": 0.0,
            "medium": 0.0,
        },
    }
    
    def __init__(
        self,
        min_confidence: float = 0.6,
        abstention_threshold: float = 0.5
    ):
        """
        Initialize Coding Readiness Agent.
        
        Args:
            min_confidence: Minimum confidence to emit signal
            abstention_threshold: Threshold below which to abstain
        """
        super().__init__(
            agent_type=AgentType.CODING,
            min_confidence=min_confidence,
            abstention_threshold=abstention_threshold
        )
        logger.info("CodingReadinessAgent initialized")
    
    def analyze(
        self,
        features: Dict[str, Any],
        study_id: str
    ) -> AgentSignal:
        """
        Analyze coding features and return risk signal.
        
        Args:
            features: Dictionary of engineered features
            study_id: Study identifier for logging
        
        Returns:
            AgentSignal with coding readiness risk assessment
        """
        logger.debug(f"Analyzing coding readiness for {study_id}")
        
        # Check if we should abstain
        should_abstain, reason = self._should_abstain(features, self.REQUIRED_FEATURES)
        
        if should_abstain:
            logger.info(f"{study_id}: Coding agent abstaining - {reason}")
            return self._create_abstention_signal(reason)
        
        # Extract feature values - handle None explicitly
        coding_completion = features.get("coding_completion_rate")
        if coding_completion is None:
            coding_completion = 0.0
        
        backlog_days = features.get("coding_backlog_days")
        if backlog_days is None:
            backlog_days = 0.0
        
        uncoded_sae = features.get("uncoded_sae_count")
        if uncoded_sae is None:
            uncoded_sae = 0
        
        coding_velocity = features.get("coding_velocity")
        pending_queries = features.get("pending_queries_coding")
        if pending_queries is None:
            pending_queries = 0
        
        # Collect evidence
        evidence: List[FeatureEvidence] = []
        
        # Analyze coding completion rate
        if coding_completion < 100:
            evidence.append(FeatureEvidence(
                feature_name="coding_completion_rate",
                feature_value=coding_completion,
                threshold=self.THRESHOLDS["coding_completion_rate"]["medium"],
                severity=self._calculate_completion_severity(
                    coding_completion,
                    self.THRESHOLDS["coding_completion_rate"]["medium"]
                ),
                description=f"Coding completion rate: {coding_completion:.1f}%"
            ))
        
        # Analyze backlog duration
        if backlog_days > 0:
            evidence.append(FeatureEvidence(
                feature_name="coding_backlog_days",
                feature_value=backlog_days,
                threshold=self.THRESHOLDS["coding_backlog_days"]["medium"],
                severity=self._calculate_severity(
                    backlog_days,
                    self.THRESHOLDS["coding_backlog_days"]["medium"],
                    max_value=60.0
                ),
                description=f"Coding backlog: {backlog_days:.1f} days"
            ))
        
        # Analyze uncoded SAEs (CRITICAL)
        if uncoded_sae > 0:
            evidence.append(FeatureEvidence(
                feature_name="uncoded_sae_count",
                feature_value=uncoded_sae,
                threshold=self.THRESHOLDS["uncoded_sae_count"]["critical"],
                severity=1.0,  # Always maximum severity
                description=f"CRITICAL: {uncoded_sae} uncoded SAE(s)"
            ))
        
        # Analyze coding velocity (if available)
        if coding_velocity is not None:
            if coding_velocity < 1.0:
                evidence.append(FeatureEvidence(
                    feature_name="coding_velocity",
                    feature_value=coding_velocity,
                    threshold=1.0,
                    severity=1.0 - coding_velocity,
                    description=f"Coding velocity: {coding_velocity:.2f} (below target)"
                ))
        
        # Analyze pending queries (if available)
        if pending_queries > 0:
            evidence.append(FeatureEvidence(
                feature_name="pending_queries_coding",
                feature_value=pending_queries,
                threshold=10.0,
                severity=min(pending_queries / 50.0, 1.0),
                description=f"{pending_queries} pending coding queries"
            ))
        
        # Determine overall risk level
        risk_level = self._assess_overall_risk(
            coding_completion, backlog_days, uncoded_sae
        )
        
        # Calculate confidence
        confidence = self._calculate_confidence(features)
        
        # Generate recommended actions
        actions = self._generate_recommendations(
            risk_level, coding_completion, backlog_days, uncoded_sae, pending_queries
        )
        
        logger.info(
            f"{study_id}: Coding readiness analysis complete - "
            f"risk={risk_level.value}, confidence={confidence:.2f}"
        )
        
        return AgentSignal(
            agent_type=self.agent_type,
            risk_level=risk_level,
            confidence=confidence,
            evidence=evidence,
            recommended_actions=actions,
            features_analyzed=len([f for f in self.REQUIRED_FEATURES + self.OPTIONAL_FEATURES 
                                   if f in features and features[f] is not None])
        )
    
    def _calculate_confidence(self, features: Dict[str, Any]) -> float:
        """
        Calculate confidence based on data availability and quality.
        
        Args:
            features: Available features
        
        Returns:
            Confidence score between 0 and 1
        """
        # Base confidence from required features
        required_available = sum(
            1 for f in self.REQUIRED_FEATURES 
            if f in features and features[f] is not None
        )
        base_confidence = required_available / len(self.REQUIRED_FEATURES)
        
        # Bonus for optional features
        optional_available = sum(
            1 for f in self.OPTIONAL_FEATURES 
            if f in features and features[f] is not None
        )
        optional_bonus = (optional_available / len(self.OPTIONAL_FEATURES)) * 0.2
        
        return min(base_confidence + optional_bonus, 1.0)
    
    def _assess_overall_risk(
        self,
        coding_completion: float,
        backlog_days: float,
        uncoded_sae: int
    ) -> RiskSignal:
        """
        Assess overall risk level from all coding metrics.
        
        Uses worst-case assessment across all metrics.
        """
        risk_scores = []
        
        # Uncoded SAEs are ALWAYS critical
        if uncoded_sae > 0:
            return RiskSignal.CRITICAL
        
        # Coding completion risk (inverted - lower is worse)
        if coding_completion <= self.THRESHOLDS["coding_completion_rate"]["critical"]:
            risk_scores.append(4)  # CRITICAL
        elif coding_completion <= self.THRESHOLDS["coding_completion_rate"]["high"]:
            risk_scores.append(3)  # HIGH
        elif coding_completion <= self.THRESHOLDS["coding_completion_rate"]["medium"]:
            risk_scores.append(2)  # MEDIUM
        else:
            risk_scores.append(1)  # LOW
        
        # Backlog duration risk
        if backlog_days >= self.THRESHOLDS["coding_backlog_days"]["critical"]:
            risk_scores.append(4)
        elif backlog_days >= self.THRESHOLDS["coding_backlog_days"]["high"]:
            risk_scores.append(3)
        elif backlog_days >= self.THRESHOLDS["coding_backlog_days"]["medium"]:
            risk_scores.append(2)
        else:
            risk_scores.append(1)
        
        # Use maximum risk score (worst case)
        max_risk = max(risk_scores) if risk_scores else 1
        
        risk_map = {
            4: RiskSignal.CRITICAL,
            3: RiskSignal.HIGH,
            2: RiskSignal.MEDIUM,
            1: RiskSignal.LOW,
        }
        
        return risk_map.get(max_risk, RiskSignal.LOW)
    
    def _calculate_completion_severity(
        self,
        completion_rate: float,
        threshold: float
    ) -> float:
        """
        Calculate severity for completion metrics (inverted scale).
        
        Lower completion = higher severity.
        """
        if completion_rate >= threshold:
            return 0.0
        
        # Calculate how far below threshold
        deficit = threshold - completion_rate
        max_deficit = threshold  # Worst case is 0% completion
        
        return min(deficit / max_deficit, 1.0)
    
    def _generate_recommendations(
        self,
        risk_level: RiskSignal,
        coding_completion: float,
        backlog_days: float,
        uncoded_sae: int,
        pending_queries: int
    ) -> List[str]:
        """Generate actionable recommendations based on findings."""
        recommendations = []
        
        # Uncoded SAEs are top priority
        if uncoded_sae > 0:
            recommendations.append(
                f"CRITICAL: {uncoded_sae} uncoded SAE(s) - "
                "immediate coding required for safety reporting"
            )
        
        # Coding completion issues
        if coding_completion < self.THRESHOLDS["coding_completion_rate"]["critical"]:
            recommendations.append(
                f"URGENT: Coding completion at {coding_completion:.1f}% - "
                "allocate additional coding resources immediately"
            )
        elif coding_completion < self.THRESHOLDS["coding_completion_rate"]["high"]:
            recommendations.append(
                f"Increase coding resources to improve {coding_completion:.1f}% completion rate"
            )
        elif coding_completion < self.THRESHOLDS["coding_completion_rate"]["medium"]:
            recommendations.append(
                f"Monitor coding progress - currently at {coding_completion:.1f}%"
            )
        
        # Backlog duration issues
        if backlog_days >= self.THRESHOLDS["coding_backlog_days"]["critical"]:
            recommendations.append(
                f"URGENT: {backlog_days:.0f}-day coding backlog - "
                "expedite coding process to prevent analysis delays"
            )
        elif backlog_days >= self.THRESHOLDS["coding_backlog_days"]["high"]:
            recommendations.append(
                f"Address {backlog_days:.0f}-day coding backlog before it impacts timelines"
            )
        elif backlog_days >= self.THRESHOLDS["coding_backlog_days"]["medium"]:
            recommendations.append(
                f"Monitor {backlog_days:.0f}-day coding backlog"
            )
        
        # Pending queries
        if pending_queries > 20:
            recommendations.append(
                f"Resolve {pending_queries} pending coding queries to improve velocity"
            )
        
        if not recommendations:
            recommendations.append("Coding readiness metrics within acceptable ranges")
        
        return recommendations


__all__ = ["CodingReadinessAgent"]
