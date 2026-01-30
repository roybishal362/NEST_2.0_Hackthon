"""
C-TRUST Data Quality Index (DQI) Calculation Engine
====================================================
Production-ready DQI calculation engine implementing the weighted composite
formula for clinical trial data quality assessment.

DQI Formula (from Requirements 4.1):
    DQI = Safety(35%) + Compliance(25%) + Completeness(20%) + Operations(15%)

DQI Bands (from Requirements 4.4):
    - GREEN:  85-100 (Analysis-ready)
    - AMBER:  65-84  (Minor issues)
    - ORANGE: 40-64  (Attention needed)
    - RED:    <40    (Not submission-ready)

**Validates: Requirements 4.1, 4.2, 4.4, 4.5**
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import math

from src.core import get_logger, DQIBand

logger = get_logger(__name__)


# ========================================
# DQI CONSTANTS (from Requirements)
# ========================================

# Exact weights from Requirements 4.1
DQI_WEIGHTS = {
    "safety": 0.35,       # 35%
    "compliance": 0.25,   # 25%
    "completeness": 0.20, # 20%
    "operations": 0.15,   # 15% (Note: 5% reserved for future dimensions)
}

# DQI Band thresholds from Requirements 4.4
DQI_BAND_THRESHOLDS = {
    DQIBand.GREEN: (85, 100),   # 85-100
    DQIBand.AMBER: (65, 84),    # 65-84
    DQIBand.ORANGE: (40, 64),   # 40-64
    DQIBand.RED: (0, 39),       # <40
}


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
        dimension: Which dimension (safety, compliance, completeness, operations)
        raw_score: Calculated score (0-100)
        weight: Weight of this dimension (from requirements)
        weighted_score: raw_score * weight
        contributing_factors: Factors that contributed to the score
        explanation: Human-readable explanation of the score
    """
    dimension: DQIDimension
    raw_score: float
    weight: float
    weighted_score: float
    contributing_factors: Dict[str, Any] = field(default_factory=dict)
    explanation: str = ""
    
    def __post_init__(self):
        """Validate and clamp scores to valid range"""
        self.raw_score = max(0.0, min(100.0, self.raw_score))
        self.weighted_score = max(0.0, min(100.0, self.weighted_score))


@dataclass
class DQIResult:
    """
    Complete DQI calculation result with dimensional breakdown.
    
    Attributes:
        overall_score: Composite DQI score (0-100)
        band: DQI band classification (GREEN/AMBER/ORANGE/RED)
        dimension_scores: Individual scores for each dimension
        confidence: Confidence in the calculation (0-1)
        timestamp: When calculation was performed
        entity_id: Study/site/subject identifier
        explanation: Overall explanation of the DQI score
    """
    overall_score: float
    band: DQIBand
    dimension_scores: Dict[DQIDimension, DimensionScore]
    confidence: float
    timestamp: datetime
    entity_id: str
    explanation: str = ""
    features_used: int = 0
    partial_calculation: bool = False
    missing_dimensions: List[DQIDimension] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate overall score"""
        self.overall_score = max(0.0, min(100.0, self.overall_score))
        self.confidence = max(0.0, min(1.0, self.confidence))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "overall_score": round(self.overall_score, 2),
            "band": self.band.value,
            "confidence": round(self.confidence, 3),
            "timestamp": self.timestamp.isoformat(),
            "entity_id": self.entity_id,
            "explanation": self.explanation,
            "features_used": self.features_used,
            "partial_calculation": self.partial_calculation,
            "missing_dimensions": [d.value for d in self.missing_dimensions],
            "dimension_breakdown": {
                dim.value: {
                    "raw_score": round(score.raw_score, 2),
                    "weight": score.weight,
                    "weighted_score": round(score.weighted_score, 2),
                    "contributing_factors": score.contributing_factors,
                    "explanation": score.explanation,
                }
                for dim, score in self.dimension_scores.items()
            },
        }
    
    def get_component_breakdown(self) -> Dict[str, float]:
        """Get simple breakdown of weighted contributions"""
        return {
            dim.value: round(score.weighted_score, 2)
            for dim, score in self.dimension_scores.items()
        }


# ========================================
# DQI CALCULATION ENGINE
# ========================================

class DQICalculationEngine:
    """
    Data Quality Index calculation engine.
    
    Implements the weighted composite DQI formula:
        DQI = Safety(35%) + Compliance(25%) + Completeness(20%) + Operations(15%)
    
    Key Features:
    - Exact weight implementation per Requirements 4.1
    - Band classification per Requirements 4.4
    - Component-level breakdown per Requirements 4.2
    - Partial calculation support per Requirements 4.5
    """
    
    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        band_thresholds: Optional[Dict[DQIBand, Tuple[int, int]]] = None
    ):
        """
        Initialize DQI calculation engine.
        
        Args:
            weights: Custom dimension weights (uses defaults if not provided)
            band_thresholds: Custom band thresholds (uses defaults if not provided)
        """
        self.weights = weights or DQI_WEIGHTS.copy()
        self.band_thresholds = band_thresholds or DQI_BAND_THRESHOLDS.copy()
        
        # Validate weights sum to <= 1.0
        total_weight = sum(self.weights.values())
        if total_weight > 1.0 + 1e-6:  # Allow small floating point error
            logger.warning(f"DQI weights sum to {total_weight}, expected <= 1.0")
        
        logger.info(
            f"DQICalculationEngine initialized: weights={self.weights}, "
            f"total_weight={total_weight:.2f}"
        )
    
    def calculate_dqi(
        self,
        features: Dict[str, Any],
        entity_id: str = "unknown"
    ) -> DQIResult:
        """
        Calculate DQI score from feature dictionary.
        
        Args:
            features: Dictionary of engineered features
            entity_id: Identifier for the entity being scored
        
        Returns:
            DQIResult with complete breakdown
        
        **Validates: Requirements 4.1, 4.2, 4.4, 4.5**
        """
        logger.info(f"Calculating DQI for entity: {entity_id}")
        
        # Calculate each dimension
        dimension_scores: Dict[DQIDimension, DimensionScore] = {}
        missing_dimensions: List[DQIDimension] = []
        features_used = 0
        
        # Safety dimension (35%)
        safety_score, safety_features = self._calculate_safety_dimension(features)
        if safety_score is not None:
            dimension_scores[DQIDimension.SAFETY] = safety_score
            features_used += safety_features
        else:
            missing_dimensions.append(DQIDimension.SAFETY)
        
        # Compliance dimension (25%)
        compliance_score, compliance_features = self._calculate_compliance_dimension(features)
        if compliance_score is not None:
            dimension_scores[DQIDimension.COMPLIANCE] = compliance_score
            features_used += compliance_features
        else:
            missing_dimensions.append(DQIDimension.COMPLIANCE)
        
        # Completeness dimension (20%)
        completeness_score, completeness_features = self._calculate_completeness_dimension(features)
        if completeness_score is not None:
            dimension_scores[DQIDimension.COMPLETENESS] = completeness_score
            features_used += completeness_features
        else:
            missing_dimensions.append(DQIDimension.COMPLETENESS)
        
        # Operations dimension (15%)
        operations_score, operations_features = self._calculate_operations_dimension(features)
        if operations_score is not None:
            dimension_scores[DQIDimension.OPERATIONS] = operations_score
            features_used += operations_features
        else:
            missing_dimensions.append(DQIDimension.OPERATIONS)
        
        # Calculate overall score (sum of weighted scores)
        overall_score = sum(ds.weighted_score for ds in dimension_scores.values())
        overall_score = max(0.0, min(100.0, overall_score))
        
        # Determine if this is a partial calculation
        partial_calculation = len(missing_dimensions) > 0
        
        # Calculate confidence based on data completeness
        confidence = self._calculate_confidence(
            dimension_scores, missing_dimensions, features_used
        )
        
        # Adjust score for partial calculation (Requirements 4.5)
        if partial_calculation:
            overall_score, confidence = self._adjust_for_partial_calculation(
                overall_score, confidence, dimension_scores, missing_dimensions
            )
        
        # Classify into band
        band = self._classify_band(overall_score)
        
        # Generate explanation
        explanation = self._generate_explanation(
            overall_score, band, dimension_scores, missing_dimensions
        )
        
        result = DQIResult(
            overall_score=overall_score,
            band=band,
            dimension_scores=dimension_scores,
            confidence=confidence,
            timestamp=datetime.now(),
            entity_id=entity_id,
            explanation=explanation,
            features_used=features_used,
            partial_calculation=partial_calculation,
            missing_dimensions=missing_dimensions,
        )
        
        logger.info(
            f"DQI calculated for {entity_id}: score={overall_score:.2f}, "
            f"band={band.value}, confidence={confidence:.2f}, "
            f"partial={partial_calculation}"
        )
        
        return result

    
    def _calculate_safety_dimension(
        self,
        features: Dict[str, Any]
    ) -> Tuple[Optional[DimensionScore], int]:
        """
        Calculate Safety dimension score (35% weight).
        
        Safety factors:
        - SAE backlog days
        - SAE overdue count
        - Fatal SAE count
        - Safety signal severity
        
        Returns:
            Tuple of (DimensionScore or None, features_used_count)
        """
        weight = self.weights.get("safety", 0.35)
        
        # Extract safety features
        sae_backlog = features.get("sae_backlog_days", None)
        sae_overdue = features.get("sae_overdue_count", None)
        fatal_sae = features.get("fatal_sae_count", None)
        safety_signals = features.get("safety_signal_count", None)
        
        # Check if we have any safety data
        safety_features = [sae_backlog, sae_overdue, fatal_sae, safety_signals]
        available_features = [f for f in safety_features if f is not None]
        
        if not available_features:
            return None, 0
        
        # Start with perfect score
        score = 100.0
        contributing_factors = {}
        explanations = []
        
        # Penalize fatal SAEs heavily (most critical)
        if fatal_sae is not None and fatal_sae > 0:
            penalty = min(fatal_sae * 30, 60)  # Max 60 point penalty
            score -= penalty
            contributing_factors["fatal_sae_count"] = fatal_sae
            explanations.append(f"{fatal_sae} fatal SAE(s) detected (-{penalty:.0f} pts)")
        
        # Penalize overdue SAEs
        if sae_overdue is not None and sae_overdue > 0:
            penalty = min(sae_overdue * 10, 30)  # Max 30 point penalty
            score -= penalty
            contributing_factors["sae_overdue_count"] = sae_overdue
            explanations.append(f"{sae_overdue} overdue SAE(s) (-{penalty:.0f} pts)")
        
        # Penalize SAE backlog
        if sae_backlog is not None and sae_backlog > 0:
            penalty = min((sae_backlog / 7) * 20, 20)  # 7 days = 20 points, max 20
            score -= penalty
            contributing_factors["sae_backlog_days"] = sae_backlog
            explanations.append(f"{sae_backlog} days SAE backlog (-{penalty:.1f} pts)")
        
        # Penalize safety signals
        if safety_signals is not None and safety_signals > 0:
            penalty = min(safety_signals * 5, 15)  # Max 15 point penalty
            score -= penalty
            contributing_factors["safety_signal_count"] = safety_signals
            explanations.append(f"{safety_signals} safety signal(s) (-{penalty:.0f} pts)")
        
        score = max(0.0, min(100.0, score))
        weighted_score = score * weight
        
        explanation = "; ".join(explanations) if explanations else "No safety issues detected"
        
        return DimensionScore(
            dimension=DQIDimension.SAFETY,
            raw_score=score,
            weight=weight,
            weighted_score=weighted_score,
            contributing_factors=contributing_factors,
            explanation=explanation,
        ), len(available_features)
    
    def _calculate_compliance_dimension(
        self,
        features: Dict[str, Any]
    ) -> Tuple[Optional[DimensionScore], int]:
        """
        Calculate Compliance dimension score (25% weight).
        
        Compliance factors:
        - Missing lab ranges percentage
        - Inactivated form percentage
        - Protocol deviation count
        - Regulatory compliance rate
        
        Returns:
            Tuple of (DimensionScore or None, features_used_count)
        """
        weight = self.weights.get("compliance", 0.25)
        
        # Extract compliance features
        missing_lab_pct = features.get("missing_lab_ranges_pct", None)
        inactivated_pct = features.get("inactivated_form_pct", None)
        protocol_deviations = features.get("protocol_deviation_count", None)
        compliance_rate = features.get("regulatory_compliance_rate", None)
        
        # Check if we have any compliance data
        compliance_features = [missing_lab_pct, inactivated_pct, protocol_deviations, compliance_rate]
        available_features = [f for f in compliance_features if f is not None]
        
        if not available_features:
            return None, 0
        
        score = 100.0
        contributing_factors = {}
        explanations = []
        
        # Penalize missing lab ranges
        if missing_lab_pct is not None and missing_lab_pct > 0:
            penalty = missing_lab_pct * 0.5  # 100% missing = 50 point penalty
            score -= penalty
            contributing_factors["missing_lab_ranges_pct"] = missing_lab_pct
            explanations.append(f"{missing_lab_pct:.1f}% missing lab ranges (-{penalty:.1f} pts)")
        
        # Penalize inactivated forms
        if inactivated_pct is not None and inactivated_pct > 0:
            penalty = inactivated_pct * 0.3  # 100% inactivated = 30 point penalty
            score -= penalty
            contributing_factors["inactivated_form_pct"] = inactivated_pct
            explanations.append(f"{inactivated_pct:.1f}% inactivated forms (-{penalty:.1f} pts)")
        
        # Penalize protocol deviations
        if protocol_deviations is not None and protocol_deviations > 0:
            penalty = min(protocol_deviations * 2, 20)  # Max 20 point penalty
            score -= penalty
            contributing_factors["protocol_deviation_count"] = protocol_deviations
            explanations.append(f"{protocol_deviations} protocol deviation(s) (-{penalty:.0f} pts)")
        
        # Boost for high compliance rate
        if compliance_rate is not None:
            if compliance_rate < 100:
                penalty = (100 - compliance_rate) * 0.2
                score -= penalty
                contributing_factors["regulatory_compliance_rate"] = compliance_rate
                explanations.append(f"{compliance_rate:.1f}% compliance rate (-{penalty:.1f} pts)")
        
        score = max(0.0, min(100.0, score))
        weighted_score = score * weight
        
        explanation = "; ".join(explanations) if explanations else "Full compliance achieved"
        
        return DimensionScore(
            dimension=DQIDimension.COMPLIANCE,
            raw_score=score,
            weight=weight,
            weighted_score=weighted_score,
            contributing_factors=contributing_factors,
            explanation=explanation,
        ), len(available_features)
    
    def _calculate_completeness_dimension(
        self,
        features: Dict[str, Any]
    ) -> Tuple[Optional[DimensionScore], int]:
        """
        Calculate Completeness dimension score (20% weight).
        
        Completeness factors:
        - Missing pages percentage
        - Visit completion rate
        - Form completion rate
        - Data entry completion rate
        
        Returns:
            Tuple of (DimensionScore or None, features_used_count)
        """
        weight = self.weights.get("completeness", 0.20)
        
        # Extract completeness features
        missing_pages_pct = features.get("missing_pages_pct", None)
        visit_completion = features.get("visit_completion_rate", None)
        form_completion = features.get("form_completion_rate", None)
        data_entry_completion = features.get("data_entry_completion_rate", None)
        
        # Check if we have any completeness data
        completeness_features = [missing_pages_pct, visit_completion, form_completion, data_entry_completion]
        available_features = [f for f in completeness_features if f is not None]
        
        if not available_features:
            return None, 0
        
        contributing_factors = {}
        explanations = []
        
        # Calculate base score from completion rates
        completion_scores = []
        
        if visit_completion is not None:
            completion_scores.append(visit_completion)
            contributing_factors["visit_completion_rate"] = visit_completion
            if visit_completion < 100:
                explanations.append(f"{visit_completion:.1f}% visit completion")
        
        if form_completion is not None:
            completion_scores.append(form_completion)
            contributing_factors["form_completion_rate"] = form_completion
            if form_completion < 100:
                explanations.append(f"{form_completion:.1f}% form completion")
        
        if data_entry_completion is not None:
            completion_scores.append(data_entry_completion)
            contributing_factors["data_entry_completion_rate"] = data_entry_completion
            if data_entry_completion < 100:
                explanations.append(f"{data_entry_completion:.1f}% data entry completion")
        
        # Start with average of completion rates, or 100 if none available
        if completion_scores:
            score = sum(completion_scores) / len(completion_scores)
        else:
            score = 100.0
        
        # Penalize missing pages
        if missing_pages_pct is not None and missing_pages_pct > 0:
            penalty = missing_pages_pct * 0.5  # 100% missing = 50 point penalty
            score -= penalty
            contributing_factors["missing_pages_pct"] = missing_pages_pct
            explanations.append(f"{missing_pages_pct:.1f}% missing pages (-{penalty:.1f} pts)")
        
        score = max(0.0, min(100.0, score))
        weighted_score = score * weight
        
        explanation = "; ".join(explanations) if explanations else "Data is complete"
        
        return DimensionScore(
            dimension=DQIDimension.COMPLETENESS,
            raw_score=score,
            weight=weight,
            weighted_score=weighted_score,
            contributing_factors=contributing_factors,
            explanation=explanation,
        ), len(available_features)
    
    def _calculate_operations_dimension(
        self,
        features: Dict[str, Any]
    ) -> Tuple[Optional[DimensionScore], int]:
        """
        Calculate Operations dimension score (15% weight).
        
        Operations factors:
        - Query aging days
        - Data entry lag days
        - Open query count
        - Query resolution rate
        
        Returns:
            Tuple of (DimensionScore or None, features_used_count)
        """
        weight = self.weights.get("operations", 0.15)
        
        # Extract operations features
        query_aging = features.get("query_aging_days", None)
        data_entry_lag = features.get("data_entry_lag_days", None)
        open_queries = features.get("open_query_count", None)
        query_resolution_rate = features.get("query_resolution_rate", None)
        
        # Check if we have any operations data
        operations_features = [query_aging, data_entry_lag, open_queries, query_resolution_rate]
        available_features = [f for f in operations_features if f is not None]
        
        if not available_features:
            return None, 0
        
        score = 100.0
        contributing_factors = {}
        explanations = []
        
        # Penalize query aging
        if query_aging is not None and query_aging > 0:
            penalty = min((query_aging / 30) * 40, 40)  # 30 days = 40 points, max 40
            score -= penalty
            contributing_factors["query_aging_days"] = query_aging
            explanations.append(f"{query_aging} days query aging (-{penalty:.1f} pts)")
        
        # Penalize data entry lag
        if data_entry_lag is not None and data_entry_lag > 0:
            penalty = min((data_entry_lag / 7) * 30, 30)  # 7 days = 30 points, max 30
            score -= penalty
            contributing_factors["data_entry_lag_days"] = data_entry_lag
            explanations.append(f"{data_entry_lag} days data entry lag (-{penalty:.1f} pts)")
        
        # Penalize open queries
        if open_queries is not None and open_queries > 0:
            penalty = min((open_queries / 100) * 30, 30)  # 100 queries = 30 points, max 30
            score -= penalty
            contributing_factors["open_query_count"] = open_queries
            explanations.append(f"{open_queries} open queries (-{penalty:.1f} pts)")
        
        # Boost for high query resolution rate
        if query_resolution_rate is not None and query_resolution_rate < 100:
            penalty = (100 - query_resolution_rate) * 0.2
            score -= penalty
            contributing_factors["query_resolution_rate"] = query_resolution_rate
            explanations.append(f"{query_resolution_rate:.1f}% query resolution (-{penalty:.1f} pts)")
        
        score = max(0.0, min(100.0, score))
        weighted_score = score * weight
        
        explanation = "; ".join(explanations) if explanations else "Operations running smoothly"
        
        return DimensionScore(
            dimension=DQIDimension.OPERATIONS,
            raw_score=score,
            weight=weight,
            weighted_score=weighted_score,
            contributing_factors=contributing_factors,
            explanation=explanation,
        ), len(available_features)

    
    def _classify_band(self, score: float) -> DQIBand:
        """
        Classify DQI score into band.
        
        Band thresholds (from Requirements 4.4):
        - GREEN:  85-100 (Analysis-ready)
        - AMBER:  65-84  (Minor issues)
        - ORANGE: 40-64  (Attention needed)
        - RED:    <40    (Not submission-ready)
        
        Args:
            score: DQI score (0-100)
        
        Returns:
            DQIBand classification
        
        **Validates: Requirements 4.4**
        """
        # Ensure score is in valid range
        score = max(0.0, min(100.0, score))
        
        if score >= 85:
            return DQIBand.GREEN
        elif score >= 65:
            return DQIBand.AMBER
        elif score >= 40:
            return DQIBand.ORANGE
        else:
            return DQIBand.RED
    
    def _calculate_confidence(
        self,
        dimension_scores: Dict[DQIDimension, DimensionScore],
        missing_dimensions: List[DQIDimension],
        features_used: int
    ) -> float:
        """
        Calculate confidence in the DQI calculation.
        
        Confidence factors:
        1. Dimension coverage (how many dimensions have data)
        2. Feature density (how many features were used)
        3. Data quality indicators
        
        Args:
            dimension_scores: Calculated dimension scores
            missing_dimensions: Dimensions without data
            features_used: Total features used in calculation
        
        Returns:
            Confidence score (0-1)
        """
        # Factor 1: Dimension coverage
        total_dimensions = 4
        available_dimensions = len(dimension_scores)
        coverage_factor = available_dimensions / total_dimensions
        
        # Factor 2: Feature density (more features = higher confidence)
        # Assume ideal is 12+ features (3 per dimension)
        ideal_features = 12
        feature_factor = min(features_used / ideal_features, 1.0)
        
        # Combine factors
        confidence = (coverage_factor * 0.6) + (feature_factor * 0.4)
        
        return max(0.0, min(1.0, confidence))
    
    def _adjust_for_partial_calculation(
        self,
        score: float,
        confidence: float,
        dimension_scores: Dict[DQIDimension, DimensionScore],
        missing_dimensions: List[DQIDimension]
    ) -> Tuple[float, float]:
        """
        Adjust score and confidence for partial calculation.
        
        When some dimensions are missing, we:
        1. Scale the score based on available weight
        2. Reduce confidence proportionally
        
        **Validates: Requirements 4.5**
        
        Args:
            score: Raw calculated score
            confidence: Raw confidence
            dimension_scores: Available dimension scores
            missing_dimensions: Missing dimensions
        
        Returns:
            Tuple of (adjusted_score, adjusted_confidence)
        """
        if not missing_dimensions:
            return score, confidence
        
        # Calculate available weight
        available_weight = sum(ds.weight for ds in dimension_scores.values())
        total_weight = sum(self.weights.values())
        
        if available_weight == 0:
            return 0.0, 0.0
        
        # Scale score to account for missing dimensions
        # This normalizes the score as if only available dimensions existed
        scaling_factor = total_weight / available_weight
        adjusted_score = score * scaling_factor
        adjusted_score = max(0.0, min(100.0, adjusted_score))
        
        # Reduce confidence based on missing dimensions
        missing_weight = sum(self.weights.get(d.value, 0) for d in missing_dimensions)
        confidence_penalty = missing_weight / total_weight
        adjusted_confidence = confidence * (1 - confidence_penalty * 0.5)
        
        logger.debug(
            f"Partial calculation adjustment: score {score:.2f} -> {adjusted_score:.2f}, "
            f"confidence {confidence:.2f} -> {adjusted_confidence:.2f}"
        )
        
        return adjusted_score, adjusted_confidence
    
    def _generate_explanation(
        self,
        score: float,
        band: DQIBand,
        dimension_scores: Dict[DQIDimension, DimensionScore],
        missing_dimensions: List[DQIDimension]
    ) -> str:
        """
        Generate human-readable explanation of DQI score.
        
        **Validates: Requirements 4.2**
        
        Args:
            score: Overall DQI score
            band: DQI band classification
            dimension_scores: Individual dimension scores
            missing_dimensions: Dimensions without data
        
        Returns:
            Human-readable explanation string
        """
        parts = []
        
        # Overall summary
        band_descriptions = {
            DQIBand.GREEN: "Analysis-ready",
            DQIBand.AMBER: "Minor issues present",
            DQIBand.ORANGE: "Attention needed",
            DQIBand.RED: "Not submission-ready",
        }
        parts.append(f"DQI Score: {score:.1f}/100 ({band.value} - {band_descriptions[band]})")
        
        # Dimension breakdown
        if dimension_scores:
            parts.append("Dimension breakdown:")
            for dim, ds in sorted(dimension_scores.items(), key=lambda x: -x[1].weighted_score):
                parts.append(
                    f"  - {dim.value.capitalize()}: {ds.raw_score:.1f} × {ds.weight:.0%} = "
                    f"{ds.weighted_score:.1f} pts"
                )
        
        # Missing dimensions warning
        if missing_dimensions:
            missing_names = [d.value for d in missing_dimensions]
            parts.append(f"Note: Missing data for {', '.join(missing_names)} dimension(s)")
        
        return "\n".join(parts)
    
    def get_weights(self) -> Dict[str, float]:
        """Get current dimension weights"""
        return self.weights.copy()
    
    def get_band_thresholds(self) -> Dict[DQIBand, Tuple[int, int]]:
        """Get current band thresholds"""
        return self.band_thresholds.copy()
    
    @staticmethod
    def validate_weights(weights: Dict[str, float]) -> bool:
        """
        Validate that weights are properly configured.
        
        Args:
            weights: Dictionary of dimension weights
        
        Returns:
            True if weights are valid
        """
        required_dimensions = ["safety", "compliance", "completeness", "operations"]
        
        # Check all dimensions present
        for dim in required_dimensions:
            if dim not in weights:
                return False
        
        # Check weights are positive
        for weight in weights.values():
            if weight < 0:
                return False
        
        # Check total weight <= 1.0 (allowing for floating point error)
        total = sum(weights.values())
        if total > 1.0 + 1e-6:
            return False
        
        return True


# ========================================
# EXPORTS
# ========================================

__all__ = [
    "DQICalculationEngine",
    "DQIResult",
    "DimensionScore",
    "DQIDimension",
    "DQI_WEIGHTS",
    "DQI_BAND_THRESHOLDS",
]
