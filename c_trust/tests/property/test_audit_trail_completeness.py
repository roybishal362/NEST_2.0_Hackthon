"""
Property-Based Tests for Audit Trail Completeness
=================================================
Tests Property 11: Audit Trail Completeness

**Property 11: Audit Trail Completeness**
*For any* system operation including data processing, agent decisions, and human 
actions, the system should create complete, immutable audit trails with timestamps 
and user attribution.

**Validates: Requirements 7.3, 10.3**

This test uses Hypothesis to generate various audit scenarios and verify
that the audit trail system maintains completeness and immutability.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List
import tempfile
import shutil

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck, assume

from src.audit import (
    AuditTrailManager,
    AuditEvent,
    AuditEventType,
    AuditQuery,
    AuditReport,
)


# ========================================
# TEST STRATEGIES
# ========================================

@st.composite
def event_type_strategy(draw):
    """Generate valid audit event types"""
    return draw(st.sampled_from(list(AuditEventType)))


@st.composite
def component_name_strategy(draw):
    """Generate valid component names"""
    components = [
        "data_pipeline", "agent.completeness", "agent.safety",
        "consensus_engine", "dqi_engine", "guardian_agent",
        "user_interface", "config_manager", "api_server"
    ]
    return draw(st.sampled_from(components))


@st.composite
def entity_id_strategy(draw):
    """Generate valid entity IDs"""
    prefix = draw(st.sampled_from(["STUDY", "SITE", "SUBJECT", "SNAPSHOT"]))
    number = draw(st.integers(min_value=1, max_value=999))
    return f"{prefix}_{number:03d}"


@st.composite
def user_id_strategy(draw):
    """Generate valid user IDs"""
    roles = ["CRA", "DM", "LEAD", "ADMIN"]
    role = draw(st.sampled_from(roles))
    number = draw(st.integers(min_value=1, max_value=99))
    return f"{role}_{number:02d}"


@st.composite
def action_strategy(draw):
    """Generate valid action descriptions"""
    actions = [
        "Processed data batch",
        "Generated risk assessment",
        "Calculated DQI score",
        "Viewed dashboard",
        "Exported report",
        "Acknowledged alert",
        "Dismissed notification",
        "Escalated issue",
        "Updated configuration",
        "Analyzed entity",
    ]
    return draw(st.sampled_from(actions))


@st.composite
def details_strategy(draw):
    """Generate valid event details"""
    return {
        "metric_value": draw(st.floats(min_value=0, max_value=100, allow_nan=False)),
        "record_count": draw(st.integers(min_value=0, max_value=1000)),
        "status": draw(st.sampled_from(["SUCCESS", "PARTIAL", "FAILED"])),
    }


@st.composite
def audit_event_params_strategy(draw):
    """Generate complete audit event parameters"""
    return {
        "event_type": draw(event_type_strategy()),
        "component_name": draw(component_name_strategy()),
        "action_taken": draw(action_strategy()),
        "entity_id": draw(st.one_of(st.none(), entity_id_strategy())),
        "user_id": draw(st.one_of(st.none(), user_id_strategy())),
        "session_id": draw(st.one_of(st.none(), st.text(min_size=8, max_size=16, alphabet="abcdef0123456789"))),
        "details": draw(st.one_of(st.none(), details_strategy())),
    }


# ========================================
# FIXTURES
# ========================================

@pytest.fixture
def temp_audit_dir():
    """Create temporary directory for audit logs"""
    temp_dir = tempfile.mkdtemp(prefix="audit_test_")
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def fresh_audit_manager(temp_audit_dir):
    """Create a fresh audit manager for each test"""
    # Reset singleton
    AuditTrailManager._instance = None
    manager = AuditTrailManager(storage_path=temp_audit_dir)
    yield manager
    # Reset singleton after test
    AuditTrailManager._instance = None


# ========================================
# PROPERTY TESTS
# ========================================

class TestAuditTrailCompletenessProperty:
    """
    Property-based tests for audit trail completeness.
    
    Feature: clinical-ai-system, Property 11: Audit Trail Completeness
    """
    
    @given(params=audit_event_params_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_all_events_have_timestamp(self, params: Dict[str, Any], fresh_audit_manager):
        """
        Feature: clinical-ai-system, Property 11: Audit Trail Completeness
        Validates: Requirements 7.3, 10.3
        
        Property: For any logged event, it should have a valid timestamp.
        """
        event = fresh_audit_manager.log_event(**params)
        
        assert event.timestamp is not None, "Event should have timestamp"
        assert isinstance(event.timestamp, datetime), "Timestamp should be datetime"
        
        # Timestamp should be recent (within last minute)
        now = datetime.now()
        assert event.timestamp <= now, "Timestamp should not be in future"
        assert event.timestamp >= now - timedelta(minutes=1), "Timestamp should be recent"
    
    @given(params=audit_event_params_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_all_events_have_unique_id(self, params: Dict[str, Any], fresh_audit_manager):
        """
        Feature: clinical-ai-system, Property 11: Audit Trail Completeness
        Validates: Requirements 7.3, 10.3
        
        Property: For any logged event, it should have a unique event ID.
        """
        event1 = fresh_audit_manager.log_event(**params)
        event2 = fresh_audit_manager.log_event(**params)
        
        assert event1.event_id is not None, "Event should have ID"
        assert event2.event_id is not None, "Event should have ID"
        assert event1.event_id != event2.event_id, "Event IDs should be unique"
    
    @given(params=audit_event_params_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_events_are_immutable(self, params: Dict[str, Any], fresh_audit_manager):
        """
        Feature: clinical-ai-system, Property 11: Audit Trail Completeness
        Validates: Requirements 7.3, 10.3
        
        Property: For any logged event, it should be immutable (frozen dataclass).
        """
        event = fresh_audit_manager.log_event(**params)
        
        # Attempt to modify should raise error
        with pytest.raises((AttributeError, TypeError)):
            event.action_taken = "Modified action"
    
    @given(params=audit_event_params_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_events_have_integrity_checksum(self, params: Dict[str, Any], fresh_audit_manager):
        """
        Feature: clinical-ai-system, Property 11: Audit Trail Completeness
        Validates: Requirements 7.3, 10.3
        
        Property: For any logged event, it should have a valid integrity checksum.
        """
        event = fresh_audit_manager.log_event(**params)
        
        assert event.checksum is not None, "Event should have checksum"
        assert len(event.checksum) == 64, "Checksum should be SHA-256 (64 hex chars)"
        assert event.verify_integrity(), "Event should pass integrity verification"
    
    @given(params=audit_event_params_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_events_preserve_user_attribution(self, params: Dict[str, Any], fresh_audit_manager):
        """
        Feature: clinical-ai-system, Property 11: Audit Trail Completeness
        Validates: Requirements 10.3
        
        Property: For any logged event with user_id, the attribution should be preserved.
        """
        event = fresh_audit_manager.log_event(**params)
        
        # User ID should be preserved exactly
        assert event.user_id == params.get("user_id"), \
            "User attribution should be preserved"
    
    @given(params=audit_event_params_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_events_are_queryable(self, params: Dict[str, Any], fresh_audit_manager):
        """
        Feature: clinical-ai-system, Property 11: Audit Trail Completeness
        Validates: Requirements 7.3
        
        Property: For any logged event, it should be retrievable via query.
        """
        event = fresh_audit_manager.log_event(**params)
        
        # Query for the event
        query = AuditQuery(
            event_types=[params["event_type"]],
            component_names=[params["component_name"]],
        )
        report = fresh_audit_manager.query_events(query)
        
        # Event should be in results
        event_ids = [e.event_id for e in report.events]
        assert event.event_id in event_ids, "Logged event should be queryable"
    
    @given(params=audit_event_params_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_events_are_serializable(self, params: Dict[str, Any], fresh_audit_manager):
        """
        Feature: clinical-ai-system, Property 11: Audit Trail Completeness
        Validates: Requirements 7.3
        
        Property: For any logged event, it should be serializable to dictionary.
        """
        event = fresh_audit_manager.log_event(**params)
        
        # Serialize to dict
        event_dict = event.to_dict()
        
        assert isinstance(event_dict, dict), "Event should serialize to dict"
        
        # Required fields should be present
        required_fields = [
            "event_id", "timestamp", "event_type", "component_name",
            "action_taken", "checksum"
        ]
        for field in required_fields:
            assert field in event_dict, f"Serialized event should have {field}"
    
    @given(params=audit_event_params_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_events_roundtrip_serialization(self, params: Dict[str, Any], fresh_audit_manager):
        """
        Feature: clinical-ai-system, Property 11: Audit Trail Completeness
        Validates: Requirements 7.3
        
        Property: For any logged event, serialization and deserialization should preserve data.
        """
        event = fresh_audit_manager.log_event(**params)
        
        # Serialize and deserialize
        event_dict = event.to_dict()
        restored_event = AuditEvent.from_dict(event_dict)
        
        # Key fields should match
        assert restored_event.event_id == event.event_id
        assert restored_event.event_type == event.event_type
        assert restored_event.component_name == event.component_name
        assert restored_event.action_taken == event.action_taken
        assert restored_event.user_id == event.user_id
        assert restored_event.entity_id == event.entity_id
        assert restored_event.checksum == event.checksum
    
    @given(
        user_id=user_id_strategy(),
        action=st.sampled_from(["VIEW", "DRILL_DOWN", "EXPORT", "ACKNOWLEDGE"]),
        entity_id=entity_id_strategy(),
    )
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_user_actions_are_tracked(
        self, 
        user_id: str, 
        action: str, 
        entity_id: str,
        fresh_audit_manager
    ):
        """
        Feature: clinical-ai-system, Property 11: Audit Trail Completeness
        Validates: Requirements 10.3
        
        Property: For any user action, it should be tracked with full attribution.
        """
        event = fresh_audit_manager.log_user_action(
            user_id=user_id,
            action=action,
            entity_id=entity_id,
        )
        
        assert event.user_id == user_id, "User ID should be tracked"
        assert event.entity_id == entity_id, "Entity ID should be tracked"
        assert action.lower() in event.action_taken.lower() or \
               event.event_type.value.lower().endswith(action.lower()), \
               "Action should be recorded"


# ========================================
# UNIT TESTS
# ========================================

class TestAuditTrailUnit:
    """Unit tests for audit trail system"""
    
    def test_audit_event_creation(self, fresh_audit_manager):
        """Test basic audit event creation"""
        event = fresh_audit_manager.log_event(
            event_type=AuditEventType.DATA_PROCESSING,
            component_name="test_component",
            action_taken="Test action",
            entity_id="TEST_001",
            user_id="USER_001",
        )
        
        assert event.event_id is not None
        assert event.timestamp is not None
        assert event.event_type == AuditEventType.DATA_PROCESSING
        assert event.component_name == "test_component"
        assert event.action_taken == "Test action"
        assert event.entity_id == "TEST_001"
        assert event.user_id == "USER_001"
    
    def test_audit_event_immutability(self, fresh_audit_manager):
        """Test that audit events are immutable"""
        event = fresh_audit_manager.log_event(
            event_type=AuditEventType.USER_VIEW,
            component_name="test",
            action_taken="View",
        )
        
        # Should not be able to modify
        with pytest.raises((AttributeError, TypeError)):
            event.action_taken = "Modified"
    
    def test_audit_event_integrity_verification(self, fresh_audit_manager):
        """Test integrity verification"""
        event = fresh_audit_manager.log_event(
            event_type=AuditEventType.AGENT_SIGNAL,
            component_name="agent.test",
            action_taken="Signal generated",
        )
        
        assert event.verify_integrity(), "Fresh event should pass integrity check"
    
    def test_query_by_event_type(self, fresh_audit_manager):
        """Test querying by event type"""
        # Log different event types
        fresh_audit_manager.log_event(
            event_type=AuditEventType.USER_VIEW,
            component_name="ui",
            action_taken="View",
        )
        fresh_audit_manager.log_event(
            event_type=AuditEventType.DATA_PROCESSING,
            component_name="pipeline",
            action_taken="Process",
        )
        
        # Query for USER_VIEW only
        query = AuditQuery(event_types=[AuditEventType.USER_VIEW])
        report = fresh_audit_manager.query_events(query)
        
        assert all(e.event_type == AuditEventType.USER_VIEW for e in report.events)
    
    def test_query_by_user_id(self, fresh_audit_manager):
        """Test querying by user ID"""
        # Log events for different users
        fresh_audit_manager.log_event(
            event_type=AuditEventType.USER_VIEW,
            component_name="ui",
            action_taken="View",
            user_id="USER_001",
        )
        fresh_audit_manager.log_event(
            event_type=AuditEventType.USER_VIEW,
            component_name="ui",
            action_taken="View",
            user_id="USER_002",
        )
        
        # Query for USER_001 only
        query = AuditQuery(user_ids=["USER_001"])
        report = fresh_audit_manager.query_events(query)
        
        assert all(e.user_id == "USER_001" for e in report.events)
    
    def test_query_by_entity_id(self, fresh_audit_manager):
        """Test querying by entity ID"""
        # Log events for different entities
        fresh_audit_manager.log_event(
            event_type=AuditEventType.DQI_CALCULATION,
            component_name="dqi",
            action_taken="Calculate",
            entity_id="SITE_001",
        )
        fresh_audit_manager.log_event(
            event_type=AuditEventType.DQI_CALCULATION,
            component_name="dqi",
            action_taken="Calculate",
            entity_id="SITE_002",
        )
        
        # Query for SITE_001 only
        query = AuditQuery(entity_ids=["SITE_001"])
        report = fresh_audit_manager.query_events(query)
        
        assert all(e.entity_id == "SITE_001" for e in report.events)
    
    def test_get_user_actions(self, fresh_audit_manager):
        """Test getting user actions"""
        # Log user actions
        fresh_audit_manager.log_user_action(
            user_id="USER_001",
            action="VIEW",
            entity_id="SITE_001",
        )
        fresh_audit_manager.log_user_action(
            user_id="USER_001",
            action="EXPORT",
            entity_id="SITE_001",
        )
        
        actions = fresh_audit_manager.get_user_actions("USER_001")
        
        assert len(actions) >= 2
        assert all(a.user_id == "USER_001" for a in actions)
    
    def test_get_entity_history(self, fresh_audit_manager):
        """Test getting entity history"""
        # Log events for entity
        fresh_audit_manager.log_event(
            event_type=AuditEventType.DATA_PROCESSING,
            component_name="pipeline",
            action_taken="Process",
            entity_id="STUDY_001",
        )
        fresh_audit_manager.log_event(
            event_type=AuditEventType.DQI_CALCULATION,
            component_name="dqi",
            action_taken="Calculate",
            entity_id="STUDY_001",
        )
        
        history = fresh_audit_manager.get_entity_history("STUDY_001")
        
        assert len(history) >= 2
        assert all(h.entity_id == "STUDY_001" for h in history)
    
    def test_log_config_change(self, fresh_audit_manager):
        """Test logging configuration changes"""
        event = fresh_audit_manager.log_config_change(
            user_id="ADMIN_001",
            config_key="dqi.safety_weight",
            previous_value=0.35,
            new_value=0.40,
        )
        
        assert event.event_type == AuditEventType.CONFIG_CHANGE
        assert event.user_id == "ADMIN_001"
        assert event.previous_state == {"value": 0.35}
        assert event.new_state == {"value": 0.40}
    
    def test_log_agent_decision(self, fresh_audit_manager):
        """Test logging agent decisions"""
        event = fresh_audit_manager.log_agent_decision(
            agent_name="completeness",
            entity_id="SITE_001",
            decision="HIGH risk detected",
            confidence=0.85,
            details={"missing_rate": 0.25},
        )
        
        assert event.event_type == AuditEventType.AGENT_SIGNAL
        assert "completeness" in event.component_name
        assert event.entity_id == "SITE_001"
        assert event.details["confidence"] == 0.85
    
    def test_report_summary_generation(self, fresh_audit_manager):
        """Test report summary generation"""
        # Log various events
        for i in range(5):
            fresh_audit_manager.log_event(
                event_type=AuditEventType.USER_VIEW,
                component_name="ui",
                action_taken="View",
                user_id=f"USER_{i:03d}",
            )
        
        query = AuditQuery()
        report = fresh_audit_manager.query_events(query)
        
        assert "total" in report.summary
        assert "by_type" in report.summary
        assert "by_component" in report.summary
        assert report.summary["total"] >= 5
