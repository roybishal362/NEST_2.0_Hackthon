"""
Property-Based Tests for Simulated Data
========================================
Tests universal properties that simulated data must satisfy.

Phase 3, Task 15: Write Property-Based Tests for Simulated Data

**Validates: Requirements US-5, US-6, FR-9**
"""

import pytest
from pathlib import Path
import json

from src.data import DataIngestionEngine
from src.data.features_real_extraction import RealFeatureExtractor
from src.intelligence.dqi import DQIEngine


class TestSimulatedDataProperties:
    """Property-based tests for simulated data"""
    
    @pytest.fixture(scope="class")
    def ingestion_engine(self):
        """Create ingestion engine"""
        return DataIngestionEngine()
    
    @pytest.fixture(scope="class")
    def feature_extractor(self):
        """Create feature extractor"""
        return RealFeatureExtractor()
    
    @pytest.fixture(scope="class")
    def dqi_engine(self):
        """Create DQI engine"""
        return DQIEngine()
    
    @pytest.fixture(scope="class")
    def simulated_studies(self):
        """Get list of simulated study IDs"""
        simulated_dir = Path("c_trust/data/simulated")
        if not simulated_dir.exists():
            pytest.skip("Simulated data not generated. Run generate_simulated_data.py first.")
        
        studies = [d.name for d in simulated_dir.iterdir() if d.is_dir()]
        if not studies:
            pytest.skip("No simulated studies found")
        
        return sorted(studies)
    
    def test_simulated_data_produces_low_dqi(self, ingestion_engine, feature_extractor, 
                                             dqi_engine, simulated_studies):
        """
        **Validates: Requirements US-5, FR-9**
        
        Property: ALL simulated studies MUST produce DQI < 65
        
        Rationale:
        - Simulated studies are designed with known quality issues
        - DQI system should detect these issues and produce low scores
        - This validates the system can distinguish good from bad data
        """
        failures = []
        
        for study_id in simulated_studies:
            # Ingest study
            study_dir = Path("c_trust/data/simulated") / study_id
            raw_data = ingestion_engine.ingest_study(str(study_dir))
            
            # Extract features
            features = feature_extractor.extract_features(raw_data, study_id)
            
            # Calculate DQI
            dqi = dqi_engine.calculate_dqi(features, study_id)
            
            # Validate
            if dqi.overall_score >= 65:
                failures.append({
                    'study_id': study_id,
                    'dqi_score': dqi.overall_score,
                    'dqi_band': dqi.risk_level
                })
        
        # Assert
        assert len(failures) == 0, (
            f"Simulated studies with DQI ≥ 65: {failures}\n"
            f"Expected: All simulated studies should have DQI < 65"
        )
    
    def test_simulated_data_produces_amber_or_worse_band(self, ingestion_engine, 
                                                         feature_extractor, dqi_engine, 
                                                         simulated_studies):
        """
        **Validates: Requirements US-5, FR-9**
        
        Property: ALL simulated studies MUST produce DQI band in [AMBER, ORANGE, RED]
        
        Rationale:
        - Low DQI scores should map to warning/critical bands
        - GREEN band indicates acceptable quality (DQI ≥ 80)
        - Simulated data should never be GREEN
        """
        failures = []
        
        for study_id in simulated_studies:
            # Ingest study
            study_dir = Path("c_trust/data/simulated") / study_id
            raw_data = ingestion_engine.ingest_study(str(study_dir))
            
            # Extract features
            features = feature_extractor.extract_features(raw_data, study_id)
            
            # Calculate DQI
            dqi = dqi_engine.calculate_dqi(features, study_id)
            
            # Validate
            if dqi.risk_level == "GREEN":
                failures.append({
                    'study_id': study_id,
                    'dqi_score': dqi.overall_score,
                    'dqi_band': dqi.risk_level
                })
        
        # Assert
        assert len(failures) == 0, (
            f"Simulated studies with GREEN band: {failures}\n"
            f"Expected: All simulated studies should have AMBER, ORANGE, or RED band"
        )
    
    def test_real_data_higher_dqi_than_simulated(self, ingestion_engine, feature_extractor, 
                                                  dqi_engine, simulated_studies):
        """
        **Validates: Requirements US-6**
        
        Property: Real NEST data MUST produce higher average DQI than simulated data
        
        Rationale:
        - Real NEST data represents acceptable quality
        - Simulated data represents poor quality
        - System should distinguish between them
        """
        # Get real NEST data DQI scores
        cache_file = Path("data_cache.json")
        if not cache_file.exists():
            pytest.skip("No data cache found. Run regenerate_cache.py first.")
        
        with open(cache_file, 'r') as f:
            cache_data = json.load(f)
        
        real_dqi_scores = [
            data['overall_score'] 
            for data in cache_data.values() 
            if data.get('overall_score') is not None
        ]
        
        if not real_dqi_scores:
            pytest.skip("No real DQI scores found in cache")
        
        # Get simulated data DQI scores
        simulated_dqi_scores = []
        for study_id in simulated_studies:
            study_dir = Path("c_trust/data/simulated") / study_id
            raw_data = ingestion_engine.ingest_study(str(study_dir))
            features = feature_extractor.extract_features(raw_data, study_id)
            dqi = dqi_engine.calculate_dqi(features, study_id)
            simulated_dqi_scores.append(dqi.overall_score)
        
        # Calculate averages
        avg_real = sum(real_dqi_scores) / len(real_dqi_scores)
        avg_simulated = sum(simulated_dqi_scores) / len(simulated_dqi_scores)
        
        # Assert
        assert avg_real > avg_simulated, (
            f"Real DQI ({avg_real:.1f}) should be > Simulated DQI ({avg_simulated:.1f})\n"
            f"Real scores: {real_dqi_scores}\n"
            f"Simulated scores: {simulated_dqi_scores}"
        )
    
    def test_simulated_data_dqi_variance(self, ingestion_engine, feature_extractor, 
                                         dqi_engine, simulated_studies):
        """
        **Validates: Requirements FR-9**
        
        Property: Simulated studies with different issue profiles MUST produce different DQI scores
        
        Rationale:
        - SIM-001 (critical safety) should have lower DQI than SIM-006 (minor issues)
        - System should be sensitive to severity of quality issues
        - Validates DQI calculation is not constant
        """
        dqi_scores = {}
        
        for study_id in simulated_studies:
            study_dir = Path("c_trust/data/simulated") / study_id
            raw_data = ingestion_engine.ingest_study(str(study_dir))
            features = feature_extractor.extract_features(raw_data, study_id)
            dqi = dqi_engine.calculate_dqi(features, study_id)
            dqi_scores[study_id] = dqi.overall_score
        
        # Check variance
        scores = list(dqi_scores.values())
        variance = max(scores) - min(scores)
        
        # Assert: Should have at least 10 points variance
        assert variance >= 10, (
            f"DQI scores should vary by at least 10 points, got {variance:.1f}\n"
            f"Scores: {dqi_scores}"
        )
    
    def test_simulated_data_enrollment_extraction(self, ingestion_engine, feature_extractor, 
                                                   simulated_studies):
        """
        **Validates: Requirements FR-6**
        
        Property: Simulated studies MUST have extractable enrollment data
        
        Rationale:
        - Simulated data includes target enrollment in profiles
        - System should extract both actual and target enrollment
        - Validates enrollment extraction works on simulated data
        """
        failures = []
        
        for study_id in simulated_studies:
            study_dir = Path("c_trust/data/simulated") / study_id
            raw_data = ingestion_engine.ingest_study(str(study_dir))
            features = feature_extractor.extract_features(raw_data, study_id)
            
            actual = features.get('actual_enrollment')
            target = features.get('target_enrollment')
            
            if actual is None or target is None:
                failures.append({
                    'study_id': study_id,
                    'actual': actual,
                    'target': target
                })
        
        # Assert
        assert len(failures) == 0, (
            f"Simulated studies with missing enrollment: {failures}\n"
            f"Expected: All simulated studies should have actual and target enrollment"
        )
    
    def test_simulated_data_feature_completeness(self, ingestion_engine, feature_extractor, 
                                                  simulated_studies):
        """
        **Validates: Requirements FR-9**
        
        Property: Simulated studies MUST have all required features for agent analysis
        
        Rationale:
        - Agents need specific features to analyze data quality
        - Simulated data should provide all required features
        - Validates data generation is complete
        """
        required_features = [
            'total_subjects',
            'actual_enrollment',
            'target_enrollment',
            'enrollment_rate',
            'visit_completion_rate',
            'missing_visits_pct',
            'missing_pages_pct',
            'open_queries_count',
            'query_resolution_rate',
            'sae_count',
            'fatal_sae_count'
        ]
        
        failures = []
        
        for study_id in simulated_studies:
            study_dir = Path("c_trust/data/simulated") / study_id
            raw_data = ingestion_engine.ingest_study(str(study_dir))
            features = feature_extractor.extract_features(raw_data, study_id)
            
            missing_features = [
                feat for feat in required_features 
                if features.get(feat) is None
            ]
            
            if missing_features:
                failures.append({
                    'study_id': study_id,
                    'missing_features': missing_features
                })
        
        # Assert
        assert len(failures) == 0, (
            f"Simulated studies with missing features: {failures}\n"
            f"Expected: All simulated studies should have all required features"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
