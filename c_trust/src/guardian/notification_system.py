"""
C-TRUST Guardian Notification System
====================================
Administrator-only notification routing for Guardian integrity events.

Key Features:
- Routes Guardian events ONLY to administrators
- Never interferes with clinical operations
- Provides comprehensive event logging
- Supports multiple notification channels

Design Principles:
1. Guardian notifications go ONLY to system administrators
2. Guardian NEVER blocks or delays clinical operations
3. All events are logged for governance review
4. Notifications are non-blocking and asynchronous
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
import uuid
import logging

from src.core import get_logger
from src.guardian.guardian_agent import (
    GuardianEvent,
    GuardianEventType,
    GuardianSeverity,
)

logger = get_logger(__name__)


# ========================================
# NOTIFICATION ENUMERATIONS
# ========================================

class NotificationChannel(str, Enum):
    """Available notification channels"""
    LOG = "LOG"           # System log (always enabled)
    DATABASE = "DATABASE" # Database storage
    EMAIL = "EMAIL"       # Email notification (future)
    WEBHOOK = "WEBHOOK"   # Webhook callback (future)
    DASHBOARD = "DASHBOARD"  # Dashboard alert


class NotificationStatus(str, Enum):
    """Status of a notification"""
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    ACKNOWLEDGED = "ACKNOWLEDGED"


# ========================================
# NOTIFICATION DATA STRUCTURES
# ========================================

@dataclass
class GuardianNotification:
    """
    Notification generated from a Guardian event.
    
    Attributes:
        notification_id: Unique notification identifier
        event: The Guardian event that triggered this notification
        channel: Notification channel used
        status: Current status of the notification
        recipient_role: Role of recipient (always ADMINISTRATOR for Guardian)
        recipient_id: Optional specific recipient ID
        sent_at: When notification was sent
        acknowledged_at: When notification was acknowledged
        acknowledged_by: Who acknowledged the notification
        metadata: Additional notification metadata
    """
    notification_id: str
    event: GuardianEvent
    channel: NotificationChannel
    status: NotificationStatus = NotificationStatus.PENDING
    recipient_role: str = "ADMINISTRATOR"  # Guardian ONLY notifies admins
    recipient_id: Optional[str] = None
    sent_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "notification_id": self.notification_id,
            "event": self.event.to_dict(),
            "channel": self.channel.value,
            "status": self.status.value,
            "recipient_role": self.recipient_role,
            "recipient_id": self.recipient_id,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "acknowledged_by": self.acknowledged_by,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class IntegrityEventLog:
    """
    Detailed log entry for Guardian integrity events.
    
    Used for governance review and audit trails.
    
    Attributes:
        log_id: Unique log identifier
        event: The Guardian event
        comparison_data: Detailed comparison data for review
        system_state: System state at time of event
        recommended_actions: List of recommended actions
        logged_at: When the event was logged
    """
    log_id: str
    event: GuardianEvent
    comparison_data: Dict[str, Any] = field(default_factory=dict)
    system_state: Dict[str, Any] = field(default_factory=dict)
    recommended_actions: List[str] = field(default_factory=list)
    logged_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "log_id": self.log_id,
            "event": self.event.to_dict(),
            "comparison_data": self.comparison_data,
            "system_state": self.system_state,
            "recommended_actions": self.recommended_actions,
            "logged_at": self.logged_at.isoformat(),
        }


# ========================================
# GUARDIAN NOTIFICATION SYSTEM
# ========================================

class GuardianNotificationSystem:
    """
    Notification system for Guardian integrity events.
    
    CRITICAL DESIGN PRINCIPLES:
    1. Guardian notifications go ONLY to system administrators
    2. Guardian NEVER blocks clinical operations
    3. All events are logged for governance review
    4. Notifications are non-blocking
    
    This system ensures that Guardian findings are properly communicated
    to administrators while never interfering with clinical workflows.
    """
    
    def __init__(
        self,
        enabled_channels: List[NotificationChannel] = None,
        admin_recipients: List[str] = None
    ):
        """
        Initialize Guardian notification system.
        
        Args:
            enabled_channels: List of enabled notification channels
            admin_recipients: List of administrator IDs to notify
        """
        # Default to LOG and DATABASE channels
        self.enabled_channels = enabled_channels or [
            NotificationChannel.LOG,
            NotificationChannel.DATABASE,
            NotificationChannel.DASHBOARD,
        ]
        
        self.admin_recipients = admin_recipients or []
        
        # Storage for notifications and logs
        self._notifications: List[GuardianNotification] = []
        self._event_logs: List[IntegrityEventLog] = []
        
        # Channel handlers (extensible for future channels)
        self._channel_handlers: Dict[NotificationChannel, Callable] = {
            NotificationChannel.LOG: self._handle_log_notification,
            NotificationChannel.DATABASE: self._handle_database_notification,
            NotificationChannel.DASHBOARD: self._handle_dashboard_notification,
        }
        
        logger.info(
            f"GuardianNotificationSystem initialized with channels: "
            f"{[c.value for c in self.enabled_channels]}"
        )
    
    # ========================================
    # NOTIFICATION ROUTING
    # ========================================
    
    def notify_administrators(
        self,
        event: GuardianEvent,
        comparison_data: Dict[str, Any] = None,
        system_state: Dict[str, Any] = None
    ) -> List[GuardianNotification]:
        """
        Send notifications to administrators for a Guardian event.
        
        This method:
        1. Creates notifications for all enabled channels
        2. Logs the event for governance review
        3. Routes to administrators ONLY
        4. Never blocks - failures are logged but don't raise exceptions
        
        Args:
            event: The Guardian event to notify about
            comparison_data: Optional detailed comparison data
            system_state: Optional system state information
        
        Returns:
            List of created notifications
        """
        notifications = []
        
        # Log the event first (always happens)
        self._log_integrity_event(event, comparison_data, system_state)
        
        # Create notifications for each enabled channel
        for channel in self.enabled_channels:
            try:
                notification = self._create_notification(event, channel)
                
                # Route through channel handler
                handler = self._channel_handlers.get(channel)
                if handler:
                    success = handler(notification)
                    notification.status = (
                        NotificationStatus.SENT if success 
                        else NotificationStatus.FAILED
                    )
                    notification.sent_at = datetime.now()
                
                self._notifications.append(notification)
                notifications.append(notification)
                
            except Exception as e:
                # CRITICAL: Never block on notification failures
                logger.error(
                    f"Failed to send Guardian notification via {channel.value}: {e}"
                )
                # Create failed notification record
                notification = self._create_notification(event, channel)
                notification.status = NotificationStatus.FAILED
                notification.metadata["error"] = str(e)
                self._notifications.append(notification)
                notifications.append(notification)
        
        logger.info(
            f"Guardian notifications sent for event {event.event_id}: "
            f"{len([n for n in notifications if n.status == NotificationStatus.SENT])} sent, "
            f"{len([n for n in notifications if n.status == NotificationStatus.FAILED])} failed"
        )
        
        return notifications
    
    def _create_notification(
        self,
        event: GuardianEvent,
        channel: NotificationChannel
    ) -> GuardianNotification:
        """Create a notification for a Guardian event"""
        return GuardianNotification(
            notification_id=str(uuid.uuid4()),
            event=event,
            channel=channel,
            recipient_role="ADMINISTRATOR",  # Always admin for Guardian
        )

    
    # ========================================
    # CHANNEL HANDLERS
    # ========================================
    
    def _handle_log_notification(self, notification: GuardianNotification) -> bool:
        """
        Handle LOG channel notification.
        
        Writes detailed notification to system log.
        """
        event = notification.event
        
        log_message = (
            f"GUARDIAN INTEGRITY EVENT [{event.severity.value}]\n"
            f"  Type: {event.event_type.value}\n"
            f"  Entity: {event.entity_id}\n"
            f"  Snapshot: {event.snapshot_id}\n"
            f"  Data Delta: {event.data_delta_summary}\n"
            f"  Expected: {event.expected_behavior}\n"
            f"  Actual: {event.actual_behavior}\n"
            f"  Recommendation: {event.recommendation}"
        )
        
        # Use appropriate log level based on severity
        if event.severity == GuardianSeverity.CRITICAL:
            logger.critical(log_message)
        elif event.severity == GuardianSeverity.WARNING:
            logger.warning(log_message)
        else:
            logger.info(log_message)
        
        return True
    
    def _handle_database_notification(self, notification: GuardianNotification) -> bool:
        """
        Handle DATABASE channel notification.
        
        Stores notification in database for persistence.
        In production, this would use the actual database.
        """
        # In production, this would persist to database
        # For now, we just track in memory
        notification.metadata["stored_in_db"] = True
        notification.metadata["db_timestamp"] = datetime.now().isoformat()
        
        logger.debug(
            f"Guardian notification {notification.notification_id} stored in database"
        )
        
        return True
    
    def _handle_dashboard_notification(self, notification: GuardianNotification) -> bool:
        """
        Handle DASHBOARD channel notification.
        
        Prepares notification for display in admin dashboard.
        """
        # Mark for dashboard display
        notification.metadata["dashboard_visible"] = True
        notification.metadata["dashboard_priority"] = (
            "HIGH" if notification.event.severity == GuardianSeverity.CRITICAL
            else "MEDIUM" if notification.event.severity == GuardianSeverity.WARNING
            else "LOW"
        )
        
        logger.debug(
            f"Guardian notification {notification.notification_id} queued for dashboard"
        )
        
        return True
    
    # ========================================
    # INTEGRITY EVENT LOGGING
    # ========================================
    
    def _log_integrity_event(
        self,
        event: GuardianEvent,
        comparison_data: Dict[str, Any] = None,
        system_state: Dict[str, Any] = None
    ) -> IntegrityEventLog:
        """
        Log a Guardian event for governance review.
        
        This creates a detailed log entry that can be used for:
        - Audit trails
        - Governance review
        - System calibration decisions
        
        Args:
            event: The Guardian event
            comparison_data: Detailed comparison data
            system_state: System state at time of event
        
        Returns:
            Created IntegrityEventLog
        """
        # Generate recommended actions based on event type
        recommended_actions = self._generate_recommended_actions(event)
        
        log_entry = IntegrityEventLog(
            log_id=str(uuid.uuid4()),
            event=event,
            comparison_data=comparison_data or {},
            system_state=system_state or {},
            recommended_actions=recommended_actions,
        )
        
        self._event_logs.append(log_entry)
        
        logger.info(
            f"Guardian integrity event logged: {log_entry.log_id} "
            f"(type={event.event_type.value}, entity={event.entity_id})"
        )
        
        return log_entry
    
    def _generate_recommended_actions(self, event: GuardianEvent) -> List[str]:
        """Generate recommended actions based on event type"""
        actions = []
        
        if event.event_type == GuardianEventType.DATA_OUTPUT_INCONSISTENCY:
            actions.extend([
                "Review agent calibration settings",
                "Check data processing pipeline for errors",
                "Verify threshold configurations",
                "Consider manual review of affected entity",
            ])
        elif event.event_type == GuardianEventType.STALENESS_DETECTED:
            actions.extend([
                "Review agent sensitivity settings",
                "Check for data pipeline delays",
                "Verify alert generation logic",
                "Consider refreshing system state",
            ])
        elif event.event_type == GuardianEventType.SYSTEM_INTEGRITY_WARNING:
            actions.extend([
                "Investigate system behavior",
                "Review recent configuration changes",
                "Check system logs for errors",
                "Consider system health check",
            ])
        
        # Always include the event's own recommendation
        if event.recommendation:
            actions.insert(0, event.recommendation)
        
        return actions

    
    # ========================================
    # NOTIFICATION MANAGEMENT
    # ========================================
    
    def acknowledge_notification(
        self,
        notification_id: str,
        acknowledged_by: str
    ) -> bool:
        """
        Acknowledge a Guardian notification.
        
        Args:
            notification_id: ID of notification to acknowledge
            acknowledged_by: ID of user acknowledging
        
        Returns:
            True if acknowledged, False if not found
        """
        for notification in self._notifications:
            if notification.notification_id == notification_id:
                notification.status = NotificationStatus.ACKNOWLEDGED
                notification.acknowledged_at = datetime.now()
                notification.acknowledged_by = acknowledged_by
                
                logger.info(
                    f"Guardian notification {notification_id} acknowledged by {acknowledged_by}"
                )
                return True
        
        return False
    
    def get_notifications(
        self,
        status: NotificationStatus = None,
        event_type: GuardianEventType = None,
        severity: GuardianSeverity = None,
        limit: int = None
    ) -> List[GuardianNotification]:
        """
        Get Guardian notifications with optional filtering.
        
        Args:
            status: Filter by notification status
            event_type: Filter by event type
            severity: Filter by severity
            limit: Maximum number to return
        
        Returns:
            List of matching notifications
        """
        notifications = self._notifications
        
        if status:
            notifications = [n for n in notifications if n.status == status]
        
        if event_type:
            notifications = [n for n in notifications if n.event.event_type == event_type]
        
        if severity:
            notifications = [n for n in notifications if n.event.severity == severity]
        
        # Sort by created_at descending
        notifications = sorted(notifications, key=lambda n: n.created_at, reverse=True)
        
        if limit:
            notifications = notifications[:limit]
        
        return notifications
    
    def get_pending_notifications(self) -> List[GuardianNotification]:
        """Get all pending (unacknowledged) notifications"""
        return self.get_notifications(status=NotificationStatus.SENT)
    
    def get_event_logs(
        self,
        event_type: GuardianEventType = None,
        entity_id: str = None,
        limit: int = None
    ) -> List[IntegrityEventLog]:
        """
        Get integrity event logs with optional filtering.
        
        Args:
            event_type: Filter by event type
            entity_id: Filter by entity ID
            limit: Maximum number to return
        
        Returns:
            List of matching event logs
        """
        logs = self._event_logs
        
        if event_type:
            logs = [l for l in logs if l.event.event_type == event_type]
        
        if entity_id:
            logs = [l for l in logs if l.event.entity_id == entity_id]
        
        # Sort by logged_at descending
        logs = sorted(logs, key=lambda l: l.logged_at, reverse=True)
        
        if limit:
            logs = logs[:limit]
        
        return logs
    
    def clear_notifications(self) -> int:
        """Clear all notifications (for testing)"""
        count = len(self._notifications)
        self._notifications.clear()
        return count
    
    def clear_event_logs(self) -> int:
        """Clear all event logs (for testing)"""
        count = len(self._event_logs)
        self._event_logs.clear()
        return count
    
    @property
    def notification_count(self) -> int:
        """Total number of notifications"""
        return len(self._notifications)
    
    @property
    def event_log_count(self) -> int:
        """Total number of event logs"""
        return len(self._event_logs)
    
    # ========================================
    # CLINICAL OPERATIONS SAFETY
    # ========================================
    
    def is_blocking_clinical_operations(self) -> bool:
        """
        Check if Guardian is blocking clinical operations.
        
        CRITICAL: This should ALWAYS return False.
        Guardian is designed to NEVER block clinical operations.
        
        Returns:
            Always False - Guardian never blocks
        """
        # Guardian NEVER blocks clinical operations
        # This method exists for verification and testing
        return False
    
    def get_clinical_impact_status(self) -> Dict[str, Any]:
        """
        Get status of Guardian's impact on clinical operations.
        
        Returns:
            Status dictionary confirming no clinical impact
        """
        return {
            "blocking_clinical_operations": False,
            "notification_mode": "ADMINISTRATOR_ONLY",
            "clinical_workflow_impact": "NONE",
            "pending_notifications": len(self.get_pending_notifications()),
            "message": "Guardian operates independently and never blocks clinical workflows",
        }


# ========================================
# EXPORTS
# ========================================

__all__ = [
    "GuardianNotificationSystem",
    "GuardianNotification",
    "IntegrityEventLog",
    "NotificationChannel",
    "NotificationStatus",
]
