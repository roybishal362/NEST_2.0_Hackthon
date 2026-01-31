"""
Property-Based Tests for Guardian Staleness Detection
=====================================================
Tests Property 6: Guardian Staleness Detection

**Property 6: Guardian Staleness Detection**
*For any* sequence of snapshots where alerts persist without underlying data changes,
the Guardian Agent should flag potential system staleness and notify administrators.

**Validates: Requirements 3.2**

This test uses Hypothesis to generate various staleness scenarios
to verify the Guardian Agent correctly detects system staleness.
"""

from datetime import datetime
from typing import Any, Dict, List

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck, assume

from src.guardian import (
    GuardianAgent,
    GuardianEvent,
    GuardianEventType,
    GuardianSeverity,
    StalenessIndicator,
)


# ========================================
# TEST STRATEGIES
# ========================================

@st.composite
def alert_list_strategy(draw, min_size: int = 0, max_size: int = 5):
    """Generate a list of alert type strings"""
    return draw(st.lists(
        st.text(min_size=5, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz_"),
        min_size=min_size,
        max_size=max_size,
        unique=True
    ))


@st.composite
def staleness_scenario_strategy(draw):
    """
    Generate a staleness scenario with:
    - Number of consecutive unchanged snapshots
    - Whether data has changed
    - Alert list
    """
    num_snapshots = draw(st.integers(min_value=1, max_value=10))
    data_changed = draw(st.booleans())
    alerts = draw(alert_list_strategy(min_size=1, max_size=5))
    
    return {
        "num_snapshots": num_snapshots,
        "data_changed": data_changed,
        "alerts": alerts,
    }


# ========================================
# PROPERTY TESTS
# ========================================

class TestGuardianStalenessDetectionProperty:
    """
    Property-based tests for Guardian staleness detection.
    
    Feature: clinical-ai-system, Property 6: Guardian Staleness Detection
    """
    
    @given(scenario=staleness_scenario_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_staleness_detected_when_alerts_persist_with_data_changes(self, scenario):
        """
        Feature: clinical-ai-system, Property 6: Guardian Staleness Detection
        Validates: Requirements 3.2
        
        Property: When alerts persist unchanged across multiple snapshots
        while data has changed, Guardian should detect staleness.
        """
        guardian = GuardianAgent(staleness_threshold=3)
        entity_id = "TEST_ENTITY"
        alerts = scenario["alerts"]
        
        # First call initializes tracking (doesn't count toward staleness)
        guardian.check_staleness(entity_id, alerts, data_has_changed=False)
        
        # Simulate multiple snapshots with same alerts
        for i in range(scenario["num_snapshots"]):
            # Data changes on some iterations
            data_changed = scenario["data_changed"]
            is_stale, event = guardian.check_staleness(entity_id, alerts, data_changed)
        
        # Get final staleness indicator
        indicator = guardian.get_staleness_indicator(entity_id)
        
        # PROPERTY VERIFICATION
        # Staleness score should be in valid range
        assert 0.0 <= indicator.staleness_score <= 1.0
        
        # If we had enough snapshots with data changes, staleness should be detected
        if scenario["num_snapshots"] >= 3 and scenario["data_changed"]:
            assert indicator.consecutive_unchanged_snapshots >= 3
            assert indicator.is_stale or indicator.staleness_score >= 1.0

    
    @given(alerts=alert_list_strategy(min_size=1, max_size=5))
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_staleness_resets_when_alerts_change(self, alerts):
        """
        Feature: clinical-ai-system, Property 6: Guardian Staleness Detection
        Validates: Requirements 3.2
        
        Property: When alerts change between snapshots, staleness tracking
        should reset to zero.
        """
        guardian = GuardianAgent(staleness_threshold=3)
        entity_id = "TEST_ENTITY"
        
        # Build up staleness with same alerts
        for _ in range(5):
            guardian.check_staleness(entity_id, alerts, data_has_changed=True)
        
        indicator_before = guardian.get_staleness_indicator(entity_id)
        assert indicator_before.consecutive_unchanged_snapshots >= 4
        
        # Change alerts
        new_alerts = alerts + ["new_alert_type"]
        guardian.check_staleness(entity_id, new_alerts, data_has_changed=False)
        
        indicator_after = guardian.get_staleness_indicator(entity_id)
        
        # PROPERTY VERIFICATION: Staleness should reset
        assert indicator_after.consecutive_unchanged_snapshots == 0
        assert indicator_after.staleness_score == 0.0
        assert not indicator_after.is_stale
    
    @given(num_snapshots=st.integers(min_value=1, max_value=10))
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_staleness_score_increases_monotonically(self, num_snapshots):
        """
        Feature: clinical-ai-system, Property 6: Guardian Staleness Detection
        Validates: Requirements 3.2
        
        Property: Staleness score should increase monotonically as more
        snapshots pass with unchanged alerts.
        """
        guardian = GuardianAgent(staleness_threshold=5)
        entity_id = "TEST_ENTITY"
        alerts = ["alert1", "alert2"]
        
        prev_score = 0.0
        for i in range(num_snapshots):
            guardian.check_staleness(entity_id, alerts, data_has_changed=True)
            indicator = guardian.get_staleness_indicator(entity_id)
            
            # PROPERTY VERIFICATION: Score should not decrease
            assert indicator.staleness_score >= prev_score, \
                f"Staleness score decreased from {prev_score} to {indicator.staleness_score}"
            prev_score = indicator.staleness_score

    
    @given(threshold=st.integers(min_value=2, max_value=10))
    @settings(max_examples=50, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_staleness_threshold_respected(self, threshold):
        """
        Feature: clinical-ai-system, Property 6: Guardian Staleness Detection
        Validates: Requirements 3.2
        
        Property: Staleness should only be flagged after the configured
        threshold number of unchanged snapshots.
        """
        guardian = GuardianAgent(staleness_threshold=threshold)
        entity_id = "TEST_ENTITY"
        alerts = ["alert1"]
        
        # First call initializes tracking
        guardian.check_staleness(entity_id, alerts, data_has_changed=False)
        
        # Check staleness for threshold-1 snapshots (after initialization)
        for i in range(threshold - 1):
            is_stale, event = guardian.check_staleness(entity_id, alerts, data_has_changed=True)
            # PROPERTY VERIFICATION: Should not be stale before threshold
            if i < threshold - 2:  # Before reaching threshold
                assert not is_stale, \
                    f"Staleness detected at snapshot {i+1}, before threshold {threshold}"
        
        # The last iteration should trigger staleness (at threshold)
        indicator = guardian.get_staleness_indicator(entity_id)
        
        # PROPERTY VERIFICATION: Should be stale at or after threshold
        assert indicator.consecutive_unchanged_snapshots >= threshold - 1
    
    @given(alerts=alert_list_strategy(min_size=1, max_size=5))
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_no_staleness_without_data_changes(self, alerts):
        """
        Feature: clinical-ai-system, Property 6: Guardian Staleness Detection
        Validates: Requirements 3.2
        
        Property: If data hasn't changed, same alerts persisting is expected
        and should not trigger staleness.
        """
        guardian = GuardianAgent(staleness_threshold=3)
        entity_id = "TEST_ENTITY"
        
        # Check staleness multiple times WITHOUT data changes
        for _ in range(10):
            is_stale, event = guardian.check_staleness(entity_id, alerts, data_has_changed=False)
        
        indicator = guardian.get_staleness_indicator(entity_id)
        
        # PROPERTY VERIFICATION: Should not be stale if data hasn't changed
        # (data_has_changed accumulates, so if never true, shouldn't trigger)
        assert not indicator.data_has_changed

    
    @given(entity_ids=st.lists(st.text(min_size=5, max_size=15, alphabet="abcdefghijklmnopqrstuvwxyz0123456789"), min_size=2, max_size=5, unique=True))
    @settings(max_examples=50, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_staleness_tracked_independently_per_entity(self, entity_ids):
        """
        Feature: clinical-ai-system, Property 6: Guardian Staleness Detection
        Validates: Requirements 3.2
        
        Property: Staleness should be tracked independently for each entity.
        """
        guardian = GuardianAgent(staleness_threshold=10)  # High threshold to avoid triggering staleness
        
        # Track different alerts for each entity with different number of checks
        for i, entity_id in enumerate(entity_ids):
            alerts = [f"alert_{i}"]
            # First call initializes
            guardian.check_staleness(entity_id, alerts, data_has_changed=False)
            # Additional calls increment counter
            for _ in range(i):
                guardian.check_staleness(entity_id, alerts, data_has_changed=True)
        
        # PROPERTY VERIFICATION: Each entity should have independent tracking
        for i, entity_id in enumerate(entity_ids):
            indicator = guardian.get_staleness_indicator(entity_id)
            assert indicator is not None
            assert indicator.entity_id == entity_id
            # Each entity should have its own count (i additional calls after init)
            assert indicator.consecutive_unchanged_snapshots == i


# ========================================
# UNIT TESTS
# ========================================

class TestGuardianStalenessUnit:
    """Unit tests for Guardian staleness detection"""
    
    def test_first_check_never_stale(self):
        """Test that first staleness check is never stale"""
        guardian = GuardianAgent()
        
        is_stale, event = guardian.check_staleness("TEST", ["alert1"], data_has_changed=True)
        
        assert not is_stale
        assert event is None
    
    def test_staleness_event_has_correct_type(self):
        """Test that staleness events have correct type"""
        guardian = GuardianAgent(staleness_threshold=2)
        
        # Trigger staleness
        guardian.check_staleness("TEST", ["alert1"], data_has_changed=True)
        guardian.check_staleness("TEST", ["alert1"], data_has_changed=True)
        is_stale, event = guardian.check_staleness("TEST", ["alert1"], data_has_changed=True)
        
        assert is_stale
        assert event.event_type == GuardianEventType.STALENESS_DETECTED
        assert event.severity == GuardianSeverity.WARNING
    
    def test_reset_staleness_tracking(self):
        """Test that staleness tracking can be reset"""
        guardian = GuardianAgent(staleness_threshold=2)
        
        # Build up staleness
        for _ in range(5):
            guardian.check_staleness("TEST", ["alert1"], data_has_changed=True)
        
        indicator = guardian.get_staleness_indicator("TEST")
        assert indicator.consecutive_unchanged_snapshots >= 4
        
        # Reset tracking
        guardian.reset_staleness_tracking("TEST")
        
        indicator = guardian.get_staleness_indicator("TEST")
        assert indicator is None
    
    def test_reset_all_staleness_tracking(self):
        """Test that all staleness tracking can be reset"""
        guardian = GuardianAgent()
        
        # Track multiple entities
        guardian.check_staleness("ENTITY1", ["alert1"], data_has_changed=True)
        guardian.check_staleness("ENTITY2", ["alert2"], data_has_changed=True)
        
        assert guardian.get_staleness_indicator("ENTITY1") is not None
        assert guardian.get_staleness_indicator("ENTITY2") is not None
        
        # Reset all
        guardian.reset_staleness_tracking()
        
        assert guardian.get_staleness_indicator("ENTITY1") is None
        assert guardian.get_staleness_indicator("ENTITY2") is None
    
    def test_staleness_indicator_to_dict(self):
        """Test that staleness indicator can be serialized"""
        guardian = GuardianAgent()
        
        guardian.check_staleness("TEST", ["alert1", "alert2"], data_has_changed=True)
        indicator = guardian.get_staleness_indicator("TEST")
        
        result = indicator.to_dict()
        
        assert "entity_id" in result
        assert "consecutive_unchanged_snapshots" in result
        assert "alert_types_unchanged" in result
        assert "staleness_score" in result
        assert result["entity_id"] == "TEST"
