"""
Property-Based Tests for DQI Calculation Accuracy
=================================================
Tests Property 7: DQI Calculation Accuracy

**Property 7: DQI Calculation Accuracy**
*For any* valid input data, the DQI calculation should produce scores using 
the exact weighted formula: Safety(35%) + Compliance(25%) + Completeness(20%) + 
Operations(15%), with proper component breakdown.

**Validates: Requirements 4.1, 4.2**

This test uses Hypothesis to generate various feature combinations and verify
that the DQI engine correctly applies the weighted formula.
"""

from datetime import datetime
from typing import Any, Dict, List

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck, assume

from src.dqi import (
    DQICalculationEngine,
    DQIResult,
    DimensionScore,
    DQIDimension,
    DQI_WEIGHTS,
    DQI_BAND_THRESHOLDS,
)
from src.core import DQIBand


# ========================================
# TEST STRATEGIES
# ========================================

@st.composite
def safety_features_strategy(draw):
    """Generate valid safety dimension features"""
    return {
        "sae_backlog_days": draw(st.floats(min_value=0, max_value=30, allow_nan=False)),
        "sae_overdue_count": draw(st.integers(min_value=0, max_value=10)),
        "fatal_sae_count": draw(st.integers(min_value=0, max_value=5)),
        "safety_signal_count": draw(st.integers(min_value=0, max_value=10)),
    }


@st.composite
def compliance_features_strategy(draw):
    """Generate valid compliance dimension features"""
    return {
        "missing_lab_ranges_pct": draw(st.floats(min_value=0, max_value=100, allow_nan=False)),
        "inactivated_form_pct": draw(st.floats(min_value=0, max_value=100, allow_nan=False)),
        "protocol_deviation_count": draw(st.integers(min_value=0, max_value=20)),
        "regulatory_compliance_rate": draw(st.floats(min_value=0, max_value=100, allow_nan=False)),
    }


@st.composite
def completeness_features_strategy(draw):
    """Generate valid completeness dimension features"""
    return {
        "missing_pages_pct": draw(st.floats(min_value=0, max_value=100, allow_nan=False)),
        "visit_completion_rate": draw(st.floats(min_value=0, max_value=100, allow_nan=False)),
        "form_completion_rate": draw(st.floats(min_value=0, max_value=100, allow_nan=False)),
        "data_entry_completion_rate": draw(st.floats(min_value=0, max_value=100, allow_nan=False)),
    }


@st.composite
def operations_features_strategy(draw):
    """Generate valid operations dimension features"""
    return {
        "query_aging_days": draw(st.floats(min_value=0, max_value=60, allow_nan=False)),
        "data_entry_lag_days": draw(st.floats(min_value=0, max_value=30, allow_nan=False)),
        "open_query_count": draw(st.integers(min_value=0, max_value=200)),
        "query_resolution_rate": draw(st.floats(min_value=0, max_value=100, allow_nan=False)),
    }


@st.composite
def complete_features_strategy(draw):
    """Generate complete feature set with all dimensions"""
    features = {}
    features.update(draw(safety_features_strategy()))
    features.update(draw(compliance_features_strategy()))
    features.update(draw(completeness_features_strategy()))
    features.update(draw(operations_features_strategy()))
    return features


@st.composite
def partial_features_strategy(draw):
    """Generate partial feature set (some dimensions missing)"""
    features = {}
    
    # Randomly include each dimension
    if draw(st.booleans()):
        features.update(draw(safety_features_strategy()))
    if draw(st.booleans()):
        features.update(draw(compliance_features_strategy()))
    if draw(st.booleans()):
        features.update(draw(completeness_features_strategy()))
    if draw(st.booleans()):
        features.update(draw(operations_features_strategy()))
    
    # Ensure at least one dimension has data
    if not features:
        features.update(draw(safety_features_strategy()))
    
    return features


# ========================================
# PROPERTY TESTS
# ========================================

class TestDQICalculationAccuracyProperty:
    """
    Property-based tests for DQI calculation accuracy.
    
    Feature: clinical-ai-system, Property 7: DQI Calculation Accuracy
    """
    
    @given(features=complete_features_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_dqi_uses_correct_weights(self, features: Dict[str, Any]):
        """
        Feature: clinical-ai-system, Property 7: DQI Calculation Accuracy
        Validates: Requirements 4.1, 4.2
        
        Property: For any complete feature set, the DQI calculation should use
        the exact weights: Safety(35%) + Compliance(25%) + Completeness(20%) + Operations(15%).
        """
        engine = DQICalculationEngine()
        result = engine.calculate_dqi(features, "TEST_ENTITY")
        
        # Verify weights are correct
        expected_weights = {
            DQIDimension.SAFETY: 0.35,
            DQIDimension.COMPLIANCE: 0.25,
            DQIDimension.COMPLETENESS: 0.20,
            DQIDimension.OPERATIONS: 0.15,
        }
        
        for dim, expected_weight in expected_weights.items():
            if dim in result.dimension_scores:
                actual_weight = result.dimension_scores[dim].weight
                assert abs(actual_weight - expected_weight) < 0.001, \
                    f"Weight mismatch for {dim.value}: expected {expected_weight}, got {actual_weight}"
    
    @given(features=complete_features_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_overall_score_equals_sum_of_weighted_scores(self, features: Dict[str, Any]):
        """
        Feature: clinical-ai-system, Property 7: DQI Calculation Accuracy
        Validates: Requirements 4.1, 4.2
        
        Property: For any feature set, the overall DQI score should equal
        the sum of all weighted dimension scores.
        """
        engine = DQICalculationEngine()
        result = engine.calculate_dqi(features, "TEST_ENTITY")
        
        # Calculate expected sum of weighted scores
        expected_sum = sum(ds.weighted_score for ds in result.dimension_scores.values())
        
        # For complete features, overall should equal sum (no scaling needed)
        if not result.partial_calculation:
            assert abs(result.overall_score - expected_sum) < 0.01, \
                f"Overall score {result.overall_score} != sum of weighted scores {expected_sum}"
    
    @given(features=complete_features_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_weighted_score_equals_raw_times_weight(self, features: Dict[str, Any]):
        """
        Feature: clinical-ai-system, Property 7: DQI Calculation Accuracy
        Validates: Requirements 4.1, 4.2
        
        Property: For any dimension, weighted_score = raw_score × weight.
        """
        engine = DQICalculationEngine()
        result = engine.calculate_dqi(features, "TEST_ENTITY")
        
        for dim, ds in result.dimension_scores.items():
            expected_weighted = ds.raw_score * ds.weight
            assert abs(ds.weighted_score - expected_weighted) < 0.01, \
                f"Weighted score mismatch for {dim.value}: " \
                f"expected {expected_weighted:.2f}, got {ds.weighted_score:.2f}"
    
    @given(features=complete_features_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_overall_score_in_valid_range(self, features: Dict[str, Any]):
        """
        Feature: clinical-ai-system, Property 7: DQI Calculation Accuracy
        Validates: Requirements 4.1, 4.2
        
        Property: For any input, the overall DQI score should be in [0, 100].
        """
        engine = DQICalculationEngine()
        result = engine.calculate_dqi(features, "TEST_ENTITY")
        
        assert 0.0 <= result.overall_score <= 100.0, \
            f"Overall score {result.overall_score} out of valid range [0, 100]"
    
    @given(features=complete_features_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_dimension_scores_in_valid_range(self, features: Dict[str, Any]):
        """
        Feature: clinical-ai-system, Property 7: DQI Calculation Accuracy
        Validates: Requirements 4.1, 4.2
        
        Property: For any input, all dimension raw scores should be in [0, 100].
        """
        engine = DQICalculationEngine()
        result = engine.calculate_dqi(features, "TEST_ENTITY")
        
        for dim, ds in result.dimension_scores.items():
            assert 0.0 <= ds.raw_score <= 100.0, \
                f"Raw score for {dim.value} ({ds.raw_score}) out of valid range [0, 100]"
    
    @given(features=complete_features_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_confidence_in_valid_range(self, features: Dict[str, Any]):
        """
        Feature: clinical-ai-system, Property 7: DQI Calculation Accuracy
        Validates: Requirements 4.1, 4.2
        
        Property: For any input, confidence should be in [0, 1].
        """
        engine = DQICalculationEngine()
        result = engine.calculate_dqi(features, "TEST_ENTITY")
        
        assert 0.0 <= result.confidence <= 1.0, \
            f"Confidence {result.confidence} out of valid range [0, 1]"
    
    @given(features=complete_features_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_component_breakdown_provided(self, features: Dict[str, Any]):
        """
        Feature: clinical-ai-system, Property 7: DQI Calculation Accuracy
        Validates: Requirements 4.2
        
        Property: For any input, the result should provide component-level breakdown.
        """
        engine = DQICalculationEngine()
        result = engine.calculate_dqi(features, "TEST_ENTITY")
        
        # Verify breakdown is available
        breakdown = result.get_component_breakdown()
        assert breakdown is not None, "Component breakdown should be provided"
        
        # Verify all dimensions are in breakdown
        for dim in [DQIDimension.SAFETY, DQIDimension.COMPLIANCE, 
                    DQIDimension.COMPLETENESS, DQIDimension.OPERATIONS]:
            assert dim.value in breakdown, f"Missing {dim.value} in breakdown"
    
    @given(features=complete_features_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_weights_sum_to_expected_total(self, features: Dict[str, Any]):
        """
        Feature: clinical-ai-system, Property 7: DQI Calculation Accuracy
        Validates: Requirements 4.1
        
        Property: The sum of all dimension weights should equal 0.95 
        (35% + 25% + 20% + 15% = 95%, with 5% reserved).
        """
        engine = DQICalculationEngine()
        weights = engine.get_weights()
        
        total_weight = sum(weights.values())
        expected_total = 0.95  # 35% + 25% + 20% + 15%
        
        assert abs(total_weight - expected_total) < 0.001, \
            f"Total weight {total_weight} != expected {expected_total}"
    
    @given(features=partial_features_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_partial_calculation_marked_correctly(self, features: Dict[str, Any]):
        """
        Feature: clinical-ai-system, Property 7: DQI Calculation Accuracy
        Validates: Requirements 4.5
        
        Property: When some dimensions are missing, partial_calculation should be True.
        """
        engine = DQICalculationEngine()
        result = engine.calculate_dqi(features, "TEST_ENTITY")
        
        # Count available dimensions
        available_dims = len(result.dimension_scores)
        
        if available_dims < 4:
            assert result.partial_calculation, \
                "partial_calculation should be True when dimensions are missing"
            assert len(result.missing_dimensions) > 0, \
                "missing_dimensions should list missing dimensions"


# ========================================
# UNIT TESTS
# ========================================

class TestDQICalculationUnit:
    """Unit tests for DQI calculation engine"""
    
    def test_default_weights_match_requirements(self):
        """Test that default weights match Requirements 4.1"""
        assert DQI_WEIGHTS["safety"] == 0.35, "Safety weight should be 35%"
        assert DQI_WEIGHTS["compliance"] == 0.25, "Compliance weight should be 25%"
        assert DQI_WEIGHTS["completeness"] == 0.20, "Completeness weight should be 20%"
        assert DQI_WEIGHTS["operations"] == 0.15, "Operations weight should be 15%"
    
    def test_perfect_scores_produce_high_dqi(self):
        """Test that perfect input produces high DQI score"""
        engine = DQICalculationEngine()
        
        # Perfect features (no issues)
        features = {
            "sae_backlog_days": 0,
            "sae_overdue_count": 0,
            "fatal_sae_count": 0,
            "missing_lab_ranges_pct": 0,
            "inactivated_form_pct": 0,
            "visit_completion_rate": 100,
            "form_completion_rate": 100,
            "missing_pages_pct": 0,
            "query_aging_days": 0,
            "data_entry_lag_days": 0,
            "open_query_count": 0,
        }
        
        result = engine.calculate_dqi(features, "PERFECT_STUDY")
        
        # Should be close to 95 (sum of all weights)
        assert result.overall_score >= 90, \
            f"Perfect input should produce high score, got {result.overall_score}"
        assert result.band == DQIBand.GREEN, \
            f"Perfect input should be GREEN band, got {result.band}"
    
    def test_poor_scores_produce_low_dqi(self):
        """Test that poor input produces low DQI score"""
        engine = DQICalculationEngine()
        
        # Poor features (many issues)
        features = {
            "sae_backlog_days": 30,
            "sae_overdue_count": 10,
            "fatal_sae_count": 3,
            "missing_lab_ranges_pct": 80,
            "inactivated_form_pct": 50,
            "visit_completion_rate": 30,
            "form_completion_rate": 40,
            "missing_pages_pct": 60,
            "query_aging_days": 45,
            "data_entry_lag_days": 14,
            "open_query_count": 150,
        }
        
        result = engine.calculate_dqi(features, "POOR_STUDY")
        
        assert result.overall_score < 50, \
            f"Poor input should produce low score, got {result.overall_score}"
        assert result.band in [DQIBand.RED, DQIBand.ORANGE], \
            f"Poor input should be RED or ORANGE band, got {result.band}"
    
    def test_result_contains_all_required_fields(self):
        """Test that result contains all required fields"""
        engine = DQICalculationEngine()
        
        features = {"sae_backlog_days": 5, "visit_completion_rate": 90}
        result = engine.calculate_dqi(features, "TEST_STUDY")
        
        assert result.overall_score is not None
        assert result.band is not None
        assert result.dimension_scores is not None
        assert result.confidence is not None
        assert result.timestamp is not None
        assert result.entity_id == "TEST_STUDY"
        assert result.explanation is not None
    
    def test_to_dict_serialization(self):
        """Test that result can be serialized to dict"""
        engine = DQICalculationEngine()
        
        features = {"sae_backlog_days": 5, "visit_completion_rate": 90}
        result = engine.calculate_dqi(features, "TEST_STUDY")
        result_dict = result.to_dict()
        
        assert "overall_score" in result_dict
        assert "band" in result_dict
        assert "dimension_breakdown" in result_dict
        assert "confidence" in result_dict
        assert "entity_id" in result_dict
    
    def test_empty_features_handled_gracefully(self):
        """Test that empty features are handled gracefully"""
        engine = DQICalculationEngine()
        
        result = engine.calculate_dqi({}, "EMPTY_STUDY")
        
        # Should handle gracefully with low confidence
        assert result.confidence == 0.0 or result.partial_calculation
        assert result.overall_score >= 0
