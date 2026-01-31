"""
Property-Based Tests for DQI Band Classification Consistency
=============================================================
Tests Property 8: DQI Band Classification Consistency

**Property 8: DQI Band Classification Consistency**
*For any* calculated DQI score, the system should consistently classify it 
into the correct band: Green(85-100), Amber(65-84), Orange(40-64), Red(<40).

**Validates: Requirements 4.4**

This test uses Hypothesis to generate various DQI scores and verify
that the band classification is consistent with the defined thresholds.
"""

from datetime import datetime
from typing import Any, Dict

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck, assume

from src.dqi import (
    DQICalculationEngine,
    DQIResult,
    DQIDimension,
    DQI_BAND_THRESHOLDS,
)
from src.core import DQIBand


# ========================================
# TEST STRATEGIES
# ========================================

@st.composite
def dqi_score_strategy(draw):
    """Generate valid DQI scores in range [0, 100]"""
    return draw(st.floats(min_value=0.0, max_value=100.0, allow_nan=False))


@st.composite
def green_band_score_strategy(draw):
    """Generate scores that should be in GREEN band (85-100)"""
    return draw(st.floats(min_value=85.0, max_value=100.0, allow_nan=False))


@st.composite
def amber_band_score_strategy(draw):
    """Generate scores that should be in AMBER band (65-84)"""
    return draw(st.floats(min_value=65.0, max_value=84.999, allow_nan=False))


@st.composite
def orange_band_score_strategy(draw):
    """Generate scores that should be in ORANGE band (40-64)"""
    return draw(st.floats(min_value=40.0, max_value=64.999, allow_nan=False))


@st.composite
def red_band_score_strategy(draw):
    """Generate scores that should be in RED band (<40)"""
    return draw(st.floats(min_value=0.0, max_value=39.999, allow_nan=False))


@st.composite
def features_for_target_score_strategy(draw, target_score: float):
    """
    Generate features that will produce approximately the target DQI score.
    
    This is a simplified approach - we adjust safety features to control the score.
    """
    # Calculate how much penalty we need to reach target score
    # Perfect score is ~95 (sum of weights), so penalty = 95 - target
    needed_penalty = max(0, 95 - target_score)
    
    # Distribute penalty across dimensions
    safety_penalty = min(needed_penalty * 0.4, 35)  # Max 35 from safety
    compliance_penalty = min(needed_penalty * 0.3, 25)  # Max 25 from compliance
    completeness_penalty = min(needed_penalty * 0.2, 20)  # Max 20 from completeness
    operations_penalty = min(needed_penalty * 0.1, 15)  # Max 15 from operations
    
    features = {
        # Safety features - control via SAE counts
        "sae_backlog_days": safety_penalty / 2.86,  # ~20 pts max from 7 days
        "sae_overdue_count": int(safety_penalty / 10),  # 10 pts each
        "fatal_sae_count": 0,  # Keep at 0 for predictability
        
        # Compliance features
        "missing_lab_ranges_pct": compliance_penalty * 2,  # 0.5 pts per %
        "inactivated_form_pct": 0,
        
        # Completeness features
        "visit_completion_rate": 100 - completeness_penalty,
        "form_completion_rate": 100,
        "missing_pages_pct": 0,
        
        # Operations features
        "query_aging_days": operations_penalty * 0.75,  # ~40 pts from 30 days
        "data_entry_lag_days": 0,
        "open_query_count": 0,
    }
    
    return features


# ========================================
# PROPERTY TESTS
# ========================================

class TestDQIBandClassificationProperty:
    """
    Property-based tests for DQI band classification consistency.
    
    Feature: clinical-ai-system, Property 8: DQI Band Classification Consistency
    """
    
    @given(score=green_band_score_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_green_band_classification(self, score: float):
        """
        Feature: clinical-ai-system, Property 8: DQI Band Classification Consistency
        Validates: Requirements 4.4
        
        Property: For any score in [85, 100], the band should be GREEN.
        """
        engine = DQICalculationEngine()
        band = engine._classify_band(score)
        
        assert band == DQIBand.GREEN, \
            f"Score {score} should be GREEN band, got {band}"
    
    @given(score=amber_band_score_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_amber_band_classification(self, score: float):
        """
        Feature: clinical-ai-system, Property 8: DQI Band Classification Consistency
        Validates: Requirements 4.4
        
        Property: For any score in [65, 84], the band should be AMBER.
        """
        engine = DQICalculationEngine()
        band = engine._classify_band(score)
        
        assert band == DQIBand.AMBER, \
            f"Score {score} should be AMBER band, got {band}"
    
    @given(score=orange_band_score_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_orange_band_classification(self, score: float):
        """
        Feature: clinical-ai-system, Property 8: DQI Band Classification Consistency
        Validates: Requirements 4.4
        
        Property: For any score in [40, 64], the band should be ORANGE.
        """
        engine = DQICalculationEngine()
        band = engine._classify_band(score)
        
        assert band == DQIBand.ORANGE, \
            f"Score {score} should be ORANGE band, got {band}"
    
    @given(score=red_band_score_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_red_band_classification(self, score: float):
        """
        Feature: clinical-ai-system, Property 8: DQI Band Classification Consistency
        Validates: Requirements 4.4
        
        Property: For any score in [0, 40), the band should be RED.
        """
        engine = DQICalculationEngine()
        band = engine._classify_band(score)
        
        assert band == DQIBand.RED, \
            f"Score {score} should be RED band, got {band}"
    
    @given(score=dqi_score_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_band_classification_is_deterministic(self, score: float):
        """
        Feature: clinical-ai-system, Property 8: DQI Band Classification Consistency
        Validates: Requirements 4.4
        
        Property: For any score, calling classify_band multiple times should
        always return the same band.
        """
        engine = DQICalculationEngine()
        
        band1 = engine._classify_band(score)
        band2 = engine._classify_band(score)
        band3 = engine._classify_band(score)
        
        assert band1 == band2 == band3, \
            f"Band classification should be deterministic for score {score}"
    
    @given(score=dqi_score_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_band_is_valid_enum_value(self, score: float):
        """
        Feature: clinical-ai-system, Property 8: DQI Band Classification Consistency
        Validates: Requirements 4.4
        
        Property: For any score, the band should be a valid DQIBand enum value.
        """
        engine = DQICalculationEngine()
        band = engine._classify_band(score)
        
        assert band in [DQIBand.GREEN, DQIBand.AMBER, DQIBand.ORANGE, DQIBand.RED], \
            f"Band {band} is not a valid DQIBand value"
    
    @given(score=dqi_score_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_band_thresholds_are_mutually_exclusive(self, score: float):
        """
        Feature: clinical-ai-system, Property 8: DQI Band Classification Consistency
        Validates: Requirements 4.4
        
        Property: For any score, exactly one band should match.
        """
        engine = DQICalculationEngine()
        band = engine._classify_band(score)
        
        # Count how many bands the score could belong to
        matching_bands = []
        
        if score >= 85:
            matching_bands.append(DQIBand.GREEN)
        if 65 <= score < 85:
            matching_bands.append(DQIBand.AMBER)
        if 40 <= score < 65:
            matching_bands.append(DQIBand.ORANGE)
        if score < 40:
            matching_bands.append(DQIBand.RED)
        
        assert len(matching_bands) == 1, \
            f"Score {score} matches {len(matching_bands)} bands: {matching_bands}"
        assert band == matching_bands[0], \
            f"Band {band} doesn't match expected {matching_bands[0]} for score {score}"
    
    @given(st.data())
    @settings(max_examples=50, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_boundary_values_classified_correctly(self, data):
        """
        Feature: clinical-ai-system, Property 8: DQI Band Classification Consistency
        Validates: Requirements 4.4
        
        Property: Boundary values should be classified correctly.
        """
        engine = DQICalculationEngine()
        
        # Test exact boundary values
        boundary_tests = [
            (0.0, DQIBand.RED),
            (39.0, DQIBand.RED),
            (39.999, DQIBand.RED),
            (40.0, DQIBand.ORANGE),
            (64.0, DQIBand.ORANGE),
            (64.999, DQIBand.ORANGE),
            (65.0, DQIBand.AMBER),
            (84.0, DQIBand.AMBER),
            (84.999, DQIBand.AMBER),
            (85.0, DQIBand.GREEN),
            (100.0, DQIBand.GREEN),
        ]
        
        for score, expected_band in boundary_tests:
            actual_band = engine._classify_band(score)
            assert actual_band == expected_band, \
                f"Boundary score {score} should be {expected_band}, got {actual_band}"
    
    @given(score=dqi_score_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_higher_score_never_worse_band(self, score: float):
        """
        Feature: clinical-ai-system, Property 8: DQI Band Classification Consistency
        Validates: Requirements 4.4
        
        Property: A higher score should never result in a worse (lower) band.
        """
        engine = DQICalculationEngine()
        
        # Define band ordering (higher is better)
        band_order = {
            DQIBand.RED: 0,
            DQIBand.ORANGE: 1,
            DQIBand.AMBER: 2,
            DQIBand.GREEN: 3,
        }
        
        band = engine._classify_band(score)
        
        # Test that slightly higher score doesn't produce worse band
        higher_score = min(score + 1.0, 100.0)
        higher_band = engine._classify_band(higher_score)
        
        assert band_order[higher_band] >= band_order[band], \
            f"Higher score {higher_score} produced worse band {higher_band} than {score} ({band})"


# ========================================
# UNIT TESTS
# ========================================

class TestDQIBandClassificationUnit:
    """Unit tests for DQI band classification"""
    
    def test_band_thresholds_match_requirements(self):
        """Test that band thresholds match Requirements 4.4"""
        # GREEN: 85-100
        assert DQI_BAND_THRESHOLDS[DQIBand.GREEN] == (85, 100)
        
        # AMBER: 65-84
        assert DQI_BAND_THRESHOLDS[DQIBand.AMBER] == (65, 84)
        
        # ORANGE: 40-64
        assert DQI_BAND_THRESHOLDS[DQIBand.ORANGE] == (40, 64)
        
        # RED: <40
        assert DQI_BAND_THRESHOLDS[DQIBand.RED] == (0, 39)
    
    def test_all_bands_have_thresholds(self):
        """Test that all DQI bands have defined thresholds"""
        for band in DQIBand:
            assert band in DQI_BAND_THRESHOLDS, \
                f"Band {band} missing from thresholds"
    
    def test_thresholds_cover_full_range(self):
        """Test that thresholds cover the full 0-100 range"""
        # Collect all threshold ranges
        ranges = list(DQI_BAND_THRESHOLDS.values())
        
        # Sort by min value
        ranges.sort(key=lambda x: x[0])
        
        # Check coverage
        assert ranges[0][0] == 0, "Thresholds should start at 0"
        assert ranges[-1][1] == 100, "Thresholds should end at 100"
    
    def test_green_band_examples(self):
        """Test specific GREEN band examples"""
        engine = DQICalculationEngine()
        
        green_scores = [85, 90, 95, 100]
        for score in green_scores:
            band = engine._classify_band(score)
            assert band == DQIBand.GREEN, \
                f"Score {score} should be GREEN, got {band}"
    
    def test_amber_band_examples(self):
        """Test specific AMBER band examples"""
        engine = DQICalculationEngine()
        
        amber_scores = [65, 70, 75, 80, 84]
        for score in amber_scores:
            band = engine._classify_band(score)
            assert band == DQIBand.AMBER, \
                f"Score {score} should be AMBER, got {band}"
    
    def test_orange_band_examples(self):
        """Test specific ORANGE band examples"""
        engine = DQICalculationEngine()
        
        orange_scores = [40, 45, 50, 55, 60, 64]
        for score in orange_scores:
            band = engine._classify_band(score)
            assert band == DQIBand.ORANGE, \
                f"Score {score} should be ORANGE, got {band}"
    
    def test_red_band_examples(self):
        """Test specific RED band examples"""
        engine = DQICalculationEngine()
        
        red_scores = [0, 10, 20, 30, 39]
        for score in red_scores:
            band = engine._classify_band(score)
            assert band == DQIBand.RED, \
                f"Score {score} should be RED, got {band}"
    
    def test_band_result_in_full_calculation(self):
        """Test that band is correctly set in full DQI calculation"""
        engine = DQICalculationEngine()
        
        # Features that should produce GREEN band
        good_features = {
            "sae_backlog_days": 0,
            "sae_overdue_count": 0,
            "fatal_sae_count": 0,
            "missing_lab_ranges_pct": 0,
            "visit_completion_rate": 100,
            "query_aging_days": 0,
        }
        
        result = engine.calculate_dqi(good_features, "GOOD_STUDY")
        
        # Verify band matches score
        expected_band = engine._classify_band(result.overall_score)
        assert result.band == expected_band, \
            f"Result band {result.band} doesn't match expected {expected_band} for score {result.overall_score}"
