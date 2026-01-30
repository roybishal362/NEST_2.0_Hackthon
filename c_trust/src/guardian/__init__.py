"""
C-TRUST Guardian System Integrity Module
========================================
Novel self-monitoring capability that ensures system accuracy over time.

The Guardian Agent is a key innovation that monitors the relationship between
data changes and system outputs to detect inconsistencies, staleness, and
integrity issues.

Key Components:
- GuardianAgent: Main agent for system integrity monitoring
- GuardianEvent: Event structure for integrity findings
- DataDelta: Data change analysis between snapshots
- OutputDelta: Output change analysis between snapshots
- StalenessIndicator: Tracking for system staleness detection
- GuardianNotificationSystem: Administrator-only notification routing

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**
"""

from .guardian_agent import (
    GuardianAgent,
    GuardianEvent,
    GuardianEventType,
    GuardianSeverity,
    DataDelta,
    OutputDelta,
    StalenessIndicator,
)

from .notification_system import (
    GuardianNotificationSystem,
    GuardianNotification,
    IntegrityEventLog,
    NotificationChannel,
    NotificationStatus,
)

__all__ = [
    # Guardian Agent
    "GuardianAgent",
    "GuardianEvent",
    "GuardianEventType",
    "GuardianSeverity",
    "DataDelta",
    "OutputDelta",
    "StalenessIndicator",
    # Notification System
    "GuardianNotificationSystem",
    "GuardianNotification",
    "IntegrityEventLog",
    "NotificationChannel",
    "NotificationStatus",
]
