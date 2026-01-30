"""
C-TRUST User Action Capture System
==================================
Implements user response tracking, feedback loop for system improvement,
and acknowledgment requirement enforcement.

NOW INTEGRATED WITH SYSTEM-BASED NOTIFICATIONS:
- Guardian integrity alerts
- DQI threshold violations
- Agent signal patterns
- Consensus confidence monitoring
- Temporal drift detection

Key Features:
- User response tracking and logging
- Feedback loop for system improvement
- Acknowledgment requirement enforcement
- Action analytics and reporting
- System-based alert tracking

**Validates: Requirements 5.5**
"""

import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
import logging

from src.core import get_logger
from src.notifications.notification_engine import (
    NotificationRoutingEngine,
    NotificationAcknowledgmentManager,
    Notification,
    UserNotificationDelivery,
    UserRole,
    NotificationType,
    NotificationPriority,
    NotificationStatus,
)
from src.notifications.system_based_notifications import (
    SystemBasedNotificationEngine,
    SystemAlert,
    SystemAlertType,
    SystemAlertSeverity,
)

logger = get_logger(__name__)


class UserActionType(str, Enum):
    """Types of user actions"""
    VIEW = "VIEW"
    READ = "READ"
    ACKNOWLEDGE = "ACKNOWLEDGE"
    DISMISS = "DISMISS"
    ESCALATE = "ESCALATE"
    COMMENT = "COMMENT"
    EXPORT = "EXPORT"
    DRILL_DOWN = "DRILL_DOWN"
    FILTER = "FILTER"
    SEARCH = "SEARCH"


class FeedbackType(str, Enum):
    """Types of user feedback"""
    HELPFUL = "HELPFUL"
    NOT_HELPFUL = "NOT_HELPFUL"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    MISSING_INFO = "MISSING_INFO"
    TOO_LATE = "TOO_LATE"
    UNCLEAR = "UNCLEAR"


@dataclass
class UserAction:
    """
    Record of a user action in the system.
    
    Attributes:
        action_id: Unique identifier
        user_id: User who performed the action
        user_role: Role of the user
        action_type: Type of action
        entity_id: Related entity (notification, study, site)
        entity_type: Type of entity
        timestamp: When action occurred
        session_id: User session identifier
        details: Additional action details
        context: Context information (page, filters, etc.)
    """
    action_id: str
    user_id: str
    user_role: UserRole
    action_type: UserActionType
    entity_id: str
    entity_type: str = "NOTIFICATION"
    timestamp: datetime = field(default_factory=datetime.now)
    session_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "action_id": self.action_id,
            "user_id": self.user_id,
            "user_role": self.user_role.value,
            "action_type": self.action_type.value,
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "timestamp": self.timestamp.isoformat(),
            "session_id": self.session_id,
            "details": self.details,
            "context": self.context,
        }


@dataclass
class UserFeedback:
    """
    User feedback on a notification or recommendation.
    
    Attributes:
        feedback_id: Unique identifier
        user_id: User providing feedback
        notification_id: Related notification
        feedback_type: Type of feedback
        comment: Optional comment
        timestamp: When feedback was provided
    """
    feedback_id: str
    user_id: str
    notification_id: str
    feedback_type: FeedbackType
    comment: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "feedback_id": self.feedback_id,
            "user_id": self.user_id,
            "notification_id": self.notification_id,
            "feedback_type": self.feedback_type.value,
            "comment": self.comment,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class AcknowledgmentRequirement:
    """
    Acknowledgment requirement for a notification.
    
    Attributes:
        notification_id: Notification requiring acknowledgment
        required_by: Deadline for acknowledgment
        required_roles: Roles that must acknowledge
        acknowledged_by: Users who have acknowledged
        is_satisfied: Whether requirement is satisfied
    """
    notification_id: str
    required_by: datetime
    required_roles: List[UserRole]
    acknowledged_by: List[str] = field(default_factory=list)
    is_satisfied: bool = False
    
    def check_satisfaction(self, deliveries: List[UserNotificationDelivery]) -> bool:
        """Check if acknowledgment requirement is satisfied"""
        acknowledged_roles = set()
        for delivery in deliveries:
            if delivery.acknowledged_at is not None:
                acknowledged_roles.add(delivery.user_role)
        
        # Requirement is satisfied if at least one user from each required role acknowledged
        for role in self.required_roles:
            if role not in acknowledged_roles:
                return False
        
        self.is_satisfied = True
        return True


class UserActionCaptureSystem:
    """
    Captures and tracks all user actions for audit and improvement.
    
    NOW INTEGRATED WITH SYSTEM-BASED NOTIFICATIONS:
    - Tracks responses to Guardian alerts
    - Monitors DQI threshold violations
    - Captures agent signal feedback
    - Records consensus confidence actions
    
    Provides comprehensive tracking of user interactions with the system,
    enabling audit trails and feedback loops for system improvement.
    
    **Validates: Requirements 5.5**
    """
    
    def __init__(
        self,
        routing_engine: NotificationRoutingEngine,
        acknowledgment_manager: NotificationAcknowledgmentManager,
        system_notification_engine: Optional[SystemBasedNotificationEngine] = None,
        audit_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        """
        Initialize user action capture system.
        
        Args:
            routing_engine: Reference to notification routing engine
            acknowledgment_manager: Reference to acknowledgment manager
            system_notification_engine: System-based notification engine
            audit_callback: Optional callback for audit logging
        """
        self.routing_engine = routing_engine
        self.acknowledgment_manager = acknowledgment_manager
        self.system_notification_engine = system_notification_engine or SystemBasedNotificationEngine()
        self.audit_callback = audit_callback
        
        self._action_counter = 0
        self._feedback_counter = 0
        self._lock = threading.Lock()
        
        # Storage
        self._actions: List[UserAction] = []
        self._feedback: List[UserFeedback] = []
        self._acknowledgment_requirements: Dict[str, AcknowledgmentRequirement] = {}
        
        # Analytics
        self._action_counts: Dict[str, Dict[str, int]] = {}  # user_id -> action_type -> count
        self._response_times: List[Tuple[str, float]] = []  # (notification_id, seconds)
        
        # System-based alert tracking
        self._system_alert_responses: Dict[str, List[Dict[str, Any]]] = {}  # alert_id -> responses
        
        logger.info("UserActionCaptureSystem initialized with system-based notifications")
    
    def _generate_action_id(self) -> str:
        """Generate unique action ID"""
        with self._lock:
            self._action_counter += 1
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            return f"ACT_{timestamp}_{self._action_counter:06d}"
    
    def _generate_feedback_id(self) -> str:
        """Generate unique feedback ID"""
        with self._lock:
            self._feedback_counter += 1
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            return f"FB_{timestamp}_{self._feedback_counter:06d}"

    
    def capture_action(
        self,
        user_id: str,
        user_role: UserRole,
        action_type: UserActionType,
        entity_id: str,
        entity_type: str = "NOTIFICATION",
        session_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> UserAction:
        """
        Capture a user action.
        
        Args:
            user_id: User performing the action
            user_role: Role of the user
            action_type: Type of action
            entity_id: Related entity ID
            entity_type: Type of entity
            session_id: Optional session identifier
            details: Additional details
            context: Context information
        
        Returns:
            Created UserAction record
        """
        action = UserAction(
            action_id=self._generate_action_id(),
            user_id=user_id,
            user_role=user_role,
            action_type=action_type,
            entity_id=entity_id,
            entity_type=entity_type,
            session_id=session_id,
            details=details or {},
            context=context or {},
        )
        
        self._actions.append(action)
        
        # Update analytics
        if user_id not in self._action_counts:
            self._action_counts[user_id] = {}
        action_key = action_type.value
        self._action_counts[user_id][action_key] = \
            self._action_counts[user_id].get(action_key, 0) + 1
        
        # Log to audit if callback provided
        if self.audit_callback:
            try:
                self.audit_callback({
                    "event_type": "USER_ACTION",
                    "action": action.to_dict(),
                })
            except Exception as e:
                logger.error(f"Audit callback error: {e}")
        
        logger.debug(
            f"Captured action {action.action_id}: "
            f"user={user_id}, type={action_type.value}, entity={entity_id}"
        )
        
        return action
    
    def capture_feedback(
        self,
        user_id: str,
        notification_id: str,
        feedback_type: FeedbackType,
        comment: Optional[str] = None,
    ) -> UserFeedback:
        """
        Capture user feedback on a notification.
        
        Args:
            user_id: User providing feedback
            notification_id: Related notification
            feedback_type: Type of feedback
            comment: Optional comment
        
        Returns:
            Created UserFeedback record
        """
        feedback = UserFeedback(
            feedback_id=self._generate_feedback_id(),
            user_id=user_id,
            notification_id=notification_id,
            feedback_type=feedback_type,
            comment=comment,
        )
        
        self._feedback.append(feedback)
        
        # Log to audit if callback provided
        if self.audit_callback:
            try:
                self.audit_callback({
                    "event_type": "USER_FEEDBACK",
                    "feedback": feedback.to_dict(),
                })
            except Exception as e:
                logger.error(f"Audit callback error: {e}")
        
        logger.info(
            f"Captured feedback {feedback.feedback_id}: "
            f"user={user_id}, notification={notification_id}, type={feedback_type.value}"
        )
        
        return feedback
    
    def track_response_time(
        self,
        notification_id: str,
        created_at: datetime,
        acknowledged_at: datetime,
    ) -> float:
        """
        Track response time for a notification.
        
        Args:
            notification_id: Notification ID
            created_at: When notification was created
            acknowledged_at: When notification was acknowledged
        
        Returns:
            Response time in seconds
        """
        response_time = (acknowledged_at - created_at).total_seconds()
        self._response_times.append((notification_id, response_time))
        
        logger.debug(
            f"Response time for {notification_id}: {response_time:.1f} seconds"
        )
        
        return response_time
    
    def create_acknowledgment_requirement(
        self,
        notification: Notification,
        deadline_hours: Optional[int] = None,
    ) -> AcknowledgmentRequirement:
        """
        Create an acknowledgment requirement for a notification.
        
        Args:
            notification: Notification requiring acknowledgment
            deadline_hours: Hours until deadline (default based on priority)
        
        Returns:
            Created AcknowledgmentRequirement
        """
        # Default deadline based on priority
        if deadline_hours is None:
            deadline_map = {
                NotificationPriority.CRITICAL: 4,
                NotificationPriority.HIGH: 24,
                NotificationPriority.MEDIUM: 72,
                NotificationPriority.LOW: 168,
            }
            deadline_hours = deadline_map.get(notification.priority, 72)
        
        requirement = AcknowledgmentRequirement(
            notification_id=notification.notification_id,
            required_by=datetime.now() + timedelta(hours=deadline_hours),
            required_roles=notification.target_roles.copy(),
        )
        
        self._acknowledgment_requirements[notification.notification_id] = requirement
        
        logger.info(
            f"Created acknowledgment requirement for {notification.notification_id}: "
            f"deadline={requirement.required_by.isoformat()}"
        )
        
        return requirement
    
    def check_acknowledgment_requirement(
        self,
        notification_id: str,
    ) -> Tuple[bool, Optional[AcknowledgmentRequirement]]:
        """
        Check if acknowledgment requirement is satisfied.
        
        Args:
            notification_id: Notification to check
        
        Returns:
            Tuple of (is_satisfied, requirement)
        """
        requirement = self._acknowledgment_requirements.get(notification_id)
        if not requirement:
            return True, None  # No requirement means satisfied
        
        # Get deliveries for this notification
        deliveries = []
        for delivery in self.routing_engine._deliveries.values():
            if delivery.notification_id == notification_id:
                deliveries.append(delivery)
        
        is_satisfied = requirement.check_satisfaction(deliveries)
        
        return is_satisfied, requirement
    
    def get_overdue_acknowledgments(self) -> List[AcknowledgmentRequirement]:
        """
        Get acknowledgment requirements that are overdue.
        
        Returns:
            List of overdue requirements
        """
        now = datetime.now()
        overdue = []
        
        for requirement in self._acknowledgment_requirements.values():
            if not requirement.is_satisfied and requirement.required_by < now:
                overdue.append(requirement)
        
        return overdue
    
    def enforce_acknowledgment(
        self,
        notification_id: str,
        escalate_on_overdue: bool = True,
    ) -> Dict[str, Any]:
        """
        Enforce acknowledgment requirement for a notification.
        
        Args:
            notification_id: Notification to enforce
            escalate_on_overdue: Whether to escalate if overdue
        
        Returns:
            Enforcement result
        """
        is_satisfied, requirement = self.check_acknowledgment_requirement(notification_id)
        
        if is_satisfied:
            return {
                "status": "SATISFIED",
                "notification_id": notification_id,
                "message": "Acknowledgment requirement satisfied",
            }
        
        if requirement is None:
            return {
                "status": "NO_REQUIREMENT",
                "notification_id": notification_id,
                "message": "No acknowledgment requirement found",
            }
        
        now = datetime.now()
        is_overdue = requirement.required_by < now
        
        if is_overdue and escalate_on_overdue:
            # Get notification and escalate
            notification = self.routing_engine.get_notification(notification_id)
            if notification:
                # Find a delivery to escalate from
                for delivery in self.routing_engine._deliveries.values():
                    if delivery.notification_id == notification_id and delivery.acknowledged_at is None:
                        self.acknowledgment_manager.escalate(
                            delivery.delivery_id,
                            "SYSTEM",
                            "Automatic escalation due to overdue acknowledgment",
                            UserRole.STUDY_LEAD,
                        )
                        break
            
            return {
                "status": "ESCALATED",
                "notification_id": notification_id,
                "message": "Notification escalated due to overdue acknowledgment",
                "overdue_by_hours": (now - requirement.required_by).total_seconds() / 3600,
            }
        
        return {
            "status": "PENDING",
            "notification_id": notification_id,
            "message": "Acknowledgment pending",
            "deadline": requirement.required_by.isoformat(),
            "time_remaining_hours": (requirement.required_by - now).total_seconds() / 3600,
        }

    
    def get_user_actions(
        self,
        user_id: Optional[str] = None,
        action_type: Optional[UserActionType] = None,
        entity_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[UserAction]:
        """
        Query user actions with filters.
        
        Args:
            user_id: Filter by user
            action_type: Filter by action type
            entity_id: Filter by entity
            start_time: Filter by start time
            end_time: Filter by end time
            limit: Maximum results
        
        Returns:
            List of matching actions
        """
        results = []
        
        for action in reversed(self._actions):  # Most recent first
            if len(results) >= limit:
                break
            
            if user_id and action.user_id != user_id:
                continue
            if action_type and action.action_type != action_type:
                continue
            if entity_id and action.entity_id != entity_id:
                continue
            if start_time and action.timestamp < start_time:
                continue
            if end_time and action.timestamp > end_time:
                continue
            
            results.append(action)
        
        return results
    
    def get_feedback_summary(
        self,
        notification_type: Optional[NotificationType] = None,
    ) -> Dict[str, Any]:
        """
        Get summary of user feedback for system improvement.
        
        Args:
            notification_type: Optional filter by notification type
        
        Returns:
            Feedback summary with counts and insights
        """
        feedback_counts: Dict[str, int] = {}
        comments: List[str] = []
        
        for fb in self._feedback:
            # Filter by notification type if specified
            if notification_type:
                notification = self.routing_engine.get_notification(fb.notification_id)
                if notification and notification.notification_type != notification_type:
                    continue
            
            # Count by type
            fb_type = fb.feedback_type.value
            feedback_counts[fb_type] = feedback_counts.get(fb_type, 0) + 1
            
            # Collect comments
            if fb.comment:
                comments.append(fb.comment)
        
        total = sum(feedback_counts.values())
        
        # Calculate improvement insights
        insights = []
        if feedback_counts.get("FALSE_POSITIVE", 0) > total * 0.2:
            insights.append("High false positive rate - consider adjusting thresholds")
        if feedback_counts.get("TOO_LATE", 0) > total * 0.1:
            insights.append("Notifications arriving too late - review timing")
        if feedback_counts.get("UNCLEAR", 0) > total * 0.15:
            insights.append("Unclear notifications - improve message clarity")
        if feedback_counts.get("MISSING_INFO", 0) > total * 0.1:
            insights.append("Missing information - add more context to notifications")
        
        return {
            "total_feedback": total,
            "by_type": feedback_counts,
            "helpful_rate": feedback_counts.get("HELPFUL", 0) / total if total > 0 else 0,
            "comments": comments[-10:],  # Last 10 comments
            "improvement_insights": insights,
        }
    
    def get_response_time_analytics(self) -> Dict[str, Any]:
        """
        Get analytics on notification response times.
        
        Returns:
            Response time analytics
        """
        if not self._response_times:
            return {
                "count": 0,
                "average_seconds": 0,
                "median_seconds": 0,
                "min_seconds": 0,
                "max_seconds": 0,
            }
        
        times = [t[1] for t in self._response_times]
        times_sorted = sorted(times)
        
        return {
            "count": len(times),
            "average_seconds": sum(times) / len(times),
            "median_seconds": times_sorted[len(times) // 2],
            "min_seconds": min(times),
            "max_seconds": max(times),
            "average_hours": sum(times) / len(times) / 3600,
        }
    
    def get_user_engagement_metrics(
        self,
        user_id: str,
    ) -> Dict[str, Any]:
        """
        Get engagement metrics for a specific user.
        
        Args:
            user_id: User to analyze
        
        Returns:
            User engagement metrics
        """
        user_actions = self._action_counts.get(user_id, {})
        total_actions = sum(user_actions.values())
        
        # Get user's acknowledgment rate
        user_deliveries = self.routing_engine._user_deliveries.get(user_id, [])
        total_deliveries = len(user_deliveries)
        acknowledged = 0
        
        for delivery_id in user_deliveries:
            delivery = self.routing_engine.get_delivery(delivery_id)
            if delivery and delivery.acknowledged_at is not None:
                acknowledged += 1
        
        acknowledgment_rate = acknowledged / total_deliveries if total_deliveries > 0 else 0
        
        return {
            "user_id": user_id,
            "total_actions": total_actions,
            "actions_by_type": user_actions,
            "total_notifications_received": total_deliveries,
            "notifications_acknowledged": acknowledged,
            "acknowledgment_rate": acknowledgment_rate,
        }
    
    
    def capture_system_alert_response(
        self,
        alert_id: str,
        user_id: str,
        user_role: UserRole,
        response_type: str,
        action_taken: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Capture user response to a system-generated alert.
        
        Args:
            alert_id: System alert ID
            user_id: User responding
            user_role: User's role
            response_type: Type of response (ACKNOWLEDGE, DISMISS, ESCALATE, etc.)
            action_taken: Action taken by user
            comment: Optional comment
        
        Returns:
            Response record
        """
        response = {
            "alert_id": alert_id,
            "user_id": user_id,
            "user_role": user_role.value,
            "response_type": response_type,
            "action_taken": action_taken,
            "comment": comment,
            "timestamp": datetime.now().isoformat(),
        }
        
        if alert_id not in self._system_alert_responses:
            self._system_alert_responses[alert_id] = []
        self._system_alert_responses[alert_id].append(response)
        
        # Log to audit
        if self.audit_callback:
            try:
                self.audit_callback({
                    "event_type": "SYSTEM_ALERT_RESPONSE",
                    "response": response,
                })
            except Exception as e:
                logger.error(f"Audit callback error: {e}")
        
        logger.info(
            f"Captured system alert response: alert={alert_id}, "
            f"user={user_id}, type={response_type}"
        )
        
        return response
    
    def get_system_alert_analytics(self) -> Dict[str, Any]:
        """
        Get analytics on system alert responses.
        
        Returns:
            Analytics on how users respond to system-generated alerts
        """
        if not self.system_notification_engine:
            return {"error": "System notification engine not available"}
        
        stats = self.system_notification_engine.get_statistics()
        
        # Calculate response rates
        total_alerts = stats["total_alerts"]
        total_responses = sum(len(responses) for responses in self._system_alert_responses.values())
        
        response_rate = total_responses / total_alerts if total_alerts > 0 else 0
        
        # Response types
        response_types = {}
        for responses in self._system_alert_responses.values():
            for response in responses:
                rtype = response["response_type"]
                response_types[rtype] = response_types.get(rtype, 0) + 1
        
        # Alert type effectiveness
        alert_effectiveness = {}
        for alert_type, count in stats["by_type"].items():
            # Count how many of this type got responses
            responded = 0
            for alert_id, responses in self._system_alert_responses.items():
                alert = self.system_notification_engine.get_alert(alert_id)
                if alert and alert.alert_type.value == alert_type and len(responses) > 0:
                    responded += 1
            
            alert_effectiveness[alert_type] = {
                "total": count,
                "responded": responded,
                "response_rate": responded / count if count > 0 else 0,
            }
        
        return {
            "total_system_alerts": total_alerts,
            "total_responses": total_responses,
            "overall_response_rate": response_rate,
            "response_types": response_types,
            "alert_effectiveness": alert_effectiveness,
            "alerts_by_severity": stats["by_severity"],
            "alerts_by_component": stats["by_component"],
        }
    
    def get_system_improvement_recommendations(self) -> List[Dict[str, Any]]:
        """
        Generate system improvement recommendations based on user feedback
        and action patterns.
        
        Returns:
            List of improvement recommendations
        """
        recommendations = []
        
        # Analyze feedback
        feedback_summary = self.get_feedback_summary()
        for insight in feedback_summary.get("improvement_insights", []):
            recommendations.append({
                "type": "FEEDBACK_BASED",
                "recommendation": insight,
                "priority": "MEDIUM",
            })
        
        # Analyze response times
        response_analytics = self.get_response_time_analytics()
        avg_hours = response_analytics.get("average_hours", 0)
        
        if avg_hours > 24:
            recommendations.append({
                "type": "RESPONSE_TIME",
                "recommendation": f"Average response time is {avg_hours:.1f} hours. Consider improving notification visibility.",
                "priority": "HIGH",
            })
        
        # Analyze overdue acknowledgments
        overdue = self.get_overdue_acknowledgments()
        if len(overdue) > 5:
            recommendations.append({
                "type": "ACKNOWLEDGMENT",
                "recommendation": f"{len(overdue)} notifications have overdue acknowledgments. Review notification routing and user workload.",
                "priority": "HIGH",
            })
        
        # Analyze action patterns
        total_views = sum(
            counts.get("VIEW", 0) 
            for counts in self._action_counts.values()
        )
        total_acks = sum(
            counts.get("ACKNOWLEDGE", 0) 
            for counts in self._action_counts.values()
        )
        
        if total_views > 0 and total_acks / total_views < 0.5:
            recommendations.append({
                "type": "ENGAGEMENT",
                "recommendation": "Low view-to-acknowledgment ratio. Notifications may need clearer action items.",
                "priority": "MEDIUM",
            })
        
        return recommendations


__all__ = [
    "UserActionCaptureSystem",
    "UserAction",
    "UserFeedback",
    "UserActionType",
    "FeedbackType",
    "AcknowledgmentRequirement",
]
