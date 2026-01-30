"""
Property-Based Tests for Role-Based Notification Routing
=========================================================
Tests Property 9: Role-Based Notification Routing

**Property 9: Role-Based Notification Routing**
*For any* generated alert or notification, the system should route it to 
appropriate user roles based on decision type and content, ensuring CRAs 
receive operational issues, Data Managers receive coding/query issues, 
and Study Leads receive escalations.

**Validates: Requirements 5.1, 5.2, 5.3, 5.4**

This test uses Hypothesis to generate various notification types and
verify that routing correctly targets the appropriate user roles.
"""

from datetime import datetime
from typing import Any, Dict, List, Set

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck, assume

from src.notifications import (
    NotificationRoutingEngine,
    NotificationAcknowledgmentManager,
    Notification,
    UserNotificationDelivery,
    UserRole,
    NotificationType,
    NotificationPriority,
    NotificationStatus,
)


# ========================================
# TEST STRATEGIES
# ========================================

@st.composite
def notification_type_strategy(draw):
    """Generate a valid NotificationType"""
    return draw(st.sampled_from(list(NotificationType)))


@st.composite
def notification_priority_strategy(draw):
    """Generate a valid NotificationPriority"""
    return draw(st.sampled_from(list(NotificationPriority)))


@st.composite
def user_role_strategy(draw):
    """Generate a valid UserRole"""
    return draw(st.sampled_from(list(UserRole)))


@st.composite
def entity_id_strategy(draw):
    """Generate a valid entity ID"""
    prefix = draw(st.sampled_from(["SITE", "STUDY", "SUBJECT"]))
    number = draw(st.integers(min_value=1, max_value=999))
    return f"{prefix}_{number:03d}"


@st.composite
def notification_strategy(draw):
    """Generate a complete notification configuration"""
    notification_type = draw(notification_type_strategy())
    priority = draw(notification_priority_strategy())
    entity_id = draw(entity_id_strategy())
    title = draw(st.text(min_size=5, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'Z'))))
    message = draw(st.text(min_size=10, max_size=200, alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'Z'))))
    
    return {
        "notification_type": notification_type,
        "priority": priority,
        "entity_id": entity_id,
        "title": title if title.strip() else "Default Title",
        "message": message if message.strip() else "Default message content",
    }


@st.composite
def users_dict_strategy(draw, min_users: int = 1, max_users: int = 10):
    """Generate a dictionary of users with roles"""
    num_users = draw(st.integers(min_value=min_users, max_value=max_users))
    users = {}
    
    for i in range(num_users):
        user_id = f"USER_{i+1:03d}"
        role = draw(user_role_strategy())
        users[user_id] = role
    
    return users


@st.composite
def users_with_all_roles_strategy(draw):
    """Generate users ensuring all roles are represented"""
    users = {}
    
    # Ensure at least one user per role
    for i, role in enumerate(UserRole):
        user_id = f"USER_{role.value}_{i+1:03d}"
        users[user_id] = role
    
    # Optionally add more users
    extra_users = draw(st.integers(min_value=0, max_value=5))
    for i in range(extra_users):
        user_id = f"USER_EXTRA_{i+1:03d}"
        role = draw(user_role_strategy())
        users[user_id] = role
    
    return users


# ========================================
# PROPERTY TESTS
# ========================================

class TestRoleBasedRoutingProperty:
    """
    Property-based tests for role-based notification routing.
    
    Feature: clinical-ai-system, Property 9: Role-Based Notification Routing
    """
    
    # Define expected role mappings for verification
    CRA_NOTIFICATION_TYPES = {
        NotificationType.SITE_OPERATIONAL,
        NotificationType.DATA_QUALITY_GAP,
        NotificationType.VISIT_COMPLETION,
        NotificationType.MISSING_DATA,
    }
    
    DATA_MANAGER_NOTIFICATION_TYPES = {
        NotificationType.CODING_ISSUE,
        NotificationType.QUERY_RESOLUTION,
        NotificationType.SUBMISSION_READINESS,
        NotificationType.DATA_VALIDATION,
    }
    
    STUDY_LEAD_NOTIFICATION_TYPES = {
        NotificationType.EXECUTIVE_SUMMARY,
        NotificationType.ESCALATION,
        NotificationType.RISK_ALERT,
        NotificationType.STUDY_MILESTONE,
        NotificationType.SAFETY_ALERT,
        NotificationType.SAE_REVIEW,
    }
    
    ADMIN_NOTIFICATION_TYPES = {
        NotificationType.SYSTEM_INTEGRITY,
        NotificationType.GUARDIAN_ALERT,
    }
    
    @given(config=notification_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_cra_receives_operational_notifications(self, config: Dict[str, Any]):
        """
        Feature: clinical-ai-system, Property 9: Role-Based Notification Routing
        Validates: Requirements 5.1, 5.2
        
        Property: CRA notifications should focus on site-level operational 
        issues and data quality gaps.
        """
        engine = NotificationRoutingEngine()
        
        notification = engine.create_notification(
            notification_type=config["notification_type"],
            priority=config["priority"],
            title=config["title"],
            message=config["message"],
            entity_id=config["entity_id"],
        )
        
        # If notification type is CRA-focused, CRA should be in target roles
        if config["notification_type"] in self.CRA_NOTIFICATION_TYPES:
            assert UserRole.CRA in notification.target_roles, \
                f"CRA should receive {config['notification_type'].value} notifications"
    
    @given(config=notification_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_data_manager_receives_coding_query_notifications(self, config: Dict[str, Any]):
        """
        Feature: clinical-ai-system, Property 9: Role-Based Notification Routing
        Validates: Requirements 5.1, 5.3
        
        Property: Data Manager notifications should emphasize coding, 
        query resolution, and submission readiness.
        """
        engine = NotificationRoutingEngine()
        
        notification = engine.create_notification(
            notification_type=config["notification_type"],
            priority=config["priority"],
            title=config["title"],
            message=config["message"],
            entity_id=config["entity_id"],
        )
        
        # If notification type is DM-focused, DM should be in target roles
        if config["notification_type"] in self.DATA_MANAGER_NOTIFICATION_TYPES:
            assert UserRole.DATA_MANAGER in notification.target_roles, \
                f"Data Manager should receive {config['notification_type'].value} notifications"
    
    @given(config=notification_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_study_lead_receives_executive_escalation_notifications(self, config: Dict[str, Any]):
        """
        Feature: clinical-ai-system, Property 9: Role-Based Notification Routing
        Validates: Requirements 5.1, 5.4
        
        Property: Study Lead notifications should provide executive summaries 
        and escalation-worthy issues.
        """
        engine = NotificationRoutingEngine()
        
        notification = engine.create_notification(
            notification_type=config["notification_type"],
            priority=config["priority"],
            title=config["title"],
            message=config["message"],
            entity_id=config["entity_id"],
        )
        
        # If notification type is Study Lead-focused, Study Lead should be in target roles
        if config["notification_type"] in self.STUDY_LEAD_NOTIFICATION_TYPES:
            assert UserRole.STUDY_LEAD in notification.target_roles, \
                f"Study Lead should receive {config['notification_type'].value} notifications"

    
    @given(config=notification_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_admin_only_receives_system_notifications(self, config: Dict[str, Any]):
        """
        Feature: clinical-ai-system, Property 9: Role-Based Notification Routing
        Validates: Requirements 5.1
        
        Property: Admin-only notifications (system integrity, guardian alerts)
        should always target Admin role. Non-critical admin notifications
        should only target Admin, while critical ones may escalate to Study Lead.
        """
        engine = NotificationRoutingEngine()
        
        notification = engine.create_notification(
            notification_type=config["notification_type"],
            priority=config["priority"],
            title=config["title"],
            message=config["message"],
            entity_id=config["entity_id"],
        )
        
        # If notification type is Admin-only, Admin should always be in target roles
        if config["notification_type"] in self.ADMIN_NOTIFICATION_TYPES:
            assert UserRole.ADMIN in notification.target_roles, \
                f"Admin should receive {config['notification_type'].value} notifications"
            
            # For non-critical admin notifications, only Admin should be targeted
            if config["priority"] != NotificationPriority.CRITICAL:
                non_admin_roles = [r for r in notification.target_roles if r != UserRole.ADMIN]
                assert len(non_admin_roles) == 0, \
                    f"Non-critical admin notifications should not target other roles: {non_admin_roles}"
    
    @given(config=notification_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_critical_priority_escalates_to_study_lead(self, config: Dict[str, Any]):
        """
        Feature: clinical-ai-system, Property 9: Role-Based Notification Routing
        Validates: Requirements 5.1, 5.4
        
        Property: Critical priority notifications should always include 
        Study Lead in target roles for escalation.
        """
        # Skip admin-only notifications as they have special routing
        assume(config["notification_type"] not in self.ADMIN_NOTIFICATION_TYPES)
        
        engine = NotificationRoutingEngine()
        
        # Create notification with CRITICAL priority
        notification = engine.create_notification(
            notification_type=config["notification_type"],
            priority=NotificationPriority.CRITICAL,
            title=config["title"],
            message=config["message"],
            entity_id=config["entity_id"],
        )
        
        # Critical notifications should always include Study Lead
        assert UserRole.STUDY_LEAD in notification.target_roles, \
            f"Critical priority should escalate to Study Lead for {config['notification_type'].value}"
    
    @given(config=notification_strategy(), users=users_with_all_roles_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_routing_delivers_to_correct_roles(self, config: Dict[str, Any], users: Dict[str, UserRole]):
        """
        Feature: clinical-ai-system, Property 9: Role-Based Notification Routing
        Validates: Requirements 5.1, 5.2, 5.3, 5.4
        
        Property: When routing a notification, only users with matching 
        target roles should receive deliveries.
        """
        engine = NotificationRoutingEngine()
        
        notification = engine.create_notification(
            notification_type=config["notification_type"],
            priority=config["priority"],
            title=config["title"],
            message=config["message"],
            entity_id=config["entity_id"],
        )
        
        deliveries = engine.route_notification(notification, users)
        
        # Verify all deliveries are to users with correct roles
        for delivery in deliveries:
            user_role = users[delivery.user_id]
            assert user_role in notification.target_roles, \
                f"User {delivery.user_id} with role {user_role.value} " \
                f"should not receive notification targeting {[r.value for r in notification.target_roles]}"
        
        # Verify all users with target roles received deliveries
        delivered_users = {d.user_id for d in deliveries}
        for user_id, role in users.items():
            if role in notification.target_roles:
                assert user_id in delivered_users, \
                    f"User {user_id} with role {role.value} should have received notification"
    
    @given(config=notification_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_notification_has_at_least_one_target_role(self, config: Dict[str, Any]):
        """
        Feature: clinical-ai-system, Property 9: Role-Based Notification Routing
        Validates: Requirements 5.1
        
        Property: Every notification should have at least one target role.
        """
        engine = NotificationRoutingEngine()
        
        notification = engine.create_notification(
            notification_type=config["notification_type"],
            priority=config["priority"],
            title=config["title"],
            message=config["message"],
            entity_id=config["entity_id"],
        )
        
        assert len(notification.target_roles) > 0, \
            f"Notification should have at least one target role"
    
    @given(config=notification_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_safety_alerts_reach_multiple_roles(self, config: Dict[str, Any]):
        """
        Feature: clinical-ai-system, Property 9: Role-Based Notification Routing
        Validates: Requirements 5.1, 5.2, 5.3, 5.4
        
        Property: Safety alerts should be routed to multiple roles 
        (Study Lead, Data Manager, CRA) for comprehensive coverage.
        """
        engine = NotificationRoutingEngine()
        
        # Create a safety alert
        notification = engine.create_notification(
            notification_type=NotificationType.SAFETY_ALERT,
            priority=config["priority"],
            title=config["title"],
            message=config["message"],
            entity_id=config["entity_id"],
        )
        
        # Safety alerts should reach multiple roles
        assert len(notification.target_roles) >= 2, \
            "Safety alerts should target multiple roles"
        assert UserRole.STUDY_LEAD in notification.target_roles, \
            "Safety alerts should always include Study Lead"
    
    @given(config=notification_strategy(), role=user_role_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_content_filtering_returns_valid_content(self, config: Dict[str, Any], role: UserRole):
        """
        Feature: clinical-ai-system, Property 9: Role-Based Notification Routing
        Validates: Requirements 5.2, 5.3, 5.4
        
        Property: Content filtering should return valid content for any role,
        with appropriate focus areas.
        """
        engine = NotificationRoutingEngine()
        
        notification = engine.create_notification(
            notification_type=config["notification_type"],
            priority=config["priority"],
            title=config["title"],
            message=config["message"],
            entity_id=config["entity_id"],
        )
        
        filtered_content = engine.filter_content_for_role(notification, role)
        
        # Verify required fields are present
        assert "notification_id" in filtered_content
        assert "title" in filtered_content
        assert "priority" in filtered_content
        assert "entity_id" in filtered_content
        assert "message" in filtered_content
        assert "focus_area" in filtered_content
        
        # Verify focus area matches role
        expected_focus = {
            UserRole.CRA: "Site Operations",
            UserRole.DATA_MANAGER: "Data Quality & Compliance",
            UserRole.STUDY_LEAD: "Executive Overview",
            UserRole.ADMIN: "System Administration",
        }
        assert filtered_content["focus_area"] == expected_focus[role], \
            f"Focus area should be '{expected_focus[role]}' for {role.value}"


# ========================================
# UNIT TESTS
# ========================================

class TestNotificationRoutingUnit:
    """Unit tests for notification routing engine"""
    
    def test_create_notification_generates_unique_id(self):
        """Test that each notification gets a unique ID"""
        engine = NotificationRoutingEngine()
        
        n1 = engine.create_notification(
            NotificationType.SITE_OPERATIONAL,
            NotificationPriority.MEDIUM,
            "Test 1", "Message 1", "SITE_001"
        )
        n2 = engine.create_notification(
            NotificationType.SITE_OPERATIONAL,
            NotificationPriority.MEDIUM,
            "Test 2", "Message 2", "SITE_002"
        )
        
        assert n1.notification_id != n2.notification_id
    
    def test_notification_expiration_based_on_priority(self):
        """Test that expiration is set based on priority"""
        engine = NotificationRoutingEngine()
        
        critical = engine.create_notification(
            NotificationType.SAFETY_ALERT,
            NotificationPriority.CRITICAL,
            "Critical", "Message", "SITE_001"
        )
        low = engine.create_notification(
            NotificationType.SITE_OPERATIONAL,
            NotificationPriority.LOW,
            "Low", "Message", "SITE_001"
        )
        
        # Critical should expire sooner than low priority
        assert critical.expires_at < low.expires_at
    
    def test_routing_to_empty_users_returns_empty_list(self):
        """Test routing with no users returns empty list"""
        engine = NotificationRoutingEngine()
        
        notification = engine.create_notification(
            NotificationType.SITE_OPERATIONAL,
            NotificationPriority.MEDIUM,
            "Test", "Message", "SITE_001"
        )
        
        deliveries = engine.route_notification(notification, {})
        assert len(deliveries) == 0
    
    def test_get_user_notifications_filters_correctly(self):
        """Test that user notifications are filtered correctly"""
        engine = NotificationRoutingEngine()
        
        notification = engine.create_notification(
            NotificationType.SITE_OPERATIONAL,
            NotificationPriority.MEDIUM,
            "Test", "Message", "SITE_001"
        )
        
        users = {"USER_001": UserRole.CRA, "USER_002": UserRole.DATA_MANAGER}
        engine.route_notification(notification, users)
        
        # CRA should see the notification
        cra_notifications = engine.get_user_notifications("USER_001")
        assert len(cra_notifications) == 1
        
        # Data Manager should not see CRA-only notification
        dm_notifications = engine.get_user_notifications("USER_002")
        assert len(dm_notifications) == 0
    
    def test_statistics_tracking(self):
        """Test that statistics are tracked correctly"""
        engine = NotificationRoutingEngine()
        
        engine.create_notification(
            NotificationType.SITE_OPERATIONAL,
            NotificationPriority.HIGH,
            "Test 1", "Message", "SITE_001"
        )
        engine.create_notification(
            NotificationType.SAFETY_ALERT,
            NotificationPriority.CRITICAL,
            "Test 2", "Message", "SITE_002"
        )
        
        stats = engine.get_statistics()
        
        assert stats["total_notifications"] == 2
        assert NotificationType.SITE_OPERATIONAL.value in stats["by_type"]
        assert NotificationType.SAFETY_ALERT.value in stats["by_type"]
