"""
Cross-Evidence Agent
====================
Specialized agent for correlating signals across multiple data sources.

Responsibilities:
- Validate consistency between EDC data and SAE reports
- Detect discrepancies between projected and actual visit data
- Cross-reference lab data with clinical events
- Identify data integrity issues across sources

Key Features:
- Multi-source consistency scoring
- EDC-SAE correlation analysis
- Visit projection deviation detection
- Cross-source mismatch identification

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


class CrossEvidenceAgent(BaseAgent):
    """
    Agent specialized in cross-source data validation.
    
    Analyzes:
    - EDC-SAE consistency score
    - Visit projection deviation
    - Data integrity issues count
    - Cross-source mismatch rate
    
    Risk Assessment:
    - CRITICAL: Consistency <70% OR deviation >30% OR integrity issues >10
    - HIGH: Consistency <80% OR deviation >20% OR integrity issues >5
    - MEDIUM: Consistency <90% OR deviation >10% OR integrity issues >2
    - LOW: Consistency ≥90% AND deviation ≤10% AND integrity issues ≤2
    
    Context: Cross-source discrepancies indicate data quality issues 
    that may affect regulatory submissions.
    """
    
    # Required features for analysis
    REQUIRED_FEATURES = [
        "edc_sae_consistency_score",   # Consistency between EDC and SAE data (0-100%)
        "visit_projection_deviation",   # Deviation from expected visit patterns (%)
    ]
    
    # Optional features that enhance analysis
    OPTIONAL_FEATURES = [
        "data_integrity_issues_count",  # Count of identified integrity issues
        "cross_source_mismatch_rate",   # Rate of mismatches between sources
        "lab_clinical_correlation",     # Correlation between lab and clinical data
        "duplicate_records_count",      # Potential duplicate records
    ]
    
    # Risk thresholds
    THRESHOLDS = {
        "edc_sae_consistency_score": {
            "critical": 70.0,   # Below 70% consistency is critical
            "high": 80.0,
            "medium": 90.0,
        },
        "visit_projection_deviation": {
            "critical": 30.0,   # More than 30% deviation is critical
            "high": 20.0,
            "medium": 10.0,
        },
        "data_integrity_issues_count": {
            "critical": 10,
            "high": 5,
            "medium": 2,
        },
        "cross_source_mismatch_rate": {
            "critical": 15.0,   # More than 15% mismatch rate
            "high": 10.0,
            "medium": 5.0,
        },
    }
    
    # Consensus weight
    CONSENSUS_WEIGHT = 1.5
    
    def __init__(
        self,
        min_confidence: float = 0.6,
        abstention_threshold: float = 0.5
    ):
        """
        Initialize Cross-Evidence Agent.
        
        Args:
            min_confidence: Minimum confidence to emit signal
            abstention_threshold: Threshold below which to abstain
        """
        super().__init__(
            agent_type=AgentType.COMPLIANCE,  # Using COMPLIANCE for cross-evidence
            min_confidence=min_confidence,
            abstention_threshold=abstention_threshold
        )
        logger.info("CrossEvidenceAgent initialized")
    
    def analyze(
        self,
        features: Dict[str, Any],
        study_id: str
    ) -> AgentSignal:
        """
        Analyze cross-evidence features and return risk signal.
        
        Args:
            features: Dictionary of engineered features
            study_id: Study identifier for logging
        
        Returns:
            AgentSignal with cross-evidence risk assessment
        """
        logger.debug(f"Analyzing cross-evidence for {study_id}")
        
        # Check if we should abstain
        should_abstain, reason = self._should_abstain(features, self.REQUIRED_FEATURES)
        
        if should_abstain:
            logger.info(f"{study_id}: Cross-evidence agent abstaining - {reason}")
            return self._create_abstention_signal(reason)
        
        # Extract feature values
        consistency_score = features.get("edc_sae_consistency_score", 100.0)
        visit_deviation = features.get("visit_projection_deviation", 0.0)
        integrity_issues = features.get("data_integrity_issues_count", 0)
        mismatch_rate = features.get("cross_source_mismatch_rate", 0.0)
        lab_correlation = features.get("lab_clinical_correlation")
        duplicate_count = features.get("duplicate_records_count", 0)
        
        # Collect evidence
        evidence: List[FeatureEvidence] = []
        
        # EDC-SAE consistency analysis
        if consistency_score < 100:
            severity_level = "CRITICAL" if consistency_score < 70 else "WARNING"
            evidence.append(FeatureEvidence(
                feature_name="edc_sae_consistency_score",
                feature_value=consistency_score,
                threshold=self.THRESHOLDS["edc_sae_consistency_score"]["medium"],
                severity=self._calculate_consistency_severity(consistency_score),
                description=f"{severity_level}: EDC-SAE data consistency at {consistency_score:.1f}%"
            ))
        
        # Visit deviation analysis
        if visit_deviation > 0:
            evidence.append(FeatureEvidence(
                feature_name="visit_projection_deviation",
                feature_value=visit_deviation,
                threshold=self.THRESHOLDS["visit_projection_deviation"]["medium"],
                severity=self._calculate_severity(
                    visit_deviation,
                    self.THRESHOLDS["visit_projection_deviation"]["medium"],
                    max_value=50.0
                ),
                description=f"Visit projection deviation: {visit_deviation:.1f}%"
            ))
        
        # Data integrity issues
        if integrity_issues > 0:
            evidence.append(FeatureEvidence(
                feature_name="data_integrity_issues_count",
                feature_value=integrity_issues,
                threshold=self.THRESHOLDS["data_integrity_issues_count"]["medium"],
                severity=min(integrity_issues / 15, 1.0),
                description=f"{integrity_issues} data integrity issues detected"
            ))
        
        # Mismatch rate analysis
        if mismatch_rate > 0:
            evidence.append(FeatureEvidence(
                feature_name="cross_source_mismatch_rate",
                feature_value=mismatch_rate,
                threshold=self.THRESHOLDS["cross_source_mismatch_rate"]["medium"],
                severity=self._calculate_severity(
                    mismatch_rate,
                    self.THRESHOLDS["cross_source_mismatch_rate"]["medium"],
                    max_value=25.0
                ),
                description=f"Cross-source mismatch rate: {mismatch_rate:.1f}%"
            ))
        
        # Duplicate records
        if duplicate_count > 0:
            evidence.append(FeatureEvidence(
                feature_name="duplicate_records_count",
                feature_value=duplicate_count,
                threshold=1,
                severity=min(duplicate_count / 20, 1.0),
                description=f"{duplicate_count} potential duplicate records"
            ))
        
        # Determine overall risk level
        risk_level = self._assess_overall_risk(
            consistency_score, visit_deviation, integrity_issues, mismatch_rate
        )
        
        # Calculate confidence
        confidence = self._calculate_confidence(features)
        
        # Generate recommended actions
        actions = self._generate_recommendations(
            risk_level, consistency_score, visit_deviation, 
            integrity_issues, mismatch_rate, duplicate_count
        )
        
        logger.info(
            f"{study_id}: Cross-evidence analysis complete - "
            f"risk={risk_level.value}, confidence={confidence:.2f}, "
            f"consistency={consistency_score:.1f}%, deviation={visit_deviation:.1f}%"
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
        """Calculate confidence based on data availability."""
        required_available = sum(
            1 for f in self.REQUIRED_FEATURES 
            if f in features and features[f] is not None
        )
        base_confidence = required_available / len(self.REQUIRED_FEATURES)
        
        optional_available = sum(
            1 for f in self.OPTIONAL_FEATURES 
            if f in features and features[f] is not None
        )
        optional_bonus = (optional_available / len(self.OPTIONAL_FEATURES)) * 0.2
        
        return min(base_confidence + optional_bonus, 1.0)
    
    def _assess_overall_risk(
        self,
        consistency_score: float,
        visit_deviation: float,
        integrity_issues: int,
        mismatch_rate: float
    ) -> RiskSignal:
        """Assess overall cross-evidence risk level."""
        risk_scores = []
        
        # Consistency risk (inverted - lower is worse)
        if consistency_score <= self.THRESHOLDS["edc_sae_consistency_score"]["critical"]:
            risk_scores.append(4)
        elif consistency_score <= self.THRESHOLDS["edc_sae_consistency_score"]["high"]:
            risk_scores.append(3)
        elif consistency_score <= self.THRESHOLDS["edc_sae_consistency_score"]["medium"]:
            risk_scores.append(2)
        else:
            risk_scores.append(1)
        
        # Visit deviation risk
        if visit_deviation >= self.THRESHOLDS["visit_projection_deviation"]["critical"]:
            risk_scores.append(4)
        elif visit_deviation >= self.THRESHOLDS["visit_projection_deviation"]["high"]:
            risk_scores.append(3)
        elif visit_deviation >= self.THRESHOLDS["visit_projection_deviation"]["medium"]:
            risk_scores.append(2)
        else:
            risk_scores.append(1)
        
        # Integrity issues risk
        if integrity_issues >= self.THRESHOLDS["data_integrity_issues_count"]["critical"]:
            risk_scores.append(4)
        elif integrity_issues >= self.THRESHOLDS["data_integrity_issues_count"]["high"]:
            risk_scores.append(3)
        elif integrity_issues >= self.THRESHOLDS["data_integrity_issues_count"]["medium"]:
            risk_scores.append(2)
        else:
            risk_scores.append(1)
        
        # Mismatch rate risk
        if mismatch_rate >= self.THRESHOLDS["cross_source_mismatch_rate"]["critical"]:
            risk_scores.append(4)
        elif mismatch_rate >= self.THRESHOLDS["cross_source_mismatch_rate"]["high"]:
            risk_scores.append(3)
        elif mismatch_rate >= self.THRESHOLDS["cross_source_mismatch_rate"]["medium"]:
            risk_scores.append(2)
        else:
            risk_scores.append(1)
        
        max_risk = max(risk_scores) if risk_scores else 1
        
        return {
            4: RiskSignal.CRITICAL,
            3: RiskSignal.HIGH,
            2: RiskSignal.MEDIUM,
            1: RiskSignal.LOW,
        }.get(max_risk, RiskSignal.LOW)
    
    def _calculate_consistency_severity(self, score: float) -> float:
        """Calculate severity for consistency score (inverted)."""
        if score >= 90:
            return 0.0
        return (90 - score) / 90
    
    def _generate_recommendations(
        self,
        risk_level: RiskSignal,
        consistency_score: float,
        visit_deviation: float,
        integrity_issues: int,
        mismatch_rate: float,
        duplicate_count: int
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        
        # Critical consistency issues
        if consistency_score < self.THRESHOLDS["edc_sae_consistency_score"]["high"]:
            recommendations.append(
                f"URGENT: EDC-SAE consistency at {consistency_score:.1f}% - "
                "review data reconciliation process and correct discrepancies"
            )
        elif consistency_score < self.THRESHOLDS["edc_sae_consistency_score"]["medium"]:
            recommendations.append(
                f"EDC-SAE consistency at {consistency_score:.1f}% - "
                "schedule data reconciliation review"
            )
        
        # Visit deviation
        if visit_deviation >= self.THRESHOLDS["visit_projection_deviation"]["high"]:
            recommendations.append(
                f"Visit deviation at {visit_deviation:.1f}% - "
                "investigate scheduling patterns and protocol adherence"
            )
        
        # Integrity issues
        if integrity_issues >= self.THRESHOLDS["data_integrity_issues_count"]["medium"]:
            recommendations.append(
                f"{integrity_issues} data integrity issues - "
                "prioritize resolution of cross-source discrepancies"
            )
        
        # Mismatch rate
        if mismatch_rate >= self.THRESHOLDS["cross_source_mismatch_rate"]["medium"]:
            recommendations.append(
                f"Cross-source mismatch rate at {mismatch_rate:.1f}% - "
                "review data integration processes"
            )
        
        # Duplicate records
        if duplicate_count > 0:
            recommendations.append(
                f"{duplicate_count} potential duplicate records - "
                "verify and merge or remove duplicates"
            )
        
        if not recommendations:
            recommendations.append("Cross-source data validation passed - data integrity confirmed")
        
        return recommendations


__all__ = ["CrossEvidenceAgent"]
