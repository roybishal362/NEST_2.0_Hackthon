"""
Property-Based Tests for Guardian Data-Output Consistency Detection
===================================================================
Tests Property 5: Guardian Data-Output Consistency Detection

**Property 5: Guardian Data-Output Consistency Detection**
*For any* pair of consecutive snapshots where underlying data improves significantly,
the Guardian Agent should detect when system outputs fail to reflect proportional
improvements and raise appropriate integrity warnings.

**Validates: Requirements 3.1, 3.3**

This test uses Hypothesis to generate various data and output delta scenarios
to verify the Guardian Agent correctly detects inconsistencies.
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
    DataDelta,
    OutputDelta,
)


# ========================================
# TEST STRATEGIES
# ========================================

@st.composite
def snapshot_data_strategy(draw, snapshot_id: str = None):
    """Generate valid snapshot data with metrics"""
    return {
        "snapshot_id": snapshot_id or draw(st.text(min_size=5, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz0123456789_")),
        "missing_pages_pct": draw(st.floats(min_value=0, max_value=100, allow_nan=False)),
        "form_completion_rate": draw(st.floats(min_value=0, max_value=100, allow_nan=False)),
        "sae_backlog_days": draw(st.floats(min_value=0, max_value=365, allow_nan=False)),
        "fatal_sae_count": draw(st.integers(min_value=0, max_value=10)),
        "open_query_count": draw(st.integers(min_value=0, max_value=500)),
        "query_aging_days": draw(st.floats(min_value=0, max_value=90, allow_nan=False)),
        "dqi_score": draw(st.floats(min_value=0, max_value=100, allow_nan=False)),
        "risk_score": draw(st.floats(min_value=0, max_value=100, allow_nan=False)),
    }


@st.composite
def improved_snapshot_pair_strategy(draw):
    """
    Generate a pair of snapshots where data has improved significantly.
    
    Improvement means:
    - Lower missing_pages_pct
    - Higher form_completion_rate
    - Lower sae_backlog_days
    - Lower open_query_count
    """
    # Generate base snapshot
    prev_snapshot = draw(snapshot_data_strategy(snapshot_id="prev_snapshot"))
    
    # Generate improved snapshot (lower bad metrics, higher good metrics)
    improvement_factor = draw(st.floats(min_value=0.2, max_value=0.5, allow_nan=False))
    
    curr_snapshot = {
        "snapshot_id": "curr_snapshot",
        # Lower is better - reduce by improvement factor
        "missing_pages_pct": max(0, prev_snapshot["missing_pages_pct"] * (1 - improvement_factor)),
        "sae_backlog_days": max(0, prev_snapshot["sae_backlog_days"] * (1 - improvement_factor)),
        "open_query_count": max(0, int(prev_snapshot["open_query_count"] * (1 - improvement_factor))),
        "query_aging_days": max(0, prev_snapshot["query_aging_days"] * (1 - improvement_factor)),
        "fatal_sae_count": max(0, prev_snapshot["fatal_sae_count"] - 1),
        # Higher is better - increase by improvement factor
        "form_completion_rate": min(100, prev_snapshot["form_completion_rate"] * (1 + improvement_factor)),
        "dqi_score": min(100, prev_snapshot["dqi_score"] * (1 + improvement_factor * 0.5)),
        "risk_score": max(0, prev_snapshot["risk_score"] * (1 - improvement_factor)),
    }
    
    return prev_snapshot, curr_snapshot


@st.composite
def degraded_snapshot_pair_strategy(draw):
    """
    Generate a pair of snapshots where data has degraded significantly.
    """
    # Generate base snapshot
    prev_snapshot = draw(snapshot_data_strategy(snapshot_id="prev_snapshot"))
    
    # Generate degraded snapshot
    degradation_factor = draw(st.floats(min_value=0.2, max_value=0.5, allow_nan=False))
    
    curr_snapshot = {
        "snapshot_id": "curr_snapshot",
        # Lower is better - increase by degradation factor (worse)
        "missing_pages_pct": min(100, prev_snapshot["missing_pages_pct"] * (1 + degradation_factor)),
        "sae_backlog_days": prev_snapshot["sae_backlog_days"] * (1 + degradation_factor),
        "open_query_count": int(prev_snapshot["open_query_count"] * (1 + degradation_factor)),
        "query_aging_days": prev_snapshot["query_aging_days"] * (1 + degradation_factor),
        "fatal_sae_count": prev_snapshot["fatal_sae_count"] + draw(st.integers(min_value=1, max_value=3)),
        # Higher is better - decrease by degradation factor (worse)
        "form_completion_rate": max(0, prev_snapshot["form_completion_rate"] * (1 - degradation_factor)),
        "dqi_score": max(0, prev_snapshot["dqi_score"] * (1 - degradation_factor * 0.5)),
        "risk_score": min(100, prev_snapshot["risk_score"] * (1 + degradation_factor)),
    }
    
    return prev_snapshot, curr_snapshot


@st.composite
def stable_snapshot_pair_strategy(draw):
    """
    Generate a pair of snapshots where data is relatively stable (minor changes).
    """
    # Generate base snapshot
    prev_snapshot = draw(snapshot_data_strategy(snapshot_id="prev_snapshot"))
    
    # Generate similar snapshot with minor variations
    noise_factor = draw(st.floats(min_value=0.01, max_value=0.05, allow_nan=False))
    direction = draw(st.sampled_from([-1, 1]))
    
    curr_snapshot = {
        "snapshot_id": "curr_snapshot",
        "missing_pages_pct": max(0, min(100, prev_snapshot["missing_pages_pct"] * (1 + direction * noise_factor))),
        "form_completion_rate": max(0, min(100, prev_snapshot["form_completion_rate"] * (1 + direction * noise_factor))),
        "sae_backlog_days": max(0, prev_snapshot["sae_backlog_days"] * (1 + direction * noise_factor)),
        "fatal_sae_count": prev_snapshot["fatal_sae_count"],
        "open_query_count": prev_snapshot["open_query_count"],
        "query_aging_days": max(0, prev_snapshot["query_aging_days"] * (1 + direction * noise_factor)),
        "dqi_score": max(0, min(100, prev_snapshot["dqi_score"] * (1 + direction * noise_factor))),
        "risk_score": max(0, min(100, prev_snapshot["risk_score"] * (1 + direction * noise_factor))),
    }
    
    return prev_snapshot, curr_snapshot


@st.composite
def output_data_strategy(draw, snapshot_id: str = None):
    """Generate valid output data"""
    return {
        "snapshot_id": snapshot_id or draw(st.text(min_size=5, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz0123456789_")),
        "risk_score": draw(st.floats(min_value=0, max_value=100, allow_nan=False)),
        "risk_level": draw(st.sampled_from(["LOW", "MEDIUM", "HIGH", "CRITICAL"])),
        "dqi_score": draw(st.floats(min_value=0, max_value=100, allow_nan=False)),
        "alerts": draw(st.lists(st.text(min_size=3, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz_"), max_size=5)),
    }


# ========================================
# PROPERTY TESTS
# ========================================

class TestGuardianDataOutputConsistencyProperty:
    """
    Property-based tests for Guardian data-output consistency detection.
    
    Feature: clinical-ai-system, Property 5: Guardian Data-Output Consistency Detection
    """
    
    @given(snapshot_pair=improved_snapshot_pair_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_detects_inconsistency_when_data_improves_but_risk_increases(self, snapshot_pair):
        """
        Feature: clinical-ai-system, Property 5: Guardian Data-Output Consistency Detection
        Validates: Requirements 3.1, 3.3
        
        Property: When data improves significantly but risk score increases,
        Guardian should detect this as an inconsistency.
        """
        prev_snapshot, curr_snapshot = snapshot_pair
        guardian = GuardianAgent()
        
        # Calculate data delta
        data_delta = guardian.calculate_data_delta(prev_snapshot, curr_snapshot, "TEST_ENTITY")
        
        # Only test when data actually improved significantly
        assume(data_delta.significant and data_delta.direction == "IMPROVED")
        
        # Create inconsistent output: risk INCREASED despite data improvement
        prev_output = {
            "snapshot_id": "prev_snapshot",
            "risk_score": 50.0,
            "risk_level": "MEDIUM",
            "dqi_score": 70.0,
            "alerts": ["alert1"],
        }
        curr_output = {
            "snapshot_id": "curr_snapshot",
            "risk_score": 80.0,  # Increased - inconsistent with improvement
            "risk_level": "HIGH",
            "dqi_score": 60.0,
            "alerts": ["alert1", "alert2"],
        }
        
        output_delta = guardian.calculate_output_delta(prev_output, curr_output, "TEST_ENTITY")
        is_consistent, event = guardian.verify_consistency(data_delta, output_delta)
        
        # PROPERTY VERIFICATION: Should detect inconsistency
        assert not is_consistent, \
            "Guardian should detect inconsistency when data improves but risk increases"
        assert event is not None, \
            "Guardian should generate event for inconsistency"
        assert event.event_type == GuardianEventType.DATA_OUTPUT_INCONSISTENCY
        assert not output_delta.proportional

    
    @given(snapshot_pair=degraded_snapshot_pair_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_detects_inconsistency_when_data_degrades_but_risk_decreases(self, snapshot_pair):
        """
        Feature: clinical-ai-system, Property 5: Guardian Data-Output Consistency Detection
        Validates: Requirements 3.1, 3.3
        
        Property: When data degrades significantly but risk score decreases,
        Guardian should detect this as an inconsistency.
        """
        prev_snapshot, curr_snapshot = snapshot_pair
        guardian = GuardianAgent()
        
        # Calculate data delta
        data_delta = guardian.calculate_data_delta(prev_snapshot, curr_snapshot, "TEST_ENTITY")
        
        # Only test when data actually degraded significantly
        assume(data_delta.significant and data_delta.direction == "DEGRADED")
        
        # Create inconsistent output: risk DECREASED despite data degradation
        prev_output = {
            "snapshot_id": "prev_snapshot",
            "risk_score": 70.0,
            "risk_level": "HIGH",
            "dqi_score": 60.0,
            "alerts": ["alert1", "alert2"],
        }
        curr_output = {
            "snapshot_id": "curr_snapshot",
            "risk_score": 30.0,  # Decreased - inconsistent with degradation
            "risk_level": "LOW",
            "dqi_score": 80.0,
            "alerts": ["alert1"],
        }
        
        output_delta = guardian.calculate_output_delta(prev_output, curr_output, "TEST_ENTITY")
        is_consistent, event = guardian.verify_consistency(data_delta, output_delta)
        
        # PROPERTY VERIFICATION: Should detect inconsistency
        assert not is_consistent, \
            "Guardian should detect inconsistency when data degrades but risk decreases"
        assert event is not None, \
            "Guardian should generate event for inconsistency"
        assert event.event_type == GuardianEventType.DATA_OUTPUT_INCONSISTENCY
        assert not output_delta.proportional

    
    @given(snapshot_pair=improved_snapshot_pair_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_accepts_consistent_improvement(self, snapshot_pair):
        """
        Feature: clinical-ai-system, Property 5: Guardian Data-Output Consistency Detection
        Validates: Requirements 3.1, 3.3
        
        Property: When data improves and risk score also improves (decreases),
        Guardian should accept this as consistent.
        """
        prev_snapshot, curr_snapshot = snapshot_pair
        guardian = GuardianAgent()
        
        # Calculate data delta
        data_delta = guardian.calculate_data_delta(prev_snapshot, curr_snapshot, "TEST_ENTITY")
        
        # Only test when data actually improved significantly
        assume(data_delta.significant and data_delta.direction == "IMPROVED")
        
        # Create consistent output: risk DECREASED with data improvement
        prev_output = {
            "snapshot_id": "prev_snapshot",
            "risk_score": 70.0,
            "risk_level": "HIGH",
            "dqi_score": 60.0,
            "alerts": ["alert1", "alert2"],
        }
        curr_output = {
            "snapshot_id": "curr_snapshot",
            "risk_score": 50.0,  # Decreased - consistent with improvement
            "risk_level": "MEDIUM",
            "dqi_score": 75.0,
            "alerts": ["alert1"],
        }
        
        output_delta = guardian.calculate_output_delta(prev_output, curr_output, "TEST_ENTITY")
        is_consistent, event = guardian.verify_consistency(data_delta, output_delta)
        
        # PROPERTY VERIFICATION: Should accept as consistent
        assert is_consistent, \
            "Guardian should accept consistent improvement"
        assert event is None, \
            "Guardian should not generate event for consistent behavior"
        assert output_delta.proportional

    
    @given(snapshot_pair=stable_snapshot_pair_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_stable_data_with_stable_output_is_consistent(self, snapshot_pair):
        """
        Feature: clinical-ai-system, Property 5: Guardian Data-Output Consistency Detection
        Validates: Requirements 3.1, 3.3
        
        Property: When data is stable (minor changes) and output is stable,
        Guardian should accept this as consistent.
        """
        prev_snapshot, curr_snapshot = snapshot_pair
        guardian = GuardianAgent()
        
        # Calculate data delta
        data_delta = guardian.calculate_data_delta(prev_snapshot, curr_snapshot, "TEST_ENTITY")
        
        # Only test when data is NOT significant
        assume(not data_delta.significant)
        
        # Create stable output
        prev_output = {
            "snapshot_id": "prev_snapshot",
            "risk_score": 50.0,
            "risk_level": "MEDIUM",
            "dqi_score": 70.0,
            "alerts": ["alert1"],
        }
        curr_output = {
            "snapshot_id": "curr_snapshot",
            "risk_score": 52.0,  # Minor change - consistent with stable data
            "risk_level": "MEDIUM",
            "dqi_score": 69.0,
            "alerts": ["alert1"],
        }
        
        output_delta = guardian.calculate_output_delta(prev_output, curr_output, "TEST_ENTITY")
        is_consistent, event = guardian.verify_consistency(data_delta, output_delta)
        
        # PROPERTY VERIFICATION: Should accept as consistent
        assert is_consistent, \
            "Guardian should accept stable data with stable output"
        assert event is None
        assert output_delta.proportional

    
    @given(snapshot_pair=stable_snapshot_pair_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_stable_data_with_large_output_change_is_inconsistent(self, snapshot_pair):
        """
        Feature: clinical-ai-system, Property 5: Guardian Data-Output Consistency Detection
        Validates: Requirements 3.1, 3.3
        
        Property: When data is stable but output changes dramatically,
        Guardian should detect this as an inconsistency.
        """
        prev_snapshot, curr_snapshot = snapshot_pair
        guardian = GuardianAgent()
        
        # Calculate data delta
        data_delta = guardian.calculate_data_delta(prev_snapshot, curr_snapshot, "TEST_ENTITY")
        
        # Only test when data is NOT significant
        assume(not data_delta.significant)
        
        # Create inconsistent output: large change despite stable data
        prev_output = {
            "snapshot_id": "prev_snapshot",
            "risk_score": 30.0,
            "risk_level": "LOW",
            "dqi_score": 80.0,
            "alerts": ["alert1"],
        }
        curr_output = {
            "snapshot_id": "curr_snapshot",
            "risk_score": 85.0,  # Large increase - inconsistent with stable data
            "risk_level": "CRITICAL",
            "dqi_score": 40.0,
            "alerts": ["alert1", "alert2", "alert3"],
        }
        
        output_delta = guardian.calculate_output_delta(prev_output, curr_output, "TEST_ENTITY")
        is_consistent, event = guardian.verify_consistency(data_delta, output_delta)
        
        # PROPERTY VERIFICATION: Should detect inconsistency
        assert not is_consistent, \
            "Guardian should detect inconsistency when stable data has large output change"
        assert event is not None
        assert event.event_type == GuardianEventType.DATA_OUTPUT_INCONSISTENCY
        assert not output_delta.proportional

    
    @given(prev_data=snapshot_data_strategy(), curr_data=snapshot_data_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_data_delta_magnitude_in_valid_range(self, prev_data, curr_data):
        """
        Feature: clinical-ai-system, Property 5: Guardian Data-Output Consistency Detection
        Validates: Requirements 3.1, 3.3
        
        Property: For any pair of snapshots, the calculated data delta
        magnitude should be in the valid range [0, 1].
        """
        guardian = GuardianAgent()
        
        data_delta = guardian.calculate_data_delta(prev_data, curr_data, "TEST_ENTITY")
        
        # PROPERTY VERIFICATION: Magnitude should be in valid range
        assert 0.0 <= data_delta.overall_change_magnitude <= 1.0, \
            f"Data delta magnitude {data_delta.overall_change_magnitude} out of range [0, 1]"
    
    @given(prev_data=snapshot_data_strategy(), curr_data=snapshot_data_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_data_delta_direction_is_valid(self, prev_data, curr_data):
        """
        Feature: clinical-ai-system, Property 5: Guardian Data-Output Consistency Detection
        Validates: Requirements 3.1, 3.3
        
        Property: For any pair of snapshots, the data delta direction
        should be one of IMPROVED, DEGRADED, or STABLE.
        """
        guardian = GuardianAgent()
        
        data_delta = guardian.calculate_data_delta(prev_data, curr_data, "TEST_ENTITY")
        
        # PROPERTY VERIFICATION: Direction should be valid
        assert data_delta.direction in ["IMPROVED", "DEGRADED", "STABLE"], \
            f"Invalid data delta direction: {data_delta.direction}"

    
    @given(prev_data=snapshot_data_strategy(), curr_data=snapshot_data_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_guardian_event_structure_is_valid(self, prev_data, curr_data):
        """
        Feature: clinical-ai-system, Property 5: Guardian Data-Output Consistency Detection
        Validates: Requirements 3.1, 3.3
        
        Property: Any Guardian event generated should have all required fields
        populated with valid values.
        """
        guardian = GuardianAgent()
        
        # Calculate data delta
        data_delta = guardian.calculate_data_delta(prev_data, curr_data, "TEST_ENTITY")
        
        # Create an inconsistent scenario to generate an event
        prev_output = {"snapshot_id": "prev", "risk_score": 30.0, "risk_level": "LOW", "dqi_score": 80.0, "alerts": []}
        curr_output = {"snapshot_id": "curr", "risk_score": 90.0, "risk_level": "CRITICAL", "dqi_score": 30.0, "alerts": []}
        
        output_delta = guardian.calculate_output_delta(prev_output, curr_output, "TEST_ENTITY")
        is_consistent, event = guardian.verify_consistency(data_delta, output_delta)
        
        # If an event was generated, verify its structure
        if event is not None:
            assert event.event_id is not None and len(event.event_id) > 0
            assert event.event_type in GuardianEventType
            assert event.severity in GuardianSeverity
            assert event.entity_id == "TEST_ENTITY"
            assert event.data_delta_summary is not None
            assert event.expected_behavior is not None
            assert event.actual_behavior is not None
            assert event.recommendation is not None
            assert event.timestamp is not None


# ========================================
# UNIT TESTS
# ========================================

class TestGuardianConsistencyUnit:
    """Unit tests for Guardian consistency detection"""
    
    def test_identical_snapshots_produce_zero_delta(self):
        """Test that identical snapshots produce zero change magnitude"""
        guardian = GuardianAgent()
        
        snapshot = {
            "snapshot_id": "test",
            "missing_pages_pct": 10.0,
            "form_completion_rate": 90.0,
            "sae_backlog_days": 5.0,
        }
        
        delta = guardian.calculate_data_delta(snapshot, snapshot.copy(), "TEST_ENTITY")
        
        assert delta.overall_change_magnitude == 0.0
        assert delta.direction == "STABLE"
        assert not delta.significant
    
    def test_significant_improvement_detected(self):
        """Test that significant improvement is correctly detected"""
        guardian = GuardianAgent()
        
        prev = {
            "snapshot_id": "prev",
            "missing_pages_pct": 50.0,
            "form_completion_rate": 50.0,
        }
        curr = {
            "snapshot_id": "curr",
            "missing_pages_pct": 10.0,  # 80% reduction - improvement
            "form_completion_rate": 90.0,  # 80% increase - improvement
        }
        
        delta = guardian.calculate_data_delta(prev, curr, "TEST_ENTITY")
        
        assert delta.direction == "IMPROVED"
        assert delta.significant
    
    def test_significant_degradation_detected(self):
        """Test that significant degradation is correctly detected"""
        guardian = GuardianAgent()
        
        prev = {
            "snapshot_id": "prev",
            "missing_pages_pct": 10.0,
            "form_completion_rate": 90.0,
        }
        curr = {
            "snapshot_id": "curr",
            "missing_pages_pct": 50.0,  # 400% increase - degradation
            "form_completion_rate": 50.0,  # 44% decrease - degradation
        }
        
        delta = guardian.calculate_data_delta(prev, curr, "TEST_ENTITY")
        
        assert delta.direction == "DEGRADED"
        assert delta.significant
    
    def test_event_stored_in_guardian(self):
        """Test that generated events are stored in Guardian"""
        guardian = GuardianAgent()
        
        assert guardian.event_count == 0
        
        # Create a scenario that generates an event
        data_delta = DataDelta(
            prev_snapshot_id="prev",
            curr_snapshot_id="curr",
            entity_id="TEST_ENTITY",
            overall_change_magnitude=0.3,
            direction="IMPROVED",
            significant=True,
        )
        
        output_delta = OutputDelta(
            prev_snapshot_id="prev",
            curr_snapshot_id="curr",
            entity_id="TEST_ENTITY",
            risk_score_change=30.0,  # Increased - inconsistent
        )
        
        guardian.verify_consistency(data_delta, output_delta)
        
        assert guardian.event_count == 1
        events = guardian.get_events()
        assert len(events) == 1
        assert events[0].entity_id == "TEST_ENTITY"
