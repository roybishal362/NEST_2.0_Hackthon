"""
EDC Quality Agent
=================
Specialized agent for detecting EDC data quality issues and operational problems.

Responsibilities:
- Monitor form completion rates
- Track data entry errors
- Identify missing required fields
- Assess EDC operational quality

Key Features:
- Form completion rate analysis
- Data entry error detection
- Required field validation
- EDC quality scoring

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


class EDCQualityAgent(BaseAgent):
    """
    Agent specialized in detecting EDC quality and operational issues.
    
    Analyzes:
    - Form completion rate
    - Data entry errors
    - Missing required fields
    - EDC system quality
    
    Risk Assessment:
    - CRITICAL: <80% completion or >10 errors
    - HIGH: <90% completion or >5 errors
    - MEDIUM: <95% completion or >2 errors
    - LOW: ≥95% completion and ≤2 errors
    """
    
    # Required features for analysis
    REQUIRED_FEATURES = [
        "form_completion_rate",
        "data_entry_errors",
    ]
    
    # Optional features that enhance analysis
    OPTIONAL_FEATURES = [
        "missing_required_fields",
        "edc_system_uptime",
        "data_validation_failures",
    ]
    
    # Risk thresholds
    THRESHOLDS = {
        "form_completion_rate": {
            "critical": 80.0,  # Below this is critical
            "high": 90.0,
            "medium": 95.0,
        },
        "data_entry_errors": {
            "critical": 10.0,
            "high": 5.0,
            "medium": 2.0,
        },
        "missing_required_fields": {
            "critical": 20.0,
            "high": 10.0,
            "medium": 5.0,
        },
    }
    
    def __init__(
        self,
        min_confidence: float = 0.6,
        abstention_threshold: float = 0.5
    ):
        """
        Initialize EDC Quality Agent.
        
        Args:
            min_confidence: Minimum confidence to emit signal
            abstention_threshold: Threshold below which to abstain
        """
        super().__init__(
            agent_type=AgentType.OPERATIONS,
            min_confidence=min_confidence,
            abstention_threshold=abstention_threshold
        )
        logger.info("EDCQualityAgent initialized")
    
    def analyze(
        self,
        features: Dict[str, Any],
        study_id: str
    ) -> AgentSignal:
        """
        Analyze EDC quality features and return risk signal.
        
        Args:
            features: Dictionary of engineered features
            study_id: Study identifier for logging
        
        Returns:
            AgentSignal with EDC quality risk assessment
        """
        logger.debug(f"Analyzing EDC quality for {study_id}")
        
        # Check if we should abstain
        should_abstain, reason = self._should_abstain(features, self.REQUIRED_FEATURES)
        
        if should_abstain:
            logger.info(f"{study_id}: EDC Quality agent abstaining - {reason}")
            return self._create_abstention_signal(reason)
        
        # Extract feature values (handle None properly)
        form_completion = features.get("form_completion_rate")
        
        data_errors = features.get("data_entry_errors")
        if data_errors is None:
            data_errors = 0
        
        missing_fields = features.get("missing_required_fields")
        if missing_fields is None:
            missing_fields = 0
        
        system_uptime = features.get("edc_system_uptime")
        
        validation_failures = features.get("data_validation_failures")
        if validation_failures is None:
            validation_failures = 0
        
        # Collect evidence
        evidence: List[FeatureEvidence] = []
        
        # Analyze form completion rate (only if available)
        if form_completion is not None and form_completion < 100:
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
        
        # Analyze data entry errors
        if data_errors > 0:
            evidence.append(FeatureEvidence(
                feature_name="data_entry_errors",
                feature_value=data_errors,
                threshold=self.THRESHOLDS["data_entry_errors"]["medium"],
                severity=self._calculate_severity(
                    data_errors,
                    self.THRESHOLDS["data_entry_errors"]["medium"],
                    max_value=50.0
                ),
                description=f"Data entry errors: {data_errors}"
            ))
        
        # Analyze missing required fields
        if missing_fields > 0:
            evidence.append(FeatureEvidence(
                feature_name="missing_required_fields",
                feature_value=missing_fields,
                threshold=self.THRESHOLDS["missing_required_fields"]["medium"],
                severity=self._calculate_severity(
                    missing_fields,
                    self.THRESHOLDS["missing_required_fields"]["medium"],
                    max_value=100.0
                ),
                description=f"Missing required fields: {missing_fields}"
            ))
        
        # Analyze system uptime (if available)
        if system_uptime is not None and system_uptime < 99.0:
            evidence.append(FeatureEvidence(
                feature_name="edc_system_uptime",
                feature_value=system_uptime,
                threshold=99.0,
                severity=1.0 - (system_uptime / 100.0),
                description=f"EDC system uptime: {system_uptime:.1f}%"
            ))
        
        # Analyze validation failures (if available)
        if validation_failures > 0:
            evidence.append(FeatureEvidence(
                feature_name="data_validation_failures",
                feature_value=validation_failures,
                threshold=10.0,
                severity=min(validation_failures / 50.0, 1.0),
                description=f"{validation_failures} data validation failures"
            ))
        
        # Determine overall risk level
        risk_level = self._assess_overall_risk(
            form_completion, data_errors, missing_fields
        )
        
        # Calculate confidence
        confidence = self._calculate_confidence(features)
        
        # Generate recommended actions
        actions = self._generate_recommendations(
            risk_level, form_completion, data_errors, missing_fields, validation_failures
        )
        
        logger.info(
            f"{study_id}: EDC quality analysis complete - "
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
        form_completion: Optional[float],
        data_errors: int,
        missing_fields: int
    ) -> RiskSignal:
        """
        Assess overall risk level from all EDC quality metrics.
        
        Uses worst-case assessment across all metrics.
        """
        risk_scores = []
        
        # Form completion risk (inverted - lower is worse) - only if available
        if form_completion is not None:
            if form_completion <= self.THRESHOLDS["form_completion_rate"]["critical"]:
                risk_scores.append(4)  # CRITICAL
            elif form_completion <= self.THRESHOLDS["form_completion_rate"]["high"]:
                risk_scores.append(3)  # HIGH
            elif form_completion <= self.THRESHOLDS["form_completion_rate"]["medium"]:
                risk_scores.append(2)  # MEDIUM
            else:
                risk_scores.append(1)  # LOW
        
        # Data entry errors risk
        if data_errors >= self.THRESHOLDS["data_entry_errors"]["critical"]:
            risk_scores.append(4)
        elif data_errors >= self.THRESHOLDS["data_entry_errors"]["high"]:
            risk_scores.append(3)
        elif data_errors >= self.THRESHOLDS["data_entry_errors"]["medium"]:
            risk_scores.append(2)
        else:
            risk_scores.append(1)
        
        # Missing required fields risk
        if missing_fields >= self.THRESHOLDS["missing_required_fields"]["critical"]:
            risk_scores.append(4)
        elif missing_fields >= self.THRESHOLDS["missing_required_fields"]["high"]:
            risk_scores.append(3)
        elif missing_fields >= self.THRESHOLDS["missing_required_fields"]["medium"]:
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
        form_completion: Optional[float],
        data_errors: int,
        missing_fields: int,
        validation_failures: int
    ) -> List[str]:
        """Generate actionable recommendations based on findings."""
        recommendations = []
        
        # Form completion issues (only if available)
        if form_completion is not None:
            if form_completion < self.THRESHOLDS["form_completion_rate"]["critical"]:
                recommendations.append(
                    f"URGENT: Form completion at {form_completion:.1f}% - "
                    "immediate EDC data entry support needed"
                )
            elif form_completion < self.THRESHOLDS["form_completion_rate"]["high"]:
                recommendations.append(
                    f"Improve form completion rate from {form_completion:.1f}% - "
                    "allocate additional data entry resources"
                )
            elif form_completion < self.THRESHOLDS["form_completion_rate"]["medium"]:
                recommendations.append(
                    f"Monitor form completion rate at {form_completion:.1f}%"
                )
        
        # Data entry errors
        if data_errors >= self.THRESHOLDS["data_entry_errors"]["critical"]:
            recommendations.append(
                f"URGENT: {data_errors} data entry errors detected - "
                "review data entry procedures and provide training"
            )
        elif data_errors >= self.THRESHOLDS["data_entry_errors"]["high"]:
            recommendations.append(
                f"Address {data_errors} data entry errors - "
                "implement additional quality checks"
            )
        elif data_errors >= self.THRESHOLDS["data_entry_errors"]["medium"]:
            recommendations.append(
                f"Monitor {data_errors} data entry errors"
            )
        
        # Missing required fields
        if missing_fields >= self.THRESHOLDS["missing_required_fields"]["critical"]:
            recommendations.append(
                f"URGENT: {missing_fields} missing required fields - "
                "complete critical data immediately"
            )
        elif missing_fields >= self.THRESHOLDS["missing_required_fields"]["high"]:
            recommendations.append(
                f"Complete {missing_fields} missing required fields"
            )
        elif missing_fields >= self.THRESHOLDS["missing_required_fields"]["medium"]:
            recommendations.append(
                f"Review {missing_fields} missing required fields"
            )
        
        # Validation failures
        if validation_failures > 20:
            recommendations.append(
                f"Resolve {validation_failures} data validation failures to improve quality"
            )
        
        if not recommendations:
            recommendations.append("EDC quality metrics within acceptable ranges")
        
        return recommendations


__all__ = ["EDCQualityAgent"]
