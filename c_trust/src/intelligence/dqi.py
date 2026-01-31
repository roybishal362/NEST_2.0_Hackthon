"""
C-TRUST DQI (Data Quality Index) Engine - Component 6
========================================
Data Quality Index calculation engine.

DQI Dimensions (from settings.yaml):
1. Safety (35%) - SAE metrics, safety signals
2. Compliance (25%) - Protocol adherence, regulatory compliance
3. Completeness (25%) - Missing data, visits, forms
4. Operations (15%) - Query aging, data entry lag

DQI Score: 0-100 composite score indicating data quality readiness.

Thresholds:
- Critical: 0-50 (Red)
- High Risk: 50-70 (Amber)
- At Risk: 70-85 (Yellow)
- On Track: 85-100 (Green)

Production Features:
- Deterministic calculation
- Dimension-level breakdown
- Temporal trending
- Threshold-based alerting
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from src.core import clamp, get_logger, yaml_config
from src.data.models import RiskLevel

logger = get_logger(__name__)


# ========================================
# DQI ENUMERATIONS
# ========================================

class DQIDimension(str, Enum):
    """DQI calculation dimensions"""
    SAFETY = "safety"
    COMPLIANCE = "compliance"
    COMPLETENESS = "completeness"
    OPERATIONS = "operations"


# ========================================
# DQI DATA STRUCTURES
# ========================================

@dataclass
class DimensionScore:
    """
    Score for a single DQI dimension.
    
    Attributes:
        dimension: Which dimension
        raw_score: Calculated score (0-100)
        weight: Weight of this dimension
        weighted_score: raw_score * weight
        contributing_features: Features that contributed
    """
    dimension: DQIDimension
    raw_score: float
    weight: float
    weighted_score: float
    contributing_features: Dict[str, float]
    
    def __post_init__(self):
        """Validate scores are in valid range"""
        self.raw_score = clamp(self.raw_score, 0, 100)
        self.weighted_score = clamp(self.weighted_score, 0, 100)


@dataclass
class DQIScore:
    """
    Complete DQI score with dimension breakdown.
    
    Attributes:
        overall_score: Composite DQI score (0-100)
        dimension_scores: Scores for each dimension
        risk_level: Risk classification
        threshold_met: Which threshold tier
        timestamp: Calculation timestamp
    """
    overall_score: float
    dimension_scores: List[DimensionScore]
    risk_level: RiskLevel
    threshold_met: str
    timestamp: datetime
    
    # Metadata
    study_id: Optional[str] = None
    features_used: int = 0
    
    def __post_init__(self):
        """Validate overall score"""
        self.overall_score = clamp(self.overall_score, 0, 100)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "overall_score": round(self.overall_score, 2),
            "risk_level": self.risk_level.value,
            "threshold_met": self.threshold_met,
            "timestamp": self.timestamp.isoformat(),
            "study_id": self.study_id,
            "dimension_scores": [
                {
                    "dimension": ds.dimension.value,
                    "raw_score": round(ds.raw_score, 2),
                    "weight": ds.weight,
                    "weighted_score": round(ds.weighted_score, 2),
                    "contributing_features": ds.contributing_features
                }
                for ds in self.dimension_scores
            ],
            "features_used": self.features_used
        }


# ========================================
# DQI ENGINE
# ========================================

class DQIEngine:
    """
    Data Quality Index calculation engine.
    
    Calculates composite DQI score from engineered features using
    weighted dimensional scoring.
    """
    
    def __init__(self):
        """Initialize DQI engine with configuration"""
        dqi_config = yaml_config.dqi_config
        
        # Load dimension weights
        dimensions_config = dqi_config.get("dimensions", {})
        self.dimension_weights = {
            DQIDimension.SAFETY: dimensions_config.get("safety", {}).get("weight", 0.35),
            DQIDimension.COMPLIANCE: dimensions_config.get("compliance", {}).get("weight", 0.25),
            DQIDimension.COMPLETENESS: dimensions_config.get("completeness", {}).get("weight", 0.25),
            DQIDimension.OPERATIONS: dimensions_config.get("operations", {}).get("weight", 0.15),
        }
        
        # Load thresholds
        thresholds_config = dqi_config.get("thresholds", {})
        self.thresholds = {
            "critical": thresholds_config.get("critical", {}).get("max", 50),
            "high": thresholds_config.get("high", {}).get("max", 70),
            "medium": thresholds_config.get("medium", {}).get("max", 85),
        }
        
        logger.info(
            f"DQIEngine initialized: weights={self.dimension_weights}, "
            f"thresholds={self.thresholds}"
        )
    
    def calculate_dqi(
        self,
        features: Dict[str, Any],
        study_id: Optional[str] = None
    ) -> DQIScore:
        """
        Calculate DQI score from features.
        
        Args:
            features: Dictionary of engineered features
            study_id: Optional study identifier
        
        Returns:
            DQIScore with dimensional breakdown
        
        Example:
            engine = DQIEngine()
            dqi = engine.calculate_dqi(features, "STUDY_01")
            print(f"DQI Score: {dqi.overall_score}")
        """
        logger.info(f"Calculating DQI for {study_id or 'unknown study'}")
        
        # Calculate each dimension
        dimension_scores = [
            self._calc_safety_dimension(features),
            self._calc_compliance_dimension(features),
            self._calc_completeness_dimension(features),
            self._calc_operations_dimension(features),
        ]
        
        # Calculate weighted overall score
        overall_score = sum(ds.weighted_score for ds in dimension_scores)
        overall_score = clamp(overall_score, 0, 100)
        
        # Determine risk level and threshold
        risk_level, threshold_met = self._assess_risk_level(overall_score)
        
        # Create DQI score object
        dqi_score = DQIScore(
            overall_score=overall_score,
            dimension_scores=dimension_scores,
            risk_level=risk_level,
            threshold_met=threshold_met,
            timestamp=datetime.now(),
            study_id=study_id,
            features_used=len(features)
        )
        
        logger.info(
            f"DQI calculated: {study_id} = {overall_score:.2f} ({risk_level.value})"
        )
        
        return dqi_score
    
    def _calc_safety_dimension(self, features: Dict[str, Any]) -> DimensionScore:
        """Calculate Safety dimension score (35%)"""
        
        # Extract safety features - handle None explicitly
        sae_backlog = features.get("sae_backlog_days")
        if sae_backlog is None:
            sae_backlog = 0
        
        sae_overdue = features.get("sae_overdue_count")
        if sae_overdue is None:
            sae_overdue = 0
        
        fatal_sae = features.get("fatal_sae_count")
        if fatal_sae is None:
            fatal_sae = 0
        
        # Score calculation (0-100 scale, higher = better)
        # Perfect score: no SAEs, no backlog, no overdue
        
        score = 100.0
        
        # Penalize fatal SAEs heavily
        if fatal_sae > 0:
            score -= min(fatal_sae * 30, 60)  # Max 60 point penalty
        
        # Penalize overdue SAEs
        if sae_overdue > 0:
            score -= min(sae_overdue * 10, 30)  # Max 30 point penalty
        
        # Penalize backlog
        if sae_backlog > 0:
            penalty = (sae_backlog / 7) * 20  # 7 days = 20 points
            score -= min(penalty, 20)
        
        score = clamp(score, 0, 100)
        
        weight = self.dimension_weights[DQIDimension.SAFETY]
        
        return DimensionScore(
            dimension=DQIDimension.SAFETY,
            raw_score=score,
            weight=weight,
            weighted_score=score * weight,
            contributing_features={
                "sae_backlog_days": sae_backlog,
                "sae_overdue_count": sae_overdue,
                "fatal_sae_count": fatal_sae,
            }
        )
    
    def _calc_compliance_dimension(self, features: Dict[str, Any]) -> DimensionScore:
        """Calculate Compliance dimension score (25%)"""
        
        # Handle None values explicitly
        missing_lab_pct = features.get("missing_lab_ranges_pct")
        if missing_lab_pct is None:
            missing_lab_pct = 0
        
        inactivated_pct = features.get("inactivated_form_pct")
        if inactivated_pct is None:
            inactivated_pct = 0
        
        score = 100.0
        
        # Penalize missing lab ranges
        score -= missing_lab_pct * 0.5  # 100% missing = 50 point penalty
        
        # Penalize inactivated forms (less severe)
        score -= inactivated_pct * 0.3  # 100% inactivated = 30 point penalty
        
        score = clamp(score, 0, 100)
        
        weight = self.dimension_weights[DQIDimension.COMPLIANCE]
        
        return DimensionScore(
            dimension=DQIDimension.COMPLIANCE,
            raw_score=score,
            weight=weight,
            weighted_score=score * weight,
            contributing_features={
                "missing_lab_ranges_pct": missing_lab_pct,
                "inactivated_form_pct": inactivated_pct,
            }
        )
    
    def _calc_completeness_dimension(self, features: Dict[str, Any]) -> DimensionScore:
        """Calculate Completeness dimension score (25%)"""
        
        # Handle None values explicitly
        missing_pages_pct = features.get("missing_pages_pct")
        if missing_pages_pct is None:
            missing_pages_pct = 0
        
        visit_completion = features.get("visit_completion_rate")
        if visit_completion is None:
            visit_completion = 100
        
        form_completion = features.get("form_completion_rate")
        if form_completion is None:
            form_completion = 100
        
        # Start with completion rates
        score = (visit_completion + form_completion) / 2
        
        # Penalize missing pages
        score -= missing_pages_pct * 0.5
        
        score = clamp(score, 0, 100)
        
        weight = self.dimension_weights[DQIDimension.COMPLETENESS]
        
        return DimensionScore(
            dimension=DQIDimension.COMPLETENESS,
            raw_score=score,
            weight=weight,
            weighted_score=score * weight,
            contributing_features={
                "missing_pages_pct": missing_pages_pct,
                "visit_completion_rate": visit_completion,
                "form_completion_rate": form_completion,
            }
        )
    
    def _calc_operations_dimension(self, features: Dict[str, Any]) -> DimensionScore:
        """Calculate Operations dimension score (15%)"""
        
        # Handle None values explicitly
        query_aging = features.get("query_aging_days")
        if query_aging is None:
            query_aging = 0
        
        data_entry_lag = features.get("data_entry_lag_days")
        if data_entry_lag is None:
            data_entry_lag = 0
        
        open_queries = features.get("open_query_count")
        if open_queries is None:
            open_queries = 0
        
        score = 100.0
        
        # Penalize query aging
        if query_aging > 0:
            penalty = (query_aging / 30) * 40  # 30 days = 40 points
            score -= min(penalty, 40)
        
        # Penalize data entry lag
        if data_entry_lag > 0:
            penalty = (data_entry_lag / 7) * 30  # 7 days = 30 points
            score -= min(penalty, 30)
        
        # Penalize open queries
        if open_queries > 0:
            penalty = (open_queries / 100) * 30  # 100 queries = 30 points
            score -= min(penalty, 30)
        
        score = clamp(score, 0, 100)
        
        weight = self.dimension_weights[DQIDimension.OPERATIONS]
        
        return DimensionScore(
            dimension=DQIDimension.OPERATIONS,
            raw_score=score,
            weight=weight,
            weighted_score=score * weight,
            contributing_features={
                "query_aging_days": query_aging,
                "data_entry_lag_days": data_entry_lag,
                "open_query_count": open_queries,
            }
        )
    
    def _assess_risk_level(self, dqi_score: float) -> tuple[RiskLevel, str]:
        """
        Assess risk level from DQI score.
        
        Returns:
            Tuple of (RiskLevel, threshold_name)
        """
        if dqi_score <= self.thresholds["critical"]:
            return RiskLevel.CRITICAL, "critical"
        elif dqi_score <= self.thresholds["high"]:
            return RiskLevel.HIGH, "high"
        elif dqi_score <= self.thresholds["medium"]:
            return RiskLevel.MEDIUM, "medium"
        else:
            return RiskLevel.LOW, "on_track"


# ========================================
# EXPORTS
# ========================================

__all__ = [
    "DQIDimension",
    "DimensionScore",
    "DQIScore",
    "DQIEngine",
]
