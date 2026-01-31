"""
C-TRUST Notifications Module
============================

Role-based notification and human-in-the-loop decision support system.

"""

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

from src.notifications.user_action_capture import (
    UserActionCaptureSystem,
    UserAction,
    UserFeedback,
    UserActionType,
    FeedbackType,
    AcknowledgmentRequirement,
)

__version__ = "1.0.0"

__all__ = [
    # Notification Engine
    "NotificationRoutingEngine",
    "NotificationAcknowledgmentManager",
    "Notification",
    "UserNotificationDelivery",
    "UserRole",
    "NotificationType",
    "NotificationPriority",
    "NotificationStatus",
    # User Action Capture
    "UserActionCaptureSystem",
    "UserAction",
    "UserFeedback",
    "UserActionType",
    "FeedbackType",
    "AcknowledgmentRequirement",
]
