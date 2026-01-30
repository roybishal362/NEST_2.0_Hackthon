"""
C-TRUST DQI Change Explanation System
=====================================
Provides structured explanations for DQI score changes between snapshots.

Key Features:
- Driver identification for DQI changes
- Structured explanation generation
- Partial DQI calculation handling with confidence adjustment

**Validates: Requirements 4.3, 4.5**
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from src.core import get_logger, DQIBand
from src.dqi.dqi_engine import (
    DQICalculationEngine,
    DQIResult,
    DimensionScore,
    DQIDimension,
)

logger = get_logger(__name__)


# ========================================
# CHANGE EXPLANATION DATA STRUCTURES
# ========================================

class ChangeDirection(str, Enum):
    """Direction of DQI change"""
    IMPROVED = "IMPROVED"
    DECLINED = "DECLINED"
    STABLE = "STABLE"


class ChangeSeverity(str, Enum):
    """Severity of DQI change"""
    CRITICAL = "CRITICAL"  # Band changed to/from RED
    SIGNIFICANT = "SIGNIFICANT"  # Band changed
    MODERATE = "MODERATE"  # Score changed >5 points
    MINOR = "MINOR"  # Score changed 1-5 points
    NEGLIGIBLE = "NEGLIGIBLE"  # Score changed <1 point


@dataclass
class DimensionChange:
    """
    Change in a single DQI dimension between snapshots.
    
    Attributes:
        dimension: Which dimension changed
        previous_score: Previous raw score
        current_score: Current raw score
        score_delta: Change in score (current - previous)
        direction: Whether improved, declined, or stable
        contributing_factors: Factors that drove the change
        explanation: Human-readable explanation
    """
    dimension: DQIDimension
    previous_score: float
    current_score: float
    score_delta: float
    direction: ChangeDirection
    contributing_factors: Dict[str, Tuple[Any, Any]]  # factor -> (prev, curr)
    explanation: str
    
    @property
    def weighted_delta(self) -> float:
        """Get weighted score delta based on dimension weight"""
        from src.dqi.dqi_engine import DQI_WEIGHTS
        weight = DQI_WEIGHTS.get(self.dimension.value, 0.0)
        return self.score_delta * weight


@dataclass
class DQIChangeExplanation:
    """
    Complete explanation of DQI change between two snapshots.
    
    Attributes:
        entity_id: Study/site/subject identifier
        previous_result: Previous DQI calculation result
        current_result: Current DQI calculation result
        overall_delta: Change in overall DQI score
        direction: Overall direction of change
        severity: Severity of the change
        dimension_changes: Changes in each dimension
        primary_drivers: Top factors driving the change
        explanation: Human-readable summary
        timestamp: When explanation was generated
    """
    entity_id: str
    previous_result: DQIResult
    current_result: DQIResult
    overall_delta: float
    direction: ChangeDirection
    severity: ChangeSeverity
    dimension_changes: Dict[DQIDimension, DimensionChange]
    primary_drivers: List[str]
    explanation: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "entity_id": self.entity_id,
            "previous_score": round(self.previous_result.overall_score, 2),
            "current_score": round(self.current_result.overall_score, 2),
            "overall_delta": round(self.overall_delta, 2),
            "direction": self.direction.value,
            "severity": self.severity.value,
            "previous_band": self.previous_result.band.value,
            "current_band": self.current_result.band.value,
            "primary_drivers": self.primary_drivers,
            "explanation": self.explanation,
            "timestamp": self.timestamp.isoformat(),
            "dimension_changes": {
                dim.value: {
                    "previous_score": round(change.previous_score, 2),
                    "current_score": round(change.current_score, 2),
                    "delta": round(change.score_delta, 2),
                    "direction": change.direction.value,
                    "explanation": change.explanation,
                }
                for dim, change in self.dimension_changes.items()
            },
        }


# ========================================
# DQI CHANGE EXPLANATION ENGINE
# ========================================

class DQIChangeExplanationEngine:
    """
    Engine for generating explanations of DQI changes.
    
    Compares two DQI results and identifies the primary drivers
    of any score changes, providing structured explanations.
    
    **Validates: Requirements 4.3, 4.5**
    """
    
    # Thresholds for change severity
    CRITICAL_THRESHOLD = 20.0  # Points
    SIGNIFICANT_THRESHOLD = 10.0
    MODERATE_THRESHOLD = 5.0
    MINOR_THRESHOLD = 1.0
    
    def __init__(self):
        """Initialize the change explanation engine"""
        logger.info("DQIChangeExplanationEngine initialized")
    
    def explain_change(
        self,
        previous_result: DQIResult,
        current_result: DQIResult,
        entity_id: Optional[str] = None
    ) -> DQIChangeExplanation:
        """
        Generate explanation for DQI change between two results.
        
        Args:
            previous_result: Previous DQI calculation result
            current_result: Current DQI calculation result
            entity_id: Optional entity identifier (uses current_result.entity_id if not provided)
        
        Returns:
            DQIChangeExplanation with detailed breakdown
        
        **Validates: Requirements 4.3**
        """
        entity_id = entity_id or current_result.entity_id
        
        logger.info(f"Generating DQI change explanation for {entity_id}")
        
        # Calculate overall change
        overall_delta = current_result.overall_score - previous_result.overall_score
        direction = self._determine_direction(overall_delta)
        severity = self._determine_severity(
            overall_delta, previous_result.band, current_result.band
        )
        
        # Analyze dimension changes
        dimension_changes = self._analyze_dimension_changes(
            previous_result, current_result
        )
        
        # Identify primary drivers
        primary_drivers = self._identify_primary_drivers(dimension_changes)
        
        # Generate explanation
        explanation = self._generate_explanation(
            overall_delta, direction, severity,
            previous_result, current_result,
            dimension_changes, primary_drivers
        )
        
        result = DQIChangeExplanation(
            entity_id=entity_id,
            previous_result=previous_result,
            current_result=current_result,
            overall_delta=overall_delta,
            direction=direction,
            severity=severity,
            dimension_changes=dimension_changes,
            primary_drivers=primary_drivers,
            explanation=explanation,
        )
        
        logger.info(
            f"DQI change explanation generated: {entity_id} "
            f"delta={overall_delta:+.2f}, direction={direction.value}, "
            f"severity={severity.value}"
        )
        
        return result
    
    def _determine_direction(self, delta: float) -> ChangeDirection:
        """Determine direction of change from delta"""
        if delta > self.MINOR_THRESHOLD:
            return ChangeDirection.IMPROVED
        elif delta < -self.MINOR_THRESHOLD:
            return ChangeDirection.DECLINED
        else:
            return ChangeDirection.STABLE
    
    def _determine_severity(
        self,
        delta: float,
        prev_band: DQIBand,
        curr_band: DQIBand
    ) -> ChangeSeverity:
        """
        Determine severity of change based on delta and band changes.
        
        Args:
            delta: Score change
            prev_band: Previous DQI band
            curr_band: Current DQI band
        
        Returns:
            ChangeSeverity classification
        """
        abs_delta = abs(delta)
        
        # Critical if band changed to/from RED
        if prev_band == DQIBand.RED or curr_band == DQIBand.RED:
            if prev_band != curr_band:
                return ChangeSeverity.CRITICAL
        
        # Significant if band changed
        if prev_band != curr_band:
            return ChangeSeverity.SIGNIFICANT
        
        # Based on score delta
        if abs_delta >= self.CRITICAL_THRESHOLD:
            return ChangeSeverity.CRITICAL
        elif abs_delta >= self.SIGNIFICANT_THRESHOLD:
            return ChangeSeverity.SIGNIFICANT
        elif abs_delta >= self.MODERATE_THRESHOLD:
            return ChangeSeverity.MODERATE
        elif abs_delta >= self.MINOR_THRESHOLD:
            return ChangeSeverity.MINOR
        else:
            return ChangeSeverity.NEGLIGIBLE
    
    def _analyze_dimension_changes(
        self,
        previous_result: DQIResult,
        current_result: DQIResult
    ) -> Dict[DQIDimension, DimensionChange]:
        """
        Analyze changes in each dimension.
        
        Args:
            previous_result: Previous DQI result
            current_result: Current DQI result
        
        Returns:
            Dictionary of dimension changes
        """
        dimension_changes = {}
        
        # Get all dimensions from both results
        all_dimensions = set(previous_result.dimension_scores.keys()) | \
                        set(current_result.dimension_scores.keys())
        
        for dim in all_dimensions:
            prev_score = previous_result.dimension_scores.get(dim)
            curr_score = current_result.dimension_scores.get(dim)
            
            # Handle missing dimensions
            prev_raw = prev_score.raw_score if prev_score else 0.0
            curr_raw = curr_score.raw_score if curr_score else 0.0
            
            delta = curr_raw - prev_raw
            direction = self._determine_direction(delta)
            
            # Identify contributing factors
            contributing_factors = self._identify_factor_changes(
                prev_score, curr_score
            )
            
            # Generate dimension explanation
            explanation = self._generate_dimension_explanation(
                dim, prev_raw, curr_raw, delta, direction, contributing_factors
            )
            
            dimension_changes[dim] = DimensionChange(
                dimension=dim,
                previous_score=prev_raw,
                current_score=curr_raw,
                score_delta=delta,
                direction=direction,
                contributing_factors=contributing_factors,
                explanation=explanation,
            )
        
        return dimension_changes
    
    def _identify_factor_changes(
        self,
        prev_score: Optional[DimensionScore],
        curr_score: Optional[DimensionScore]
    ) -> Dict[str, Tuple[Any, Any]]:
        """
        Identify which factors changed between dimension scores.
        
        Args:
            prev_score: Previous dimension score
            curr_score: Current dimension score
        
        Returns:
            Dictionary mapping factor name to (previous, current) values
        """
        changes = {}
        
        prev_factors = prev_score.contributing_factors if prev_score else {}
        curr_factors = curr_score.contributing_factors if curr_score else {}
        
        # Get all factor names
        all_factors = set(prev_factors.keys()) | set(curr_factors.keys())
        
        for factor in all_factors:
            prev_val = prev_factors.get(factor, 0)
            curr_val = curr_factors.get(factor, 0)
            
            # Only include if changed
            if prev_val != curr_val:
                changes[factor] = (prev_val, curr_val)
        
        return changes
    
    def _identify_primary_drivers(
        self,
        dimension_changes: Dict[DQIDimension, DimensionChange]
    ) -> List[str]:
        """
        Identify the primary drivers of DQI change.
        
        Ranks dimensions by their weighted contribution to the overall change.
        
        Args:
            dimension_changes: Dictionary of dimension changes
        
        Returns:
            List of primary driver descriptions, sorted by impact
        """
        drivers = []
        
        # Sort dimensions by absolute weighted delta
        sorted_dims = sorted(
            dimension_changes.items(),
            key=lambda x: abs(x[1].weighted_delta),
            reverse=True
        )
        
        for dim, change in sorted_dims:
            if abs(change.score_delta) >= self.MINOR_THRESHOLD:
                direction_word = "improved" if change.direction == ChangeDirection.IMPROVED else "declined"
                drivers.append(
                    f"{dim.value.capitalize()} {direction_word} by {abs(change.score_delta):.1f} points"
                )
        
        return drivers[:3]  # Return top 3 drivers
    
    def _generate_dimension_explanation(
        self,
        dimension: DQIDimension,
        prev_score: float,
        curr_score: float,
        delta: float,
        direction: ChangeDirection,
        contributing_factors: Dict[str, Tuple[Any, Any]]
    ) -> str:
        """Generate explanation for a single dimension change"""
        if direction == ChangeDirection.STABLE:
            return f"{dimension.value.capitalize()} remained stable at {curr_score:.1f}"
        
        direction_word = "improved" if direction == ChangeDirection.IMPROVED else "declined"
        
        parts = [
            f"{dimension.value.capitalize()} {direction_word} from {prev_score:.1f} to {curr_score:.1f} ({delta:+.1f})"
        ]
        
        # Add factor details
        if contributing_factors:
            factor_details = []
            for factor, (prev, curr) in contributing_factors.items():
                factor_name = factor.replace("_", " ")
                factor_details.append(f"{factor_name}: {prev} → {curr}")
            
            if factor_details:
                parts.append("Factors: " + "; ".join(factor_details[:3]))
        
        return ". ".join(parts)
    
    def _generate_explanation(
        self,
        overall_delta: float,
        direction: ChangeDirection,
        severity: ChangeSeverity,
        previous_result: DQIResult,
        current_result: DQIResult,
        dimension_changes: Dict[DQIDimension, DimensionChange],
        primary_drivers: List[str]
    ) -> str:
        """
        Generate overall explanation of DQI change.
        
        **Validates: Requirements 4.3**
        """
        parts = []
        
        # Overall summary
        if direction == ChangeDirection.STABLE:
            parts.append(
                f"DQI score remained stable at {current_result.overall_score:.1f} "
                f"({current_result.band.value} band)"
            )
        else:
            direction_word = "improved" if direction == ChangeDirection.IMPROVED else "declined"
            parts.append(
                f"DQI score {direction_word} from {previous_result.overall_score:.1f} "
                f"to {current_result.overall_score:.1f} ({overall_delta:+.1f} points)"
            )
        
        # Band change
        if previous_result.band != current_result.band:
            parts.append(
                f"Band changed from {previous_result.band.value} to {current_result.band.value}"
            )
        
        # Primary drivers
        if primary_drivers:
            parts.append("Primary drivers: " + "; ".join(primary_drivers))
        
        # Severity note
        severity_notes = {
            ChangeSeverity.CRITICAL: "This is a critical change requiring immediate attention.",
            ChangeSeverity.SIGNIFICANT: "This is a significant change that should be reviewed.",
            ChangeSeverity.MODERATE: "This is a moderate change worth monitoring.",
            ChangeSeverity.MINOR: "This is a minor change.",
            ChangeSeverity.NEGLIGIBLE: "This change is negligible.",
        }
        parts.append(severity_notes[severity])
        
        # Confidence note for partial calculations
        if current_result.partial_calculation:
            parts.append(
                f"Note: Current calculation is partial (confidence: {current_result.confidence:.0%})"
            )
        
        return " ".join(parts)
