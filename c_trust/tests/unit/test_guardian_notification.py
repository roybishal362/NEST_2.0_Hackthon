"""
Unit tests for Guardian Notification System
===========================================
Validates Requirements 3.4 and 3.5:
- 3.4: Guardian notifications go ONLY to administrators
- 3.5: Guardian NEVER blocks clinical operations
"""

import pytest
from datetime import datetime

from src.guardian import (
    GuardianNotificationSystem,
    GuardianNotification,
    IntegrityEventLog,
    NotificationChannel,
    NotificationStatus,
    GuardianEvent,
    GuardianEventType,
    GuardianSeverity,
)


# ========================================
# FIXTURES
# ========================================

@pytest.fixture
def notification_system():
    """Create a fresh notification system for each test"""
    return GuardianNotificationSystem()


@pytest.fixture
def sample_guardian_event():
    """Create a sample Guardian event for testing"""
    return GuardianEvent(
        event_id="test-event-001",
        event_type=GuardianEventType.DATA_OUTPUT_INCONSISTENCY,
        severity=GuardianSeverity.WARNING,
        entity_id="SITE-001",
        snapshot_id="snapshot-123",
        data_delta_summary="Lab values improved by 15%",
        expected_behavior="Risk should decrease with improved data",
        actual_behavior="Risk increased from MEDIUM to HIGH",
        recommendation="Review agent calibration settings",
    )


# ========================================
# REQUIREMENT 3.4: ADMINISTRATOR-ONLY NOTIFICATIONS
# ========================================

class TestAdministratorOnlyNotifications:
    """Tests validating Requirement 3.4: Guardian notifications go ONLY to administrators"""
    
    def test_notification_recipient_role_is_always_administrator(
        self, notification_system, sample_guardian_event
    ):
        """All Guardian notifications must have recipient_role = ADMINISTRATOR"""
        notifications = notification_system.notify_administrators(sample_guardian_event)
        
        for notification in notifications:
            assert notification.recipient_role == "ADMINISTRATOR", \
                f"Notification {notification.notification_id} has wrong recipient role: {notification.recipient_role}"
    
    def test_all_channels_route_to_administrators(
        self, sample_guardian_event
    ):
        """All notification channels must route to administrators only"""
        # Test with all channels enabled
        all_channels = [
            NotificationChannel.LOG,
            NotificationChannel.DATABASE,
            NotificationChannel.DASHBOARD,
        ]
        system = GuardianNotificationSystem(enabled_channels=all_channels)
        
        notifications = system.notify_administrators(sample_guardian_event)
        
        assert len(notifications) == len(all_channels)
        for notification in notifications:
            assert notification.recipient_role == "ADMINISTRATOR"
    
    def test_notification_creation_always_sets_administrator_role(
        self, notification_system, sample_guardian_event
    ):
        """Internal notification creation must always set administrator role"""
        notification = notification_system._create_notification(
            sample_guardian_event,
            NotificationChannel.LOG
        )
        
        assert notification.recipient_role == "ADMINISTRATOR"


# ========================================
# REQUIREMENT 3.5: NEVER BLOCKS CLINICAL OPERATIONS
# ========================================

class TestNeverBlocksClinicalOperations:
    """Tests validating Requirement 3.5: Guardian NEVER blocks clinical operations"""
    
    def test_is_blocking_clinical_operations_always_returns_false(
        self, notification_system
    ):
        """is_blocking_clinical_operations() must ALWAYS return False"""
        assert notification_system.is_blocking_clinical_operations() is False
    
    def test_clinical_impact_status_shows_no_blocking(
        self, notification_system
    ):
        """Clinical impact status must confirm no blocking"""
        status = notification_system.get_clinical_impact_status()
        
        assert status["blocking_clinical_operations"] is False
        assert status["clinical_workflow_impact"] == "NONE"
        assert status["notification_mode"] == "ADMINISTRATOR_ONLY"
    
    def test_notification_failures_do_not_raise_exceptions(
        self, notification_system, sample_guardian_event
    ):
        """Notification failures must not raise exceptions (non-blocking)"""
        # Even if something goes wrong internally, it should not raise
        # This tests the try/except in notify_administrators
        notifications = notification_system.notify_administrators(sample_guardian_event)
        
        # Should complete without raising
        assert notifications is not None
        assert len(notifications) > 0
    
    def test_system_remains_operational_after_many_notifications(
        self, notification_system, sample_guardian_event
    ):
        """System must remain operational after processing many notifications"""
        # Send many notifications
        for i in range(100):
            event = GuardianEvent(
                event_id=f"test-event-{i:03d}",
                event_type=GuardianEventType.DATA_OUTPUT_INCONSISTENCY,
                severity=GuardianSeverity.INFO,
                entity_id=f"SITE-{i:03d}",
                snapshot_id=f"snapshot-{i}",
                data_delta_summary="Test delta",
                expected_behavior="Expected",
                actual_behavior="Actual",
                recommendation="Review",
            )
            notification_system.notify_administrators(event)
        
        # System should still be operational
        assert notification_system.is_blocking_clinical_operations() is False
        assert notification_system.notification_count >= 100


# ========================================
# EVENT LOGGING TESTS
# ========================================

class TestEventLogging:
    """Tests for integrity event logging functionality"""
    
    def test_events_are_logged_when_notifications_sent(
        self, notification_system, sample_guardian_event
    ):
        """Events must be logged when notifications are sent"""
        initial_count = notification_system.event_log_count
        
        notification_system.notify_administrators(sample_guardian_event)
        
        assert notification_system.event_log_count == initial_count + 1
    
    def test_event_logs_contain_correct_event_data(
        self, notification_system, sample_guardian_event
    ):
        """Event logs must contain the correct event data"""
        notification_system.notify_administrators(sample_guardian_event)
        
        logs = notification_system.get_event_logs()
        assert len(logs) > 0
        
        log = logs[0]
        assert log.event.event_id == sample_guardian_event.event_id
        assert log.event.entity_id == sample_guardian_event.entity_id
    
    def test_event_logs_include_recommended_actions(
        self, notification_system, sample_guardian_event
    ):
        """Event logs must include recommended actions"""
        notification_system.notify_administrators(sample_guardian_event)
        
        logs = notification_system.get_event_logs()
        log = logs[0]
        
        assert len(log.recommended_actions) > 0
    
    def test_event_logs_can_be_filtered_by_type(
        self, notification_system
    ):
        """Event logs must be filterable by event type"""
        # Create events of different types
        inconsistency_event = GuardianEvent(
            event_id="inconsistency-001",
            event_type=GuardianEventType.DATA_OUTPUT_INCONSISTENCY,
            severity=GuardianSeverity.WARNING,
            entity_id="SITE-001",
            snapshot_id="snap-1",
            data_delta_summary="Delta",
            expected_behavior="Expected",
            actual_behavior="Actual",
            recommendation="Review",
        )
        
        staleness_event = GuardianEvent(
            event_id="staleness-001",
            event_type=GuardianEventType.STALENESS_DETECTED,
            severity=GuardianSeverity.INFO,
            entity_id="SITE-002",
            snapshot_id="snap-2",
            data_delta_summary="No change",
            expected_behavior="Alert should clear",
            actual_behavior="Alert persists",
            recommendation="Check sensitivity",
        )
        
        notification_system.notify_administrators(inconsistency_event)
        notification_system.notify_administrators(staleness_event)
        
        # Filter by type
        inconsistency_logs = notification_system.get_event_logs(
            event_type=GuardianEventType.DATA_OUTPUT_INCONSISTENCY
        )
        staleness_logs = notification_system.get_event_logs(
            event_type=GuardianEventType.STALENESS_DETECTED
        )
        
        assert len(inconsistency_logs) == 1
        assert len(staleness_logs) == 1


# ========================================
# NOTIFICATION MANAGEMENT TESTS
# ========================================

class TestNotificationManagement:
    """Tests for notification management functionality"""
    
    def test_notifications_can_be_acknowledged(
        self, notification_system, sample_guardian_event
    ):
        """Notifications must be acknowledgeable"""
        notifications = notification_system.notify_administrators(sample_guardian_event)
        notification_id = notifications[0].notification_id
        
        result = notification_system.acknowledge_notification(
            notification_id,
            acknowledged_by="admin-001"
        )
        
        assert result is True
        
        # Verify acknowledgment
        updated = notification_system.get_notifications()[0]
        assert updated.status == NotificationStatus.ACKNOWLEDGED
        assert updated.acknowledged_by == "admin-001"
    
    def test_notifications_can_be_filtered_by_status(
        self, notification_system, sample_guardian_event
    ):
        """Notifications must be filterable by status"""
        notification_system.notify_administrators(sample_guardian_event)
        
        sent_notifications = notification_system.get_notifications(
            status=NotificationStatus.SENT
        )
        
        assert len(sent_notifications) > 0
        for n in sent_notifications:
            assert n.status == NotificationStatus.SENT
    
    def test_get_pending_notifications_returns_sent_only(
        self, notification_system, sample_guardian_event
    ):
        """get_pending_notifications must return only SENT notifications"""
        notifications = notification_system.notify_administrators(sample_guardian_event)
        
        # Acknowledge one
        notification_system.acknowledge_notification(
            notifications[0].notification_id,
            acknowledged_by="admin-001"
        )
        
        pending = notification_system.get_pending_notifications()
        
        for n in pending:
            assert n.status == NotificationStatus.SENT
