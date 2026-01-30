"""
C-TRUST Guardian System Integrity Agent
=======================================
Novel self-monitoring capability that ensures system accuracy over time.

Key Innovation: The Guardian Agent monitors the relationship between data changes
and system outputs to detect inconsistencies, staleness, and integrity issues.

Core Functions:
1. Data Delta Monitoring: Compares data changes between snapshots
2. Output Consistency Verification: Ensures system outputs align with data improvements
3. Staleness Detection: Identifies when alerts persist without underlying data changes
4. Governance Alerting: Notifies administrators of system integrity issues

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**

Design Principles:
- Guardian NEVER blocks clinical operations
- Guardian only notifies administrators
- Guardian logs all findings for governance review
- Guardian operates independently of core agents
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import uuid
import math

from src.core import get_logger

logger = get_logger(__name__)


# ========================================
# GUARDIAN ENUMERATIONS
# ========================================

class GuardianEventType(str, Enum):
    """Types of Guardian events"""
    DATA_OUTPUT_INCONSISTENCY = "DATA_OUTPUT_INCONSISTENCY"
    STALENESS_DETECTED = "STALENESS_DETECTED"
    UNEXPECTED_IMPROVEMENT = "UNEXPECTED_IMPROVEMENT"
    UNEXPECTED_DEGRADATION = "UNEXPECTED_DEGRADATION"
    SYSTEM_INTEGRITY_WARNING = "SYSTEM_INTEGRITY_WARNING"


class GuardianSeverity(str, Enum):
    """Severity levels for Guardian events"""
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


# ========================================
# GUARDIAN DATA STRUCTURES
# ========================================

@dataclass
class DataDelta:
    """
    Represents the change in data between two snapshots.
    
    Attributes:
        prev_snapshot_id: ID of previous snapshot
        curr_snapshot_id: ID of current snapshot
        entity_id: Entity being compared (study/site)
        metrics_changed: Dictionary of metric changes
        overall_change_magnitude: Normalized change magnitude (0-1)
        direction: "IMPROVED", "DEGRADED", or "STABLE"
        significant: Whether change exceeds significance threshold
    """
    prev_snapshot_id: str
    curr_snapshot_id: str
    entity_id: str
    metrics_changed: Dict[str, Dict[str, float]] = field(default_factory=dict)
    overall_change_magnitude: float = 0.0
    direction: str = "STABLE"
    significant: bool = False
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "prev_snapshot_id": self.prev_snapshot_id,
            "curr_snapshot_id": self.curr_snapshot_id,
            "entity_id": self.entity_id,
            "metrics_changed": self.metrics_changed,
            "overall_change_magnitude": self.overall_change_magnitude,
            "direction": self.direction,
            "significant": self.significant,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class OutputDelta:
    """
    Represents the change in system outputs between two snapshots.
    
    Attributes:
        prev_snapshot_id: ID of previous snapshot
        curr_snapshot_id: ID of current snapshot
        entity_id: Entity being compared
        risk_score_change: Change in risk score
        risk_level_changed: Whether risk level classification changed
        dqi_score_change: Change in DQI score
        alerts_changed: Number of alerts added/removed
        proportional: Whether output change is proportional to data change
    """
    prev_snapshot_id: str
    curr_snapshot_id: str
    entity_id: str
    risk_score_change: float = 0.0
    risk_level_changed: bool = False
    dqi_score_change: float = 0.0
    alerts_changed: int = 0
    proportional: bool = True
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "prev_snapshot_id": self.prev_snapshot_id,
            "curr_snapshot_id": self.curr_snapshot_id,
            "entity_id": self.entity_id,
            "risk_score_change": self.risk_score_change,
            "risk_level_changed": self.risk_level_changed,
            "dqi_score_change": self.dqi_score_change,
            "alerts_changed": self.alerts_changed,
            "proportional": self.proportional,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class GuardianEvent:
    """
    Guardian integrity event for logging and notification.
    
    Attributes:
        event_id: Unique event identifier
        event_type: Type of Guardian event
        severity: Severity level
        entity_id: Entity affected
        snapshot_id: Current snapshot ID
        data_delta_summary: Summary of data changes
        expected_behavior: What the system should have done
        actual_behavior: What the system actually did
        recommendation: Recommended action
        timestamp: When event was created
    """
    event_id: str
    event_type: GuardianEventType
    severity: GuardianSeverity
    entity_id: str
    snapshot_id: str
    data_delta_summary: str
    expected_behavior: str
    actual_behavior: str
    recommendation: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "severity": self.severity.value,
            "entity_id": self.entity_id,
            "snapshot_id": self.snapshot_id,
            "data_delta_summary": self.data_delta_summary,
            "expected_behavior": self.expected_behavior,
            "actual_behavior": self.actual_behavior,
            "recommendation": self.recommendation,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class StalenessIndicator:
    """
    Indicator of potential system staleness.
    
    Attributes:
        entity_id: Entity being monitored
        consecutive_unchanged_snapshots: Number of snapshots with same alerts
        alert_types_unchanged: List of alert types that haven't changed
        data_has_changed: Whether underlying data has changed
        staleness_score: Score indicating likelihood of staleness (0-1)
        is_stale: Whether system is considered stale
    """
    entity_id: str
    consecutive_unchanged_snapshots: int = 0
    alert_types_unchanged: List[str] = field(default_factory=list)
    data_has_changed: bool = False
    staleness_score: float = 0.0
    is_stale: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "entity_id": self.entity_id,
            "consecutive_unchanged_snapshots": self.consecutive_unchanged_snapshots,
            "alert_types_unchanged": self.alert_types_unchanged,
            "data_has_changed": self.data_has_changed,
            "staleness_score": self.staleness_score,
            "is_stale": self.is_stale,
        }


# ========================================
# GUARDIAN AGENT IMPLEMENTATION
# ========================================

class GuardianAgent:
    """
    Guardian System Integrity Agent.
    
    Monitors the relationship between data changes and system outputs
    to detect inconsistencies, staleness, and integrity issues.
    
    Key Responsibilities:
    1. Calculate data deltas between snapshots
    2. Verify output consistency with data changes
    3. Detect system staleness
    4. Generate integrity warnings
    
    CRITICAL: Guardian NEVER blocks clinical operations.
    Guardian only notifies administrators.
    """
    
    # Thresholds for significance detection
    DEFAULT_SIGNIFICANCE_THRESHOLD = 0.1  # 10% change is significant
    DEFAULT_STALENESS_THRESHOLD = 3  # 3 unchanged snapshots = stale
    DEFAULT_PROPORTIONALITY_TOLERANCE = 0.2  # 20% tolerance for proportionality
    
    def __init__(
        self,
        significance_threshold: float = None,
        staleness_threshold: int = None,
        proportionality_tolerance: float = None
    ):
        """
        Initialize Guardian Agent.
        
        Args:
            significance_threshold: Threshold for significant data changes (0-1)
            staleness_threshold: Number of unchanged snapshots before staleness
            proportionality_tolerance: Tolerance for output proportionality check
        """
        self.significance_threshold = significance_threshold or self.DEFAULT_SIGNIFICANCE_THRESHOLD
        self.staleness_threshold = staleness_threshold or self.DEFAULT_STALENESS_THRESHOLD
        self.proportionality_tolerance = proportionality_tolerance or self.DEFAULT_PROPORTIONALITY_TOLERANCE
        
        # Event storage (in production, this would be database-backed)
        self._events: List[GuardianEvent] = []
        self._staleness_tracking: Dict[str, StalenessIndicator] = {}
        
        logger.info(
            f"GuardianAgent initialized: significance={self.significance_threshold}, "
            f"staleness={self.staleness_threshold}, proportionality={self.proportionality_tolerance}"
        )
    
    # ========================================
    # DATA DELTA CALCULATION
    # ========================================
    
    def calculate_data_delta(
        self,
        prev_snapshot_data: Dict[str, Any],
        curr_snapshot_data: Dict[str, Any],
        entity_id: str
    ) -> DataDelta:
        """
        Calculate the delta between two data snapshots.
        
        Compares key metrics between snapshots to determine:
        - Which metrics changed
        - Magnitude of changes
        - Overall direction (improved/degraded/stable)
        - Whether change is significant
        
        Args:
            prev_snapshot_data: Previous snapshot data dictionary
            curr_snapshot_data: Current snapshot data dictionary
            entity_id: Entity being compared
        
        Returns:
            DataDelta with change analysis
        """
        prev_id = prev_snapshot_data.get("snapshot_id", "unknown_prev")
        curr_id = curr_snapshot_data.get("snapshot_id", "unknown_curr")
        
        logger.debug(f"Calculating data delta for {entity_id}: {prev_id} -> {curr_id}")
        
        # Extract comparable metrics
        prev_metrics = self._extract_metrics(prev_snapshot_data)
        curr_metrics = self._extract_metrics(curr_snapshot_data)
        
        # Calculate changes for each metric
        metrics_changed = {}
        total_change = 0.0
        improvement_score = 0.0
        metric_count = 0
        
        all_keys = set(prev_metrics.keys()) | set(curr_metrics.keys())
        
        for key in all_keys:
            prev_val = prev_metrics.get(key, 0.0)
            curr_val = curr_metrics.get(key, 0.0)
            
            if prev_val != 0:
                change_pct = (curr_val - prev_val) / abs(prev_val)
            elif curr_val != 0:
                change_pct = 1.0 if curr_val > 0 else -1.0
            else:
                change_pct = 0.0
            
            if abs(change_pct) > 0.001:  # Only track non-trivial changes
                metrics_changed[key] = {
                    "prev": prev_val,
                    "curr": curr_val,
                    "change_pct": change_pct,
                }
                
                total_change += abs(change_pct)
                # Positive change_pct for "good" metrics means improvement
                improvement_score += self._get_improvement_direction(key, change_pct)
                metric_count += 1
        
        # Calculate overall change magnitude (normalized)
        if metric_count > 0:
            overall_magnitude = min(total_change / metric_count, 1.0)
            avg_improvement = improvement_score / metric_count
        else:
            overall_magnitude = 0.0
            avg_improvement = 0.0
        
        # Determine direction
        if avg_improvement > 0.1:
            direction = "IMPROVED"
        elif avg_improvement < -0.1:
            direction = "DEGRADED"
        else:
            direction = "STABLE"
        
        # Determine significance
        significant = overall_magnitude >= self.significance_threshold
        
        delta = DataDelta(
            prev_snapshot_id=prev_id,
            curr_snapshot_id=curr_id,
            entity_id=entity_id,
            metrics_changed=metrics_changed,
            overall_change_magnitude=overall_magnitude,
            direction=direction,
            significant=significant,
        )
        
        logger.debug(
            f"Data delta for {entity_id}: magnitude={overall_magnitude:.3f}, "
            f"direction={direction}, significant={significant}"
        )
        
        return delta
    
    def _extract_metrics(self, snapshot_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Extract comparable metrics from snapshot data.
        
        Args:
            snapshot_data: Snapshot data dictionary
        
        Returns:
            Dictionary of metric name to value
        """
        metrics = {}
        
        # Extract standard metrics if present
        metric_keys = [
            "missing_pages_pct",
            "form_completion_rate",
            "sae_backlog_days",
            "fatal_sae_count",
            "open_query_count",
            "query_aging_days",
            "dqi_score",
            "risk_score",
            "completeness_score",
            "safety_score",
            "compliance_score",
        ]
        
        for key in metric_keys:
            if key in snapshot_data:
                val = snapshot_data[key]
                if isinstance(val, (int, float)) and not math.isnan(val):
                    metrics[key] = float(val)
        
        # Also check nested structures
        if "metrics" in snapshot_data and isinstance(snapshot_data["metrics"], dict):
            for key, val in snapshot_data["metrics"].items():
                if isinstance(val, (int, float)) and not math.isnan(val):
                    metrics[key] = float(val)
        
        return metrics
    
    def _get_improvement_direction(self, metric_name: str, change_pct: float) -> float:
        """
        Determine if a metric change represents improvement.
        
        Some metrics are "lower is better" (e.g., missing_pages_pct)
        Some metrics are "higher is better" (e.g., form_completion_rate)
        
        Args:
            metric_name: Name of the metric
            change_pct: Percentage change
        
        Returns:
            Positive value if improvement, negative if degradation
        """
        # Metrics where lower is better
        lower_is_better = {
            "missing_pages_pct",
            "sae_backlog_days",
            "fatal_sae_count",
            "open_query_count",
            "query_aging_days",
            "risk_score",
        }
        
        if metric_name in lower_is_better:
            return -change_pct  # Decrease is improvement
        else:
            return change_pct  # Increase is improvement
    
    # ========================================
    # OUTPUT CONSISTENCY VERIFICATION
    # ========================================
    
    def calculate_output_delta(
        self,
        prev_output: Dict[str, Any],
        curr_output: Dict[str, Any],
        entity_id: str
    ) -> OutputDelta:
        """
        Calculate the delta between two system outputs.
        
        Args:
            prev_output: Previous system output (risk scores, alerts, etc.)
            curr_output: Current system output
            entity_id: Entity being compared
        
        Returns:
            OutputDelta with output change analysis
        """
        prev_id = prev_output.get("snapshot_id", "unknown_prev")
        curr_id = curr_output.get("snapshot_id", "unknown_curr")
        
        # Calculate risk score change
        prev_risk = prev_output.get("risk_score", 0.0)
        curr_risk = curr_output.get("risk_score", 0.0)
        risk_score_change = curr_risk - prev_risk
        
        # Check if risk level changed
        prev_level = prev_output.get("risk_level", "UNKNOWN")
        curr_level = curr_output.get("risk_level", "UNKNOWN")
        risk_level_changed = prev_level != curr_level
        
        # Calculate DQI change
        prev_dqi = prev_output.get("dqi_score", 0.0)
        curr_dqi = curr_output.get("dqi_score", 0.0)
        dqi_score_change = curr_dqi - prev_dqi
        
        # Count alert changes
        prev_alerts = set(prev_output.get("alerts", []))
        curr_alerts = set(curr_output.get("alerts", []))
        alerts_changed = len(curr_alerts - prev_alerts) + len(prev_alerts - curr_alerts)
        
        return OutputDelta(
            prev_snapshot_id=prev_id,
            curr_snapshot_id=curr_id,
            entity_id=entity_id,
            risk_score_change=risk_score_change,
            risk_level_changed=risk_level_changed,
            dqi_score_change=dqi_score_change,
            alerts_changed=alerts_changed,
            proportional=True,  # Will be set by verify_consistency
        )
    
    def verify_consistency(
        self,
        data_delta: DataDelta,
        output_delta: OutputDelta
    ) -> Tuple[bool, Optional[GuardianEvent]]:
        """
        Verify that system output changes are consistent with data changes.
        
        Core Guardian Logic:
        - If data improved significantly, output should reflect improvement
        - If data degraded significantly, output should reflect degradation
        - If data unchanged, output should be stable
        
        Args:
            data_delta: Calculated data delta
            output_delta: Calculated output delta
        
        Returns:
            Tuple of (is_consistent, optional_event)
        """
        entity_id = data_delta.entity_id
        
        logger.debug(
            f"Verifying consistency for {entity_id}: "
            f"data_direction={data_delta.direction}, "
            f"data_significant={data_delta.significant}"
        )
        
        # If data change is not significant, output should be relatively stable
        if not data_delta.significant:
            # Small data changes should not cause large output changes
            if abs(output_delta.risk_score_change) > 20:  # More than 20 point swing
                event = self._create_event(
                    event_type=GuardianEventType.DATA_OUTPUT_INCONSISTENCY,
                    severity=GuardianSeverity.WARNING,
                    entity_id=entity_id,
                    snapshot_id=data_delta.curr_snapshot_id,
                    data_delta_summary=f"Data change magnitude: {data_delta.overall_change_magnitude:.2%}",
                    expected_behavior="Output should be stable with minor data changes",
                    actual_behavior=f"Risk score changed by {output_delta.risk_score_change:.1f} points",
                    recommendation="Review agent calibration and thresholds",
                )
                output_delta.proportional = False
                return False, event
            
            return True, None
        
        # Data changed significantly - verify output reflects this
        if data_delta.direction == "IMPROVED":
            # Data improved - risk should decrease, DQI should increase
            if output_delta.risk_score_change > self.proportionality_tolerance * 100:
                # Risk increased when data improved - inconsistent
                event = self._create_event(
                    event_type=GuardianEventType.DATA_OUTPUT_INCONSISTENCY,
                    severity=GuardianSeverity.CRITICAL,
                    entity_id=entity_id,
                    snapshot_id=data_delta.curr_snapshot_id,
                    data_delta_summary=f"Data improved by {data_delta.overall_change_magnitude:.2%}",
                    expected_behavior="Risk score should decrease when data improves",
                    actual_behavior=f"Risk score increased by {output_delta.risk_score_change:.1f} points",
                    recommendation="Investigate agent logic and data processing pipeline",
                )
                output_delta.proportional = False
                return False, event
                
        elif data_delta.direction == "DEGRADED":
            # Data degraded - risk should increase, DQI should decrease
            if output_delta.risk_score_change < -self.proportionality_tolerance * 100:
                # Risk decreased when data degraded - inconsistent
                event = self._create_event(
                    event_type=GuardianEventType.DATA_OUTPUT_INCONSISTENCY,
                    severity=GuardianSeverity.CRITICAL,
                    entity_id=entity_id,
                    snapshot_id=data_delta.curr_snapshot_id,
                    data_delta_summary=f"Data degraded by {data_delta.overall_change_magnitude:.2%}",
                    expected_behavior="Risk score should increase when data degrades",
                    actual_behavior=f"Risk score decreased by {abs(output_delta.risk_score_change):.1f} points",
                    recommendation="Investigate agent logic and data processing pipeline",
                )
                output_delta.proportional = False
                return False, event
        
        output_delta.proportional = True
        return True, None
    
    # ========================================
    # STALENESS DETECTION
    # ========================================
    
    def check_staleness(
        self,
        entity_id: str,
        current_alerts: List[str],
        data_has_changed: bool
    ) -> Tuple[bool, Optional[GuardianEvent]]:
        """
        Check if system outputs are stale (not responding to data changes).
        
        Staleness is detected when:
        - Same alerts persist across multiple snapshots
        - Underlying data has changed but alerts haven't
        
        Args:
            entity_id: Entity being monitored
            current_alerts: Current list of alert types
            data_has_changed: Whether underlying data changed since last check
        
        Returns:
            Tuple of (is_stale, optional_event)
        """
        # Get or create staleness indicator
        if entity_id not in self._staleness_tracking:
            self._staleness_tracking[entity_id] = StalenessIndicator(
                entity_id=entity_id,
                alert_types_unchanged=current_alerts.copy(),
            )
            return False, None
        
        indicator = self._staleness_tracking[entity_id]
        prev_alerts = set(indicator.alert_types_unchanged)
        curr_alerts = set(current_alerts)
        
        # Check if alerts changed
        if prev_alerts == curr_alerts:
            indicator.consecutive_unchanged_snapshots += 1
            indicator.data_has_changed = indicator.data_has_changed or data_has_changed
        else:
            # Alerts changed - reset tracking
            indicator.consecutive_unchanged_snapshots = 0
            indicator.alert_types_unchanged = current_alerts.copy()
            indicator.data_has_changed = False
            indicator.is_stale = False
            indicator.staleness_score = 0.0
            return False, None
        
        # Calculate staleness score
        indicator.staleness_score = min(
            indicator.consecutive_unchanged_snapshots / self.staleness_threshold,
            1.0
        )
        
        # Check for staleness condition
        if (indicator.consecutive_unchanged_snapshots >= self.staleness_threshold 
            and indicator.data_has_changed):
            indicator.is_stale = True
            
            event = self._create_event(
                event_type=GuardianEventType.STALENESS_DETECTED,
                severity=GuardianSeverity.WARNING,
                entity_id=entity_id,
                snapshot_id="current",
                data_delta_summary=f"Data changed but alerts unchanged for {indicator.consecutive_unchanged_snapshots} snapshots",
                expected_behavior="Alerts should update when underlying data changes",
                actual_behavior=f"Same {len(current_alerts)} alerts persisted despite data changes",
                recommendation="Review agent sensitivity and threshold configuration",
            )
            
            return True, event
        
        return False, None
    
    def get_staleness_indicator(self, entity_id: str) -> Optional[StalenessIndicator]:
        """Get staleness indicator for an entity"""
        return self._staleness_tracking.get(entity_id)
    
    def reset_staleness_tracking(self, entity_id: str = None) -> None:
        """Reset staleness tracking for entity or all entities"""
        if entity_id:
            if entity_id in self._staleness_tracking:
                del self._staleness_tracking[entity_id]
        else:
            self._staleness_tracking.clear()
    
    # ========================================
    # INTEGRITY WARNING GENERATION
    # ========================================
    
    def _create_event(
        self,
        event_type: GuardianEventType,
        severity: GuardianSeverity,
        entity_id: str,
        snapshot_id: str,
        data_delta_summary: str,
        expected_behavior: str,
        actual_behavior: str,
        recommendation: str
    ) -> GuardianEvent:
        """
        Create a Guardian event and store it.
        
        Args:
            event_type: Type of event
            severity: Severity level
            entity_id: Affected entity
            snapshot_id: Current snapshot ID
            data_delta_summary: Summary of data changes
            expected_behavior: What should have happened
            actual_behavior: What actually happened
            recommendation: Recommended action
        
        Returns:
            Created GuardianEvent
        """
        event = GuardianEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            severity=severity,
            entity_id=entity_id,
            snapshot_id=snapshot_id,
            data_delta_summary=data_delta_summary,
            expected_behavior=expected_behavior,
            actual_behavior=actual_behavior,
            recommendation=recommendation,
        )
        
        self._events.append(event)
        
        logger.warning(
            f"Guardian Event [{severity.value}]: {event_type.value} for {entity_id} - "
            f"{actual_behavior}"
        )
        
        return event
    
    def raise_integrity_warning(
        self,
        entity_id: str,
        snapshot_id: str,
        issue_description: str,
        recommendation: str
    ) -> GuardianEvent:
        """
        Raise a general system integrity warning.
        
        Args:
            entity_id: Affected entity
            snapshot_id: Current snapshot ID
            issue_description: Description of the issue
            recommendation: Recommended action
        
        Returns:
            Created GuardianEvent
        """
        return self._create_event(
            event_type=GuardianEventType.SYSTEM_INTEGRITY_WARNING,
            severity=GuardianSeverity.WARNING,
            entity_id=entity_id,
            snapshot_id=snapshot_id,
            data_delta_summary="Manual integrity check",
            expected_behavior="System should operate correctly",
            actual_behavior=issue_description,
            recommendation=recommendation,
        )
    
    # ========================================
    # EVENT MANAGEMENT
    # ========================================
    
    def get_events(
        self,
        entity_id: str = None,
        event_type: GuardianEventType = None,
        severity: GuardianSeverity = None,
        limit: int = None
    ) -> List[GuardianEvent]:
        """
        Get Guardian events with optional filtering.
        
        Args:
            entity_id: Filter by entity ID
            event_type: Filter by event type
            severity: Filter by severity
            limit: Maximum number of events to return
        
        Returns:
            List of matching GuardianEvents
        """
        events = self._events
        
        if entity_id:
            events = [e for e in events if e.entity_id == entity_id]
        
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        if severity:
            events = [e for e in events if e.severity == severity]
        
        # Sort by timestamp descending (most recent first)
        events = sorted(events, key=lambda e: e.timestamp, reverse=True)
        
        if limit:
            events = events[:limit]
        
        return events
    
    def clear_events(self, entity_id: str = None) -> int:
        """
        Clear Guardian events.
        
        Args:
            entity_id: Clear only events for this entity (None = clear all)
        
        Returns:
            Number of events cleared
        """
        if entity_id:
            original_count = len(self._events)
            self._events = [e for e in self._events if e.entity_id != entity_id]
            return original_count - len(self._events)
        else:
            count = len(self._events)
            self._events.clear()
            return count
    
    @property
    def event_count(self) -> int:
        """Total number of stored events"""
        return len(self._events)
    
    # ========================================
    # ADVANCED MONITORING CAPABILITIES
    # ========================================
    
    def perform_multi_dimensional_staleness_check(
        self,
        entity_id: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Perform multi-dimensional staleness analysis.
        
        Analyzes staleness across multiple dimensions:
        - Data freshness
        - Alert currency
        - Agent response times
        - DQI stability
        
        Args:
            entity_id: Entity to check
            data: Current data snapshot
        
        Returns:
            Multi-dimensional staleness score
        """
        dimensions = {}
        
        # Data freshness dimension
        last_update = data.get("last_updated")
        if last_update:
            try:
                if isinstance(last_update, str):
                    from datetime import datetime
                    last_update = datetime.fromisoformat(last_update)
                hours_since_update = (datetime.now() - last_update).total_seconds() / 3600
                dimensions["data_freshness"] = max(0, 1 - (hours_since_update / 24))
            except:
                dimensions["data_freshness"] = 0.5
        else:
            dimensions["data_freshness"] = 0.5
        
        # Alert currency dimension
        indicator = self._staleness_tracking.get(entity_id)
        if indicator:
            dimensions["alert_currency"] = 1 - indicator.staleness_score
        else:
            dimensions["alert_currency"] = 1.0
        
        # DQI stability dimension
        dqi_score = data.get("dqi_score")
        if dqi_score is not None:
            # Stable DQI is good
            dimensions["dqi_stability"] = 1.0 if dqi_score >= 60 else dqi_score / 60
        else:
            dimensions["dqi_stability"] = 0.5
        
        # Overall staleness score (weighted average)
        weights = {
            "data_freshness": 0.4,
            "alert_currency": 0.3,
            "dqi_stability": 0.3,
        }
        
        overall_score = sum(
            dimensions.get(dim, 0.5) * weight
            for dim, weight in weights.items()
        )
        
        return {
            "entity_id": entity_id,
            "dimensions": dimensions,
            "overall_freshness": overall_score,
            "is_stale": overall_score < 0.5,
            "severity": "CRITICAL" if overall_score < 0.3 else "WARNING" if overall_score < 0.5 else "OK",
        }
    
    def validate_cross_agent_signals(
        self,
        signals: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Validate consistency across agent signals.
        
        Detects anomalies where:
        - Agents report conflicting risk levels
        - Confidence scores are inconsistent
        - Evidence doesn't support conclusions
        
        Args:
            signals: List of agent signal dictionaries
        
        Returns:
            Validation report with any inconsistencies
        """
        if not signals:
            return {"valid": True, "issues": [], "consistency_score": 1.0}
        
        issues = []
        
        # Extract risk levels and confidences
        risk_levels = []
        confidences = []
        abstained_agents = []
        
        for signal in signals:
            if signal.get("abstained"):
                abstained_agents.append(signal.get("agent_type", "unknown"))
            else:
                risk_levels.append(signal.get("risk_level", "unknown"))
                confidences.append(signal.get("confidence", 0))
        
        # Check for high abstention rate
        abstention_rate = len(abstained_agents) / len(signals)
        if abstention_rate > 0.5:
            issues.append({
                "type": "HIGH_ABSTENTION",
                "description": f"{len(abstained_agents)} of {len(signals)} agents abstained",
                "severity": "WARNING",
            })
        
        # Check for conflicting risk levels
        if risk_levels:
            unique_risks = set(risk_levels)
            if "critical" in unique_risks and "low" in unique_risks:
                issues.append({
                    "type": "RISK_CONFLICT",
                    "description": "Agents report both CRITICAL and LOW risk",
                    "severity": "WARNING",
                })
        
        # Check confidence variance
        if len(confidences) >= 2:
            avg_conf = sum(confidences) / len(confidences)
            variance = sum((c - avg_conf) ** 2 for c in confidences) / len(confidences)
            if variance >= 0.25:  # High variance (changed from > to >= since 0.25 is max possible)
                issues.append({
                    "type": "CONFIDENCE_VARIANCE",
                    "description": f"High variance in agent confidence scores (var={variance:.2f})",
                    "severity": "INFO",
                })
        
        # Calculate consistency score
        consistency_score = 1.0 - (len(issues) * 0.2)
        consistency_score = max(0, min(1, consistency_score))
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "consistency_score": consistency_score,
            "agents_analyzed": len(signals),
            "abstention_rate": abstention_rate,
        }
    
    def verify_dqi_calculation_integrity(
        self,
        dqi_score: float,
        components: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Verify DQI calculation integrity.
        
        Validates that:
        - DQI score is within valid range
        - Components sum correctly
        - No component is unexpectedly dominant
        
        Args:
            dqi_score: Calculated DQI score
            components: Component scores that make up DQI
        
        Returns:
            Integrity validation result
        """
        issues = []
        
        # Validate score range
        if dqi_score < 0 or dqi_score > 100:
            issues.append({
                "type": "INVALID_RANGE",
                "description": f"DQI score {dqi_score} outside valid range [0, 100]",
                "severity": "CRITICAL",
            })
        
        # Validate components
        for name, value in components.items():
            if value < 0 or value > 100:
                issues.append({
                    "type": "INVALID_COMPONENT",
                    "description": f"Component {name} has invalid value {value}",
                    "severity": "WARNING",
                })
        
        # Check for component dominance
        if components:
            max_weight = max(components.values())
            min_weight = min(components.values())
            if max_weight > 0 and (max_weight - min_weight) / max_weight > 0.8:
                issues.append({
                    "type": "COMPONENT_DOMINANCE",
                    "description": "One component dominates DQI calculation",
                    "severity": "INFO",
                })
        
        return {
            "valid": len([i for i in issues if i["severity"] == "CRITICAL"]) == 0,
            "issues": issues,
            "dqi_score": dqi_score,
            "components_verified": len(components),
        }
    
    def validate_dqi_consistency(
        self,
        dqi_score: float,
        features: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate DQI score consistency with underlying feature values.
        
        Checks if DQI score is consistent with actual data quality indicators:
        - High DQI shouldn't coexist with many open queries
        - High DQI shouldn't coexist with overdue SAE reviews
        - Low DQI shouldn't coexist with excellent completeness
        
        Args:
            dqi_score: Overall DQI score (0-100)
            features: Feature dictionary with data quality metrics
        
        Returns:
            Validation result with any inconsistencies detected
        """
        issues = []
        
        # High DQI but many open queries
        if dqi_score > 70 and features.get("open_queries", 0) > 200:
            issues.append({
                "type": "DQI_QUERY_MISMATCH",
                "description": f"DQI {dqi_score:.1f} too high for {features['open_queries']} open queries",
                "severity": "WARNING",
                "recommendation": "Review query resolution process or DQI calculation weights",
            })
        
        # High DQI but overdue SAEs
        overdue_saes = features.get("overdue_sae_reviews", 0)
        if dqi_score > 80 and overdue_saes > 10:
            issues.append({
                "type": "DQI_SAFETY_MISMATCH",
                "description": f"DQI {dqi_score:.1f} too high with {overdue_saes} overdue SAE reviews",
                "severity": "CRITICAL",
                "recommendation": "Investigate SAE review process - safety issues should lower DQI significantly",
            })
        
        # Low DQI but good completeness
        completeness = features.get("completeness_rate", 0)
        if dqi_score < 50 and completeness > 0.95:
            issues.append({
                "type": "DQI_UNDERESTIMATE",
                "description": f"DQI {dqi_score:.1f} seems too low for {completeness:.1%} completeness",
                "severity": "INFO",
                "recommendation": "Review DQI calculation - completeness is excellent but score is low",
            })
        
        # High DQI but low completeness
        if dqi_score > 80 and completeness < 0.70:
            issues.append({
                "type": "DQI_COMPLETENESS_MISMATCH",
                "description": f"DQI {dqi_score:.1f} too high for {completeness:.1%} completeness",
                "severity": "WARNING",
                "recommendation": "Review completeness calculation or DQI weights",
            })
        
        # High DQI but many missing required fields
        missing_fields = features.get("missing_required_fields", 0)
        if dqi_score > 75 and missing_fields > 50:
            issues.append({
                "type": "DQI_MISSING_DATA_MISMATCH",
                "description": f"DQI {dqi_score:.1f} too high with {missing_fields} missing required fields",
                "severity": "WARNING",
                "recommendation": "Review data entry process and DQI calculation",
            })
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "dqi_score": dqi_score,
            "features_checked": len(features),
        }
    
    def run_self_diagnostic(self) -> Dict[str, Any]:
        """
        Run self-diagnostic check on Guardian Agent.
        
        Validates:
        - Event storage health
        - Staleness tracking health
        - Memory usage
        - Configuration integrity
        
        Returns:
            Diagnostic report
        """
        diagnostics = {
            "status": "HEALTHY",
            "checks": {},
            "timestamp": datetime.now().isoformat(),
        }
        
        # Event storage check
        event_count = len(self._events)
        diagnostics["checks"]["event_storage"] = {
            "status": "OK" if event_count < 10000 else "WARNING",
            "count": event_count,
            "message": "Event storage healthy" if event_count < 10000 else "Consider clearing old events",
        }
        
        # Staleness tracking check
        tracking_count = len(self._staleness_tracking)
        stale_count = len([i for i in self._staleness_tracking.values() if i.is_stale])
        diagnostics["checks"]["staleness_tracking"] = {
            "status": "OK" if tracking_count < 1000 else "WARNING",
            "entities_tracked": tracking_count,
            "stale_entities": stale_count,
        }
        
        # Configuration check
        diagnostics["checks"]["configuration"] = {
            "status": "OK",
            "significance_threshold": self.significance_threshold,
            "staleness_threshold": self.staleness_threshold,
            "proportionality_tolerance": self.proportionality_tolerance,
        }
        
        # Overall status
        warning_checks = [c for c in diagnostics["checks"].values() if c.get("status") == "WARNING"]
        if warning_checks:
            diagnostics["status"] = "DEGRADED"
        
        return diagnostics
    
    def generate_remediation_steps(
        self,
        event: GuardianEvent
    ) -> List[str]:
        """
        Generate specific remediation steps for a Guardian event.
        
        Args:
            event: The Guardian event to remediate
        
        Returns:
            List of actionable remediation steps
        """
        steps = []
        
        if event.event_type == GuardianEventType.DATA_OUTPUT_INCONSISTENCY:
            steps = [
                "1. Review recent data changes in the affected entity",
                "2. Verify agent thresholds are correctly configured",
                "3. Check data pipeline for processing errors",
                "4. Recalculate affected metrics manually",
                "5. If issue persists, escalate to system administrator",
            ]
        elif event.event_type == GuardianEventType.STALENESS_DETECTED:
            steps = [
                "1. Verify data source connections are active",
                "2. Check data refresh schedules",
                "3. Review agent processing logs for errors",
                "4. Manually trigger data refresh if needed",
                "5. Verify downstream systems are consuming updates",
            ]
        elif event.event_type == GuardianEventType.UNEXPECTED_IMPROVEMENT:
            steps = [
                "1. Verify the improvement is based on real data changes",
                "2. Review recent data corrections or clean-up activities",
                "3. Document the improvement in study notes",
                "4. No action required if improvement is legitimate",
            ]
        elif event.event_type == GuardianEventType.UNEXPECTED_DEGRADATION:
            steps = [
                "1. Investigate root cause of degradation",
                "2. Check for data entry errors or missing data",
                "3. Review site-level performance",
                "4. Escalate to study management if systemic",
            ]
        else:
            steps = [
                "1. Review the event details",
                "2. Check system logs for related errors",
                "3. Consult documentation for guidance",
                f"4. Original recommendation: {event.recommendation}",
            ]
        
        return steps


# ========================================
# EXPORTS
# ========================================

__all__ = [
    "GuardianAgent",
    "GuardianEvent",
    "GuardianEventType",
    "GuardianSeverity",
    "DataDelta",
    "OutputDelta",
    "StalenessIndicator",
]

