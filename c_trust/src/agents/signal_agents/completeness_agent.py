"""
Data Completeness Agent
=======================
Specialized agent for detecting missing data, incomplete forms, and data gaps.

Responsibilities:
- Detect missing visits and incomplete forms
- Calculate completeness scores and aging metrics
- Identify data quality gaps at study/site/subject levels

Key Features:
- Missing pages percentage analysis
- Form completion rate tracking
- Visit completion monitoring
- Data entry lag detection

**Validates: Requirements 2.1**
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


class DataCompletenessAgent(BaseAgent):
    """
    Agent specialized in detecting missing data and completeness issues.
    
    Analyzes:
    - Missing CRF pages percentage
    - Form completion rates
    - Visit completion rates
    - Data entry lag
    
    Risk Assessment:
    - CRITICAL: >40% missing data or <50% completion
    - HIGH: >25% missing data or <65% completion
    - MEDIUM: >10% missing data or <80% completion
    - LOW: ≤10% missing data and ≥80% completion
    """
    
    # Required features for analysis
    # CRITICAL FIX: Only form_completion_rate is truly required
    # missing_pages_pct is now optional (calculated from EDC data when available)
    REQUIRED_FEATURES = [
        "form_completion_rate",  # Always available from EDC Metrics
    ]
    
    # Optional features that enhance analysis
    OPTIONAL_FEATURES = [
        "missing_pages_pct",  # Now optional (but preferred when available)
        "visit_completion_rate",
        "data_entry_lag_days",
        "_visit_gap_count",
    ]
    
    # Risk thresholds
    THRESHOLDS = {
        "missing_pages_pct": {
            "critical": 40.0,
            "high": 25.0,
            "medium": 10.0,
        },
        "form_completion_rate": {
            "critical": 50.0,  # Below this is critical
            "high": 65.0,
            "medium": 80.0,
        },
        "visit_completion_rate": {
            "critical": 50.0,
            "high": 65.0,
            "medium": 80.0,
        },
        "data_entry_lag_days": {
            "critical": 14.0,
            "high": 7.0,
            "medium": 3.0,
        },
    }
    
    def __init__(
        self,
        min_confidence: float = 0.6,
        abstention_threshold: float = 0.5
    ):
        """
        Initialize Data Completeness Agent.
        
        Args:
            min_confidence: Minimum confidence to emit signal
            abstention_threshold: Threshold below which to abstain
        """
        super().__init__(
            agent_type=AgentType.COMPLETENESS,
            min_confidence=min_confidence,
            abstention_threshold=abstention_threshold
        )
        logger.info("DataCompletenessAgent initialized")
    
    def analyze(
        self,
        features: Dict[str, Any],
        study_id: str
    ) -> AgentSignal:
        """
        Analyze completeness features and return risk signal.
        
        Args:
            features: Dictionary of engineered features
            study_id: Study identifier for logging
        
        Returns:
            AgentSignal with completeness risk assessment
        """
        logger.debug(f"Analyzing completeness for {study_id}")
        
        # Check if we should abstain
        should_abstain, reason = self._should_abstain(features, self.REQUIRED_FEATURES)
        
        if should_abstain:
            logger.info(f"{study_id}: Completeness agent abstaining - {reason}")
            return self._create_abstention_signal(reason)
        
        # Extract feature values
        missing_pct = features.get("missing_pages_pct", 0.0)
        form_completion = features.get("form_completion_rate", 100.0)
        visit_completion = features.get("visit_completion_rate")
        data_entry_lag = features.get("data_entry_lag_days")
        visit_gap_count = features.get("_visit_gap_count", 0)
        
        # Collect evidence
        evidence: List[FeatureEvidence] = []
        
        # Analyze missing pages
        if missing_pct > 0:
            evidence.append(FeatureEvidence(
                feature_name="missing_pages_pct",
                feature_value=missing_pct,
                threshold=self.THRESHOLDS["missing_pages_pct"]["medium"],
                severity=self._calculate_severity(
                    missing_pct,
                    self.THRESHOLDS["missing_pages_pct"]["medium"],
                    max_value=100.0
                ),
                description=f"Missing {missing_pct:.1f}% of CRF pages"
            ))
        
        # Analyze form completion
        if form_completion < 100:
            evidence.append(FeatureEvidence(
                feature_name="form_completion_rate",
                feature_value=form_completion,
                threshold=self.THRESHOLDS["form_completion_rate"]["medium"],
                severity=self._calculate_completion_severity(
                    form_completion,
                    self.THRESHOLDS["form_completion_rate"]["medium"]
                ),
                description=f"Form completion rate: {form_completion:.1f}%"
            ))
        
        # Analyze visit completion (if available)
        if visit_completion is not None and visit_completion < 100:
            evidence.append(FeatureEvidence(
                feature_name="visit_completion_rate",
                feature_value=visit_completion,
                threshold=self.THRESHOLDS["visit_completion_rate"]["medium"],
                severity=self._calculate_completion_severity(
                    visit_completion,
                    self.THRESHOLDS["visit_completion_rate"]["medium"]
                ),
                description=f"Visit completion rate: {visit_completion:.1f}% ({visit_gap_count} gaps)"
            ))
        
        # Analyze data entry lag (if available)
        if data_entry_lag is not None and data_entry_lag > 0:
            evidence.append(FeatureEvidence(
                feature_name="data_entry_lag_days",
                feature_value=data_entry_lag,
                threshold=self.THRESHOLDS["data_entry_lag_days"]["medium"],
                severity=self._calculate_severity(
                    data_entry_lag,
                    self.THRESHOLDS["data_entry_lag_days"]["medium"],
                    max_value=30.0
                ),
                description=f"Average data entry lag: {data_entry_lag:.1f} days"
            ))
        
        # Determine overall risk level
        risk_level = self._assess_overall_risk(
            missing_pct, form_completion, visit_completion, data_entry_lag
        )
        
        # Calculate confidence
        confidence = self._calculate_confidence(features)
        
        # Generate recommended actions
        actions = self._generate_recommendations(
            risk_level, missing_pct, form_completion, visit_completion, data_entry_lag
        )
        
        logger.info(
            f"{study_id}: Completeness analysis complete - "
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
        missing_pct: float,
        form_completion: float,
        visit_completion: Optional[float],
        data_entry_lag: Optional[float]
    ) -> RiskSignal:
        """
        Assess overall risk level from all completeness metrics.
        
        Uses worst-case assessment across all metrics.
        """
        risk_scores = []
        
        # Missing pages risk
        if missing_pct >= self.THRESHOLDS["missing_pages_pct"]["critical"]:
            risk_scores.append(4)  # CRITICAL
        elif missing_pct >= self.THRESHOLDS["missing_pages_pct"]["high"]:
            risk_scores.append(3)  # HIGH
        elif missing_pct >= self.THRESHOLDS["missing_pages_pct"]["medium"]:
            risk_scores.append(2)  # MEDIUM
        else:
            risk_scores.append(1)  # LOW
        
        # Form completion risk (inverted - lower is worse)
        if form_completion <= self.THRESHOLDS["form_completion_rate"]["critical"]:
            risk_scores.append(4)
        elif form_completion <= self.THRESHOLDS["form_completion_rate"]["high"]:
            risk_scores.append(3)
        elif form_completion <= self.THRESHOLDS["form_completion_rate"]["medium"]:
            risk_scores.append(2)
        else:
            risk_scores.append(1)
        
        # Visit completion risk (if available)
        if visit_completion is not None:
            if visit_completion <= self.THRESHOLDS["visit_completion_rate"]["critical"]:
                risk_scores.append(4)
            elif visit_completion <= self.THRESHOLDS["visit_completion_rate"]["high"]:
                risk_scores.append(3)
            elif visit_completion <= self.THRESHOLDS["visit_completion_rate"]["medium"]:
                risk_scores.append(2)
            else:
                risk_scores.append(1)
        
        # Data entry lag risk (if available)
        if data_entry_lag is not None:
            if data_entry_lag >= self.THRESHOLDS["data_entry_lag_days"]["critical"]:
                risk_scores.append(4)
            elif data_entry_lag >= self.THRESHOLDS["data_entry_lag_days"]["high"]:
                risk_scores.append(3)
            elif data_entry_lag >= self.THRESHOLDS["data_entry_lag_days"]["medium"]:
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
        missing_pct: float,
        form_completion: float,
        visit_completion: Optional[float],
        data_entry_lag: Optional[float]
    ) -> List[str]:
        """Generate actionable recommendations based on findings."""
        recommendations = []
        
        if missing_pct > self.THRESHOLDS["missing_pages_pct"]["high"]:
            recommendations.append(
                f"URGENT: Address {missing_pct:.1f}% missing CRF pages - "
                "prioritize data entry for critical forms"
            )
        elif missing_pct > self.THRESHOLDS["missing_pages_pct"]["medium"]:
            recommendations.append(
                f"Review and complete {missing_pct:.1f}% missing CRF pages"
            )
        
        if form_completion < self.THRESHOLDS["form_completion_rate"]["high"]:
            recommendations.append(
                f"URGENT: Form completion at {form_completion:.1f}% - "
                "immediate data entry support needed"
            )
        elif form_completion < self.THRESHOLDS["form_completion_rate"]["medium"]:
            recommendations.append(
                f"Improve form completion rate from {form_completion:.1f}%"
            )
        
        if visit_completion is not None and visit_completion < self.THRESHOLDS["visit_completion_rate"]["medium"]:
            recommendations.append(
                f"Visit completion at {visit_completion:.1f}% - "
                "review visit scheduling and data capture"
            )
        
        if data_entry_lag is not None and data_entry_lag > self.THRESHOLDS["data_entry_lag_days"]["medium"]:
            recommendations.append(
                f"Data entry lag of {data_entry_lag:.1f} days - "
                "expedite data entry process"
            )
        
        if not recommendations:
            recommendations.append("Completeness metrics within acceptable ranges")
        
        return recommendations


__all__ = ["DataCompletenessAgent"]
