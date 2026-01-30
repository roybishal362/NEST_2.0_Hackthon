"""
Property-Based Tests for Configuration Change Control
=====================================================
Tests Property 12: Configuration Change Control

**Property 12: Configuration Change Control**
*For any* configuration modification including thresholds, weights, or rules,
the system should require human approval, maintain versioned history, and
never implement automatic self-modification.

**Validates: Requirements 8.1, 8.2, 8.5**

This test uses Hypothesis to generate various configuration change scenarios
and verify that the configuration management system maintains proper controls.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List
import tempfile
import shutil
import os

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck, assume

from src.governance import (
    VersionedConfigManager,
    ConfigVersion,
    ConfigChangeRequest,
    ConfigChangeStatus,
    ConfigChangeType,
)


# ========================================
# TEST STRATEGIES
# ========================================

@st.composite
def config_key_strategy(draw):
    """Generate valid configuration keys"""
    keys = [
        "dqi.weights.safety",
        "dqi.weights.compliance",
        "dqi.weights.completeness",
        "dqi.weights.operations",
        "guardian.sensitivity",
        "guardian.staleness_detection_hours",
        "agents.data_completeness.weight",
        "agents.safety_compliance.weight",
        "agents.query_quality.weight",
        "processing.batch_size",
        "processing.timeout_minutes",
    ]
    return draw(st.sampled_from(keys))


@st.composite
def change_type_strategy(draw):
    """Generate valid change types"""
    return draw(st.sampled_from(list(ConfigChangeType)))


@st.composite
def numeric_value_strategy(draw):
    """Generate valid numeric configuration values"""
    return draw(st.floats(min_value=0.01, max_value=100.0, allow_nan=False, allow_infinity=False))


@st.composite
def user_id_strategy(draw):
    """Generate valid user IDs"""
    roles = ["ADMIN", "GOVERNANCE", "LEAD"]
    role = draw(st.sampled_from(roles))
    number = draw(st.integers(min_value=1, max_value=99))
    return f"{role}_{number:02d}"


@st.composite
def justification_strategy(draw):
    """Generate valid justifications"""
    justifications = [
        "Guardian Agent detected consistency issues",
        "Historical analysis suggests threshold adjustment",
        "Performance optimization based on recent data",
        "Regulatory compliance requirement",
        "User feedback indicates need for adjustment",
        "Quarterly calibration review",
    ]
    return draw(st.sampled_from(justifications))


@st.composite
def change_request_params_strategy(draw):
    """Generate complete change request parameters"""
    return {
        "change_type": draw(change_type_strategy()),
        "config_key": draw(config_key_strategy()),
        "proposed_value": draw(numeric_value_strategy()),
        "justification": draw(justification_strategy()),
        "requested_by": draw(user_id_strategy()),
    }


# ========================================
# FIXTURES
# ========================================

@pytest.fixture
def temp_config_dir():
    """Create temporary directory for configuration"""
    temp_dir = tempfile.mkdtemp(prefix="config_test_")
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def fresh_config_manager(temp_config_dir):
    """Create a fresh configuration manager for each test"""
    config_path = os.path.join(temp_config_dir, "system_config.yaml")
    history_path = os.path.join(temp_config_dir, "history")
    
    manager = VersionedConfigManager(
        config_path=config_path,
        history_path=history_path,
        initial_version="1.0.0",
    )
    yield manager


# ========================================
# PROPERTY TESTS
# ========================================

class TestConfigurationChangeControlProperty:
    """
    Property-based tests for configuration change control.
    
    Feature: clinical-ai-system, Property 12: Configuration Change Control
    """
    
    @given(params=change_request_params_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_change_requests_start_pending(
        self,
        params: Dict[str, Any],
        fresh_config_manager,
    ):
        """
        Feature: clinical-ai-system, Property 12: Configuration Change Control
        Validates: Requirements 8.1, 8.2
        
        Property: For any configuration change request, it should start in PENDING status.
        """
        request = fresh_config_manager.create_change_request(**params)
        
        assert request.status == ConfigChangeStatus.PENDING, \
            "New change requests should start in PENDING status"
    
    @given(params=change_request_params_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_change_requests_require_approval(
        self,
        params: Dict[str, Any],
        fresh_config_manager,
    ):
        """
        Feature: clinical-ai-system, Property 12: Configuration Change Control
        Validates: Requirements 8.2
        
        Property: For any configuration change, it should require human approval
        before being applied.
        """
        request = fresh_config_manager.create_change_request(**params)
        
        # Attempt to apply without approval should fail
        success, message, version = fresh_config_manager.apply_change_request(
            request_id=request.request_id,
            applied_by="ADMIN_01",
        )
        
        assert not success, "Unapproved changes should not be applied"
        assert "not approved" in message.lower(), "Error message should indicate approval required"
    
    @given(params=change_request_params_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_approved_changes_create_new_version(
        self,
        params: Dict[str, Any],
        fresh_config_manager,
    ):
        """
        Feature: clinical-ai-system, Property 12: Configuration Change Control
        Validates: Requirements 8.1
        
        Property: For any approved configuration change, applying it should
        create a new version with incremented version number.
        """
        # Get initial version count
        initial_versions = len(fresh_config_manager.list_versions())
        initial_version = fresh_config_manager.get_active_version()
        
        # Create and approve change request
        request = fresh_config_manager.create_change_request(**params)
        
        success, _ = fresh_config_manager.approve_change_request(
            request_id=request.request_id,
            reviewed_by="GOVERNANCE_01",
            review_notes="Approved for testing",
        )
        assert success, "Approval should succeed"
        
        # Apply the change
        success, message, new_version = fresh_config_manager.apply_change_request(
            request_id=request.request_id,
            applied_by="ADMIN_01",
        )
        
        assert success, "Applying approved change should succeed"
        assert new_version is not None, "New version should be created"
        
        # Verify version count increased
        assert len(fresh_config_manager.list_versions()) == initial_versions + 1, \
            "Version count should increase"
        
        # Verify version number incremented
        assert new_version.version_number != initial_version.version_number, \
            "Version number should change"
    
    @given(params=change_request_params_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_change_history_is_maintained(
        self,
        params: Dict[str, Any],
        fresh_config_manager,
    ):
        """
        Feature: clinical-ai-system, Property 12: Configuration Change Control
        Validates: Requirements 8.1
        
        Property: For any configuration change request, it should be recorded
        in the change history with all details preserved.
        """
        request = fresh_config_manager.create_change_request(**params)
        
        # Retrieve from history
        history = fresh_config_manager.get_change_history(config_key=params["config_key"])
        
        # Find our request in history
        found = False
        for hist_request in history:
            if hist_request.request_id == request.request_id:
                found = True
                assert hist_request.config_key == params["config_key"]
                assert hist_request.proposed_value == params["proposed_value"]
                assert hist_request.justification == params["justification"]
                assert hist_request.requested_by == params["requested_by"]
                break
        
        assert found, "Change request should be in history"
    
    @given(params=change_request_params_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_rejected_changes_not_applied(
        self,
        params: Dict[str, Any],
        fresh_config_manager,
    ):
        """
        Feature: clinical-ai-system, Property 12: Configuration Change Control
        Validates: Requirements 8.2
        
        Property: For any rejected configuration change, it should not be
        applicable to the system.
        """
        request = fresh_config_manager.create_change_request(**params)
        
        # Reject the request
        success, _ = fresh_config_manager.reject_change_request(
            request_id=request.request_id,
            reviewed_by="GOVERNANCE_01",
            review_notes="Rejected for testing",
        )
        assert success, "Rejection should succeed"
        
        # Attempt to apply should fail
        success, message, version = fresh_config_manager.apply_change_request(
            request_id=request.request_id,
            applied_by="ADMIN_01",
        )
        
        assert not success, "Rejected changes should not be applied"
        assert version is None, "No version should be created for rejected changes"
    
    @given(params=change_request_params_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_versions_have_integrity_checksums(
        self,
        params: Dict[str, Any],
        fresh_config_manager,
    ):
        """
        Feature: clinical-ai-system, Property 12: Configuration Change Control
        Validates: Requirements 8.1
        
        Property: For any configuration version, it should have a valid
        integrity checksum that can be verified.
        """
        # Create, approve, and apply a change
        request = fresh_config_manager.create_change_request(**params)
        fresh_config_manager.approve_change_request(
            request_id=request.request_id,
            reviewed_by="GOVERNANCE_01",
        )
        success, _, new_version = fresh_config_manager.apply_change_request(
            request_id=request.request_id,
            applied_by="ADMIN_01",
        )
        
        if success and new_version:
            assert new_version.checksum is not None, "Version should have checksum"
            assert len(new_version.checksum) == 64, "Checksum should be SHA-256"
            assert new_version.verify_integrity(), "Version should pass integrity check"
    
    @given(
        params1=change_request_params_strategy(),
        params2=change_request_params_strategy(),
    )
    @settings(max_examples=50, deadline=15000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_no_automatic_self_modification(
        self,
        params1: Dict[str, Any],
        params2: Dict[str, Any],
        fresh_config_manager,
    ):
        """
        Feature: clinical-ai-system, Property 12: Configuration Change Control
        Validates: Requirements 8.5
        
        Property: The system should never implement automatic self-modification.
        All changes must go through the approval workflow.
        """
        # Create two change requests
        request1 = fresh_config_manager.create_change_request(**params1)
        request2 = fresh_config_manager.create_change_request(**params2)
        
        # Both should be pending
        assert request1.status == ConfigChangeStatus.PENDING
        assert request2.status == ConfigChangeStatus.PENDING
        
        # Get pending requests
        pending = fresh_config_manager.get_pending_requests()
        
        # All pending requests should require human action
        for req in pending:
            assert req.status == ConfigChangeStatus.PENDING, \
                "Pending requests should not auto-approve"
            
            # Verify cannot apply without approval
            success, _, _ = fresh_config_manager.apply_change_request(
                request_id=req.request_id,
                applied_by="SYSTEM",  # Even system user cannot bypass
            )
            assert not success, "System should not auto-apply changes"
    
    @given(params=change_request_params_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_approval_records_reviewer(
        self,
        params: Dict[str, Any],
        fresh_config_manager,
    ):
        """
        Feature: clinical-ai-system, Property 12: Configuration Change Control
        Validates: Requirements 8.2
        
        Property: For any approved change, the reviewer information should
        be recorded for audit purposes.
        """
        request = fresh_config_manager.create_change_request(**params)
        reviewer = "GOVERNANCE_01"
        review_notes = "Approved after review"
        
        success, _ = fresh_config_manager.approve_change_request(
            request_id=request.request_id,
            reviewed_by=reviewer,
            review_notes=review_notes,
        )
        
        assert success, "Approval should succeed"
        
        # Verify reviewer info is recorded
        history = fresh_config_manager.get_change_history()
        for req in history:
            if req.request_id == request.request_id:
                assert req.reviewed_by == reviewer, "Reviewer should be recorded"
                assert req.reviewed_at is not None, "Review time should be recorded"
                assert req.review_notes == review_notes, "Review notes should be recorded"
                break


# ========================================
# UNIT TESTS
# ========================================

class TestConfigurationChangeControlUnit:
    """Unit tests for configuration change control"""
    
    def test_create_change_request(self, fresh_config_manager):
        """Test basic change request creation"""
        request = fresh_config_manager.create_change_request(
            change_type=ConfigChangeType.WEIGHT_UPDATE,
            config_key="dqi.weights.safety",
            proposed_value=0.40,
            justification="Testing weight adjustment",
            requested_by="ADMIN_01",
        )
        
        assert request.request_id is not None
        assert request.status == ConfigChangeStatus.PENDING
        assert request.change_type == ConfigChangeType.WEIGHT_UPDATE
        assert request.config_key == "dqi.weights.safety"
        assert request.proposed_value == 0.40
    
    def test_approve_and_apply_change(self, fresh_config_manager):
        """Test full approval and apply workflow"""
        # Create request
        request = fresh_config_manager.create_change_request(
            change_type=ConfigChangeType.THRESHOLD_UPDATE,
            config_key="guardian.sensitivity",
            proposed_value=0.15,
            justification="Adjusting sensitivity",
            requested_by="ADMIN_01",
        )
        
        # Approve
        success, _ = fresh_config_manager.approve_change_request(
            request_id=request.request_id,
            reviewed_by="GOVERNANCE_01",
        )
        assert success
        assert request.status == ConfigChangeStatus.APPROVED
        
        # Apply
        success, message, new_version = fresh_config_manager.apply_change_request(
            request_id=request.request_id,
            applied_by="ADMIN_01",
        )
        assert success
        assert new_version is not None
        assert request.status == ConfigChangeStatus.APPLIED
    
    def test_reject_change_request(self, fresh_config_manager):
        """Test change request rejection"""
        request = fresh_config_manager.create_change_request(
            change_type=ConfigChangeType.RULE_UPDATE,
            config_key="processing.batch_size",
            proposed_value=5000,
            justification="Testing rejection",
            requested_by="ADMIN_01",
        )
        
        success, _ = fresh_config_manager.reject_change_request(
            request_id=request.request_id,
            reviewed_by="GOVERNANCE_01",
            review_notes="Not approved for testing",
        )
        
        assert success
        assert request.status == ConfigChangeStatus.REJECTED
    
    def test_version_rollback(self, fresh_config_manager):
        """Test rollback to previous version"""
        # Get initial version
        initial_version = fresh_config_manager.get_active_version()
        
        # Create and apply a change
        request = fresh_config_manager.create_change_request(
            change_type=ConfigChangeType.WEIGHT_UPDATE,
            config_key="dqi.weights.safety",
            proposed_value=0.50,
            justification="Testing rollback",
            requested_by="ADMIN_01",
        )
        fresh_config_manager.approve_change_request(
            request_id=request.request_id,
            reviewed_by="GOVERNANCE_01",
        )
        fresh_config_manager.apply_change_request(
            request_id=request.request_id,
            applied_by="ADMIN_01",
        )
        
        # Rollback to initial version
        success, message = fresh_config_manager.rollback_to_version(
            version_id=initial_version.version_id,
            rolled_back_by="ADMIN_01",
            reason="Testing rollback functionality",
        )
        
        assert success
        assert "Rolled back" in message
    
    def test_get_pending_requests(self, fresh_config_manager):
        """Test getting pending requests"""
        # Create multiple requests
        for i in range(3):
            fresh_config_manager.create_change_request(
                change_type=ConfigChangeType.THRESHOLD_UPDATE,
                config_key=f"test.key.{i}",
                proposed_value=i * 0.1,
                justification=f"Test request {i}",
                requested_by="ADMIN_01",
            )
        
        pending = fresh_config_manager.get_pending_requests()
        assert len(pending) >= 3
        assert all(r.status == ConfigChangeStatus.PENDING for r in pending)
    
    def test_version_integrity_verification(self, fresh_config_manager):
        """Test version integrity verification"""
        version = fresh_config_manager.get_active_version()
        
        assert version.checksum is not None
        assert version.verify_integrity()
    
    def test_cannot_apply_pending_request(self, fresh_config_manager):
        """Test that pending requests cannot be applied"""
        request = fresh_config_manager.create_change_request(
            change_type=ConfigChangeType.WEIGHT_UPDATE,
            config_key="dqi.weights.safety",
            proposed_value=0.40,
            justification="Testing",
            requested_by="ADMIN_01",
        )
        
        success, message, version = fresh_config_manager.apply_change_request(
            request_id=request.request_id,
            applied_by="ADMIN_01",
        )
        
        assert not success
        assert "not approved" in message.lower()
        assert version is None
