"""
Integration Test: Enrollment Data Accuracy
==========================================
Validates enrollment extraction accuracy across all 23 NEST studies.

Phase 2, Task 10: Validate Enrollment Data Accuracy
"""

import pytest
import pandas as pd
from pathlib import Path

from src.data import DataIngestionEngine
from src.data.features_real_extraction import RealFeatureExtractor


class TestEnrollmentAccuracy:
    """Integration tests for enrollment data accuracy"""
    
    @pytest.fixture(scope="class")
    def ingestion_engine(self):
        """Create ingestion engine"""
        return DataIngestionEngine()
    
    @pytest.fixture(scope="class")
    def feature_extractor(self):
        """Create feature extractor"""
        return RealFeatureExtractor()
    
    def test_enrollment_extraction_all_studies(self, ingestion_engine, feature_extractor):
        """
        Test enrollment extraction for all 23 NEST studies.
        
        Validates:
        - Actual enrollment is extracted correctly
        - Target enrollment is extracted correctly
        - Enrollment rate is calculated correctly
        - No studies show None if data exists
        """
        # Ingest all studies
        all_data = ingestion_engine.ingest_all_studies(parallel=False)
        
        results = []
        
        for study_id, raw_data in all_data.items():
            # Extract enrollment
            actual = feature_extractor.extract_actual_enrollment(raw_data, study_id)
            target = feature_extractor.extract_target_enrollment(raw_data, study_id)
            rate = feature_extractor.calculate_enrollment_rate(actual, target)
            
            results.append({
                "study_id": study_id,
                "actual": actual,
                "target": target,
                "rate_pct": rate,
                "has_actual": actual is not None,
                "has_target": target is not None,
                "has_rate": rate is not None
            })
        
        # Generate report
        df = pd.DataFrame(results)
        report_path = Path("enrollment_accuracy_report.csv")
        df.to_csv(report_path, index=False)
        
        print(f"\n{'='*80}")
        print("ENROLLMENT ACCURACY REPORT")
        print(f"{'='*80}")
        print(f"Total studies: {len(results)}")
        print(f"Studies with actual enrollment: {df['has_actual'].sum()}")
        print(f"Studies with target enrollment: {df['has_target'].sum()}")
        print(f"Studies with enrollment rate: {df['has_rate'].sum()}")
        print(f"\nReport saved to: {report_path}")
        print(f"{'='*80}\n")
        
        # Assertions
        assert len(results) == 23, f"Expected 23 studies, got {len(results)}"
        
        # At least 80% of studies should have actual enrollment
        actual_pct = (df['has_actual'].sum() / len(results)) * 100
        assert actual_pct >= 80, f"Only {actual_pct:.1f}% of studies have actual enrollment (expected >= 80%)"
        
        # At least 50% of studies should have target enrollment
        target_pct = (df['has_target'].sum() / len(results)) * 100
        assert target_pct >= 50, f"Only {target_pct:.1f}% of studies have target enrollment (expected >= 50%)"
    
    def test_enrollment_rate_calculation_accuracy(self, ingestion_engine, feature_extractor):
        """
        Test enrollment rate calculation accuracy.
        
        Validates:
        - Rate matches manual calculation
        - Rate is capped at 100%
        - Rate is rounded to 1 decimal
        """
        all_data = ingestion_engine.ingest_all_studies(parallel=False)
        
        for study_id, raw_data in all_data.items():
            actual = feature_extractor.extract_actual_enrollment(raw_data, study_id)
            target = feature_extractor.extract_target_enrollment(raw_data, study_id)
            rate = feature_extractor.calculate_enrollment_rate(actual, target)
            
            if actual is not None and target is not None and target > 0:
                # Manual calculation
                expected_rate = min((actual / target) * 100, 100.0)
                expected_rate = round(expected_rate, 1)
                
                assert rate == expected_rate, (
                    f"{study_id}: Rate mismatch - "
                    f"expected {expected_rate}%, got {rate}% "
                    f"(actual={actual}, target={target})"
                )
    
    def test_enrollment_data_consistency(self, ingestion_engine, feature_extractor):
        """
        Test enrollment data consistency.
        
        Validates:
        - Actual enrollment is always >= 0
        - Target enrollment is always > 0 (if not None)
        - Rate is always in [0, 100]
        """
        all_data = ingestion_engine.ingest_all_studies(parallel=False)
        
        for study_id, raw_data in all_data.items():
            actual = feature_extractor.extract_actual_enrollment(raw_data, study_id)
            target = feature_extractor.extract_target_enrollment(raw_data, study_id)
            rate = feature_extractor.calculate_enrollment_rate(actual, target)
            
            if actual is not None:
                assert actual >= 0, f"{study_id}: Actual enrollment {actual} is negative"
            
            if target is not None:
                assert target > 0, f"{study_id}: Target enrollment {target} is not positive"
            
            if rate is not None:
                assert 0.0 <= rate <= 100.0, f"{study_id}: Rate {rate}% is outside bounds [0, 100]"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
