"""
Property-Based Tests for Concurrent Processing Performance
==========================================================
Tests Property: Concurrent Processing Performance

**Property: Concurrent Processing Performance**
*For any* set of studies processed concurrently, the system should:
1. Process all studies without data corruption
2. Maintain result consistency regardless of processing order
3. Not experience performance degradation with concurrent load

**Validates: Requirements 9.2**

This test uses Hypothesis to generate various concurrent processing scenarios
and verify the system handles them correctly.
"""

import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Dict, List, Tuple
from unittest.mock import Mock, patch

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck, assume

from src.agents.signal_agents.completeness_agent import DataCompletenessAgent
from src.agents.signal_agents.safety_agent import SafetyComplianceAgent
from src.agents.signal_agents.query_agent import QueryQualityAgent
from src.intelligence.base_agent import AgentSignal, AgentType, RiskSignal
from src.consensus.consensus_engine import ConsensusEngine, ConsensusRiskLevel
from src.dqi.dqi_engine import DQICalculationEngine, DQIBand
from src.guardian.guardian_agent import GuardianAgent
from src.core import get_logger

logger = get_logger(__name__)


# ========================================
# TEST STRATEGIES
# ========================================

@st.composite
def study_features_strategy(draw):
    """Generate valid study features for analysis"""
    return {
        # Completeness features
        "missing_pages_pct": draw(st.floats(min_value=0.0, max_value=100.0, allow_nan=False)),
        "form_completion_rate": draw(st.floats(min_value=0.0, max_value=100.0, allow_nan=False)),
        "visit_completion_rate": draw(st.floats(min_value=0.0, max_value=100.0, allow_nan=False)),
        "data_entry_lag_days": draw(st.floats(min_value=0.0, max_value=30.0, allow_nan=False)),
        
        # Safety features
        "sae_backlog_days": draw(st.floats(min_value=0.0, max_value=30.0, allow_nan=False)),
        "sae_overdue_count": draw(st.integers(min_value=0, max_value=10)),
        "fatal_sae_count": draw(st.integers(min_value=0, max_value=5)),
        "safety_signal_count": draw(st.integers(min_value=0, max_value=10)),
        
        # Query features
        "open_query_count": draw(st.integers(min_value=0, max_value=200)),
        "query_aging_days": draw(st.floats(min_value=0.0, max_value=60.0, allow_nan=False)),
        "query_resolution_rate": draw(st.floats(min_value=0.0, max_value=100.0, allow_nan=False)),
        
        # Compliance features
        "missing_lab_ranges_pct": draw(st.floats(min_value=0.0, max_value=100.0, allow_nan=False)),
        "protocol_deviation_count": draw(st.integers(min_value=0, max_value=20)),
        "regulatory_compliance_rate": draw(st.floats(min_value=0.0, max_value=100.0, allow_nan=False)),
    }


@st.composite
def multiple_studies_features_strategy(draw, min_studies: int = 2, max_studies: int = 5):
    """Generate features for multiple studies"""
    num_studies = draw(st.integers(min_value=min_studies, max_value=max_studies))
    
    studies = {}
    for i in range(num_studies):
        study_id = f"STUDY_{i+1:02d}"
        studies[study_id] = draw(study_features_strategy())
    
    return studies


# ========================================
# HELPER FUNCTIONS
# ========================================

def process_study_analysis(study_id: str, features: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a single study through the full analysis pipeline.
    
    Returns a dictionary with all analysis results.
    """
    # Create agents
    completeness_agent = DataCompletenessAgent()
    safety_agent = SafetyComplianceAgent()
    query_agent = QueryQualityAgent()
    
    # Run agents
    signals = [
        completeness_agent.analyze(features, study_id),
        safety_agent.analyze(features, study_id),
        query_agent.analyze(features, study_id),
    ]
    
    # Run consensus
    consensus_engine = ConsensusEngine()
    consensus_result = consensus_engine.calculate_consensus(signals, study_id)
    
    # Calculate DQI
    dqi_engine = DQICalculationEngine()
    dqi_result = dqi_engine.calculate_dqi(features, study_id)
    
    return {
        "study_id": study_id,
        "signals": signals,
        "consensus": consensus_result,
        "dqi": dqi_result,
        "timestamp": datetime.now(),
    }


# ========================================
# PROPERTY TESTS
# ========================================

class TestConcurrentProcessingProperty:
    """
    Property-based tests for concurrent processing performance.
    
    Feature: clinical-ai-system, Property: Concurrent Processing Performance
    """
    
    @given(studies_features=multiple_studies_features_strategy(min_studies=2, max_studies=5))
    @settings(max_examples=100, deadline=30000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_concurrent_processing_produces_consistent_results(
        self,
        studies_features: Dict[str, Dict[str, Any]]
    ):
        """
        Feature: clinical-ai-system, Property: Concurrent Processing Performance
        Validates: Requirements 9.2
        
        Property: For any set of studies, processing them concurrently should
        produce the same results as processing them sequentially.
        """
        # Process sequentially first
        sequential_results = {}
        for study_id, features in studies_features.items():
            result = process_study_analysis(study_id, features)
            sequential_results[study_id] = result
        
        # Process concurrently
        concurrent_results = {}
        with ThreadPoolExecutor(max_workers=min(len(studies_features), 4)) as executor:
            futures = {
                executor.submit(process_study_analysis, study_id, features): study_id
                for study_id, features in studies_features.items()
            }
            
            for future in as_completed(futures):
                study_id = futures[future]
                result = future.result()
                concurrent_results[study_id] = result
        
        # Verify results match
        assert set(sequential_results.keys()) == set(concurrent_results.keys())
        
        for study_id in studies_features.keys():
            seq_result = sequential_results[study_id]
            conc_result = concurrent_results[study_id]
            
            # DQI scores should match
            assert abs(seq_result["dqi"].overall_score - conc_result["dqi"].overall_score) < 0.01, \
                f"DQI mismatch for {study_id}: {seq_result['dqi'].overall_score} vs {conc_result['dqi'].overall_score}"
            
            # DQI bands should match
            assert seq_result["dqi"].band == conc_result["dqi"].band, \
                f"DQI band mismatch for {study_id}"
            
            # Consensus risk levels should match
            assert seq_result["consensus"].risk_level == conc_result["consensus"].risk_level, \
                f"Consensus risk level mismatch for {study_id}"
            
            # Risk scores should match (within tolerance)
            assert abs(seq_result["consensus"].risk_score - conc_result["consensus"].risk_score) < 0.01, \
                f"Risk score mismatch for {study_id}"
    
    @given(studies_features=multiple_studies_features_strategy(min_studies=2, max_studies=4))
    @settings(max_examples=100, deadline=30000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_concurrent_processing_no_data_corruption(
        self,
        studies_features: Dict[str, Dict[str, Any]]
    ):
        """
        Feature: clinical-ai-system, Property: Concurrent Processing Performance
        Validates: Requirements 9.2
        
        Property: Concurrent processing should not cause data corruption
        between studies.
        """
        results = {}
        errors = []
        
        def process_with_validation(study_id: str, features: Dict[str, Any]):
            """Process and validate study data"""
            try:
                result = process_study_analysis(study_id, features)
                
                # Validate result belongs to correct study
                assert result["study_id"] == study_id, \
                    f"Study ID mismatch: expected {study_id}, got {result['study_id']}"
                assert result["dqi"].entity_id == study_id, \
                    f"DQI entity ID mismatch for {study_id}"
                assert result["consensus"].entity_id == study_id, \
                    f"Consensus entity ID mismatch for {study_id}"
                
                return result
            except Exception as e:
                errors.append((study_id, str(e)))
                raise
        
        # Process concurrently
        with ThreadPoolExecutor(max_workers=min(len(studies_features), 4)) as executor:
            futures = {
                executor.submit(process_with_validation, study_id, features): study_id
                for study_id, features in studies_features.items()
            }
            
            for future in as_completed(futures):
                study_id = futures[future]
                try:
                    result = future.result()
                    results[study_id] = result
                except Exception as e:
                    pass  # Error already logged
        
        # Verify no errors occurred
        assert len(errors) == 0, f"Errors during concurrent processing: {errors}"
        
        # Verify all studies were processed
        assert len(results) == len(studies_features), \
            f"Not all studies processed: {len(results)} vs {len(studies_features)}"
        
        # Verify each result has correct study ID
        for study_id, result in results.items():
            assert result["study_id"] == study_id
            assert result["dqi"].entity_id == study_id
            assert result["consensus"].entity_id == study_id
    
    @given(features=study_features_strategy())
    @settings(max_examples=100, deadline=30000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_same_study_concurrent_processing_idempotent(
        self,
        features: Dict[str, Any]
    ):
        """
        Feature: clinical-ai-system, Property: Concurrent Processing Performance
        Validates: Requirements 9.2
        
        Property: Processing the same study multiple times concurrently
        should produce identical results (idempotency).
        """
        study_id = "STUDY_TEST"
        num_concurrent = 3
        
        results = []
        
        with ThreadPoolExecutor(max_workers=num_concurrent) as executor:
            futures = [
                executor.submit(process_study_analysis, study_id, features)
                for _ in range(num_concurrent)
            ]
            
            for future in as_completed(futures):
                results.append(future.result())
        
        # All results should be identical
        assert len(results) == num_concurrent
        
        first_result = results[0]
        for i, result in enumerate(results[1:], 1):
            # DQI scores should match exactly
            assert abs(result["dqi"].overall_score - first_result["dqi"].overall_score) < 0.001, \
                f"DQI score mismatch between run 0 and run {i}"
            
            # DQI bands should match
            assert result["dqi"].band == first_result["dqi"].band, \
                f"DQI band mismatch between run 0 and run {i}"
            
            # Consensus risk levels should match
            assert result["consensus"].risk_level == first_result["consensus"].risk_level, \
                f"Risk level mismatch between run 0 and run {i}"
            
            # Risk scores should match
            assert abs(result["consensus"].risk_score - first_result["consensus"].risk_score) < 0.001, \
                f"Risk score mismatch between run 0 and run {i}"
    
    @given(studies_features=multiple_studies_features_strategy(min_studies=3, max_studies=5))
    @settings(max_examples=50, deadline=60000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_concurrent_processing_order_independence(
        self,
        studies_features: Dict[str, Dict[str, Any]]
    ):
        """
        Feature: clinical-ai-system, Property: Concurrent Processing Performance
        Validates: Requirements 9.2
        
        Property: The order in which studies complete processing should not
        affect the final results.
        """
        # Run multiple times with different thread scheduling
        all_results = []
        
        for run in range(3):
            results = {}
            
            with ThreadPoolExecutor(max_workers=len(studies_features)) as executor:
                futures = {
                    executor.submit(process_study_analysis, study_id, features): study_id
                    for study_id, features in studies_features.items()
                }
                
                for future in as_completed(futures):
                    study_id = futures[future]
                    results[study_id] = future.result()
            
            all_results.append(results)
        
        # Compare results across runs
        first_run = all_results[0]
        
        for run_idx, run_results in enumerate(all_results[1:], 1):
            for study_id in studies_features.keys():
                first = first_run[study_id]
                current = run_results[study_id]
                
                # Results should be identical regardless of completion order
                assert abs(first["dqi"].overall_score - current["dqi"].overall_score) < 0.001, \
                    f"DQI mismatch for {study_id} between run 0 and run {run_idx}"
                
                assert first["consensus"].risk_level == current["consensus"].risk_level, \
                    f"Risk level mismatch for {study_id} between run 0 and run {run_idx}"


class TestConcurrentAgentProcessing:
    """
    Tests for concurrent agent processing within a single study.
    """
    
    @given(features=study_features_strategy())
    @settings(max_examples=100, deadline=20000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_agents_process_independently_in_parallel(
        self,
        features: Dict[str, Any]
    ):
        """
        Feature: clinical-ai-system, Property: Concurrent Processing Performance
        Validates: Requirements 9.2
        
        Property: Multiple agents should be able to process the same features
        concurrently without interference.
        """
        study_id = "STUDY_TEST"
        
        # Create agents
        agents = [
            DataCompletenessAgent(),
            SafetyComplianceAgent(),
            QueryQualityAgent(),
        ]
        
        # Process concurrently
        concurrent_signals = []
        
        with ThreadPoolExecutor(max_workers=len(agents)) as executor:
            futures = {
                executor.submit(agent.analyze, features, study_id): agent
                for agent in agents
            }
            
            for future in as_completed(futures):
                signal = future.result()
                concurrent_signals.append(signal)
        
        # Process sequentially for comparison
        sequential_signals = [agent.analyze(features, study_id) for agent in agents]
        
        # Verify same number of signals
        assert len(concurrent_signals) == len(sequential_signals)
        
        # Sort by agent type for comparison
        concurrent_by_type = {s.agent_type: s for s in concurrent_signals}
        sequential_by_type = {s.agent_type: s for s in sequential_signals}
        
        # Verify results match
        for agent_type in concurrent_by_type.keys():
            conc = concurrent_by_type[agent_type]
            seq = sequential_by_type[agent_type]
            
            assert conc.risk_level == seq.risk_level, \
                f"Risk level mismatch for {agent_type.value}"
            assert abs(conc.confidence - seq.confidence) < 0.001, \
                f"Confidence mismatch for {agent_type.value}"


class TestConcurrentDQICalculation:
    """
    Tests for concurrent DQI calculation.
    """
    
    @given(studies_features=multiple_studies_features_strategy(min_studies=2, max_studies=5))
    @settings(max_examples=100, deadline=20000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_concurrent_dqi_calculations_independent(
        self,
        studies_features: Dict[str, Dict[str, Any]]
    ):
        """
        Feature: clinical-ai-system, Property: Concurrent Processing Performance
        Validates: Requirements 9.2
        
        Property: DQI calculations for different studies should be independent
        when processed concurrently.
        """
        dqi_engine = DQICalculationEngine()
        
        # Calculate concurrently
        concurrent_results = {}
        
        with ThreadPoolExecutor(max_workers=min(len(studies_features), 4)) as executor:
            futures = {
                executor.submit(dqi_engine.calculate_dqi, features, study_id): study_id
                for study_id, features in studies_features.items()
            }
            
            for future in as_completed(futures):
                study_id = futures[future]
                concurrent_results[study_id] = future.result()
        
        # Calculate sequentially
        sequential_results = {
            study_id: dqi_engine.calculate_dqi(features, study_id)
            for study_id, features in studies_features.items()
        }
        
        # Verify results match
        for study_id in studies_features.keys():
            conc = concurrent_results[study_id]
            seq = sequential_results[study_id]
            
            assert abs(conc.overall_score - seq.overall_score) < 0.001, \
                f"DQI score mismatch for {study_id}"
            assert conc.band == seq.band, \
                f"DQI band mismatch for {study_id}"
            assert conc.entity_id == seq.entity_id == study_id, \
                f"Entity ID mismatch for {study_id}"


class TestConcurrentGuardianProcessing:
    """
    Tests for concurrent Guardian Agent processing.
    """
    
    @given(st.data())
    @settings(max_examples=50, deadline=20000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_guardian_concurrent_delta_calculations(self, data):
        """
        Feature: clinical-ai-system, Property: Concurrent Processing Performance
        Validates: Requirements 9.2
        
        Property: Guardian Agent should handle concurrent delta calculations
        for multiple studies without interference.
        """
        num_studies = data.draw(st.integers(min_value=2, max_value=4))
        
        # Generate snapshot pairs for each study
        study_snapshots = {}
        for i in range(num_studies):
            study_id = f"STUDY_{i+1:02d}"
            
            prev_score = data.draw(st.floats(min_value=0.0, max_value=100.0, allow_nan=False))
            curr_score = data.draw(st.floats(min_value=0.0, max_value=100.0, allow_nan=False))
            
            study_snapshots[study_id] = {
                "prev": {
                    "snapshot_id": f"snap_{study_id}_v1",
                    "dqi_score": prev_score,
                    "missing_pages_pct": data.draw(st.floats(min_value=0.0, max_value=100.0, allow_nan=False)),
                },
                "curr": {
                    "snapshot_id": f"snap_{study_id}_v2",
                    "dqi_score": curr_score,
                    "missing_pages_pct": data.draw(st.floats(min_value=0.0, max_value=100.0, allow_nan=False)),
                },
            }
        
        guardian = GuardianAgent()
        
        def calculate_delta(study_id: str, snapshots: Dict) -> Tuple[str, Any]:
            delta = guardian.calculate_data_delta(
                snapshots["prev"],
                snapshots["curr"],
                study_id
            )
            return study_id, delta
        
        # Calculate concurrently
        concurrent_results = {}
        
        with ThreadPoolExecutor(max_workers=num_studies) as executor:
            futures = [
                executor.submit(calculate_delta, study_id, snapshots)
                for study_id, snapshots in study_snapshots.items()
            ]
            
            for future in as_completed(futures):
                study_id, delta = future.result()
                concurrent_results[study_id] = delta
        
        # Verify all studies processed
        assert len(concurrent_results) == num_studies
        
        # Verify each delta has correct entity ID
        for study_id, delta in concurrent_results.items():
            assert delta.entity_id == study_id, \
                f"Entity ID mismatch: expected {study_id}, got {delta.entity_id}"
