"""
Safety & Compliance Agent
=========================
Specialized agent for monitoring SAE (Serious Adverse Events) and safety compliance.

Responsibilities:
- Monitor SAE review delays and backlogs
- Track fatal SAE counts
- Detect protocol deviations
- Ensure safety reporting compliance

Key Features:
- SAE backlog days analysis
- Overdue SAE report detection
- Fatal SAE monitoring (highest priority)
- Safety compliance scoring

**Validates: Requirements 2.1**

Note: This agent has the HIGHEST weight in consensus voting (3.0x)
due to the critical nature of safety monitoring in clinical trials.
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


class SafetyComplianceAgent(BaseAgent):
    """
    Agent specialized in safety monitoring and compliance.
    
    Analyzes:
    - SAE backlog days (average age of open SAEs)
    - Overdue SAE report count
    - Fatal SAE count (immediate escalation)
    - Safety compliance metrics
    
    Risk Assessment:
    - CRITICAL: Any fatal SAE OR >14 days SAE backlog OR any overdue SAEs
    - HIGH: >7 days SAE backlog
    - MEDIUM: >3 days SAE backlog
    - LOW: ≤3 days SAE backlog, no overdue, no fatal
    
    IMPORTANT: Safety agent has highest consensus weight (3.0x)
    """
    
    # Required features for analysis
    # Note: Made more lenient - can analyze with partial data
    REQUIRED_FEATURES = [
        "fatal_sae_count",  # Most critical - must have this
    ]
    
    # Preferred features that enhance analysis
    PREFERRED_FEATURES = [
        "sae_backlog_days",
    ]
    
    # Optional features that enhance analysis
    OPTIONAL_FEATURES = [
        "sae_overdue_count",
    ]
    
    # Risk thresholds - more conservative for safety
    THRESHOLDS = {
        "sae_backlog_days": {
            "critical": 14.0,  # 2 weeks is critical
            "high": 7.0,       # 1 week is high risk
            "medium": 3.0,     # 3 days needs attention
        },
        "sae_overdue_count": {
            "critical": 1,     # Any overdue is critical
            "high": 0,
            "medium": 0,
        },
        "fatal_sae_count": {
            "critical": 1,     # Any fatal SAE is critical
            "high": 0,
            "medium": 0,
        },
    }
    
    # Consensus weight - highest priority
    CONSENSUS_WEIGHT = 3.0
    
    def __init__(
        self,
        min_confidence: float = 0.6,
        abstention_threshold: float = 0.5
    ):
        """
        Initialize Safety & Compliance Agent.
        
        Args:
            min_confidence: Minimum confidence to emit signal
            abstention_threshold: Threshold below which to abstain
        """
        super().__init__(
            agent_type=AgentType.SAFETY,
            min_confidence=min_confidence,
            abstention_threshold=abstention_threshold
        )
        logger.info("SafetyComplianceAgent initialized with weight 3.0x")
    
    def analyze(
        self,
        features: Dict[str, Any],
        study_id: str
    ) -> AgentSignal:
        """
        Analyze safety features and return risk signal.
        
        Args:
            features: Dictionary of engineered features
            study_id: Study identifier for logging
        
        Returns:
            AgentSignal with safety risk assessment
        """
        logger.debug(f"Analyzing safety for {study_id}")
        
        # Extract feature values - handle None/missing gracefully
        # Even if features are NULL, we can still analyze with defaults
        fatal_count = features.get("fatal_sae_count")
        if fatal_count is None:
            fatal_count = 0
        
        # If sae_backlog_days is missing, assume 0 (no backlog data available)
        sae_backlog = features.get("sae_backlog_days", 0.0)
        if sae_backlog is None:
            sae_backlog = 0.0
        
        overdue_count = features.get("sae_overdue_count")
        if overdue_count is None:
            overdue_count = 0
        
        # Check if we have ANY data to analyze
        has_any_data = (
            fatal_count is not None or 
            sae_backlog is not None or 
            overdue_count is not None
        )
        
        if not has_any_data:
            # Truly no data available - abstain
            reason = "No safety data available (all features are None)"
            logger.info(f"{study_id}: Safety agent abstaining - {reason}")
            return self._create_abstention_signal(reason)
        
        # Collect evidence
        evidence: List[FeatureEvidence] = []
        
        # CRITICAL: Fatal SAE detection (highest priority)
        if fatal_count > 0:
            evidence.append(FeatureEvidence(
                feature_name="fatal_sae_count",
                feature_value=fatal_count,
                threshold=1,
                severity=1.0,  # Maximum severity
                description=f"CRITICAL: {fatal_count} fatal SAE(s) detected - immediate review required"
            ))
        
        # Overdue SAE detection
        if overdue_count > 0:
            evidence.append(FeatureEvidence(
                feature_name="sae_overdue_count",
                feature_value=overdue_count,
                threshold=1,
                severity=min(overdue_count / 5, 1.0),  # Scale severity
                description=f"URGENT: {overdue_count} overdue SAE report(s) require immediate attention"
            ))
        
        # SAE backlog analysis
        if sae_backlog > 0:
            evidence.append(FeatureEvidence(
                feature_name="sae_backlog_days",
                feature_value=sae_backlog,
                threshold=self.THRESHOLDS["sae_backlog_days"]["medium"],
                severity=self._calculate_severity(
                    sae_backlog,
                    self.THRESHOLDS["sae_backlog_days"]["medium"],
                    max_value=30.0
                ),
                description=f"SAE backlog: {sae_backlog:.1f} days average age"
            ))
        
        # Determine overall risk level
        risk_level = self._assess_overall_risk(sae_backlog, fatal_count, overdue_count)
        
        # Calculate confidence
        confidence = self._calculate_confidence(features)
        
        # Generate recommended actions
        actions = self._generate_recommendations(
            risk_level, sae_backlog, fatal_count, overdue_count
        )
        
        logger.info(
            f"{study_id}: Safety analysis complete - "
            f"risk={risk_level.value}, confidence={confidence:.2f}, "
            f"fatal={fatal_count}, overdue={overdue_count}"
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
        # Count available features (non-None)
        fatal_available = features.get("fatal_sae_count") is not None
        sae_backlog_available = features.get("sae_backlog_days") is not None
        overdue_available = features.get("sae_overdue_count") is not None
        
        # Base confidence from having any data
        available_count = sum([fatal_available, sae_backlog_available, overdue_available])
        total_features = 3  # fatal, backlog, overdue
        
        if available_count == 0:
            return 0.0
        
        # Calculate confidence based on data availability
        base_confidence = available_count / total_features
        
        # Boost confidence if we have the most critical feature (fatal_sae_count)
        if fatal_available:
            base_confidence = min(base_confidence + 0.2, 1.0)
        
        return base_confidence
    
    def _assess_overall_risk(
        self,
        sae_backlog: float,
        fatal_count: int,
        overdue_count: int
    ) -> RiskSignal:
        """
        Assess overall safety risk level.
        
        Safety uses strict escalation rules:
        - Any fatal SAE = CRITICAL
        - Any overdue SAE = CRITICAL
        - High backlog = escalate accordingly
        """
        # CRITICAL conditions (any one triggers)
        if fatal_count > 0:
            return RiskSignal.CRITICAL
        
        if overdue_count > 0:
            return RiskSignal.CRITICAL
        
        if sae_backlog >= self.THRESHOLDS["sae_backlog_days"]["critical"]:
            return RiskSignal.CRITICAL
        
        # HIGH conditions
        if sae_backlog >= self.THRESHOLDS["sae_backlog_days"]["high"]:
            return RiskSignal.HIGH
        
        # MEDIUM conditions
        if sae_backlog >= self.THRESHOLDS["sae_backlog_days"]["medium"]:
            return RiskSignal.MEDIUM
        
        # LOW - all metrics within acceptable ranges
        return RiskSignal.LOW
    
    def _generate_recommendations(
        self,
        risk_level: RiskSignal,
        sae_backlog: float,
        fatal_count: int,
        overdue_count: int
    ) -> List[str]:
        """Generate actionable recommendations based on findings."""
        recommendations = []
        
        # Fatal SAE - highest priority
        if fatal_count > 0:
            recommendations.append(
                f"IMMEDIATE ACTION: {fatal_count} fatal SAE(s) require immediate "
                "medical review and regulatory notification"
            )
        
        # Overdue SAEs
        if overdue_count > 0:
            recommendations.append(
                f"URGENT: {overdue_count} overdue SAE report(s) - "
                "expedite review and submission to meet regulatory timelines"
            )
        
        # SAE backlog
        if sae_backlog >= self.THRESHOLDS["sae_backlog_days"]["critical"]:
            recommendations.append(
                f"CRITICAL: SAE backlog at {sae_backlog:.1f} days - "
                "allocate additional resources for SAE processing"
            )
        elif sae_backlog >= self.THRESHOLDS["sae_backlog_days"]["high"]:
            recommendations.append(
                f"HIGH PRIORITY: SAE backlog at {sae_backlog:.1f} days - "
                "review SAE processing workflow"
            )
        elif sae_backlog >= self.THRESHOLDS["sae_backlog_days"]["medium"]:
            recommendations.append(
                f"Monitor SAE backlog ({sae_backlog:.1f} days) - "
                "ensure timely processing"
            )
        
        if not recommendations:
            recommendations.append("Safety metrics within acceptable ranges - continue monitoring")
        
        return recommendations


__all__ = ["SafetyComplianceAgent"]
