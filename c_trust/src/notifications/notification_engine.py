"""
C-TRUST Role-Based Notification Routing Engine
===============================================
Implements role-based notification distribution, content filtering,
and acknowledgment workflow for Human-in-the-Loop decision support.

Key Features:
- Role-based notification routing (CRA, Data Manager, Study Lead)
- Content filtering based on user role and decision type
- Notification acknowledgment workflow
- User action capture and logging

**Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5**
"""

import hashlib
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
import logging

from src.core import get_logger

logger = get_logger(__name__)


class UserRole(str, Enum):
    """User roles in the clinical trial system"""
    CRA = "CRA"                    # Clinical Research Associate
    DATA_MANAGER = "DATA_MANAGER"  # Data Manager
    STUDY_LEAD = "STUDY_LEAD"      # Study Program Manager
    ADMIN = "ADMIN"                # System Administrator


class NotificationType(str, Enum):
    """Types of notifications"""
    # Operational Issues (CRA focus)
    SITE_OPERATIONAL = "SITE_OPERATIONAL"
    DATA_QUALITY_GAP = "DATA_QUALITY_GAP"
    VISIT_COMPLETION = "VISIT_COMPLETION"
    MISSING_DATA = "MISSING_DATA"
    
    # Data Management Issues (Data Manager focus)
    CODING_ISSUE = "CODING_ISSUE"
    QUERY_RESOLUTION = "QUERY_RESOLUTION"
    SUBMISSION_READINESS = "SUBMISSION_READINESS"
    DATA_VALIDATION = "DATA_VALIDATION"
    
    # Executive/Escalation Issues (Study Lead focus)
    EXECUTIVE_SUMMARY = "EXECUTIVE_SUMMARY"
    ESCALATION = "ESCALATION"
    RISK_ALERT = "RISK_ALERT"
    STUDY_MILESTONE = "STUDY_MILESTONE"
    
    # Safety Issues (All roles, priority to Study Lead)
    SAFETY_ALERT = "SAFETY_ALERT"
    SAE_REVIEW = "SAE_REVIEW"
    
    # System Issues (Admin only)
    SYSTEM_INTEGRITY = "SYSTEM_INTEGRITY"
    GUARDIAN_ALERT = "GUARDIAN_ALERT"


class NotificationPriority(str, Enum):
    """Priority levels for notifications"""
    CRITICAL = "CRITICAL"  # Immediate attention required
    HIGH = "HIGH"          # Address within 24 hours
    MEDIUM = "MEDIUM"      # Address within 72 hours
    LOW = "LOW"            # Informational, routine review


class NotificationStatus(str, Enum):
    """Status of a notification"""
    PENDING = "PENDING"          # Not yet delivered
    DELIVERED = "DELIVERED"      # Delivered to user
    READ = "READ"                # User has viewed
    ACKNOWLEDGED = "ACKNOWLEDGED" # User has acknowledged
    DISMISSED = "DISMISSED"      # User dismissed without action
    ESCALATED = "ESCALATED"      # Escalated to higher role
    EXPIRED = "EXPIRED"          # Past due without action


@dataclass
class Notification:
    """
    A notification to be routed to users.
    
    Attributes:
        notification_id: Unique identifier
        notification_type: Type of notification
        priority: Priority level
        title: Short title
        message: Detailed message
        entity_id: Related entity (study, site, subject)
        entity_type: Type of entity
        target_roles: Roles that should receive this notification
        evidence: Supporting evidence
        recommended_actions: Suggested actions
        created_at: When notification was created
        expires_at: When notification expires
        status: Current status
        metadata: Additional metadata
    """
    notification_id: str
    notification_type: NotificationType
    priority: NotificationPriority
    title: str
    message: str
    entity_id: str
    entity_type: str = "SITE"
    target_roles: List[UserRole] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)
    recommended_actions: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    status: NotificationStatus = NotificationStatus.PENDING
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Set default expiration if not provided"""
        if self.expires_at is None:
            # Default expiration based on priority
            expiry_hours = {
                NotificationPriority.CRITICAL: 24,
                NotificationPriority.HIGH: 72,
                NotificationPriority.MEDIUM: 168,  # 1 week
                NotificationPriority.LOW: 336,     # 2 weeks
            }
            hours = expiry_hours.get(self.priority, 168)
            self.expires_at = self.created_at + timedelta(hours=hours)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "notification_id": self.notification_id,
            "notification_type": self.notification_type.value,
            "priority": self.priority.value,
            "title": self.title,
            "message": self.message,
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "target_roles": [r.value for r in self.target_roles],
            "evidence": self.evidence,
            "recommended_actions": self.recommended_actions,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "status": self.status.value,
            "metadata": self.metadata,
        }
    
    def is_expired(self) -> bool:
        """Check if notification has expired"""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at




@dataclass
class UserNotificationDelivery:
    """
    Record of notification delivery to a specific user.
    
    Attributes:
        delivery_id: Unique identifier
        notification_id: Reference to notification
        user_id: User who received notification
        user_role: Role of the user
        delivered_at: When delivered
        read_at: When user read it
        acknowledged_at: When user acknowledged
        action_taken: Action user took
        comment: User's comment
    """
    delivery_id: str
    notification_id: str
    user_id: str
    user_role: UserRole
    delivered_at: datetime = field(default_factory=datetime.now)
    read_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    action_taken: Optional[str] = None
    comment: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "delivery_id": self.delivery_id,
            "notification_id": self.notification_id,
            "user_id": self.user_id,
            "user_role": self.user_role.value,
            "delivered_at": self.delivered_at.isoformat(),
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "action_taken": self.action_taken,
            "comment": self.comment,
        }


class NotificationRoutingEngine:
    """
    Role-based notification routing engine.
    
    Routes notifications to appropriate users based on their role,
    the notification type, and content filtering rules.
    
    Routing Rules:
    - CRA: Site-level operational issues, data quality gaps
    - Data Manager: Coding, query resolution, submission readiness
    - Study Lead: Executive summaries, escalations, risk alerts
    - Admin: System integrity, Guardian alerts
    
    **Validates: Requirements 5.1, 5.2, 5.3, 5.4**
    """
    
    # Role-to-notification-type mapping
    ROLE_NOTIFICATION_MAPPING: Dict[UserRole, Set[NotificationType]] = {
        UserRole.CRA: {
            NotificationType.SITE_OPERATIONAL,
            NotificationType.DATA_QUALITY_GAP,
            NotificationType.VISIT_COMPLETION,
            NotificationType.MISSING_DATA,
        },
        UserRole.DATA_MANAGER: {
            NotificationType.CODING_ISSUE,
            NotificationType.QUERY_RESOLUTION,
            NotificationType.SUBMISSION_READINESS,
            NotificationType.DATA_VALIDATION,
        },
        UserRole.STUDY_LEAD: {
            NotificationType.EXECUTIVE_SUMMARY,
            NotificationType.ESCALATION,
            NotificationType.RISK_ALERT,
            NotificationType.STUDY_MILESTONE,
            NotificationType.SAFETY_ALERT,
            NotificationType.SAE_REVIEW,
        },
        UserRole.ADMIN: {
            NotificationType.SYSTEM_INTEGRITY,
            NotificationType.GUARDIAN_ALERT,
        },
    }
    
    # Notification types that go to multiple roles
    MULTI_ROLE_NOTIFICATIONS: Dict[NotificationType, List[UserRole]] = {
        NotificationType.SAFETY_ALERT: [UserRole.STUDY_LEAD, UserRole.DATA_MANAGER, UserRole.CRA],
        NotificationType.SAE_REVIEW: [UserRole.STUDY_LEAD, UserRole.DATA_MANAGER],
        NotificationType.ESCALATION: [UserRole.STUDY_LEAD, UserRole.DATA_MANAGER],
    }
    
    def __init__(self):
        """Initialize the notification routing engine"""
        self._notification_counter = 0
        self._delivery_counter = 0
        self._lock = threading.Lock()
        
        # Storage for notifications and deliveries
        self._notifications: Dict[str, Notification] = {}
        self._deliveries: Dict[str, UserNotificationDelivery] = {}
        self._user_deliveries: Dict[str, List[str]] = {}  # user_id -> delivery_ids
        
        # Callbacks for notification events
        self._delivery_callbacks: List[Callable[[UserNotificationDelivery], None]] = []
        
        logger.info("NotificationRoutingEngine initialized")
    
    def _generate_notification_id(self) -> str:
        """Generate unique notification ID"""
        with self._lock:
            self._notification_counter += 1
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            return f"NOTIF_{timestamp}_{self._notification_counter:06d}"
    
    def _generate_delivery_id(self) -> str:
        """Generate unique delivery ID"""
        with self._lock:
            self._delivery_counter += 1
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            return f"DELIV_{timestamp}_{self._delivery_counter:06d}"
    
    def determine_target_roles(
        self,
        notification_type: NotificationType,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
    ) -> List[UserRole]:
        """
        Determine which roles should receive a notification.
        
        Args:
            notification_type: Type of notification
            priority: Priority level (affects escalation)
        
        Returns:
            List of target roles
        """
        # Check multi-role notifications first
        if notification_type in self.MULTI_ROLE_NOTIFICATIONS:
            return self.MULTI_ROLE_NOTIFICATIONS[notification_type].copy()
        
        # Find primary role for this notification type
        target_roles = []
        for role, types in self.ROLE_NOTIFICATION_MAPPING.items():
            if notification_type in types:
                target_roles.append(role)
        
        # Critical priority escalates to Study Lead
        if priority == NotificationPriority.CRITICAL and UserRole.STUDY_LEAD not in target_roles:
            target_roles.append(UserRole.STUDY_LEAD)
        
        return target_roles if target_roles else [UserRole.DATA_MANAGER]
    
    def create_notification(
        self,
        notification_type: NotificationType,
        priority: NotificationPriority,
        title: str,
        message: str,
        entity_id: str,
        entity_type: str = "SITE",
        evidence: Optional[List[str]] = None,
        recommended_actions: Optional[List[str]] = None,
        target_roles: Optional[List[UserRole]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Notification:
        """
        Create a new notification.
        
        Args:
            notification_type: Type of notification
            priority: Priority level
            title: Short title
            message: Detailed message
            entity_id: Related entity ID
            entity_type: Type of entity
            evidence: Supporting evidence
            recommended_actions: Suggested actions
            target_roles: Override target roles (auto-determined if None)
            metadata: Additional metadata
        
        Returns:
            Created Notification
        """
        notification_id = self._generate_notification_id()
        
        # Determine target roles if not specified
        if target_roles is None:
            target_roles = self.determine_target_roles(notification_type, priority)
        
        notification = Notification(
            notification_id=notification_id,
            notification_type=notification_type,
            priority=priority,
            title=title,
            message=message,
            entity_id=entity_id,
            entity_type=entity_type,
            target_roles=target_roles,
            evidence=evidence or [],
            recommended_actions=recommended_actions or [],
            metadata=metadata or {},
        )
        
        self._notifications[notification_id] = notification
        
        logger.info(
            f"Created notification {notification_id}: "
            f"type={notification_type.value}, "
            f"priority={priority.value}, "
            f"targets={[r.value for r in target_roles]}"
        )
        
        return notification

    
    def route_notification(
        self,
        notification: Notification,
        users: Dict[str, UserRole],
    ) -> List[UserNotificationDelivery]:
        """
        Route a notification to appropriate users based on their roles.
        
        Args:
            notification: Notification to route
            users: Dictionary of user_id -> UserRole
        
        Returns:
            List of delivery records
        """
        deliveries = []
        
        for user_id, user_role in users.items():
            # Check if user's role is in target roles
            if user_role in notification.target_roles:
                delivery = self._deliver_to_user(notification, user_id, user_role)
                deliveries.append(delivery)
        
        # Update notification status
        if deliveries:
            notification.status = NotificationStatus.DELIVERED
        
        logger.info(
            f"Routed notification {notification.notification_id} "
            f"to {len(deliveries)} user(s)"
        )
        
        return deliveries
    
    def _deliver_to_user(
        self,
        notification: Notification,
        user_id: str,
        user_role: UserRole,
    ) -> UserNotificationDelivery:
        """Deliver notification to a specific user"""
        delivery_id = self._generate_delivery_id()
        
        delivery = UserNotificationDelivery(
            delivery_id=delivery_id,
            notification_id=notification.notification_id,
            user_id=user_id,
            user_role=user_role,
        )
        
        # Store delivery
        self._deliveries[delivery_id] = delivery
        
        # Track user's deliveries
        if user_id not in self._user_deliveries:
            self._user_deliveries[user_id] = []
        self._user_deliveries[user_id].append(delivery_id)
        
        # Notify callbacks
        for callback in self._delivery_callbacks:
            try:
                callback(delivery)
            except Exception as e:
                logger.error(f"Delivery callback error: {e}")
        
        logger.debug(f"Delivered {notification.notification_id} to {user_id} ({user_role.value})")
        
        return delivery
    
    def filter_content_for_role(
        self,
        notification: Notification,
        role: UserRole,
    ) -> Dict[str, Any]:
        """
        Filter notification content based on user role.
        
        Different roles see different levels of detail:
        - CRA: Site-level operational details
        - Data Manager: Technical details, coding/query specifics
        - Study Lead: Executive summary, key metrics
        
        Args:
            notification: Original notification
            role: User's role
        
        Returns:
            Filtered notification content
        """
        base_content = {
            "notification_id": notification.notification_id,
            "title": notification.title,
            "priority": notification.priority.value,
            "entity_id": notification.entity_id,
            "entity_type": notification.entity_type,
            "created_at": notification.created_at.isoformat(),
        }
        
        if role == UserRole.CRA:
            # CRA sees operational details
            return {
                **base_content,
                "message": self._format_cra_message(notification),
                "focus_area": "Site Operations",
                "evidence": notification.evidence[:3],  # Limited evidence
                "recommended_actions": [
                    a for a in notification.recommended_actions
                    if self._is_cra_action(a)
                ],
            }
        
        elif role == UserRole.DATA_MANAGER:
            # Data Manager sees technical details
            return {
                **base_content,
                "message": self._format_dm_message(notification),
                "focus_area": "Data Quality & Compliance",
                "evidence": notification.evidence,  # Full evidence
                "recommended_actions": [
                    a for a in notification.recommended_actions
                    if self._is_dm_action(a)
                ],
                "technical_details": notification.metadata.get("technical_details", {}),
            }
        
        elif role == UserRole.STUDY_LEAD:
            # Study Lead sees executive summary
            return {
                **base_content,
                "message": self._format_study_lead_message(notification),
                "focus_area": "Executive Overview",
                "evidence": notification.evidence[:2],  # Key evidence only
                "recommended_actions": notification.recommended_actions,
                "impact_summary": notification.metadata.get("impact_summary", ""),
                "escalation_required": notification.priority in [
                    NotificationPriority.CRITICAL,
                    NotificationPriority.HIGH
                ],
            }
        
        elif role == UserRole.ADMIN:
            # Admin sees everything
            return {
                **base_content,
                "message": notification.message,
                "focus_area": "System Administration",
                "evidence": notification.evidence,
                "recommended_actions": notification.recommended_actions,
                "metadata": notification.metadata,
            }
        
        return base_content
    
    def _format_cra_message(self, notification: Notification) -> str:
        """Format message for CRA role"""
        # Focus on site-level operational issues
        if notification.notification_type in [
            NotificationType.SITE_OPERATIONAL,
            NotificationType.VISIT_COMPLETION,
            NotificationType.MISSING_DATA,
        ]:
            return notification.message
        
        # Simplify other messages for CRA
        return f"Site operational issue: {notification.title}. Please review site data quality."
    
    def _format_dm_message(self, notification: Notification) -> str:
        """Format message for Data Manager role"""
        # Data managers get full technical details
        return notification.message
    
    def _format_study_lead_message(self, notification: Notification) -> str:
        """Format message for Study Lead role"""
        # Executive summary format
        if notification.priority == NotificationPriority.CRITICAL:
            return f"URGENT: {notification.message}"
        elif notification.priority == NotificationPriority.HIGH:
            return f"Action Required: {notification.message}"
        return f"For Review: {notification.message}"
    
    def _is_cra_action(self, action: str) -> bool:
        """Check if action is relevant for CRA"""
        cra_keywords = ["site", "visit", "subject", "form", "data entry", "monitor"]
        return any(kw in action.lower() for kw in cra_keywords)
    
    def _is_dm_action(self, action: str) -> bool:
        """Check if action is relevant for Data Manager"""
        dm_keywords = ["query", "coding", "validation", "submission", "review", "data"]
        return any(kw in action.lower() for kw in dm_keywords)

    
    def get_user_notifications(
        self,
        user_id: str,
        include_acknowledged: bool = False,
        include_expired: bool = False,
    ) -> List[Notification]:
        """
        Get notifications for a specific user.
        
        Args:
            user_id: User identifier
            include_acknowledged: Include acknowledged notifications
            include_expired: Include expired notifications
        
        Returns:
            List of notifications for the user
        """
        delivery_ids = self._user_deliveries.get(user_id, [])
        notifications = []
        
        for delivery_id in delivery_ids:
            delivery = self._deliveries.get(delivery_id)
            if not delivery:
                continue
            
            notification = self._notifications.get(delivery.notification_id)
            if not notification:
                continue
            
            # Filter based on status
            if not include_acknowledged and delivery.acknowledged_at is not None:
                continue
            
            if not include_expired and notification.is_expired():
                continue
            
            notifications.append(notification)
        
        # Sort by priority and creation time
        priority_order = {
            NotificationPriority.CRITICAL: 0,
            NotificationPriority.HIGH: 1,
            NotificationPriority.MEDIUM: 2,
            NotificationPriority.LOW: 3,
        }
        
        notifications.sort(
            key=lambda n: (priority_order.get(n.priority, 4), n.created_at),
            reverse=False
        )
        
        return notifications
    
    def get_notification(self, notification_id: str) -> Optional[Notification]:
        """Get a notification by ID"""
        return self._notifications.get(notification_id)
    
    def get_delivery(self, delivery_id: str) -> Optional[UserNotificationDelivery]:
        """Get a delivery record by ID"""
        return self._deliveries.get(delivery_id)
    
    def get_pending_acknowledgments(
        self,
        user_id: Optional[str] = None,
    ) -> List[UserNotificationDelivery]:
        """
        Get deliveries pending acknowledgment.
        
        Args:
            user_id: Optional filter by user
        
        Returns:
            List of deliveries pending acknowledgment
        """
        pending = []
        
        for delivery in self._deliveries.values():
            if delivery.acknowledged_at is not None:
                continue
            
            if user_id and delivery.user_id != user_id:
                continue
            
            notification = self._notifications.get(delivery.notification_id)
            if notification and not notification.is_expired():
                pending.append(delivery)
        
        return pending
    
    def register_delivery_callback(
        self,
        callback: Callable[[UserNotificationDelivery], None]
    ) -> None:
        """Register callback for notification deliveries"""
        self._delivery_callbacks.append(callback)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get notification statistics"""
        total = len(self._notifications)
        by_type = {}
        by_priority = {}
        by_status = {}
        
        for notification in self._notifications.values():
            # By type
            type_key = notification.notification_type.value
            by_type[type_key] = by_type.get(type_key, 0) + 1
            
            # By priority
            priority_key = notification.priority.value
            by_priority[priority_key] = by_priority.get(priority_key, 0) + 1
            
            # By status
            status_key = notification.status.value
            by_status[status_key] = by_status.get(status_key, 0) + 1
        
        return {
            "total_notifications": total,
            "total_deliveries": len(self._deliveries),
            "by_type": by_type,
            "by_priority": by_priority,
            "by_status": by_status,
        }


class NotificationAcknowledgmentManager:
    """
    Manages notification acknowledgment workflow.
    
    Ensures all notifications are explicitly acknowledged and
    captures user actions for audit purposes.
    
    **Validates: Requirements 5.5**
    """
    
    def __init__(
        self,
        routing_engine: NotificationRoutingEngine,
        audit_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        """
        Initialize acknowledgment manager.
        
        Args:
            routing_engine: Reference to routing engine
            audit_callback: Optional callback for audit logging
        """
        self.routing_engine = routing_engine
        self.audit_callback = audit_callback
        self._acknowledgment_history: List[Dict[str, Any]] = []
        
        logger.info("NotificationAcknowledgmentManager initialized")
    
    def mark_as_read(
        self,
        delivery_id: str,
        user_id: str,
    ) -> bool:
        """
        Mark a notification as read.
        
        Args:
            delivery_id: Delivery record ID
            user_id: User marking as read
        
        Returns:
            True if successful
        """
        delivery = self.routing_engine.get_delivery(delivery_id)
        if not delivery:
            logger.warning(f"Delivery {delivery_id} not found")
            return False
        
        if delivery.user_id != user_id:
            logger.warning(f"User {user_id} cannot mark delivery {delivery_id} as read")
            return False
        
        delivery.read_at = datetime.now()
        
        self._log_action(delivery, "READ", user_id)
        
        logger.debug(f"Delivery {delivery_id} marked as read by {user_id}")
        return True
    
    def acknowledge(
        self,
        delivery_id: str,
        user_id: str,
        action_taken: str,
        comment: Optional[str] = None,
    ) -> bool:
        """
        Acknowledge a notification with action taken.
        
        Args:
            delivery_id: Delivery record ID
            user_id: User acknowledging
            action_taken: Action the user took
            comment: Optional comment
        
        Returns:
            True if successful
        """
        delivery = self.routing_engine.get_delivery(delivery_id)
        if not delivery:
            logger.warning(f"Delivery {delivery_id} not found")
            return False
        
        if delivery.user_id != user_id:
            logger.warning(f"User {user_id} cannot acknowledge delivery {delivery_id}")
            return False
        
        # Update delivery
        delivery.acknowledged_at = datetime.now()
        delivery.action_taken = action_taken
        delivery.comment = comment
        
        # Update notification status
        notification = self.routing_engine.get_notification(delivery.notification_id)
        if notification:
            notification.status = NotificationStatus.ACKNOWLEDGED
        
        self._log_action(delivery, "ACKNOWLEDGE", user_id, action_taken, comment)
        
        logger.info(
            f"Delivery {delivery_id} acknowledged by {user_id}: "
            f"action={action_taken}"
        )
        return True
    
    def dismiss(
        self,
        delivery_id: str,
        user_id: str,
        reason: Optional[str] = None,
    ) -> bool:
        """
        Dismiss a notification without action.
        
        Args:
            delivery_id: Delivery record ID
            user_id: User dismissing
            reason: Optional reason for dismissal
        
        Returns:
            True if successful
        """
        delivery = self.routing_engine.get_delivery(delivery_id)
        if not delivery:
            logger.warning(f"Delivery {delivery_id} not found")
            return False
        
        if delivery.user_id != user_id:
            logger.warning(f"User {user_id} cannot dismiss delivery {delivery_id}")
            return False
        
        # Update delivery
        delivery.acknowledged_at = datetime.now()
        delivery.action_taken = "DISMISSED"
        delivery.comment = reason
        
        # Update notification status
        notification = self.routing_engine.get_notification(delivery.notification_id)
        if notification:
            notification.status = NotificationStatus.DISMISSED
        
        self._log_action(delivery, "DISMISS", user_id, "DISMISSED", reason)
        
        logger.info(f"Delivery {delivery_id} dismissed by {user_id}")
        return True
    
    def escalate(
        self,
        delivery_id: str,
        user_id: str,
        escalation_reason: str,
        target_role: UserRole = UserRole.STUDY_LEAD,
    ) -> Optional[Notification]:
        """
        Escalate a notification to a higher role.
        
        Args:
            delivery_id: Delivery record ID
            user_id: User escalating
            escalation_reason: Reason for escalation
            target_role: Role to escalate to
        
        Returns:
            New escalated notification if successful
        """
        delivery = self.routing_engine.get_delivery(delivery_id)
        if not delivery:
            logger.warning(f"Delivery {delivery_id} not found")
            return None
        
        original_notification = self.routing_engine.get_notification(delivery.notification_id)
        if not original_notification:
            logger.warning(f"Notification {delivery.notification_id} not found")
            return None
        
        # Create escalated notification
        escalated = self.routing_engine.create_notification(
            notification_type=NotificationType.ESCALATION,
            priority=NotificationPriority.HIGH,
            title=f"ESCALATED: {original_notification.title}",
            message=f"Escalated by {user_id}: {escalation_reason}\n\nOriginal: {original_notification.message}",
            entity_id=original_notification.entity_id,
            entity_type=original_notification.entity_type,
            evidence=original_notification.evidence,
            recommended_actions=original_notification.recommended_actions,
            target_roles=[target_role],
            metadata={
                "original_notification_id": original_notification.notification_id,
                "escalated_by": user_id,
                "escalation_reason": escalation_reason,
            },
        )
        
        # Update original notification status
        original_notification.status = NotificationStatus.ESCALATED
        
        # Mark original delivery as acknowledged
        delivery.acknowledged_at = datetime.now()
        delivery.action_taken = "ESCALATED"
        delivery.comment = escalation_reason
        
        self._log_action(delivery, "ESCALATE", user_id, "ESCALATED", escalation_reason)
        
        logger.info(
            f"Notification {original_notification.notification_id} "
            f"escalated to {target_role.value} by {user_id}"
        )
        
        return escalated
    
    def _log_action(
        self,
        delivery: UserNotificationDelivery,
        action_type: str,
        user_id: str,
        action_taken: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> None:
        """Log acknowledgment action for audit"""
        record = {
            "timestamp": datetime.now().isoformat(),
            "delivery_id": delivery.delivery_id,
            "notification_id": delivery.notification_id,
            "user_id": user_id,
            "user_role": delivery.user_role.value,
            "action_type": action_type,
            "action_taken": action_taken,
            "comment": comment,
        }
        
        self._acknowledgment_history.append(record)
        
        if self.audit_callback:
            try:
                self.audit_callback(record)
            except Exception as e:
                logger.error(f"Audit callback error: {e}")
    
    def get_acknowledgment_history(
        self,
        user_id: Optional[str] = None,
        notification_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get acknowledgment history.
        
        Args:
            user_id: Optional filter by user
            notification_id: Optional filter by notification
        
        Returns:
            List of acknowledgment records
        """
        history = self._acknowledgment_history
        
        if user_id:
            history = [r for r in history if r["user_id"] == user_id]
        
        if notification_id:
            history = [r for r in history if r["notification_id"] == notification_id]
        
        return history
    
    def get_pending_count(self, user_id: str) -> int:
        """Get count of pending acknowledgments for a user"""
        pending = self.routing_engine.get_pending_acknowledgments(user_id)
        return len(pending)
    
    def requires_acknowledgment(self, notification: Notification) -> bool:
        """
        Check if a notification requires explicit acknowledgment.
        
        All notifications require acknowledgment per Requirements 5.5.
        
        Args:
            notification: Notification to check
        
        Returns:
            True (all notifications require acknowledgment)
        """
        # Per Requirements 5.5: All notifications require explicit acknowledgment
        return True


__all__ = [
    "NotificationRoutingEngine",
    "NotificationAcknowledgmentManager",
    "Notification",
    "UserNotificationDelivery",
    "UserRole",
    "NotificationType",
    "NotificationPriority",
    "NotificationStatus",
]
