"""
Stability Agent
===============
Specialized agent for assessing study stability and operational health.

Responsibilities:
- Monitor enrollment velocity
- Track site activation rates
- Assess dropout rates
- Evaluate overall study stability

Key Features:
- Enrollment velocity analysis
- Site activation tracking
- Dropout rate monitoring
- **INVERTED RISK LOGIC**: Good performance = LOW risk

**Validates: Requirements 2.4**

IMPORTANT: This agent uses INVERTED risk logic:
- High enrollment velocity = LOW risk (good)
- High site activation = LOW risk (good)
- Low dropout rate = LOW risk (good)
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


class StabilityAgent(BaseAgent):
    """
    Agent specialized in assessing study stability and operational health.
    
    **INVERTED RISK LOGIC**: Unlike other agents, this agent treats
    good performance as LOW risk. High enrollment and activation rates
    indicate a stable, well-performing study.
    
    Analyzes:
    - Enrollment velocity (higher = better)
    - Site activation rate (higher = better)
    - Dropout rate (lower = better)
    
    Risk Assessment (INVERTED):
    - LOW: ≥90% velocity, ≥90% activation, ≤10% dropout (GOOD performance)
    - MEDIUM: ≥75% velocity, ≥75% activation, ≤15% dropout
    - HIGH: ≥50% velocity, ≥50% activation, ≤20% dropout
    - CRITICAL: <50% velocity, <50% activation, >20% dropout (POOR performance)
    """
    
    # Required features for analysis
    REQUIRED_FEATURES = [
        "enrollment_velocity",
        "site_activation_rate",
        "dropout_rate",
    ]
    
    # Optional features that enhance analysis
    OPTIONAL_FEATURES = [
        "enrollment_trend",
        "site_performance_variance",
        "patient_retention_rate",
    ]
    
    # Risk thresholds (INVERTED LOGIC)
    # Higher values = BETTER performance = LOWER risk
    THRESHOLDS = {
        "enrollment_velocity": {
            "low": 90.0,      # ≥90% = LOW risk (excellent)
            "medium": 75.0,   # ≥75% = MEDIUM risk (acceptable)
            "high": 50.0,     # ≥50% = HIGH risk (concerning)
            # <50% = CRITICAL risk (poor)
        },
        "site_activation_rate": {
            "low": 90.0,      # ≥90% = LOW risk (excellent)
            "medium": 75.0,   # ≥75% = MEDIUM risk (acceptable)
            "high": 50.0,     # ≥50% = HIGH risk (concerning)
            # <50% = CRITICAL risk (poor)
        },
        "dropout_rate": {
            "low": 10.0,      # ≤10% = LOW risk (excellent)
            "medium": 15.0,   # ≤15% = MEDIUM risk (acceptable)
            "high": 20.0,     # ≤20% = HIGH risk (concerning)
            # >20% = CRITICAL risk (poor)
        },
    }
    
    def __init__(
        self,
        min_confidence: float = 0.6,
        abstention_threshold: float = 0.5
    ):
        """
        Initialize Stability Agent.
        
        Args:
            min_confidence: Minimum confidence to emit signal
            abstention_threshold: Threshold below which to abstain
        """
        super().__init__(
            agent_type=AgentType.STABILITY,
            min_confidence=min_confidence,
            abstention_threshold=abstention_threshold
        )
        logger.info("StabilityAgent initialized (INVERTED RISK LOGIC)")
    
    def analyze(
        self,
        features: Dict[str, Any],
        study_id: str
    ) -> AgentSignal:
        """
        Analyze stability features and return risk signal.
        
        **INVERTED LOGIC**: Good performance = LOW risk
        
        Args:
            features: Dictionary of engineered features
            study_id: Study identifier for logging
        
        Returns:
            AgentSignal with stability risk assessment
        """
        logger.debug(f"Analyzing stability for {study_id}")
        
        # Check if we should abstain
        should_abstain, reason = self._should_abstain(features, self.REQUIRED_FEATURES)
        
        if should_abstain:
            logger.info(f"{study_id}: Stability agent abstaining - {reason}")
            return self._create_abstention_signal(reason)
        
        # Extract feature values
        enrollment_velocity = features.get("enrollment_velocity", 0.0)
        site_activation = features.get("site_activation_rate", 0.0)
        dropout_rate = features.get("dropout_rate", 0.0)
        enrollment_trend = features.get("enrollment_trend")
        site_variance = features.get("site_performance_variance")
        retention_rate = features.get("patient_retention_rate")
        
        # Collect evidence
        evidence: List[FeatureEvidence] = []
        
        # Analyze enrollment velocity (higher = better)
        if enrollment_velocity < 100:
            evidence.append(FeatureEvidence(
                feature_name="enrollment_velocity",
                feature_value=enrollment_velocity,
                threshold=self.THRESHOLDS["enrollment_velocity"]["low"],
                severity=self._calculate_inverted_severity(
                    enrollment_velocity,
                    self.THRESHOLDS["enrollment_velocity"]["low"]
                ),
                description=f"Enrollment velocity: {enrollment_velocity:.1f}%"
            ))
        
        # Analyze site activation rate (higher = better)
        if site_activation < 100:
            evidence.append(FeatureEvidence(
                feature_name="site_activation_rate",
                feature_value=site_activation,
                threshold=self.THRESHOLDS["site_activation_rate"]["low"],
                severity=self._calculate_inverted_severity(
                    site_activation,
                    self.THRESHOLDS["site_activation_rate"]["low"]
                ),
                description=f"Site activation rate: {site_activation:.1f}%"
            ))
        
        # Analyze dropout rate (lower = better)
        if dropout_rate > 0:
            evidence.append(FeatureEvidence(
                feature_name="dropout_rate",
                feature_value=dropout_rate,
                threshold=self.THRESHOLDS["dropout_rate"]["low"],
                severity=self._calculate_severity(
                    dropout_rate,
                    self.THRESHOLDS["dropout_rate"]["low"],
                    max_value=50.0
                ),
                description=f"Dropout rate: {dropout_rate:.1f}%"
            ))
        
        # Analyze enrollment trend (if available)
        if enrollment_trend is not None:
            if enrollment_trend < 0:
                evidence.append(FeatureEvidence(
                    feature_name="enrollment_trend",
                    feature_value=enrollment_trend,
                    threshold=0.0,
                    severity=min(abs(enrollment_trend) / 10.0, 1.0),
                    description=f"Enrollment trend: {enrollment_trend:+.1f}% (declining)"
                ))
            elif enrollment_trend > 0:
                evidence.append(FeatureEvidence(
                    feature_name="enrollment_trend",
                    feature_value=enrollment_trend,
                    threshold=0.0,
                    severity=0.0,  # Positive trend is good
                    description=f"Enrollment trend: {enrollment_trend:+.1f}% (improving)"
                ))
        
        # Analyze site performance variance (if available)
        if site_variance is not None and site_variance > 20.0:
            evidence.append(FeatureEvidence(
                feature_name="site_performance_variance",
                feature_value=site_variance,
                threshold=20.0,
                severity=min(site_variance / 50.0, 1.0),
                description=f"High site performance variance: {site_variance:.1f}%"
            ))
        
        # Analyze retention rate (if available)
        if retention_rate is not None and retention_rate < 90.0:
            evidence.append(FeatureEvidence(
                feature_name="patient_retention_rate",
                feature_value=retention_rate,
                threshold=90.0,
                severity=self._calculate_inverted_severity(retention_rate, 90.0),
                description=f"Patient retention rate: {retention_rate:.1f}%"
            ))
        
        # Determine overall risk level (INVERTED LOGIC)
        risk_level = self._assess_overall_risk_inverted(
            enrollment_velocity, site_activation, dropout_rate
        )
        
        # Calculate confidence
        confidence = self._calculate_confidence(features)
        
        # Generate recommended actions
        actions = self._generate_recommendations(
            risk_level, enrollment_velocity, site_activation, dropout_rate, enrollment_trend
        )
        
        logger.info(
            f"{study_id}: Stability analysis complete - "
            f"risk={risk_level.value}, confidence={confidence:.2f} (INVERTED LOGIC)"
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
    
    def _assess_overall_risk_inverted(
        self,
        enrollment_velocity: float,
        site_activation: float,
        dropout_rate: float
    ) -> RiskSignal:
        """
        Assess overall risk level with INVERTED logic.
        
        INVERTED: High performance = LOW risk
        
        Uses best-case assessment (opposite of other agents).
        """
        risk_scores = []
        
        # Enrollment velocity (INVERTED: higher = better = lower risk)
        if enrollment_velocity >= self.THRESHOLDS["enrollment_velocity"]["low"]:
            risk_scores.append(1)  # LOW risk (excellent)
        elif enrollment_velocity >= self.THRESHOLDS["enrollment_velocity"]["medium"]:
            risk_scores.append(2)  # MEDIUM risk
        elif enrollment_velocity >= self.THRESHOLDS["enrollment_velocity"]["high"]:
            risk_scores.append(3)  # HIGH risk
        else:
            risk_scores.append(4)  # CRITICAL risk (poor)
        
        # Site activation (INVERTED: higher = better = lower risk)
        if site_activation >= self.THRESHOLDS["site_activation_rate"]["low"]:
            risk_scores.append(1)  # LOW risk (excellent)
        elif site_activation >= self.THRESHOLDS["site_activation_rate"]["medium"]:
            risk_scores.append(2)  # MEDIUM risk
        elif site_activation >= self.THRESHOLDS["site_activation_rate"]["high"]:
            risk_scores.append(3)  # HIGH risk
        else:
            risk_scores.append(4)  # CRITICAL risk (poor)
        
        # Dropout rate (NORMAL: lower = better = lower risk)
        if dropout_rate <= self.THRESHOLDS["dropout_rate"]["low"]:
            risk_scores.append(1)  # LOW risk (excellent)
        elif dropout_rate <= self.THRESHOLDS["dropout_rate"]["medium"]:
            risk_scores.append(2)  # MEDIUM risk
        elif dropout_rate <= self.THRESHOLDS["dropout_rate"]["high"]:
            risk_scores.append(3)  # HIGH risk
        else:
            risk_scores.append(4)  # CRITICAL risk (poor)
        
        # Use MAXIMUM risk score (worst case - even for inverted logic)
        # If any metric is poor, overall risk is high
        max_risk = max(risk_scores) if risk_scores else 1
        
        risk_map = {
            4: RiskSignal.CRITICAL,
            3: RiskSignal.HIGH,
            2: RiskSignal.MEDIUM,
            1: RiskSignal.LOW,
        }
        
        return risk_map.get(max_risk, RiskSignal.LOW)
    
    def _calculate_inverted_severity(
        self,
        value: float,
        threshold: float
    ) -> float:
        """
        Calculate severity for INVERTED metrics (higher = better).
        
        Lower value = higher severity (opposite of normal).
        """
        if value >= threshold:
            return 0.0  # Above threshold = no severity
        
        # Calculate how far below threshold
        deficit = threshold - value
        max_deficit = threshold  # Worst case is 0%
        
        return min(deficit / max_deficit, 1.0)
    
    def _generate_recommendations(
        self,
        risk_level: RiskSignal,
        enrollment_velocity: float,
        site_activation: float,
        dropout_rate: float,
        enrollment_trend: Optional[float]
    ) -> List[str]:
        """Generate actionable recommendations based on findings."""
        recommendations = []
        
        # Enrollment velocity issues
        if enrollment_velocity < self.THRESHOLDS["enrollment_velocity"]["high"]:
            recommendations.append(
                f"URGENT: Enrollment velocity at {enrollment_velocity:.1f}% - "
                "implement recruitment acceleration strategies immediately"
            )
        elif enrollment_velocity < self.THRESHOLDS["enrollment_velocity"]["medium"]:
            recommendations.append(
                f"Improve enrollment velocity from {enrollment_velocity:.1f}% - "
                "review recruitment strategies and site performance"
            )
        elif enrollment_velocity < self.THRESHOLDS["enrollment_velocity"]["low"]:
            recommendations.append(
                f"Monitor enrollment velocity at {enrollment_velocity:.1f}%"
            )
        
        # Site activation issues
        if site_activation < self.THRESHOLDS["site_activation_rate"]["high"]:
            recommendations.append(
                f"URGENT: Site activation at {site_activation:.1f}% - "
                "expedite site initiation and activation processes"
            )
        elif site_activation < self.THRESHOLDS["site_activation_rate"]["medium"]:
            recommendations.append(
                f"Improve site activation rate from {site_activation:.1f}% - "
                "address site startup delays"
            )
        elif site_activation < self.THRESHOLDS["site_activation_rate"]["low"]:
            recommendations.append(
                f"Monitor site activation rate at {site_activation:.1f}%"
            )
        
        # Dropout rate issues
        if dropout_rate > self.THRESHOLDS["dropout_rate"]["high"]:
            recommendations.append(
                f"URGENT: Dropout rate at {dropout_rate:.1f}% - "
                "investigate causes and implement retention strategies"
            )
        elif dropout_rate > self.THRESHOLDS["dropout_rate"]["medium"]:
            recommendations.append(
                f"Address {dropout_rate:.1f}% dropout rate - "
                "enhance patient engagement and support"
            )
        elif dropout_rate > self.THRESHOLDS["dropout_rate"]["low"]:
            recommendations.append(
                f"Monitor {dropout_rate:.1f}% dropout rate"
            )
        
        # Enrollment trend
        if enrollment_trend is not None and enrollment_trend < -5.0:
            recommendations.append(
                f"Declining enrollment trend ({enrollment_trend:+.1f}%) - "
                "urgent intervention needed to reverse trend"
            )
        
        if not recommendations:
            recommendations.append(
                "Study stability metrics are excellent - maintain current performance"
            )
        
        return recommendations


__all__ = ["StabilityAgent"]
