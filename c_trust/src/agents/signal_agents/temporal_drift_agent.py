"""
Temporal Drift Agent
====================
Specialized agent for detecting temporal issues, data entry lag, and timeline drift.

Responsibilities:
- Monitor data entry lag and trends
- Track overdue visits
- Identify temporal drift patterns
- Assess timeline compliance

Key Features:
- Average data entry lag analysis
- Lag trend detection
- Overdue visit monitoring
- Timeline drift assessment

**Validates: Requirements 2.3**
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


class TemporalDriftAgent(BaseAgent):
    """
    Agent specialized in detecting temporal drift and timeline issues.
    
    Analyzes:
    - Average data entry lag (days)
    - Lag trend (increasing/decreasing)
    - Overdue visits count
    - Timeline compliance
    
    Risk Assessment:
    - CRITICAL: >30 days lag or >20 overdue visits
    - HIGH: >15 days lag or >10 overdue visits
    - MEDIUM: >7 days lag or >5 overdue visits
    - LOW: ≤7 days lag and ≤5 overdue visits
    """
    
    # Required features for analysis
    # Note: Made more lenient - can analyze with partial data
    REQUIRED_FEATURES = [
        "avg_data_entry_lag_days",  # Must have at least lag data
    ]
    
    # Preferred features that enhance analysis
    PREFERRED_FEATURES = [
        "overdue_visits_count",
    ]
    
    # Optional features that enhance analysis
    OPTIONAL_FEATURES = [
        "lag_trend",
        "max_data_entry_lag_days",
        "visit_completion_rate",
    ]
    
    # Risk thresholds
    THRESHOLDS = {
        "avg_data_entry_lag_days": {
            "critical": 30.0,
            "high": 15.0,
            "medium": 7.0,
        },
        "overdue_visits_count": {
            "critical": 20,
            "high": 10,
            "medium": 5,
        },
        "max_data_entry_lag_days": {
            "critical": 60.0,
            "high": 45.0,
            "medium": 30.0,
        },
    }
    
    def __init__(
        self,
        min_confidence: float = 0.6,
        abstention_threshold: float = 0.5
    ):
        """
        Initialize Temporal Drift Agent.
        
        Args:
            min_confidence: Minimum confidence to emit signal
            abstention_threshold: Threshold below which to abstain
        """
        super().__init__(
            agent_type=AgentType.TIMELINE,
            min_confidence=min_confidence,
            abstention_threshold=abstention_threshold
        )
        logger.info("TemporalDriftAgent initialized")
    
    def analyze(
        self,
        features: Dict[str, Any],
        study_id: str
    ) -> AgentSignal:
        """
        Analyze temporal features and return risk signal.
        
        Args:
            features: Dictionary of engineered features
            study_id: Study identifier for logging
        
        Returns:
            AgentSignal with temporal drift risk assessment
        """
        logger.debug(f"Analyzing temporal drift for {study_id}")
        
        # Extract feature values - handle None/missing gracefully
        # Even if features are NULL, we can still analyze with defaults
        avg_lag = features.get("avg_data_entry_lag_days")
        if avg_lag is None:
            avg_lag = 0.0
        
        # If overdue_visits_count is missing, assume 0 (no overdue data available)
        overdue_visits = features.get("overdue_visits_count", 0)
        if overdue_visits is None:
            overdue_visits = 0
        
        lag_trend = features.get("lag_trend")
        max_lag = features.get("max_data_entry_lag_days")
        visit_completion = features.get("visit_completion_rate")
        
        # Check if we have ANY data to analyze
        has_any_data = (
            avg_lag is not None or 
            overdue_visits is not None or
            lag_trend is not None or
            max_lag is not None
        )
        
        if not has_any_data:
            # Truly no data available - abstain
            reason = "No temporal drift data available (all features are None)"
            logger.info(f"{study_id}: Temporal drift agent abstaining - {reason}")
            return self._create_abstention_signal(reason)
        
        # Collect evidence
        evidence: List[FeatureEvidence] = []
        
        # Analyze average data entry lag
        if avg_lag > 0:
            evidence.append(FeatureEvidence(
                feature_name="avg_data_entry_lag_days",
                feature_value=avg_lag,
                threshold=self.THRESHOLDS["avg_data_entry_lag_days"]["medium"],
                severity=self._calculate_severity(
                    avg_lag,
                    self.THRESHOLDS["avg_data_entry_lag_days"]["medium"],
                    max_value=60.0
                ),
                description=f"Average data entry lag: {avg_lag:.1f} days"
            ))
        
        # Analyze overdue visits
        if overdue_visits > 0:
            evidence.append(FeatureEvidence(
                feature_name="overdue_visits_count",
                feature_value=overdue_visits,
                threshold=self.THRESHOLDS["overdue_visits_count"]["medium"],
                severity=self._calculate_severity(
                    overdue_visits,
                    self.THRESHOLDS["overdue_visits_count"]["medium"],
                    max_value=50.0
                ),
                description=f"{overdue_visits} overdue visits"
            ))
        
        # Analyze lag trend (if available)
        if lag_trend is not None:
            if lag_trend > 0:  # Increasing lag is bad
                evidence.append(FeatureEvidence(
                    feature_name="lag_trend",
                    feature_value=lag_trend,
                    threshold=0.0,
                    severity=min(abs(lag_trend) / 10.0, 1.0),
                    description=f"Data entry lag increasing (trend: {lag_trend:+.1f} days/week)"
                ))
            elif lag_trend < -1.0:  # Improving significantly
                evidence.append(FeatureEvidence(
                    feature_name="lag_trend",
                    feature_value=lag_trend,
                    threshold=0.0,
                    severity=0.0,
                    description=f"Data entry lag improving (trend: {lag_trend:+.1f} days/week)"
                ))
        
        # Analyze maximum lag (if available)
        if max_lag is not None and max_lag > self.THRESHOLDS["max_data_entry_lag_days"]["medium"]:
            evidence.append(FeatureEvidence(
                feature_name="max_data_entry_lag_days",
                feature_value=max_lag,
                threshold=self.THRESHOLDS["max_data_entry_lag_days"]["medium"],
                severity=self._calculate_severity(
                    max_lag,
                    self.THRESHOLDS["max_data_entry_lag_days"]["medium"],
                    max_value=90.0
                ),
                description=f"Maximum data entry lag: {max_lag:.1f} days"
            ))
        
        # Analyze visit completion (if available)
        if visit_completion is not None and visit_completion < 100:
            evidence.append(FeatureEvidence(
                feature_name="visit_completion_rate",
                feature_value=visit_completion,
                threshold=90.0,
                severity=self._calculate_completion_severity(visit_completion, 90.0),
                description=f"Visit completion rate: {visit_completion:.1f}%"
            ))
        
        # Determine overall risk level
        risk_level = self._assess_overall_risk(
            avg_lag, overdue_visits, lag_trend, max_lag
        )
        
        # Calculate confidence
        confidence = self._calculate_confidence(features)
        
        # Generate recommended actions
        actions = self._generate_recommendations(
            risk_level, avg_lag, overdue_visits, lag_trend, max_lag
        )
        
        logger.info(
            f"{study_id}: Temporal drift analysis complete - "
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
        # Count available features (non-None)
        avg_lag_available = features.get("avg_data_entry_lag_days") is not None
        overdue_available = features.get("overdue_visits_count") is not None
        lag_trend_available = features.get("lag_trend") is not None
        max_lag_available = features.get("max_data_entry_lag_days") is not None
        visit_completion_available = features.get("visit_completion_rate") is not None
        
        # Base confidence from having any data
        available_count = sum([
            avg_lag_available, overdue_available, lag_trend_available, 
            max_lag_available, visit_completion_available
        ])
        total_features = 5
        
        if available_count == 0:
            return 0.0
        
        # Calculate confidence based on data availability
        base_confidence = available_count / total_features
        
        # Boost confidence if we have the most critical features
        if avg_lag_available and overdue_available:
            base_confidence = min(base_confidence + 0.2, 1.0)
        
        return base_confidence
    
    def _assess_overall_risk(
        self,
        avg_lag: float,
        overdue_visits: int,
        lag_trend: Optional[float],
        max_lag: Optional[float]
    ) -> RiskSignal:
        """
        Assess overall risk level from all temporal metrics.
        
        Uses worst-case assessment across all metrics.
        """
        risk_scores = []
        
        # Average lag risk
        if avg_lag >= self.THRESHOLDS["avg_data_entry_lag_days"]["critical"]:
            risk_scores.append(4)  # CRITICAL
        elif avg_lag >= self.THRESHOLDS["avg_data_entry_lag_days"]["high"]:
            risk_scores.append(3)  # HIGH
        elif avg_lag >= self.THRESHOLDS["avg_data_entry_lag_days"]["medium"]:
            risk_scores.append(2)  # MEDIUM
        else:
            risk_scores.append(1)  # LOW
        
        # Overdue visits risk
        if overdue_visits >= self.THRESHOLDS["overdue_visits_count"]["critical"]:
            risk_scores.append(4)
        elif overdue_visits >= self.THRESHOLDS["overdue_visits_count"]["high"]:
            risk_scores.append(3)
        elif overdue_visits >= self.THRESHOLDS["overdue_visits_count"]["medium"]:
            risk_scores.append(2)
        else:
            risk_scores.append(1)
        
        # Lag trend risk (if available)
        if lag_trend is not None and lag_trend > 0:
            # Increasing lag is concerning
            if lag_trend > 5.0:  # >5 days/week increase
                risk_scores.append(4)
            elif lag_trend > 2.0:  # >2 days/week increase
                risk_scores.append(3)
            elif lag_trend > 0.5:  # >0.5 days/week increase
                risk_scores.append(2)
        
        # Maximum lag risk (if available)
        if max_lag is not None:
            if max_lag >= self.THRESHOLDS["max_data_entry_lag_days"]["critical"]:
                risk_scores.append(4)
            elif max_lag >= self.THRESHOLDS["max_data_entry_lag_days"]["high"]:
                risk_scores.append(3)
            elif max_lag >= self.THRESHOLDS["max_data_entry_lag_days"]["medium"]:
                risk_scores.append(2)
        
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
        avg_lag: float,
        overdue_visits: int,
        lag_trend: Optional[float],
        max_lag: Optional[float]
    ) -> List[str]:
        """Generate actionable recommendations based on findings."""
        recommendations = []
        
        # Average lag issues
        if avg_lag >= self.THRESHOLDS["avg_data_entry_lag_days"]["critical"]:
            recommendations.append(
                f"URGENT: {avg_lag:.0f}-day average data entry lag - "
                "expedite data entry process immediately"
            )
        elif avg_lag >= self.THRESHOLDS["avg_data_entry_lag_days"]["high"]:
            recommendations.append(
                f"Address {avg_lag:.0f}-day data entry lag - "
                "allocate additional data entry resources"
            )
        elif avg_lag >= self.THRESHOLDS["avg_data_entry_lag_days"]["medium"]:
            recommendations.append(
                f"Monitor {avg_lag:.0f}-day data entry lag - "
                "consider process improvements"
            )
        
        # Overdue visits issues
        if overdue_visits >= self.THRESHOLDS["overdue_visits_count"]["critical"]:
            recommendations.append(
                f"URGENT: {overdue_visits} overdue visits - "
                "immediate action required to prevent timeline delays"
            )
        elif overdue_visits >= self.THRESHOLDS["overdue_visits_count"]["high"]:
            recommendations.append(
                f"Address {overdue_visits} overdue visits - "
                "review visit scheduling and completion process"
            )
        elif overdue_visits >= self.THRESHOLDS["overdue_visits_count"]["medium"]:
            recommendations.append(
                f"Monitor {overdue_visits} overdue visits"
            )
        
        # Lag trend issues
        if lag_trend is not None and lag_trend > 0.5:
            recommendations.append(
                f"Data entry lag increasing by {lag_trend:.1f} days/week - "
                "investigate root cause and implement corrective actions"
            )
        
        # Maximum lag issues
        if max_lag is not None and max_lag >= self.THRESHOLDS["max_data_entry_lag_days"]["high"]:
            recommendations.append(
                f"Maximum lag of {max_lag:.0f} days detected - "
                "identify and address outlier cases"
            )
        
        if not recommendations:
            recommendations.append("Temporal metrics within acceptable ranges")
        
        return recommendations


__all__ = ["TemporalDriftAgent"]
