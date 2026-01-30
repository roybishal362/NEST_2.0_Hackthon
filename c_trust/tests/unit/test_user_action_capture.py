"""
Unit Tests for User Action Capture System
=========================================
Tests the user response tracking, feedback loop, and acknowledgment
requirement enforcement functionality.

**Validates: Requirements 5.5**
"""

from datetime import datetime, timedelta
import pytest

from src.notifications import (
    NotificationRoutingEngine,
    NotificationAcknowledgmentManager,
    UserActionCaptureSystem,
    UserAction,
    UserFeedback,
    UserActionType,
    FeedbackType,
    AcknowledgmentRequirement,
    UserRole,
    NotificationType,
    NotificationPriority,
)


class TestUserActionCapture:
    """Tests for user action capture functionality"""
    
    @pytest.fixture
    def system(self):
        """Create a complete notification system for testing"""
        engine = NotificationRoutingEngine()
        ack_mgr = NotificationAcknowledgmentManager(engine)
        capture = UserActionCaptureSystem(engine, ack_mgr)
        return engine, ack_mgr, capture
    
    def test_capture_action_creates_record(self, system):
        """Test that capturing an action creates a proper record"""
        engine, ack_mgr, capture = system
        
        action = capture.capture_action(
            user_id="USER_001",
            user_role=UserRole.CRA,
            action_type=UserActionType.VIEW,
            entity_id="NOTIF_001",
        )
        
        assert action.action_id is not None
        assert action.user_id == "USER_001"
        assert action.user_role == UserRole.CRA
        assert action.action_type == UserActionType.VIEW
        assert action.entity_id == "NOTIF_001"
    
    def test_capture_action_with_details(self, system):
        """Test capturing action with additional details"""
        engine, ack_mgr, capture = system
        
        action = capture.capture_action(
            user_id="USER_001",
            user_role=UserRole.DATA_MANAGER,
            action_type=UserActionType.ACKNOWLEDGE,
            entity_id="NOTIF_001",
            session_id="SESSION_123",
            details={"comment": "Reviewed and approved"},
            context={"page": "dashboard", "filter": "high_priority"},
        )
        
        assert action.session_id == "SESSION_123"
        assert action.details["comment"] == "Reviewed and approved"
        assert action.context["page"] == "dashboard"
    
    def test_capture_feedback(self, system):
        """Test capturing user feedback"""
        engine, ack_mgr, capture = system
        
        feedback = capture.capture_feedback(
            user_id="USER_001",
            notification_id="NOTIF_001",
            feedback_type=FeedbackType.HELPFUL,
            comment="This alert was very useful",
        )
        
        assert feedback.feedback_id is not None
        assert feedback.user_id == "USER_001"
        assert feedback.notification_id == "NOTIF_001"
        assert feedback.feedback_type == FeedbackType.HELPFUL
        assert feedback.comment == "This alert was very useful"
    
    def test_track_response_time(self, system):
        """Test tracking notification response time"""
        engine, ack_mgr, capture = system
        
        created = datetime.now() - timedelta(hours=2)
        acknowledged = datetime.now()
        
        response_time = capture.track_response_time(
            "NOTIF_001", created, acknowledged
        )
        
        # Should be approximately 2 hours in seconds
        assert 7100 < response_time < 7300  # ~2 hours with some tolerance
    
    def test_create_acknowledgment_requirement(self, system):
        """Test creating acknowledgment requirement"""
        engine, ack_mgr, capture = system
        
        notification = engine.create_notification(
            NotificationType.SAFETY_ALERT,
            NotificationPriority.HIGH,
            "Safety Alert",
            "Important safety issue",
            "SITE_001",
        )
        
        requirement = capture.create_acknowledgment_requirement(notification)
        
        assert requirement.notification_id == notification.notification_id
        assert requirement.required_by > datetime.now()
        assert len(requirement.required_roles) > 0
        assert not requirement.is_satisfied
    
    def test_acknowledgment_requirement_deadline_by_priority(self, system):
        """Test that deadline is set based on priority"""
        engine, ack_mgr, capture = system
        
        critical = engine.create_notification(
            NotificationType.SAFETY_ALERT,
            NotificationPriority.CRITICAL,
            "Critical", "Message", "SITE_001",
        )
        low = engine.create_notification(
            NotificationType.SITE_OPERATIONAL,
            NotificationPriority.LOW,
            "Low", "Message", "SITE_001",
        )
        
        critical_req = capture.create_acknowledgment_requirement(critical)
        low_req = capture.create_acknowledgment_requirement(low)
        
        # Critical should have shorter deadline
        assert critical_req.required_by < low_req.required_by
    
    def test_check_acknowledgment_requirement_unsatisfied(self, system):
        """Test checking unsatisfied acknowledgment requirement"""
        engine, ack_mgr, capture = system
        
        notification = engine.create_notification(
            NotificationType.SAFETY_ALERT,
            NotificationPriority.HIGH,
            "Safety Alert",
            "Important safety issue",
            "SITE_001",
        )
        
        capture.create_acknowledgment_requirement(notification)
        
        is_satisfied, requirement = capture.check_acknowledgment_requirement(
            notification.notification_id
        )
        
        assert not is_satisfied
        assert requirement is not None
    
    def test_check_acknowledgment_requirement_satisfied(self, system):
        """Test checking satisfied acknowledgment requirement"""
        engine, ack_mgr, capture = system
        
        # Use a notification type that only targets one role
        notification = engine.create_notification(
            NotificationType.SITE_OPERATIONAL,
            NotificationPriority.MEDIUM,
            "Site Alert",
            "Site operational issue",
            "SITE_001",
        )
        
        # Route to users - CRA is the target for SITE_OPERATIONAL
        users = {"USER_001": UserRole.CRA}
        deliveries = engine.route_notification(notification, users)
        
        # Create requirement
        capture.create_acknowledgment_requirement(notification)
        
        # Acknowledge
        ack_mgr.acknowledge(
            deliveries[0].delivery_id,
            "USER_001",
            "Reviewed and addressed",
        )
        
        is_satisfied, requirement = capture.check_acknowledgment_requirement(
            notification.notification_id
        )
        
        assert is_satisfied
    
    def test_get_user_actions_with_filters(self, system):
        """Test querying user actions with filters"""
        engine, ack_mgr, capture = system
        
        # Capture multiple actions
        capture.capture_action("USER_001", UserRole.CRA, UserActionType.VIEW, "NOTIF_001")
        capture.capture_action("USER_001", UserRole.CRA, UserActionType.ACKNOWLEDGE, "NOTIF_001")
        capture.capture_action("USER_002", UserRole.DATA_MANAGER, UserActionType.VIEW, "NOTIF_002")
        
        # Filter by user
        user1_actions = capture.get_user_actions(user_id="USER_001")
        assert len(user1_actions) == 2
        
        # Filter by action type
        view_actions = capture.get_user_actions(action_type=UserActionType.VIEW)
        assert len(view_actions) == 2
        
        # Filter by entity
        notif1_actions = capture.get_user_actions(entity_id="NOTIF_001")
        assert len(notif1_actions) == 2
    
    def test_get_feedback_summary(self, system):
        """Test getting feedback summary"""
        engine, ack_mgr, capture = system
        
        # Capture various feedback
        capture.capture_feedback("USER_001", "NOTIF_001", FeedbackType.HELPFUL)
        capture.capture_feedback("USER_002", "NOTIF_002", FeedbackType.HELPFUL)
        capture.capture_feedback("USER_003", "NOTIF_003", FeedbackType.FALSE_POSITIVE)
        capture.capture_feedback("USER_004", "NOTIF_004", FeedbackType.UNCLEAR, "Need more details")
        
        summary = capture.get_feedback_summary()
        
        assert summary["total_feedback"] == 4
        assert summary["by_type"]["HELPFUL"] == 2
        assert summary["by_type"]["FALSE_POSITIVE"] == 1
        assert summary["by_type"]["UNCLEAR"] == 1
        assert summary["helpful_rate"] == 0.5
    
    def test_get_response_time_analytics(self, system):
        """Test getting response time analytics"""
        engine, ack_mgr, capture = system
        
        now = datetime.now()
        
        # Track multiple response times
        capture.track_response_time("NOTIF_001", now - timedelta(hours=1), now)
        capture.track_response_time("NOTIF_002", now - timedelta(hours=2), now)
        capture.track_response_time("NOTIF_003", now - timedelta(hours=3), now)
        
        analytics = capture.get_response_time_analytics()
        
        assert analytics["count"] == 3
        assert analytics["average_hours"] == pytest.approx(2.0, rel=0.1)
        assert analytics["min_seconds"] < analytics["max_seconds"]
    
    def test_get_user_engagement_metrics(self, system):
        """Test getting user engagement metrics"""
        engine, ack_mgr, capture = system
        
        # Create and route notification
        notification = engine.create_notification(
            NotificationType.SITE_OPERATIONAL,
            NotificationPriority.MEDIUM,
            "Test", "Message", "SITE_001",
        )
        users = {"USER_001": UserRole.CRA}
        deliveries = engine.route_notification(notification, users)
        
        # Capture actions
        capture.capture_action("USER_001", UserRole.CRA, UserActionType.VIEW, notification.notification_id)
        capture.capture_action("USER_001", UserRole.CRA, UserActionType.ACKNOWLEDGE, notification.notification_id)
        
        # Acknowledge
        ack_mgr.acknowledge(deliveries[0].delivery_id, "USER_001", "Done")
        
        metrics = capture.get_user_engagement_metrics("USER_001")
        
        assert metrics["user_id"] == "USER_001"
        assert metrics["total_actions"] == 2
        assert metrics["total_notifications_received"] == 1
        assert metrics["notifications_acknowledged"] == 1
        assert metrics["acknowledgment_rate"] == 1.0
    
    def test_enforce_acknowledgment_satisfied(self, system):
        """Test enforcement when acknowledgment is satisfied"""
        engine, ack_mgr, capture = system
        
        notification = engine.create_notification(
            NotificationType.SITE_OPERATIONAL,
            NotificationPriority.MEDIUM,
            "Test", "Message", "SITE_001",
        )
        users = {"USER_001": UserRole.CRA}
        deliveries = engine.route_notification(notification, users)
        
        capture.create_acknowledgment_requirement(notification)
        ack_mgr.acknowledge(deliveries[0].delivery_id, "USER_001", "Done")
        
        result = capture.enforce_acknowledgment(notification.notification_id)
        
        assert result["status"] == "SATISFIED"
    
    def test_enforce_acknowledgment_pending(self, system):
        """Test enforcement when acknowledgment is pending"""
        engine, ack_mgr, capture = system
        
        notification = engine.create_notification(
            NotificationType.SITE_OPERATIONAL,
            NotificationPriority.MEDIUM,
            "Test", "Message", "SITE_001",
        )
        
        capture.create_acknowledgment_requirement(notification)
        
        result = capture.enforce_acknowledgment(notification.notification_id)
        
        assert result["status"] == "PENDING"
        assert "deadline" in result
        assert "time_remaining_hours" in result
    
    def test_action_to_dict_serialization(self, system):
        """Test that actions can be serialized to dict"""
        engine, ack_mgr, capture = system
        
        action = capture.capture_action(
            user_id="USER_001",
            user_role=UserRole.CRA,
            action_type=UserActionType.VIEW,
            entity_id="NOTIF_001",
        )
        
        action_dict = action.to_dict()
        
        assert "action_id" in action_dict
        assert "user_id" in action_dict
        assert "user_role" in action_dict
        assert "action_type" in action_dict
        assert "timestamp" in action_dict
        assert action_dict["user_role"] == "CRA"
        assert action_dict["action_type"] == "VIEW"
