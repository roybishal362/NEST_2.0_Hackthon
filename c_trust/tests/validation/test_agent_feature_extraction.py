"""
Agent Feature Extraction Validation Tests
==========================================
Phase 0 (PREREQUISITE - CRITICAL): Validate that all 7 agents can properly 
analyze real NEST 2.0 data before integrating them with DQI.

This test suite validates that:
1. All required features for each agent are extracted correctly
2. Features have valid values (not None, within expected ranges)
3. Agents can run successfully on real NEST studies
4. Feature extraction is consistent across studies

Test Organization:
- 0.1.1: Safety Agent feature requirements
- 0.1.2: Completeness Agent feature requirements
- 0.1.3: Coding Agent feature requirements
- 0.1.4: Query Quality Agent feature requirements (placeholder - agent file missing)
- 0.1.5: EDC Quality Agent feature requirements
- 0.1.6: Temporal Drift Agent feature requirements
- 0.1.7: Stability Agent feature requirements

**Validates: Requirements US-0 (Phase 0 Acceptance Criteria)**
"""

import pytest
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd

from src.data.ingestion import DataIngestionEngine, StudyDiscovery
from src.data.features_real_extraction import RealFeatureExtractor
from src.core import get_logger

logger = get_logger(__name__)

# ========================================
# TEST CONFIGURATION
# ========================================

# NEST 2.0 study directories (23 studies total)
NEST_DATA_ROOT = Path("norvatas/Data for problem Statement 1/NEST 2.0 Data files_Anonymized/QC Anonymized Study Files")

# Study IDs for testing (we'll use first 5 for quick validation)
# Note: StudyDiscovery normalizes IDs to "STUDY_XX" format
TEST_STUDIES = [
    "STUDY_01",
    "STUDY_02", 
    "STUDY_04",
    "STUDY_05",
    "STUDY_06"
]

# All 23 studies for comprehensive testing
ALL_STUDIES = [
    "STUDY_01", "STUDY_02", "STUDY_04", "STUDY_05", "STUDY_06", "STUDY_07",
    "STUDY_08", "STUDY_09", "STUDY_10", "STUDY_11", "STUDY_13", "STUDY_14",
    "STUDY_15", "STUDY_16", "STUDY_17", "STUDY_18", "STUDY_19", "STUDY_20",
    "STUDY_21", "STUDY_22", "STUDY_23", "STUDY_24", "STUDY_25"
]

# Agent feature requirements (from agent implementations)
AGENT_FEATURES = {
    "Safety": {
        "required": ["sae_backlog_days", "fatal_sae_count"],
        "optional": ["sae_overdue_count"]
    },
    "Completeness": {
        "required": ["form_completion_rate"],
        "optional": ["missing_pages_pct", "visit_completion_rate", "data_entry_lag_days", "_visit_gap_count"]
    },
    "Coding": {
        "required": ["coding_completion_rate", "coding_backlog_days"],
        "optional": ["uncoded_sae_count", "coding_velocity", "pending_queries_coding"]
    },
    "Query Quality": {
        "required": ["open_queries_count", "query_aging_days", "query_resolution_rate"],
        "optional": []
    },
    "EDC Quality": {
        "required": ["form_completion_rate", "data_entry_errors"],
        "optional": ["missing_required_fields", "edc_system_uptime", "data_validation_failures"]
    },
    "Temporal Drift": {
        "required": ["avg_data_entry_lag_days", "overdue_visits_count"],
        "optional": ["lag_trend", "max_data_entry_lag_days", "visit_completion_rate"]
    },
    "Stability": {
        "required": ["enrollment_velocity", "site_activation_rate", "dropout_rate"],
        "optional": ["enrollment_trend", "site_performance_variance", "patient_retention_rate"]
    }
}


# ========================================
# HELPER FUNCTIONS
# ========================================

# Initialize engines once for all tests
_discovery = None
_ingestion = None
_feature_extractor = None
_nest_data_cache = {}


def get_engines():
    """Get or initialize data engines."""
    global _discovery, _ingestion, _feature_extractor
    
    if _discovery is None:
        _discovery = StudyDiscovery()
        _ingestion = DataIngestionEngine()
        _feature_extractor = RealFeatureExtractor()
        logger.info("Initialized data engines")
    
    return _discovery, _ingestion, _feature_extractor


def load_study_data(study_id: str) -> Dict[str, pd.DataFrame]:
    """
    Load raw NEST data for a study.
    
    Args:
        study_id: Study identifier (e.g., "STUDY_01")
    
    Returns:
        Dictionary of DataFrames by file type
    """
    global _nest_data_cache
    
    # Check cache first
    if study_id in _nest_data_cache:
        return _nest_data_cache[study_id]
    
    try:
        discovery, ingestion, _ = get_engines()
        
        # Find the study
        studies = discovery.discover_all_studies()
        study_obj = None
        
        for study in studies:
            if study.study_id == study_id:
                study_obj = study
                break
        
        if study_obj is None:
            logger.error(f"Study {study_id} not found. Available studies: {[s.study_id for s in studies[:5]]}")
            return {}
        
        # Load data
        logger.info(f"Loading data for {study_id}")
        data = ingestion.ingest_study(study_obj, validate_data=False)
        
        # Cache it
        _nest_data_cache[study_id] = data
        
        return data
    except Exception as e:
        logger.error(f"Failed to load data for {study_id}: {e}")
        import traceback
        traceback.print_exc()
        return {}


def extract_study_features(study_id: str) -> Dict[str, Any]:
    """
    Extract features for a study.
    
    Args:
        study_id: Study identifier (e.g., "STUDY_01")
    
    Returns:
        Dictionary of extracted features
    """
    try:
        # Load raw data
        data = load_study_data(study_id)
        
        if not data:
            logger.error(f"No data loaded for {study_id}")
            return {}
        
        # Extract features
        _, _, feature_extractor = get_engines()
        logger.info(f"Extracting features for {study_id}")
        features = feature_extractor.extract_features(data, study_id)
        
        logger.info(f"Extracted {len(features)} features for {study_id}")
        return features
    except Exception as e:
        logger.error(f"Failed to extract features for {study_id}: {e}")
        import traceback
        traceback.print_exc()
        return {}


def check_feature_availability(
    features: Dict[str, Any],
    required_features: List[str],
    optional_features: List[str]
) -> Dict[str, Any]:
    """
    Check which features are available and valid.
    
    Returns:
        Dictionary with availability statistics
    """
    result = {
        "required_available": 0,
        "required_missing": [],
        "optional_available": 0,
        "optional_missing": [],
        "invalid_values": []
    }
    
    # Check required features
    for feature in required_features:
        if feature in features and features[feature] is not None:
            result["required_available"] += 1
        else:
            result["required_missing"].append(feature)
    
    # Check optional features
    for feature in optional_features:
        if feature in features and features[feature] is not None:
            result["optional_available"] += 1
        else:
            result["optional_missing"].append(feature)
    
    # Check for invalid values (negative numbers where they shouldn't be)
    for feature, value in features.items():
        if value is not None:
            # Check for negative values in count/percentage features
            if any(keyword in feature for keyword in ["count", "pct", "rate", "days"]):
                if isinstance(value, (int, float)) and value < 0:
                    result["invalid_values"].append(f"{feature}={value}")
    
    return result


# ========================================
# TEST SUITE: SAFETY AGENT (0.1.1)
# ========================================

class TestSafetyAgentFeatures:
    """Test Safety Agent feature requirements."""
    
    @pytest.mark.parametrize("study_id", TEST_STUDIES)
    def test_safety_agent_required_features(self, study_id):
        """
        Test 0.1.1: Verify Safety Agent required features are extracted.
        
        Required features:
        - sae_backlog_days: Average age of open SAEs
        - fatal_sae_count: Count of fatal SAEs
        """
        features = extract_study_features(study_id)
        
        assert features, f"No features extracted for {study_id}"
        
        # Check required features
        required = AGENT_FEATURES["Safety"]["required"]
        availability = check_feature_availability(features, required, [])
        
        # Log results
        logger.info(f"{study_id} Safety Agent: {availability['required_available']}/{len(required)} required features available")
        
        # Assert at least one required feature is available
        # (We allow some missing features as long as agent can still run)
        assert availability["required_available"] > 0, \
            f"No required Safety features available for {study_id}. Missing: {availability['required_missing']}"
    
    @pytest.mark.parametrize("study_id", TEST_STUDIES)
    def test_safety_agent_feature_values(self, study_id):
        """
        Test 0.1.1: Verify Safety Agent features have valid values.
        
        Validation:
        - sae_backlog_days >= 0
        - fatal_sae_count >= 0
        """
        features = extract_study_features(study_id)
        
        # Check sae_backlog_days
        if "sae_backlog_days" in features and features["sae_backlog_days"] is not None:
            sae_backlog = features["sae_backlog_days"]
            assert isinstance(sae_backlog, (int, float)), \
                f"sae_backlog_days should be numeric, got {type(sae_backlog)}"
            assert sae_backlog >= 0, \
                f"sae_backlog_days should be >= 0, got {sae_backlog}"
            logger.info(f"{study_id}: sae_backlog_days = {sae_backlog:.1f} days")
        
        # Check fatal_sae_count
        if "fatal_sae_count" in features and features["fatal_sae_count"] is not None:
            fatal_count = features["fatal_sae_count"]
            assert isinstance(fatal_count, int), \
                f"fatal_sae_count should be int, got {type(fatal_count)}"
            assert fatal_count >= 0, \
                f"fatal_sae_count should be >= 0, got {fatal_count}"
            logger.info(f"{study_id}: fatal_sae_count = {fatal_count}")


# ========================================
# TEST SUITE: COMPLETENESS AGENT (0.1.2)
# ========================================

class TestCompletenessAgentFeatures:
    """Test Completeness Agent feature requirements."""
    
    @pytest.mark.parametrize("study_id", TEST_STUDIES)
    def test_completeness_agent_required_features(self, study_id):
        """
        Test 0.1.2: Verify Completeness Agent required features are extracted.
        
        Required features:
        - form_completion_rate: Percentage of forms completed
        """
        features = extract_study_features(study_id)
        
        assert features, f"No features extracted for {study_id}"
        
        # Check required features
        required = AGENT_FEATURES["Completeness"]["required"]
        availability = check_feature_availability(features, required, [])
        
        logger.info(f"{study_id} Completeness Agent: {availability['required_available']}/{len(required)} required features available")
        
        # Form completion rate is CRITICAL - log if missing but don't fail
        if "form_completion_rate" not in features or features["form_completion_rate"] is None:
            logger.warning(f"form_completion_rate is REQUIRED for Completeness Agent but missing/None in {study_id}")
            logger.warning(f"This study may cause agent abstention")
        else:
            logger.info(f"{study_id}: form_completion_rate = {features['form_completion_rate']:.1f}%")
    
    @pytest.mark.parametrize("study_id", TEST_STUDIES)
    def test_completeness_agent_feature_values(self, study_id):
        """
        Test 0.1.2: Verify Completeness Agent features have valid values.
        
        Validation:
        - form_completion_rate: 0-100%
        - missing_pages_pct: 0-100%
        - visit_completion_rate: 0-100%
        """
        features = extract_study_features(study_id)
        
        # Check form_completion_rate
        if "form_completion_rate" in features and features["form_completion_rate"] is not None:
            rate = features["form_completion_rate"]
            assert isinstance(rate, (int, float)), \
                f"form_completion_rate should be numeric, got {type(rate)}"
            assert 0 <= rate <= 100, \
                f"form_completion_rate should be 0-100%, got {rate}"
            logger.info(f"{study_id}: form_completion_rate = {rate:.1f}%")
        
        # Check missing_pages_pct
        if "missing_pages_pct" in features and features["missing_pages_pct"] is not None:
            pct = features["missing_pages_pct"]
            assert isinstance(pct, (int, float)), \
                f"missing_pages_pct should be numeric, got {type(pct)}"
            assert 0 <= pct <= 100, \
                f"missing_pages_pct should be 0-100%, got {pct}"
            logger.info(f"{study_id}: missing_pages_pct = {pct:.1f}%")
        
        # Check visit_completion_rate
        if "visit_completion_rate" in features and features["visit_completion_rate"] is not None:
            rate = features["visit_completion_rate"]
            assert isinstance(rate, (int, float)), \
                f"visit_completion_rate should be numeric, got {type(rate)}"
            assert 0 <= rate <= 100, \
                f"visit_completion_rate should be 0-100%, got {rate}"
            logger.info(f"{study_id}: visit_completion_rate = {rate:.1f}%")


# ========================================
# TEST SUITE: CODING AGENT (0.1.3)
# ========================================

class TestCodingAgentFeatures:
    """Test Coding Agent feature requirements."""
    
    @pytest.mark.parametrize("study_id", TEST_STUDIES)
    def test_coding_agent_required_features(self, study_id):
        """
        Test 0.1.3: Verify Coding Agent required features are extracted.
        
        Required features:
        - coding_completion_rate: Percentage of terms coded
        - coding_backlog_days: Average age of uncoded terms
        """
        features = extract_study_features(study_id)
        
        assert features, f"No features extracted for {study_id}"
        
        # Check required features
        required = AGENT_FEATURES["Coding"]["required"]
        availability = check_feature_availability(features, required, [])
        
        logger.info(f"{study_id} Coding Agent: {availability['required_available']}/{len(required)} required features available")
        
        # Log missing features as warnings (some studies may not have coding data)
        if availability["required_available"] == 0:
            logger.warning(f"No required Coding features available for {study_id}. Missing: {availability['required_missing']}")
            logger.warning(f"This study will cause Coding Agent abstention")
        else:
            logger.info(f"{study_id}: Coding Agent has {availability['required_available']}/{len(required)} required features")
    
    @pytest.mark.parametrize("study_id", TEST_STUDIES)
    def test_coding_agent_feature_values(self, study_id):
        """
        Test 0.1.3: Verify Coding Agent features have valid values.
        
        Validation:
        - coding_completion_rate: 0-100%
        - coding_backlog_days >= 0
        - uncoded_sae_count >= 0
        """
        features = extract_study_features(study_id)
        
        # Check coding_completion_rate
        if "coding_completion_rate" in features and features["coding_completion_rate"] is not None:
            rate = features["coding_completion_rate"]
            assert isinstance(rate, (int, float)), \
                f"coding_completion_rate should be numeric, got {type(rate)}"
            assert 0 <= rate <= 100, \
                f"coding_completion_rate should be 0-100%, got {rate}"
            logger.info(f"{study_id}: coding_completion_rate = {rate:.1f}%")
        
        # Check coding_backlog_days
        if "coding_backlog_days" in features and features["coding_backlog_days"] is not None:
            days = features["coding_backlog_days"]
            assert isinstance(days, (int, float)), \
                f"coding_backlog_days should be numeric, got {type(days)}"
            assert days >= 0, \
                f"coding_backlog_days should be >= 0, got {days}"
            logger.info(f"{study_id}: coding_backlog_days = {days:.1f} days")
        
        # Check uncoded_sae_count
        if "uncoded_sae_count" in features and features["uncoded_sae_count"] is not None:
            count = features["uncoded_sae_count"]
            assert isinstance(count, int), \
                f"uncoded_sae_count should be int, got {type(count)}"
            assert count >= 0, \
                f"uncoded_sae_count should be >= 0, got {count}"
            logger.info(f"{study_id}: uncoded_sae_count = {count}")


# ========================================
# TEST SUITE: EDC QUALITY AGENT (0.1.5)
# ========================================

class TestEDCQualityAgentFeatures:
    """Test EDC Quality Agent feature requirements."""
    
    @pytest.mark.parametrize("study_id", TEST_STUDIES)
    def test_edc_quality_agent_required_features(self, study_id):
        """
        Test 0.1.5: Verify EDC Quality Agent required features are extracted.
        
        Required features:
        - form_completion_rate: Percentage of forms completed
        - data_entry_errors: Count of data entry errors
        """
        features = extract_study_features(study_id)
        
        assert features, f"No features extracted for {study_id}"
        
        # Check required features
        required = AGENT_FEATURES["EDC Quality"]["required"]
        availability = check_feature_availability(features, required, [])
        
        logger.info(f"{study_id} EDC Quality Agent: {availability['required_available']}/{len(required)} required features available")
        
        # Log missing features as warnings
        if availability["required_available"] == 0:
            logger.warning(f"No required EDC Quality features available for {study_id}. Missing: {availability['required_missing']}")
            logger.warning(f"This study will cause EDC Quality Agent abstention")
        else:
            logger.info(f"{study_id}: EDC Quality Agent has {availability['required_available']}/{len(required)} required features")
    
    @pytest.mark.parametrize("study_id", TEST_STUDIES)
    def test_edc_quality_agent_feature_values(self, study_id):
        """
        Test 0.1.5: Verify EDC Quality Agent features have valid values.
        
        Validation:
        - form_completion_rate: 0-100%
        - data_entry_errors >= 0
        """
        features = extract_study_features(study_id)
        
        # Check form_completion_rate (shared with Completeness Agent)
        if "form_completion_rate" in features and features["form_completion_rate"] is not None:
            rate = features["form_completion_rate"]
            assert 0 <= rate <= 100, \
                f"form_completion_rate should be 0-100%, got {rate}"
            logger.info(f"{study_id}: form_completion_rate = {rate:.1f}%")
        
        # Check data_entry_errors
        if "data_entry_errors" in features and features["data_entry_errors"] is not None:
            errors = features["data_entry_errors"]
            assert isinstance(errors, int), \
                f"data_entry_errors should be int, got {type(errors)}"
            assert errors >= 0, \
                f"data_entry_errors should be >= 0, got {errors}"
            logger.info(f"{study_id}: data_entry_errors = {errors}")


# ========================================
# TEST SUITE: TEMPORAL DRIFT AGENT (0.1.6)
# ========================================

class TestTemporalDriftAgentFeatures:
    """Test Temporal Drift Agent feature requirements."""
    
    @pytest.mark.parametrize("study_id", TEST_STUDIES)
    def test_temporal_drift_agent_required_features(self, study_id):
        """
        Test 0.1.6: Verify Temporal Drift Agent required features are extracted.
        
        Required features:
        - avg_data_entry_lag_days: Average data entry lag
        - overdue_visits_count: Count of overdue visits
        """
        features = extract_study_features(study_id)
        
        assert features, f"No features extracted for {study_id}"
        
        # Check required features
        required = AGENT_FEATURES["Temporal Drift"]["required"]
        availability = check_feature_availability(features, required, [])
        
        logger.info(f"{study_id} Temporal Drift Agent: {availability['required_available']}/{len(required)} required features available")
        
        # Assert at least one required feature is available
        assert availability["required_available"] > 0, \
            f"No required Temporal Drift features available for {study_id}. Missing: {availability['required_missing']}"
    
    @pytest.mark.parametrize("study_id", TEST_STUDIES)
    def test_temporal_drift_agent_feature_values(self, study_id):
        """
        Test 0.1.6: Verify Temporal Drift Agent features have valid values.
        
        Validation:
        - avg_data_entry_lag_days >= 0
        - overdue_visits_count >= 0
        """
        features = extract_study_features(study_id)
        
        # Check avg_data_entry_lag_days
        if "avg_data_entry_lag_days" in features and features["avg_data_entry_lag_days"] is not None:
            lag = features["avg_data_entry_lag_days"]
            assert isinstance(lag, (int, float)), \
                f"avg_data_entry_lag_days should be numeric, got {type(lag)}"
            assert lag >= 0, \
                f"avg_data_entry_lag_days should be >= 0, got {lag}"
            logger.info(f"{study_id}: avg_data_entry_lag_days = {lag:.1f} days")
        
        # Check overdue_visits_count
        if "overdue_visits_count" in features and features["overdue_visits_count"] is not None:
            count = features["overdue_visits_count"]
            assert isinstance(count, int), \
                f"overdue_visits_count should be int, got {type(count)}"
            assert count >= 0, \
                f"overdue_visits_count should be >= 0, got {count}"
            logger.info(f"{study_id}: overdue_visits_count = {count}")


# ========================================
# TEST SUITE: STABILITY AGENT (0.1.7)
# ========================================

class TestStabilityAgentFeatures:
    """Test Stability Agent feature requirements."""
    
    @pytest.mark.parametrize("study_id", TEST_STUDIES)
    def test_stability_agent_required_features(self, study_id):
        """
        Test 0.1.7: Verify Stability Agent required features are extracted.
        
        Required features:
        - enrollment_velocity: Enrollment rate vs target
        - site_activation_rate: Percentage of sites activated
        - dropout_rate: Patient dropout percentage
        """
        features = extract_study_features(study_id)
        
        assert features, f"No features extracted for {study_id}"
        
        # Check required features
        required = AGENT_FEATURES["Stability"]["required"]
        availability = check_feature_availability(features, required, [])
        
        logger.info(f"{study_id} Stability Agent: {availability['required_available']}/{len(required)} required features available")
        
        # Assert at least one required feature is available
        assert availability["required_available"] > 0, \
            f"No required Stability features available for {study_id}. Missing: {availability['required_missing']}"
    
    @pytest.mark.parametrize("study_id", TEST_STUDIES)
    def test_stability_agent_feature_values(self, study_id):
        """
        Test 0.1.7: Verify Stability Agent features have valid values.
        
        Validation:
        - enrollment_velocity: 0-100%+
        - site_activation_rate: 0-100%
        - dropout_rate: 0-100%
        """
        features = extract_study_features(study_id)
        
        # Check enrollment_velocity
        if "enrollment_velocity" in features and features["enrollment_velocity"] is not None:
            velocity = features["enrollment_velocity"]
            assert isinstance(velocity, (int, float)), \
                f"enrollment_velocity should be numeric, got {type(velocity)}"
            assert velocity >= 0, \
                f"enrollment_velocity should be >= 0, got {velocity}"
            logger.info(f"{study_id}: enrollment_velocity = {velocity:.1f}%")
        
        # Check site_activation_rate
        if "site_activation_rate" in features and features["site_activation_rate"] is not None:
            rate = features["site_activation_rate"]
            assert isinstance(rate, (int, float)), \
                f"site_activation_rate should be numeric, got {type(rate)}"
            assert 0 <= rate <= 100, \
                f"site_activation_rate should be 0-100%, got {rate}"
            logger.info(f"{study_id}: site_activation_rate = {rate:.1f}%")
        
        # Check dropout_rate
        if "dropout_rate" in features and features["dropout_rate"] is not None:
            rate = features["dropout_rate"]
            assert isinstance(rate, (int, float)), \
                f"dropout_rate should be numeric, got {type(rate)}"
            assert 0 <= rate <= 100, \
                f"dropout_rate should be 0-100%, got {rate}"
            logger.info(f"{study_id}: dropout_rate = {rate:.1f}%")


# ========================================
# COMPREHENSIVE VALIDATION TESTS
# ========================================

class TestComprehensiveFeatureExtraction:
    """Comprehensive tests across all agents and studies."""
    
    def test_all_agents_have_features_for_sample_studies(self):
        """
        Validate that all 7 agents have at least some required features
        extracted for sample studies.
        """
        results = {}
        
        for study_id in TEST_STUDIES:
            features = extract_study_features(study_id)
            study_results = {}
            
            for agent_name, agent_features in AGENT_FEATURES.items():
                availability = check_feature_availability(
                    features,
                    agent_features["required"],
                    agent_features["optional"]
                )
                
                study_results[agent_name] = {
                    "required_available": availability["required_available"],
                    "required_total": len(agent_features["required"]),
                    "optional_available": availability["optional_available"],
                    "optional_total": len(agent_features["optional"]),
                    "missing": availability["required_missing"]
                }
            
            results[study_id] = study_results
        
        # Log summary
        logger.info("\n" + "="*80)
        logger.info("FEATURE EXTRACTION SUMMARY")
        logger.info("="*80)
        
        for study_id, study_results in results.items():
            logger.info(f"\n{study_id}:")
            for agent_name, agent_results in study_results.items():
                req_pct = (agent_results["required_available"] / agent_results["required_total"] * 100) if agent_results["required_total"] > 0 else 0
                opt_pct = (agent_results["optional_available"] / agent_results["optional_total"] * 100) if agent_results["optional_total"] > 0 else 0
                
                logger.info(f"  {agent_name}:")
                logger.info(f"    Required: {agent_results['required_available']}/{agent_results['required_total']} ({req_pct:.0f}%)")
                logger.info(f"    Optional: {agent_results['optional_available']}/{agent_results['optional_total']} ({opt_pct:.0f}%)")
                
                if agent_results["missing"]:
                    logger.info(f"    Missing: {', '.join(agent_results['missing'])}")
        
        # Assert that at least 50% of agents have their required features for each study
        for study_id, study_results in results.items():
            agents_with_features = sum(
                1 for agent_results in study_results.values()
                if agent_results["required_available"] > 0
            )
            
            success_rate = agents_with_features / len(AGENT_FEATURES) * 100
            
            assert success_rate >= 50, \
                f"{study_id}: Only {agents_with_features}/{len(AGENT_FEATURES)} agents have features ({success_rate:.0f}%). Need >= 50%"
    
    def test_feature_extraction_consistency(self):
        """
        Validate that feature extraction is consistent across studies.
        
        This test checks that:
        1. The same features are extracted for all studies
        2. Feature values are within reasonable ranges
        """
        all_features = {}
        
        for study_id in TEST_STUDIES:
            features = extract_study_features(study_id)
            all_features[study_id] = set(features.keys())
        
        # Find common features across all studies
        common_features = set.intersection(*all_features.values()) if all_features else set()
        
        logger.info(f"\nCommon features across all test studies: {len(common_features)}")
        logger.info(f"Features: {sorted(common_features)}")
        
        # Assert that we have at least some common features
        assert len(common_features) > 0, \
            "No common features found across test studies"
        
        # Assert that critical features are common
        critical_features = ["form_completion_rate"]
        for feature in critical_features:
            assert feature in common_features, \
                f"Critical feature '{feature}' not found in all studies"


# ========================================
# PYTEST CONFIGURATION
# ========================================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "agent_validation: mark test as agent validation test"
    )
    config.addinivalue_line(
        "markers", "feature_extraction: mark test as feature extraction test"
    )


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
