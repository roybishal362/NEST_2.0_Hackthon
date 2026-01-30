"""
Unit Tests for Enrollment Extraction
====================================
Tests the real enrollment data extraction functions.

Phase 2, Task 7: Unit Tests for Enrollment Extraction
"""

import pytest
import pandas as pd
from typing import Dict, Optional

from src.data.features_real_extraction import RealFeatureExtractor
from src.data.models import FileType


class TestEnrollmentExtraction:
    """Test enrollment extraction functions"""
    
    @pytest.fixture
    def extractor(self):
        """Create extractor instance"""
        return RealFeatureExtractor()
    
    @pytest.fixture
    def valid_edc_data(self):
        """Create valid EDC data with CPID column"""
        return pd.DataFrame({
            'CPID': ['P001', 'P002', 'P003', 'P004', 'P005'],
            'Site': ['Site 1', 'Site 1', 'Site 2', 'Site 2', 'Site 3'],
            'Visit': ['V1', 'V1', 'V1', 'V2', 'V1']
        })
    
    @pytest.fixture
    def valid_visit_projection_data(self):
        """Create valid Visit Projection data with target enrollment"""
        return pd.DataFrame({
            'Target Enrollment': [100, 100, 100],  # Column header format
            'Site': ['Site 1', 'Site 2', 'Site 3']
        })
    
    # ========================================
    # Test 7.1: CPID Parsing with Valid Data
    # ========================================
    
    def test_extract_actual_enrollment_with_cpid(self, extractor, valid_edc_data):
        """Test actual enrollment extraction with valid CPID data"""
        raw_data = {FileType.EDC_METRICS: valid_edc_data}
        
        actual = extractor.extract_actual_enrollment(raw_data, "TEST_STUDY")
        
        assert actual == 5, "Should count 5 unique CPIDs"
    
    def test_extract_actual_enrollment_with_patient_id(self, extractor):
        """Test actual enrollment extraction with 'Patient ID' column"""
        edc_data = pd.DataFrame({
            'Patient ID': ['P001', 'P002', 'P003'],
            'Site': ['Site 1', 'Site 1', 'Site 2']
        })
        raw_data = {FileType.EDC_METRICS: edc_data}
        
        actual = extractor.extract_actual_enrollment(raw_data, "TEST_STUDY")
        
        assert actual == 3, "Should count 3 unique Patient IDs"
    
    def test_extract_actual_enrollment_with_subject_id(self, extractor):
        """Test actual enrollment extraction with 'Subject' column"""
        edc_data = pd.DataFrame({
            'Subject': ['S001', 'S002', 'S003', 'S004'],
            'Site': ['Site 1', 'Site 1', 'Site 2', 'Site 2']
        })
        raw_data = {FileType.EDC_METRICS: edc_data}
        
        actual = extractor.extract_actual_enrollment(raw_data, "TEST_STUDY")
        
        assert actual == 4, "Should count 4 unique Subjects"
    
    def test_extract_actual_enrollment_with_duplicates(self, extractor):
        """Test that duplicate CPIDs are counted only once"""
        edc_data = pd.DataFrame({
            'CPID': ['P001', 'P001', 'P002', 'P002', 'P003'],  # Duplicates
            'Visit': ['V1', 'V2', 'V1', 'V2', 'V1']
        })
        raw_data = {FileType.EDC_METRICS: edc_data}
        
        actual = extractor.extract_actual_enrollment(raw_data, "TEST_STUDY")
        
        assert actual == 3, "Should count only unique CPIDs (3, not 5)"
    
    # ========================================
    # Test 7.2: CPID Parsing with Missing Data
    # ========================================
    
    def test_extract_actual_enrollment_no_edc_data(self, extractor):
        """Test actual enrollment extraction with no EDC data"""
        raw_data = {}
        
        actual = extractor.extract_actual_enrollment(raw_data, "TEST_STUDY")
        
        assert actual is None, "Should return None when EDC data is missing"
    
    def test_extract_actual_enrollment_empty_edc_data(self, extractor):
        """Test actual enrollment extraction with empty EDC DataFrame"""
        raw_data = {FileType.EDC_METRICS: pd.DataFrame()}
        
        actual = extractor.extract_actual_enrollment(raw_data, "TEST_STUDY")
        
        assert actual is None, "Should return None when EDC data is empty"
    
    def test_extract_actual_enrollment_no_patient_column(self, extractor):
        """Test actual enrollment extraction with no patient/CPID column"""
        edc_data = pd.DataFrame({
            'Site': ['Site 1', 'Site 2'],
            'Visit': ['V1', 'V1']
        })
        raw_data = {FileType.EDC_METRICS: edc_data}
        
        actual = extractor.extract_actual_enrollment(raw_data, "TEST_STUDY")
        
        assert actual is None, "Should return None when no patient column found"
    
    # ========================================
    # Test 7.3: Target Enrollment Extraction
    # ========================================
    
    def test_extract_target_enrollment_from_visit_projection(self, extractor, valid_visit_projection_data):
        """Test target enrollment extraction from Visit Projection Tracker"""
        raw_data = {FileType.VISIT_PROJECTION: valid_visit_projection_data}
        
        target = extractor.extract_target_enrollment(raw_data, "TEST_STUDY")
        
        assert target == 100, "Should extract target enrollment of 100"
    
    def test_extract_target_enrollment_from_column_header(self, extractor):
        """Test target enrollment extraction from column header"""
        visit_data = pd.DataFrame({
            'Target Enrollment': [100, 100, 100],
            'Site': ['Site 1', 'Site 2', 'Site 3']
        })
        raw_data = {FileType.VISIT_PROJECTION: visit_data}
        
        target = extractor.extract_target_enrollment(raw_data, "TEST_STUDY")
        
        assert target == 100, "Should extract target enrollment from column"
    
    def test_extract_target_enrollment_no_data(self, extractor):
        """Test target enrollment extraction with no data"""
        raw_data = {}
        
        target = extractor.extract_target_enrollment(raw_data, "TEST_STUDY")
        
        assert target is None, "Should return None when no data available"
    
    def test_extract_target_enrollment_no_target_column(self, extractor):
        """Test target enrollment extraction with no target column"""
        visit_data = pd.DataFrame({
            'Site': ['Site 1', 'Site 2'],
            'Visits': [10, 15]
        })
        raw_data = {FileType.VISIT_PROJECTION: visit_data}
        
        target = extractor.extract_target_enrollment(raw_data, "TEST_STUDY")
        
        assert target is None, "Should return None when no target column found"
    
    # ========================================
    # Test 7.4: Enrollment Rate Calculation
    # ========================================
    
    def test_calculate_enrollment_rate_normal(self, extractor):
        """Test enrollment rate calculation with normal values"""
        rate = extractor.calculate_enrollment_rate(actual=75, target=100)
        
        assert rate == 75.0, "Should calculate 75% enrollment rate"
    
    def test_calculate_enrollment_rate_full_enrollment(self, extractor):
        """Test enrollment rate calculation at 100%"""
        rate = extractor.calculate_enrollment_rate(actual=100, target=100)
        
        assert rate == 100.0, "Should calculate 100% enrollment rate"
    
    def test_calculate_enrollment_rate_over_enrollment(self, extractor):
        """Test enrollment rate calculation with over-enrollment (capped at 100%)"""
        rate = extractor.calculate_enrollment_rate(actual=120, target=100)
        
        assert rate == 100.0, "Should cap over-enrollment at 100%"
    
    def test_calculate_enrollment_rate_low_enrollment(self, extractor):
        """Test enrollment rate calculation with low enrollment"""
        rate = extractor.calculate_enrollment_rate(actual=25, target=100)
        
        assert rate == 25.0, "Should calculate 25% enrollment rate"
    
    def test_calculate_enrollment_rate_zero_actual(self, extractor):
        """Test enrollment rate calculation with zero actual enrollment"""
        rate = extractor.calculate_enrollment_rate(actual=0, target=100)
        
        assert rate == 0.0, "Should calculate 0% enrollment rate"
    
    def test_calculate_enrollment_rate_rounding(self, extractor):
        """Test enrollment rate calculation rounds to 1 decimal"""
        rate = extractor.calculate_enrollment_rate(actual=33, target=100)
        
        assert rate == 33.0, "Should round to 1 decimal place"
        assert isinstance(rate, float), "Should return float"
    
    # ========================================
    # Test 7.5: Null Handling (FR-6)
    # ========================================
    
    def test_calculate_enrollment_rate_none_actual(self, extractor):
        """Test enrollment rate calculation with None actual"""
        rate = extractor.calculate_enrollment_rate(actual=None, target=100)
        
        assert rate is None, "Should return None when actual is None"
    
    def test_calculate_enrollment_rate_none_target(self, extractor):
        """Test enrollment rate calculation with None target"""
        rate = extractor.calculate_enrollment_rate(actual=75, target=None)
        
        assert rate is None, "Should return None when target is None"
    
    def test_calculate_enrollment_rate_both_none(self, extractor):
        """Test enrollment rate calculation with both None"""
        rate = extractor.calculate_enrollment_rate(actual=None, target=None)
        
        assert rate is None, "Should return None when both are None"
    
    def test_calculate_enrollment_rate_zero_target(self, extractor):
        """Test enrollment rate calculation with zero target (invalid)"""
        rate = extractor.calculate_enrollment_rate(actual=50, target=0)
        
        assert rate is None, "Should return None when target is 0 (invalid)"
    
    def test_calculate_enrollment_rate_negative_target(self, extractor):
        """Test enrollment rate calculation with negative target (invalid)"""
        rate = extractor.calculate_enrollment_rate(actual=50, target=-100)
        
        assert rate is None, "Should return None when target is negative (invalid)"
    
    # ========================================
    # Test 7.6: Over-Enrollment Capping (FR-6)
    # ========================================
    
    def test_calculate_enrollment_rate_150_percent(self, extractor):
        """Test enrollment rate capped at 100% for 150% enrollment"""
        rate = extractor.calculate_enrollment_rate(actual=150, target=100)
        
        assert rate == 100.0, "Should cap 150% enrollment at 100%"
    
    def test_calculate_enrollment_rate_200_percent(self, extractor):
        """Test enrollment rate capped at 100% for 200% enrollment"""
        rate = extractor.calculate_enrollment_rate(actual=200, target=100)
        
        assert rate == 100.0, "Should cap 200% enrollment at 100%"
    
    def test_calculate_enrollment_rate_just_over_100(self, extractor):
        """Test enrollment rate capped at 100% for 101% enrollment"""
        rate = extractor.calculate_enrollment_rate(actual=101, target=100)
        
        assert rate == 100.0, "Should cap 101% enrollment at 100%"
    
    # ========================================
    # Test 7.7: Integration Test
    # ========================================
    
    def test_full_enrollment_extraction_pipeline(self, extractor, valid_edc_data, valid_visit_projection_data):
        """Test full enrollment extraction pipeline"""
        raw_data = {
            FileType.EDC_METRICS: valid_edc_data,
            FileType.VISIT_PROJECTION: valid_visit_projection_data
        }
        
        # Extract actual
        actual = extractor.extract_actual_enrollment(raw_data, "TEST_STUDY")
        assert actual == 5, "Should extract 5 actual subjects"
        
        # Extract target
        target = extractor.extract_target_enrollment(raw_data, "TEST_STUDY")
        assert target == 100, "Should extract target of 100"
        
        # Calculate rate
        rate = extractor.calculate_enrollment_rate(actual, target)
        assert rate == 5.0, "Should calculate 5% enrollment rate"
    
    def test_enrollment_extraction_with_missing_target(self, extractor, valid_edc_data):
        """Test enrollment extraction when target is missing"""
        raw_data = {FileType.EDC_METRICS: valid_edc_data}
        
        actual = extractor.extract_actual_enrollment(raw_data, "TEST_STUDY")
        target = extractor.extract_target_enrollment(raw_data, "TEST_STUDY")
        rate = extractor.calculate_enrollment_rate(actual, target)
        
        assert actual == 5, "Should extract actual enrollment"
        assert target is None, "Should return None for missing target"
        assert rate is None, "Should return None for rate when target is missing"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
