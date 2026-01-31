"""
C-TRUST System-Based Notification Engine
=========================================
Generates notifications based on C-TRUST system architecture:
- Guardian Agent integrity checks
- DQI score thresholds
- Agent signal patterns
- Consensus confidence levels
- Temporal drift detection
- Data quality anomalies

This replaces role-based notifications with intelligent system-driven alerts.

Key Features:
- Guardian-driven integrity alerts
- DQI threshold-based notifications
- Agent abstention pattern detection
- Consensus confidence monitoring
- Temporal drift alerts
- Automated severity classification
"""

import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set
import logging

from src.core import get_logger
from src.notifications.notification_engine import (
    Notification,
    NotificationPriority,
    NotificationType,
    NotificationStatus,
    UserRole,
)

logger = get_logger(__name__)


class SystemAlertType(str, Enum):
    """System-based alert types"""
    # Guardian Alerts
    GUARDIAN_INTEGRITY_FAILURE = "GUARDIAN_INTEGRITY_FAILURE"
    GUARDIAN_SEMANTIC_INCONSISTENCY = "GUARDIAN_SEMANTIC_INCONSISTENCY"
    GUARDIAN_STALENESS_DETECTED = "GUARDIAN_STALENESS_DETECTED"
    GUARDIAN_CACHE_ANOMALY = "GUARDIAN_CACHE_ANOMALY"
    
    # DQI Alerts
    DQI_CRITICAL_LOW = "DQI_CRITICAL_LOW"
    DQI_DECLINING_TREND = "DQI_DECLINING_TREND"
    DQI_DIMENSION_FAILURE = "DQI_DIMENSION_FAILURE"
    
    # Agent Alerts
    AGENT_HIGH_ABSTENTION = "AGENT_HIGH_ABSTENTION"
    AGENT_CONSENSUS_FAILURE = "AGENT_CONSENSUS_FAILURE"
    AGENT_SIGNAL_ANOMALY = "AGENT_SIGNAL_ANOMALY"
    AGENT_CONFIDENCE_LOW = "AGENT_CONFIDENCE_LOW"
    
    # Temporal Alerts
    TEMPORAL_DRIFT_DETECTED = "TEMPORAL_DRIFT_DETECTED"
    TEMPORAL_PATTERN_BREAK = "TEMPORAL_PATTERN_BREAK"
    
    # Data Quality Alerts
    DATA_COMPLETENESS_LOW = "DATA_COMPLETENESS_LOW"
    DATA_CONSISTENCY_ISSUE = "DATA_CONSISTENCY_ISSUE"
    DATA_FRESHNESS_STALE = "DATA_FRESHNESS_STALE"


class SystemAlertSeverity(str, Enum):
    """Severity levels based on system impact"""
    CRITICAL = "CRITICAL"  # System integrity compromised
    HIGH = "HIGH"          # Significant quality degradation
    MEDIUM = "MEDIUM"      # Quality concern requiring attention
    LOW = "LOW"            # Informational, monitoring needed


@dataclass
class SystemAlert:
    """
    System-generated alert based on C-TRUST architecture.
    
    Attributes:
        alert_id: Unique identifier
        alert_type: Type of system alert
        severity: Severity level
        title: Alert title
        message: Detailed message
        entity_id: Related entity (study, site, subject)
        entity_type: Type of entity
        source_component: Which system component generated this
        metrics: Relevant metrics
        evidence: Supporting evidence
        recommended_actions: System-recommended actions
        created_at: When alert was created
        threshold_violated: Which threshold was violated
        metadata: Additional context
    """
    alert_id: str
    alert_type: SystemAlertType
    severity: SystemAlertSeverity
    title: str
    message: str
    entity_id: str
    entity_type: str = "STUDY"
    source_component: str = "GUARDIAN"
    metrics: Dict[str, float] = field(default_factory=dict)
    evidence: List[str] = field(default_factory=list)
    recommended_actions: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    threshold_violated: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_notification(self) -> Notification:
        """Convert system alert to notification"""
        # Map severity to priority
        priority_map = {
            SystemAlertSeverity.CRITICAL: NotificationPriority.CRITICAL,
            SystemAlertSeverity.HIGH: NotificationPriority.HIGH,
            SystemAlertSeverity.MEDIUM: NotificationPriority.MEDIUM,
            SystemAlertSeverity.LOW: NotificationPriority.LOW,
        }
        
        # Map alert type to notification type
        if "GUARDIAN" in self.alert_type.value:
            notif_type = NotificationType.GUARDIAN_ALERT
        elif "DQI" in self.alert_type.value:
            notif_type = NotificationType.DATA_QUALITY_GAP
        elif "AGENT" in self.alert_type.value:
            notif_type = NotificationType.SYSTEM_INTEGRITY
        elif "TEMPORAL" in self.alert_type.value:
            notif_type = NotificationType.DATA_VALIDATION
        else:
            notif_type = NotificationType.DATA_QUALITY_GAP
        
        # Determine target roles based on severity and type
        target_roles = self._determine_target_roles()
        
        return Notification(
            notification_id=self.alert_id,
            notification_type=notif_type,
            priority=priority_map[self.severity],
            title=self.title,
            message=self.message,
            entity_id=self.entity_id,
            entity_type=self.entity_type,
            target_roles=target_roles,
            evidence=self.evidence,
            recommended_actions=self.recommended_actions,
            metadata={
                **self.metadata,
                "alert_type": self.alert_type.value,
                "source_component": self.source_component,
                "metrics": self.metrics,
                "threshold_violated": self.threshold_violated,
            },
        )
    
    def _determine_target_roles(self) -> List[UserRole]:
        """Determine which roles should receive this alert"""
        # Critical alerts go to everyone
        if self.severity == SystemAlertSeverity.CRITICAL:
            return [UserRole.STUDY_LEAD, UserRole.DATA_MANAGER, UserRole.CRA]
        
        # Guardian alerts go to admin and study lead
        if "GUARDIAN" in self.alert_type.value:
            return [UserRole.ADMIN, UserRole.STUDY_LEAD]
        
        # DQI alerts go to data manager and study lead
        if "DQI" in self.alert_type.value:
            return [UserRole.DATA_MANAGER, UserRole.STUDY_LEAD]
        
        # Agent alerts go to admin
        if "AGENT" in self.alert_type.value:
            return [UserRole.ADMIN, UserRole.DATA_MANAGER]
        
        # Data quality alerts go to data manager and CRA
        if "DATA" in self.alert_type.value:
            return [UserRole.DATA_MANAGER, UserRole.CRA]
        
        # Default to data manager
        return [UserRole.DATA_MANAGER]


class SystemBasedNotificationEngine:
    """
    Generates notifications based on C-TRUST system architecture.
    
    Monitors:
    - Guardian integrity checks
    - DQI scores and trends
    - Agent signals and consensus
    - Temporal patterns
    - Data quality metrics
    """
    
    # Thresholds for alert generation
    DQI_CRITICAL_THRESHOLD = 40.0  # DQI below this is critical
    DQI_WARNING_THRESHOLD = 60.0   # DQI below this is warning
    AGENT_ABSTENTION_THRESHOLD = 0.5  # >50% abstention is concerning
    CONSENSUS_CONFIDENCE_THRESHOLD = 0.6  # <60% confidence is low
    GUARDIAN_INTEGRITY_THRESHOLD = 0.7  # <70% integrity is concerning
    
    def __init__(self):
        """Initialize system-based notification engine"""
        self._alert_counter = 0
        self._lock = threading.Lock()
        self._alerts: Dict[str, SystemAlert] = {}
        
        logger.info("SystemBasedNotificationEngine initialized")
    
    def _generate_alert_id(self) -> str:
        """Generate unique alert ID"""
        with self._lock:
            self._alert_counter += 1
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            return f"SYSALERT_{timestamp}_{self._alert_counter:06d}"
    
    def check_guardian_status(
        self,
        study_id: str,
        integrity_score: float,
        active_alerts: int,
        failed_checks: List[str],
        system_health: Dict[str, Any],
    ) -> List[SystemAlert]:
        """
        Check Guardian status and generate alerts.
        
        Args:
            study_id: Study identifier
            integrity_score: Guardian integrity score (0-1)
            active_alerts: Number of active Guardian alerts
            failed_checks: List of failed integrity checks
            system_health: System health metrics
        
        Returns:
            List of generated alerts
        """
        alerts = []
        
        # Critical: Integrity score below threshold
        if integrity_score < self.GUARDIAN_INTEGRITY_THRESHOLD:
            alert = SystemAlert(
                alert_id=self._generate_alert_id(),
                alert_type=SystemAlertType.GUARDIAN_INTEGRITY_FAILURE,
                severity=SystemAlertSeverity.CRITICAL if integrity_score < 0.5 else SystemAlertSeverity.HIGH,
                title=f"Guardian Integrity Failure - Study {study_id}",
                message=f"Guardian integrity score ({integrity_score:.1%}) is below acceptable threshold. "
                        f"System integrity may be compromised. {len(failed_checks)} checks failed.",
                entity_id=study_id,
                entity_type="STUDY",
                source_component="GUARDIAN",
                metrics={
                    "integrity_score": integrity_score,
                    "active_alerts": active_alerts,
                    "failed_checks_count": len(failed_checks),
                },
                evidence=failed_checks[:5],  # Top 5 failed checks
                recommended_actions=[
                    "Review Guardian report for detailed findings",
                    "Investigate failed integrity checks",
                    "Verify data pipeline health",
                    "Check for system anomalies",
                ],
                threshold_violated=f"integrity_score < {self.GUARDIAN_INTEGRITY_THRESHOLD}",
            )
            alerts.append(alert)
            self._alerts[alert.alert_id] = alert
        
        # Semantic inconsistency detected
        semantic_score = system_health.get("semantic_consistency_score", 1.0)
        if semantic_score < 0.8:
            alert = SystemAlert(
                alert_id=self._generate_alert_id(),
                alert_type=SystemAlertType.GUARDIAN_SEMANTIC_INCONSISTENCY,
                severity=SystemAlertSeverity.HIGH,
                title=f"Semantic Inconsistency Detected - Study {study_id}",
                message=f"Semantic consistency score ({semantic_score:.1%}) indicates data inconsistencies. "
                        f"Cross-agent validation may be failing.",
                entity_id=study_id,
                entity_type="STUDY",
                source_component="GUARDIAN",
                metrics={"semantic_consistency_score": semantic_score},
                evidence=[f"Semantic consistency: {semantic_score:.1%}"],
                recommended_actions=[
                    "Review cross-agent validation results",
                    "Check for data transformation errors",
                    "Verify feature extraction consistency",
                ],
                threshold_violated="semantic_consistency_score < 0.8",
            )
            alerts.append(alert)
            self._alerts[alert.alert_id] = alert
        
        # Staleness detected
        stale_count = system_health.get("stale_files_count", 0)
        if stale_count > 0:
            alert = SystemAlert(
                alert_id=self._generate_alert_id(),
                alert_type=SystemAlertType.GUARDIAN_STALENESS_DETECTED,
                severity=SystemAlertSeverity.MEDIUM,
                title=f"Stale Data Detected - Study {study_id}",
                message=f"{stale_count} stale data files detected. Data freshness may be compromised.",
                entity_id=study_id,
                entity_type="STUDY",
                source_component="GUARDIAN",
                metrics={"stale_files_count": stale_count},
                evidence=[f"{stale_count} stale files"],
                recommended_actions=[
                    "Review data ingestion pipeline",
                    "Check for delayed data updates",
                    "Verify data source connectivity",
                ],
            )
            alerts.append(alert)
            self._alerts[alert.alert_id] = alert
        
        return alerts
    
    def check_dqi_score(
        self,
        study_id: str,
        dqi_score: float,
        dimension_scores: Dict[str, float],
        risk_level: str,
    ) -> List[SystemAlert]:
        """
        Check DQI score and generate alerts.
        
        Args:
            study_id: Study identifier
            dqi_score: Overall DQI score (0-100)
            dimension_scores: Scores by dimension
            risk_level: Risk level classification
        
        Returns:
            List of generated alerts
        """
        alerts = []
        
        # Critical: DQI below critical threshold
        if dqi_score < self.DQI_CRITICAL_THRESHOLD:
            alert = SystemAlert(
                alert_id=self._generate_alert_id(),
                alert_type=SystemAlertType.DQI_CRITICAL_LOW,
                severity=SystemAlertSeverity.CRITICAL,
                title=f"Critical DQI Score - Study {study_id}",
                message=f"DQI score ({dqi_score:.1f}/100) is critically low. "
                        f"Data quality is severely compromised. Risk level: {risk_level}",
                entity_id=study_id,
                entity_type="STUDY",
                source_component="DQI_ENGINE",
                metrics={
                    "dqi_score": dqi_score,
                    **dimension_scores,
                },
                evidence=[
                    f"Overall DQI: {dqi_score:.1f}/100",
                    f"Risk Level: {risk_level}",
                    *[f"{dim}: {score:.1f}" for dim, score in dimension_scores.items() if score < 50],
                ],
                recommended_actions=[
                    "Immediate data quality review required",
                    "Investigate low-scoring dimensions",
                    "Review data collection processes",
                    "Consider data remediation plan",
                ],
                threshold_violated=f"dqi_score < {self.DQI_CRITICAL_THRESHOLD}",
            )
            alerts.append(alert)
            self._alerts[alert.alert_id] = alert
        
        # Warning: DQI below warning threshold
        elif dqi_score < self.DQI_WARNING_THRESHOLD:
            alert = SystemAlert(
                alert_id=self._generate_alert_id(),
                alert_type=SystemAlertType.DQI_DECLINING_TREND,
                severity=SystemAlertSeverity.HIGH,
                title=f"Low DQI Score - Study {study_id}",
                message=f"DQI score ({dqi_score:.1f}/100) is below acceptable threshold. "
                        f"Data quality requires attention.",
                entity_id=study_id,
                entity_type="STUDY",
                source_component="DQI_ENGINE",
                metrics={
                    "dqi_score": dqi_score,
                    **dimension_scores,
                },
                evidence=[
                    f"Overall DQI: {dqi_score:.1f}/100",
                    *[f"{dim}: {score:.1f}" for dim, score in dimension_scores.items() if score < 60],
                ],
                recommended_actions=[
                    "Review data quality metrics",
                    "Identify improvement opportunities",
                    "Monitor DQI trend",
                ],
                threshold_violated=f"dqi_score < {self.DQI_WARNING_THRESHOLD}",
            )
            alerts.append(alert)
            self._alerts[alert.alert_id] = alert
        
        # Check individual dimensions
        for dimension, score in dimension_scores.items():
            if score < 40:
                alert = SystemAlert(
                    alert_id=self._generate_alert_id(),
                    alert_type=SystemAlertType.DQI_DIMENSION_FAILURE,
                    severity=SystemAlertSeverity.HIGH,
                    title=f"DQI Dimension Failure: {dimension} - Study {study_id}",
                    message=f"DQI dimension '{dimension}' score ({score:.1f}/100) is critically low.",
                    entity_id=study_id,
                    entity_type="STUDY",
                    source_component="DQI_ENGINE",
                    metrics={dimension: score},
                    evidence=[f"{dimension}: {score:.1f}/100"],
                    recommended_actions=[
                        f"Focus on improving {dimension}",
                        "Review dimension-specific data quality",
                        "Implement targeted improvements",
                    ],
                    threshold_violated=f"{dimension}_score < 40",
                )
                alerts.append(alert)
                self._alerts[alert.alert_id] = alert
        
        return alerts
    
    def check_agent_signals(
        self,
        study_id: str,
        agent_signals: Dict[str, Any],
        consensus_confidence: float,
        agents_abstained: int,
        total_agents: int,
    ) -> List[SystemAlert]:
        """
        Check agent signals and generate alerts.
        
        Args:
            study_id: Study identifier
            agent_signals: Agent signal results
            consensus_confidence: Consensus confidence level
            agents_abstained: Number of agents that abstained
            total_agents: Total number of agents
        
        Returns:
            List of generated alerts
        """
        alerts = []
        
        # High abstention rate
        abstention_rate = agents_abstained / total_agents if total_agents > 0 else 0
        if abstention_rate > self.AGENT_ABSTENTION_THRESHOLD:
            alert = SystemAlert(
                alert_id=self._generate_alert_id(),
                alert_type=SystemAlertType.AGENT_HIGH_ABSTENTION,
                severity=SystemAlertSeverity.HIGH,
                title=f"High Agent Abstention Rate - Study {study_id}",
                message=f"{agents_abstained}/{total_agents} agents abstained ({abstention_rate:.1%}). "
                        f"Insufficient data for reliable analysis.",
                entity_id=study_id,
                entity_type="STUDY",
                source_component="AGENT_LAYER",
                metrics={
                    "abstention_rate": abstention_rate,
                    "agents_abstained": agents_abstained,
                    "total_agents": total_agents,
                },
                evidence=[f"Abstention rate: {abstention_rate:.1%}"],
                recommended_actions=[
                    "Review data completeness",
                    "Check feature extraction",
                    "Verify agent requirements are met",
                    "Consider data enrichment",
                ],
                threshold_violated=f"abstention_rate > {self.AGENT_ABSTENTION_THRESHOLD}",
            )
            alerts.append(alert)
            self._alerts[alert.alert_id] = alert
        
        # Low consensus confidence
        if consensus_confidence < self.CONSENSUS_CONFIDENCE_THRESHOLD:
            alert = SystemAlert(
                alert_id=self._generate_alert_id(),
                alert_type=SystemAlertType.AGENT_CONFIDENCE_LOW,
                severity=SystemAlertSeverity.MEDIUM,
                title=f"Low Consensus Confidence - Study {study_id}",
                message=f"Consensus confidence ({consensus_confidence:.1%}) is below threshold. "
                        f"Agent agreement is low.",
                entity_id=study_id,
                entity_type="STUDY",
                source_component="CONSENSUS_LAYER",
                metrics={"consensus_confidence": consensus_confidence},
                evidence=[f"Consensus confidence: {consensus_confidence:.1%}"],
                recommended_actions=[
                    "Review agent signal patterns",
                    "Check for conflicting signals",
                    "Verify data quality",
                    "Consider manual review",
                ],
                threshold_violated=f"consensus_confidence < {self.CONSENSUS_CONFIDENCE_THRESHOLD}",
            )
            alerts.append(alert)
            self._alerts[alert.alert_id] = alert
        
        return alerts
    
    def check_temporal_patterns(
        self,
        study_id: str,
        drift_detected: bool,
        drift_magnitude: float,
        pattern_breaks: List[str],
    ) -> List[SystemAlert]:
        """
        Check temporal patterns and generate alerts.
        
        Args:
            study_id: Study identifier
            drift_detected: Whether drift was detected
            drift_magnitude: Magnitude of drift
            pattern_breaks: List of pattern breaks
        
        Returns:
            List of generated alerts
        """
        alerts = []
        
        if drift_detected and drift_magnitude > 0.3:
            alert = SystemAlert(
                alert_id=self._generate_alert_id(),
                alert_type=SystemAlertType.TEMPORAL_DRIFT_DETECTED,
                severity=SystemAlertSeverity.HIGH if drift_magnitude > 0.5 else SystemAlertSeverity.MEDIUM,
                title=f"Temporal Drift Detected - Study {study_id}",
                message=f"Significant temporal drift detected (magnitude: {drift_magnitude:.2f}). "
                        f"Data patterns have changed over time.",
                entity_id=study_id,
                entity_type="STUDY",
                source_component="TEMPORAL_LAYER",
                metrics={"drift_magnitude": drift_magnitude},
                evidence=[f"Drift magnitude: {drift_magnitude:.2f}"],
                recommended_actions=[
                    "Review temporal trends",
                    "Check for protocol changes",
                    "Verify data collection consistency",
                    "Investigate pattern changes",
                ],
                threshold_violated="drift_magnitude > 0.3",
            )
            alerts.append(alert)
            self._alerts[alert.alert_id] = alert
        
        return alerts
    
    def get_alert(self, alert_id: str) -> Optional[SystemAlert]:
        """Get alert by ID"""
        return self._alerts.get(alert_id)
    
    def get_active_alerts(
        self,
        entity_id: Optional[str] = None,
        severity: Optional[SystemAlertSeverity] = None,
    ) -> List[SystemAlert]:
        """
        Get active alerts with optional filters.
        
        Args:
            entity_id: Filter by entity
            severity: Filter by severity
        
        Returns:
            List of matching alerts
        """
        alerts = list(self._alerts.values())
        
        if entity_id:
            alerts = [a for a in alerts if a.entity_id == entity_id]
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        # Sort by severity and creation time
        severity_order = {
            SystemAlertSeverity.CRITICAL: 0,
            SystemAlertSeverity.HIGH: 1,
            SystemAlertSeverity.MEDIUM: 2,
            SystemAlertSeverity.LOW: 3,
        }
        
        alerts.sort(
            key=lambda a: (severity_order.get(a.severity, 4), a.created_at),
            reverse=False
        )
        
        return alerts
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get alert statistics"""
        total = len(self._alerts)
        by_type = {}
        by_severity = {}
        by_component = {}
        
        for alert in self._alerts.values():
            # By type
            type_key = alert.alert_type.value
            by_type[type_key] = by_type.get(type_key, 0) + 1
            
            # By severity
            severity_key = alert.severity.value
            by_severity[severity_key] = by_severity.get(severity_key, 0) + 1
            
            # By component
            component_key = alert.source_component
            by_component[component_key] = by_component.get(component_key, 0) + 1
        
        return {
            "total_alerts": total,
            "by_type": by_type,
            "by_severity": by_severity,
            "by_component": by_component,
        }


__all__ = [
    "SystemBasedNotificationEngine",
    "SystemAlert",
    "SystemAlertType",
    "SystemAlertSeverity",
]
