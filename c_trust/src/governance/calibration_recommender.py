"""
C-TRUST Guardian-Driven Calibration Recommender
===============================================
Generates calibration recommendations based on Guardian Agent findings
and historical performance data.

Key Features:
- Recommendation generation from Guardian findings
- Offline calibration support with historical data
- No automatic self-modification in production
- Human approval required for all recommendations


Design Principles:
- Guardian findings inform recommendations, not automatic changes
- All recommendations require human review and approval
- Offline calibration uses historical data analysis
- System NEVER implements automatic learning in production
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import uuid
import statistics

from src.core import get_logger

logger = get_logger(__name__)


# ========================================
# ENUMERATIONS
# ========================================

class CalibrationSource(str, Enum):
    """Source of calibration recommendation"""
    GUARDIAN_CONSISTENCY = "GUARDIAN_CONSISTENCY"
    GUARDIAN_STALENESS = "GUARDIAN_STALENESS"
    HISTORICAL_ANALYSIS = "HISTORICAL_ANALYSIS"
    PERFORMANCE_DRIFT = "PERFORMANCE_DRIFT"
    MANUAL_REVIEW = "MANUAL_REVIEW"


class RecommendationPriority(str, Enum):
    """Priority level for calibration recommendations"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RecommendationStatus(str, Enum):
    """Status of calibration recommendation"""
    PENDING = "PENDING"
    REVIEWED = "REVIEWED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    IMPLEMENTED = "IMPLEMENTED"


# ========================================
# DATA STRUCTURES
# ========================================

@dataclass
class CalibrationRecommendation:
    """
    Represents a calibration recommendation.
    
    All recommendations require human review and approval.
    The system NEVER implements automatic changes.
    
    Attributes:
        recommendation_id: Unique identifier
        source: Source of the recommendation
        priority: Priority level
        config_key: Configuration key to adjust
        current_value: Current configuration value
        recommended_value: Recommended new value
        justification: Detailed justification for the change
        evidence: Supporting evidence for the recommendation
        expected_impact: Expected impact of the change
        created_at: When recommendation was created
        status: Current status
        reviewed_by: User who reviewed (if any)
        reviewed_at: When reviewed (if any)
        review_notes: Notes from reviewer (if any)
    """
    recommendation_id: str
    source: CalibrationSource
    priority: RecommendationPriority
    config_key: str
    current_value: Any
    recommended_value: Any
    justification: str
    evidence: List[Dict[str, Any]]
    expected_impact: str
    created_at: datetime = field(default_factory=datetime.now)
    status: RecommendationStatus = RecommendationStatus.PENDING
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "recommendation_id": self.recommendation_id,
            "source": self.source.value,
            "priority": self.priority.value,
            "config_key": self.config_key,
            "current_value": self.current_value,
            "recommended_value": self.recommended_value,
            "justification": self.justification,
            "evidence": self.evidence,
            "expected_impact": self.expected_impact,
            "created_at": self.created_at.isoformat(),
            "status": self.status.value,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "review_notes": self.review_notes,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CalibrationRecommendation":
        """Create CalibrationRecommendation from dictionary"""
        return cls(
            recommendation_id=data["recommendation_id"],
            source=CalibrationSource(data["source"]),
            priority=RecommendationPriority(data["priority"]),
            config_key=data["config_key"],
            current_value=data["current_value"],
            recommended_value=data["recommended_value"],
            justification=data["justification"],
            evidence=data["evidence"],
            expected_impact=data["expected_impact"],
            created_at=datetime.fromisoformat(data["created_at"]),
            status=RecommendationStatus(data["status"]),
            reviewed_by=data.get("reviewed_by"),
            reviewed_at=datetime.fromisoformat(data["reviewed_at"]) if data.get("reviewed_at") else None,
            review_notes=data.get("review_notes"),
        )


@dataclass
class HistoricalPerformanceData:
    """
    Historical performance data for offline calibration.
    
    Attributes:
        entity_id: Entity being analyzed
        metric_name: Name of the metric
        values: List of historical values
        timestamps: Corresponding timestamps
        agent_predictions: Agent predictions at each point
        actual_outcomes: Actual outcomes at each point
    """
    entity_id: str
    metric_name: str
    values: List[float]
    timestamps: List[datetime]
    agent_predictions: List[Dict[str, Any]] = field(default_factory=list)
    actual_outcomes: List[Dict[str, Any]] = field(default_factory=list)
    
    def get_trend(self) -> str:
        """Calculate trend direction"""
        if len(self.values) < 2:
            return "STABLE"
        
        recent = self.values[-5:] if len(self.values) >= 5 else self.values
        if len(recent) < 2:
            return "STABLE"
        
        avg_first_half = statistics.mean(recent[:len(recent)//2])
        avg_second_half = statistics.mean(recent[len(recent)//2:])
        
        diff = avg_second_half - avg_first_half
        if diff > 0.05:
            return "INCREASING"
        elif diff < -0.05:
            return "DECREASING"
        return "STABLE"
    
    def get_volatility(self) -> float:
        """Calculate volatility (standard deviation)"""
        if len(self.values) < 2:
            return 0.0
        return statistics.stdev(self.values)


# ========================================
# CALIBRATION RECOMMENDER
# ========================================

class CalibrationRecommender:
    """
    Guardian-Driven Calibration Recommender.
    
    Generates calibration recommendations based on:
    - Guardian Agent findings (consistency issues, staleness)
    - Historical performance data analysis
    - Performance drift detection
    
    CRITICAL: This system NEVER implements automatic changes.
    All recommendations require human review and approval.
    
    **Validates: Requirements 8.3, 8.4, 8.5**
    """
    
    # Thresholds for recommendation generation
    DEFAULT_CONSISTENCY_THRESHOLD = 0.15
    DEFAULT_STALENESS_THRESHOLD = 3
    DEFAULT_DRIFT_THRESHOLD = 0.10
    
    def __init__(
        self,
        consistency_threshold: float = None,
        staleness_threshold: int = None,
        drift_threshold: float = None,
    ):
        """
        Initialize calibration recommender.
        
        Args:
            consistency_threshold: Threshold for consistency issues
            staleness_threshold: Threshold for staleness detection
            drift_threshold: Threshold for performance drift
        """
        self.consistency_threshold = consistency_threshold or self.DEFAULT_CONSISTENCY_THRESHOLD
        self.staleness_threshold = staleness_threshold or self.DEFAULT_STALENESS_THRESHOLD
        self.drift_threshold = drift_threshold or self.DEFAULT_DRIFT_THRESHOLD
        
        self._recommendations: List[CalibrationRecommendation] = []
        self._historical_data: Dict[str, List[HistoricalPerformanceData]] = {}
        
        logger.info(
            f"CalibrationRecommender initialized: "
            f"consistency={self.consistency_threshold}, "
            f"staleness={self.staleness_threshold}, "
            f"drift={self.drift_threshold}"
        )
    
    # ========================================
    # GUARDIAN-DRIVEN RECOMMENDATIONS
    # ========================================
    
    def generate_from_guardian_consistency(
        self,
        entity_id: str,
        data_delta_magnitude: float,
        output_delta_magnitude: float,
        current_sensitivity: float,
        guardian_event_details: Dict[str, Any],
    ) -> Optional[CalibrationRecommendation]:
        """
        Generate recommendation from Guardian consistency finding.
        
        When Guardian detects data-output inconsistency, this method
        analyzes the finding and generates a calibration recommendation.
        
        Args:
            entity_id: Entity with consistency issue
            data_delta_magnitude: Magnitude of data change
            output_delta_magnitude: Magnitude of output change
            current_sensitivity: Current Guardian sensitivity setting
            guardian_event_details: Details from Guardian event
        
        Returns:
            CalibrationRecommendation or None if no recommendation needed
        """
        # Calculate the discrepancy
        discrepancy = abs(data_delta_magnitude - output_delta_magnitude)
        
        if discrepancy < self.consistency_threshold:
            return None
        
        # Determine recommended sensitivity adjustment
        if data_delta_magnitude > output_delta_magnitude:
            # System is under-reacting to data changes
            # Recommend increasing sensitivity
            recommended_sensitivity = min(current_sensitivity * 1.2, 0.5)
            justification = (
                f"Guardian detected under-reaction to data changes. "
                f"Data changed by {data_delta_magnitude:.2%} but output only changed by "
                f"{output_delta_magnitude:.2%}. Increasing sensitivity may help the system "
                f"respond more appropriately to data improvements."
            )
            expected_impact = "System will be more responsive to data quality improvements"
        else:
            # System is over-reacting to data changes
            # Recommend decreasing sensitivity
            recommended_sensitivity = max(current_sensitivity * 0.8, 0.05)
            justification = (
                f"Guardian detected over-reaction to data changes. "
                f"Data changed by {data_delta_magnitude:.2%} but output changed by "
                f"{output_delta_magnitude:.2%}. Decreasing sensitivity may reduce "
                f"unnecessary alert fluctuations."
            )
            expected_impact = "System will be more stable with fewer false positives"
        
        # Determine priority based on discrepancy magnitude
        if discrepancy > 0.3:
            priority = RecommendationPriority.HIGH
        elif discrepancy > 0.2:
            priority = RecommendationPriority.MEDIUM
        else:
            priority = RecommendationPriority.LOW
        
        recommendation = CalibrationRecommendation(
            recommendation_id=str(uuid.uuid4()),
            source=CalibrationSource.GUARDIAN_CONSISTENCY,
            priority=priority,
            config_key="guardian.sensitivity",
            current_value=current_sensitivity,
            recommended_value=recommended_sensitivity,
            justification=justification,
            evidence=[
                {
                    "entity_id": entity_id,
                    "data_delta": data_delta_magnitude,
                    "output_delta": output_delta_magnitude,
                    "discrepancy": discrepancy,
                    "guardian_event": guardian_event_details,
                }
            ],
            expected_impact=expected_impact,
        )
        
        self._recommendations.append(recommendation)
        
        logger.info(
            f"Generated consistency recommendation: {recommendation.recommendation_id} - "
            f"sensitivity {current_sensitivity} -> {recommended_sensitivity}"
        )
        
        return recommendation
    
    def generate_from_guardian_staleness(
        self,
        entity_id: str,
        consecutive_unchanged: int,
        alert_types: List[str],
        current_staleness_threshold: int,
        guardian_event_details: Dict[str, Any],
    ) -> Optional[CalibrationRecommendation]:
        """
        Generate recommendation from Guardian staleness finding.
        
        When Guardian detects system staleness, this method analyzes
        the finding and generates a calibration recommendation.
        
        Args:
            entity_id: Entity with staleness issue
            consecutive_unchanged: Number of unchanged snapshots
            alert_types: Types of alerts that haven't changed
            current_staleness_threshold: Current staleness threshold
            guardian_event_details: Details from Guardian event
        
        Returns:
            CalibrationRecommendation or None if no recommendation needed
        """
        if consecutive_unchanged < self.staleness_threshold:
            return None
        
        # Analyze the staleness pattern
        staleness_ratio = consecutive_unchanged / current_staleness_threshold
        
        if staleness_ratio > 2.0:
            # Severe staleness - recommend lowering threshold
            recommended_threshold = max(current_staleness_threshold - 1, 2)
            priority = RecommendationPriority.HIGH
            justification = (
                f"Guardian detected severe staleness for {entity_id}. "
                f"Alerts unchanged for {consecutive_unchanged} snapshots "
                f"(threshold: {current_staleness_threshold}). "
                f"Lowering staleness threshold will enable earlier detection."
            )
        else:
            # Moderate staleness - recommend reviewing agent thresholds
            recommended_threshold = current_staleness_threshold
            priority = RecommendationPriority.MEDIUM
            justification = (
                f"Guardian detected staleness for {entity_id}. "
                f"Alerts unchanged for {consecutive_unchanged} snapshots. "
                f"Consider reviewing agent sensitivity thresholds for: {', '.join(alert_types)}."
            )
        
        recommendation = CalibrationRecommendation(
            recommendation_id=str(uuid.uuid4()),
            source=CalibrationSource.GUARDIAN_STALENESS,
            priority=priority,
            config_key="guardian.staleness_detection_hours",
            current_value=current_staleness_threshold,
            recommended_value=recommended_threshold,
            justification=justification,
            evidence=[
                {
                    "entity_id": entity_id,
                    "consecutive_unchanged": consecutive_unchanged,
                    "alert_types": alert_types,
                    "staleness_ratio": staleness_ratio,
                    "guardian_event": guardian_event_details,
                }
            ],
            expected_impact="Earlier detection of system staleness issues",
        )
        
        self._recommendations.append(recommendation)
        
        logger.info(
            f"Generated staleness recommendation: {recommendation.recommendation_id}"
        )
        
        return recommendation
    
    # ========================================
    # HISTORICAL DATA ANALYSIS
    # ========================================
    
    def add_historical_data(
        self,
        entity_id: str,
        metric_name: str,
        value: float,
        timestamp: datetime,
        agent_prediction: Optional[Dict[str, Any]] = None,
        actual_outcome: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Add historical performance data for offline calibration.
        
        Args:
            entity_id: Entity being tracked
            metric_name: Name of the metric
            value: Metric value
            timestamp: When the value was recorded
            agent_prediction: Agent's prediction at this point
            actual_outcome: Actual outcome at this point
        """
        key = f"{entity_id}:{metric_name}"
        
        if key not in self._historical_data:
            self._historical_data[key] = []
        
        # Find or create data entry
        data_entry = None
        for entry in self._historical_data[key]:
            if entry.entity_id == entity_id and entry.metric_name == metric_name:
                data_entry = entry
                break
        
        if not data_entry:
            data_entry = HistoricalPerformanceData(
                entity_id=entity_id,
                metric_name=metric_name,
                values=[],
                timestamps=[],
            )
            self._historical_data[key].append(data_entry)
        
        data_entry.values.append(value)
        data_entry.timestamps.append(timestamp)
        
        if agent_prediction:
            data_entry.agent_predictions.append(agent_prediction)
        if actual_outcome:
            data_entry.actual_outcomes.append(actual_outcome)
    
    def analyze_historical_performance(
        self,
        entity_id: str,
        metric_name: str,
        current_threshold: float,
    ) -> Optional[CalibrationRecommendation]:
        """
        Analyze historical performance data for calibration.
        
        This is the offline calibration capability that uses historical
        data to generate recommendations.
        
        Args:
            entity_id: Entity to analyze
            metric_name: Metric to analyze
            current_threshold: Current threshold for this metric
        
        Returns:
            CalibrationRecommendation or None if no recommendation needed
        """
        key = f"{entity_id}:{metric_name}"
        
        if key not in self._historical_data:
            return None
        
        data_entries = self._historical_data[key]
        if not data_entries:
            return None
        
        # Combine all data for this entity/metric
        all_values = []
        for entry in data_entries:
            all_values.extend(entry.values)
        
        if len(all_values) < 10:
            # Not enough data for meaningful analysis
            return None
        
        # Calculate statistics
        mean_value = statistics.mean(all_values)
        std_value = statistics.stdev(all_values)
        
        # Check if current threshold is appropriate
        # Threshold should be around mean + 1 std for typical alerting
        recommended_threshold = mean_value + std_value
        
        threshold_diff = abs(current_threshold - recommended_threshold) / current_threshold
        
        if threshold_diff < self.drift_threshold:
            # Current threshold is appropriate
            return None
        
        # Determine priority
        if threshold_diff > 0.3:
            priority = RecommendationPriority.HIGH
        elif threshold_diff > 0.2:
            priority = RecommendationPriority.MEDIUM
        else:
            priority = RecommendationPriority.LOW
        
        recommendation = CalibrationRecommendation(
            recommendation_id=str(uuid.uuid4()),
            source=CalibrationSource.HISTORICAL_ANALYSIS,
            priority=priority,
            config_key=f"thresholds.{metric_name}",
            current_value=current_threshold,
            recommended_value=round(recommended_threshold, 3),
            justification=(
                f"Historical analysis of {len(all_values)} data points for {entity_id} "
                f"suggests threshold adjustment. Current threshold ({current_threshold}) "
                f"differs from recommended ({recommended_threshold:.3f}) by {threshold_diff:.1%}. "
                f"Mean: {mean_value:.3f}, Std: {std_value:.3f}."
            ),
            evidence=[
                {
                    "entity_id": entity_id,
                    "metric_name": metric_name,
                    "data_points": len(all_values),
                    "mean": mean_value,
                    "std": std_value,
                    "threshold_diff": threshold_diff,
                }
            ],
            expected_impact="Improved alert accuracy based on historical patterns",
        )
        
        self._recommendations.append(recommendation)
        
        logger.info(
            f"Generated historical analysis recommendation: {recommendation.recommendation_id}"
        )
        
        return recommendation
    
    # ========================================
    # RECOMMENDATION MANAGEMENT
    # ========================================
    
    def get_pending_recommendations(self) -> List[CalibrationRecommendation]:
        """Get all pending recommendations"""
        return [r for r in self._recommendations if r.status == RecommendationStatus.PENDING]
    
    def get_recommendations_by_source(
        self,
        source: CalibrationSource,
    ) -> List[CalibrationRecommendation]:
        """Get recommendations by source"""
        return [r for r in self._recommendations if r.source == source]
    
    def get_recommendations_by_priority(
        self,
        priority: RecommendationPriority,
    ) -> List[CalibrationRecommendation]:
        """Get recommendations by priority"""
        return [r for r in self._recommendations if r.priority == priority]
    
    def review_recommendation(
        self,
        recommendation_id: str,
        reviewed_by: str,
        accepted: bool,
        review_notes: str,
    ) -> Tuple[bool, str]:
        """
        Review a calibration recommendation.
        
        This is the human review step required for all recommendations.
        The system NEVER implements automatic changes.
        
        Args:
            recommendation_id: ID of the recommendation
            reviewed_by: User reviewing the recommendation
            accepted: Whether the recommendation is accepted
            review_notes: Notes from the reviewer
        
        Returns:
            Tuple of (success, message)
        """
        recommendation = self._get_recommendation(recommendation_id)
        if not recommendation:
            return False, f"Recommendation not found: {recommendation_id}"
        
        if recommendation.status != RecommendationStatus.PENDING:
            return False, f"Recommendation is not pending: {recommendation.status.value}"
        
        recommendation.reviewed_by = reviewed_by
        recommendation.reviewed_at = datetime.now()
        recommendation.review_notes = review_notes
        
        if accepted:
            recommendation.status = RecommendationStatus.ACCEPTED
            logger.info(f"Recommendation accepted: {recommendation_id} by {reviewed_by}")
            return True, "Recommendation accepted"
        else:
            recommendation.status = RecommendationStatus.REJECTED
            logger.info(f"Recommendation rejected: {recommendation_id} by {reviewed_by}")
            return True, "Recommendation rejected"
    
    def mark_implemented(
        self,
        recommendation_id: str,
    ) -> Tuple[bool, str]:
        """
        Mark a recommendation as implemented.
        
        This should be called after the configuration change has been
        applied through the proper approval workflow.
        
        Args:
            recommendation_id: ID of the recommendation
        
        Returns:
            Tuple of (success, message)
        """
        recommendation = self._get_recommendation(recommendation_id)
        if not recommendation:
            return False, f"Recommendation not found: {recommendation_id}"
        
        if recommendation.status != RecommendationStatus.ACCEPTED:
            return False, f"Recommendation is not accepted: {recommendation.status.value}"
        
        recommendation.status = RecommendationStatus.IMPLEMENTED
        
        logger.info(f"Recommendation marked as implemented: {recommendation_id}")
        return True, "Recommendation marked as implemented"
    
    def _get_recommendation(
        self,
        recommendation_id: str,
    ) -> Optional[CalibrationRecommendation]:
        """Get a recommendation by ID"""
        for rec in self._recommendations:
            if rec.recommendation_id == recommendation_id:
                return rec
        return None
    
    def get_all_recommendations(self) -> List[CalibrationRecommendation]:
        """Get all recommendations"""
        return sorted(self._recommendations, key=lambda r: r.created_at, reverse=True)
    
    def clear_historical_data(self) -> None:
        """Clear historical data (for testing)"""
        self._historical_data.clear()
    
    def clear_recommendations(self) -> None:
        """Clear recommendations (for testing)"""
        self._recommendations.clear()


# Global calibration recommender instance
calibration_recommender = CalibrationRecommender()


__all__ = [
    "CalibrationRecommender",
    "CalibrationRecommendation",
    "CalibrationSource",
    "RecommendationPriority",
    "RecommendationStatus",
    "HistoricalPerformanceData",
    "calibration_recommender",
]
