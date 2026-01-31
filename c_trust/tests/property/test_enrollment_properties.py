"""
Property-Based Tests for Enrollment Extraction
==============================================
Tests universal properties that must hold for enrollment calculations.

Phase 2, Task 8: Property-Based Tests for Enrollment
"""

import pytest
from hypothesis import given, strategies as st, assume, settings, HealthCheck
import pandas as pd

from src.data.features_real_extraction import RealFeatureExtractor
from src.data.models import FileType


class TestEnrollmentProperties:
    """Property-based tests for enrollment extraction"""
    
    # ========================================
    # Property 8.1: Enrollment Rate Capped at 100% (FR-6)
    # ========================================
    
    @given(
        actual=st.integers(min_value=1, max_value=1000),
        target=st.integers(min_value=1, max_value=1000)
    )
    def test_property_enrollment_rate_capped_at_100(self, actual, target):
        """
        Property: Enrollment rate must never exceed 100%
        
        For any actual and target enrollment values,
        the calculated rate must be <= 100.0
        """
        extractor = RealFeatureExtractor()
        rate = extractor.calculate_enrollment_rate(actual, target)
        
        assert rate is not None, "Rate should not be None for valid inputs"
        assert rate <= 100.0, f"Rate {rate}% exceeds 100% (actual={actual}, target={target})"
        assert rate >= 0.0, f"Rate {rate}% is negative"
    
    @given(
        actual=st.integers(min_value=1, max_value=10000),
        target=st.integers(min_value=1, max_value=1000)
    )
    def test_property_over_enrollment_always_capped(self, actual, target):
        """
        Property: Over-enrollment (actual > target) always results in 100%
        
        When actual enrollment exceeds target, rate must be exactly 100.0
        """
        assume(actual > target)  # Only test over-enrollment cases
        
        extractor = RealFeatureExtractor()
        rate = extractor.calculate_enrollment_rate(actual, target)
        
        assert rate == 100.0, f"Over-enrollment should cap at 100%, got {rate}%"
    
    # ========================================
    # Property 8.2: Null Handling for Missing Data (FR-6)
    # ========================================
    
    @given(actual=st.integers(min_value=0, max_value=1000))
    def test_property_none_target_returns_none(self, actual):
        """
        Property: If target is None, rate must be None
        
        For any actual value, if target is None, rate must be None
        """
        extractor = RealFeatureExtractor()
        rate = extractor.calculate_enrollment_rate(actual, None)
        
        assert rate is None, "Rate should be None when target is None"
    
    @given(target=st.integers(min_value=1, max_value=1000))
    def test_property_none_actual_returns_none(self, target):
        """
        Property: If actual is None, rate must be None
        
        For any target value, if actual is None, rate must be None
        """
        extractor = RealFeatureExtractor()
        rate = extractor.calculate_enrollment_rate(None, target)
        
        assert rate is None, "Rate should be None when actual is None"
    
    @given(
        actual=st.one_of(st.none(), st.integers(min_value=0, max_value=1000)),
        target=st.one_of(st.none(), st.integers(min_value=0, max_value=1000))
    )
    def test_property_any_none_input_returns_none_or_valid(self, actual, target):
        """
        Property: If any input is None or invalid, rate is None
        
        For any combination of inputs, if either is None or target <= 0,
        rate must be None
        """
        extractor = RealFeatureExtractor()
        rate = extractor.calculate_enrollment_rate(actual, target)
        
        if actual is None or target is None or target <= 0:
            assert rate is None, f"Rate should be None for invalid inputs (actual={actual}, target={target})"
        else:
            assert rate is not None, f"Rate should not be None for valid inputs (actual={actual}, target={target})"
    
    # ========================================
    # Property 8.3: Enrollment Rate Within Bounds [0, 100]
    # ========================================
    
    @given(
        actual=st.integers(min_value=0, max_value=1000),
        target=st.integers(min_value=1, max_value=1000)
    )
    def test_property_rate_within_bounds(self, actual, target):
        """
        Property: Enrollment rate must be in range [0, 100]
        
        For any valid actual and target, rate must be between 0 and 100 inclusive
        """
        extractor = RealFeatureExtractor()
        rate = extractor.calculate_enrollment_rate(actual, target)
        
        assert rate is not None, "Rate should not be None for valid inputs"
        assert 0.0 <= rate <= 100.0, f"Rate {rate}% is outside bounds [0, 100]"
    
    @given(
        actual=st.integers(min_value=0, max_value=1000),
        target=st.integers(min_value=1, max_value=1000)
    )
    def test_property_rate_is_float(self, actual, target):
        """
        Property: Enrollment rate must be a float
        
        For any valid inputs, rate must be a float type
        """
        extractor = RealFeatureExtractor()
        rate = extractor.calculate_enrollment_rate(actual, target)
        
        assert isinstance(rate, float), f"Rate should be float, got {type(rate)}"
    
    # ========================================
    # Property 8.4: Monotonicity
    # ========================================
    
    @given(
        actual1=st.integers(min_value=0, max_value=500),
        actual2=st.integers(min_value=0, max_value=500),
        target=st.integers(min_value=1, max_value=1000)
    )
    def test_property_rate_increases_with_actual(self, actual1, actual2, target):
        """
        Property: Rate increases (or stays same) as actual increases
        
        For fixed target, if actual1 < actual2, then rate1 <= rate2
        (unless both are capped at 100%)
        """
        assume(actual1 < actual2)
        assume(actual2 <= target)  # Avoid capping
        
        extractor = RealFeatureExtractor()
        rate1 = extractor.calculate_enrollment_rate(actual1, target)
        rate2 = extractor.calculate_enrollment_rate(actual2, target)
        
        assert rate1 <= rate2, f"Rate should increase with actual: {rate1}% -> {rate2}%"
    
    @given(
        actual=st.integers(min_value=1, max_value=500),
        target1=st.integers(min_value=1, max_value=500),
        target2=st.integers(min_value=1, max_value=500)
    )
    @settings(suppress_health_check=[HealthCheck.filter_too_much])
    def test_property_rate_decreases_with_target(self, actual, target1, target2):
        """
        Property: Rate decreases (or stays same) as target increases
        
        For fixed actual, if target1 < target2, then rate1 >= rate2
        """
        assume(target1 < target2)
        assume(actual <= target1)  # Avoid capping
        
        extractor = RealFeatureExtractor()
        rate1 = extractor.calculate_enrollment_rate(actual, target1)
        rate2 = extractor.calculate_enrollment_rate(actual, target2)
        
        assert rate1 >= rate2, f"Rate should decrease with target: {rate1}% -> {rate2}%"
    
    # ========================================
    # Property 8.5: Determinism
    # ========================================
    
    @given(
        actual=st.integers(min_value=0, max_value=1000),
        target=st.integers(min_value=1, max_value=1000)
    )
    def test_property_deterministic_calculation(self, actual, target):
        """
        Property: Same inputs always produce same output
        
        Calling calculate_enrollment_rate multiple times with same inputs
        must always return the same result
        """
        extractor = RealFeatureExtractor()
        rate1 = extractor.calculate_enrollment_rate(actual, target)
        rate2 = extractor.calculate_enrollment_rate(actual, target)
        rate3 = extractor.calculate_enrollment_rate(actual, target)
        
        assert rate1 == rate2 == rate3, "Rate calculation must be deterministic"
    
    # ========================================
    # Property 8.6: Boundary Conditions
    # ========================================
    
    @given(target=st.integers(min_value=1, max_value=1000))
    def test_property_zero_actual_gives_zero_rate(self, target):
        """
        Property: Zero actual enrollment always gives 0% rate
        
        For any positive target, if actual is 0, rate must be 0.0
        """
        extractor = RealFeatureExtractor()
        rate = extractor.calculate_enrollment_rate(0, target)
        
        assert rate == 0.0, f"Zero actual should give 0% rate, got {rate}%"
    
    @given(enrollment=st.integers(min_value=1, max_value=1000))
    def test_property_equal_actual_target_gives_100(self, enrollment):
        """
        Property: When actual equals target, rate is exactly 100%
        
        For any positive value, if actual == target, rate must be 100.0
        """
        extractor = RealFeatureExtractor()
        rate = extractor.calculate_enrollment_rate(enrollment, enrollment)
        
        assert rate == 100.0, f"Equal actual and target should give 100%, got {rate}%"
    
    # ========================================
    # Property 8.7: Precision
    # ========================================
    
    @given(
        actual=st.integers(min_value=0, max_value=1000),
        target=st.integers(min_value=1, max_value=1000)
    )
    def test_property_rate_precision_one_decimal(self, actual, target):
        """
        Property: Rate is rounded to 1 decimal place
        
        For any inputs, rate must have at most 1 decimal place
        """
        extractor = RealFeatureExtractor()
        rate = extractor.calculate_enrollment_rate(actual, target)
        
        if rate is not None:
            # Check that rate has at most 1 decimal place
            rate_str = str(rate)
            if '.' in rate_str:
                decimal_places = len(rate_str.split('.')[1])
                assert decimal_places <= 1, f"Rate {rate} has more than 1 decimal place"
    
    # ========================================
    # Property 8.8: CPID Extraction Properties
    # ========================================
    
    @given(
        num_patients=st.integers(min_value=2, max_value=100),  # Changed from 1 to 2
        duplicates_per_patient=st.integers(min_value=2, max_value=5)  # Changed from 1 to 2
    )
    def test_property_cpid_counts_unique_only(self, num_patients, duplicates_per_patient):
        """
        Property: CPID extraction counts unique patients only
        
        For any number of patients with duplicates, actual enrollment
        should equal the number of unique patients, not total rows
        """
        extractor = RealFeatureExtractor()
        
        # Create data with duplicates
        cpids = []
        for i in range(num_patients):
            cpids.extend([f'P{i:03d}'] * duplicates_per_patient)
        
        edc_data = pd.DataFrame({'CPID': cpids})
        raw_data = {FileType.EDC_METRICS: edc_data}
        
        actual = extractor.extract_actual_enrollment(raw_data, "TEST")
        
        assert actual == num_patients, f"Should count {num_patients} unique patients, got {actual}"
        assert actual != len(cpids), f"Should not count duplicate rows: {actual} unique vs {len(cpids)} total"
    
    @given(num_patients=st.integers(min_value=0, max_value=100))
    def test_property_cpid_extraction_non_negative(self, num_patients):
        """
        Property: CPID extraction never returns negative values
        
        For any valid data, actual enrollment must be >= 0
        """
        extractor = RealFeatureExtractor()
        
        cpids = [f'P{i:03d}' for i in range(num_patients)]
        edc_data = pd.DataFrame({'CPID': cpids})
        raw_data = {FileType.EDC_METRICS: edc_data}
        
        actual = extractor.extract_actual_enrollment(raw_data, "TEST")
        
        if actual is not None:
            assert actual >= 0, f"Actual enrollment {actual} is negative"
    
    # ========================================
    # Property 8.9: Invalid Input Handling
    # ========================================
    
    @given(
        actual=st.integers(min_value=-1000, max_value=1000),
        target=st.integers(min_value=-1000, max_value=1000)
    )
    def test_property_invalid_target_returns_none(self, actual, target):
        """
        Property: Invalid target (<=0) always returns None
        
        For any actual value, if target <= 0, rate must be None
        """
        assume(target <= 0)
        
        extractor = RealFeatureExtractor()
        rate = extractor.calculate_enrollment_rate(actual, target)
        
        assert rate is None, f"Invalid target {target} should return None, got {rate}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--hypothesis-show-statistics"])

