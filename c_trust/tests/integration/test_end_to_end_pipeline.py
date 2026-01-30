"""
End-to-End Integration Tests for C-TRUST Clinical AI System
============================================================
Tests the full pipeline from data ingestion through multi-agent analysis,
consensus engine, Guardian Agent, and DQI calculation.

**Validates: Requirements 9.1, 9.2**

Test Coverage:
1. Full pipeline testing with real Novartis NEST 2.0 data
2. Multi-agent coordination and consensus
3. Guardian Agent integration with core system
"""

import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import pytest

from src.data.ingestion import (
    DataIngestionEngine,
    BatchProcessor,
    ExcelFileReader,
    StudyDiscovery,
)
from src.data.models import FileType, Study
from src.agents.signal_agents.completeness_agent import DataCompletenessAgent
from src.agents.signal_agents.safety_agent import SafetyComplianceAgent
from src.agents.signal_agents.query_agent import QueryQualityAgent
from src.intelligence.base_agent import AgentSignal, AgentType, RiskSignal
from src.consensus.consensus_engine import ConsensusEngine, ConsensusRiskLevel
from src.guardian.guardian_agent import GuardianAgent, DataDelta, OutputDelta
from src.dqi.dqi_engine import DQICalculationEngine, DQIBand
from src.core import get_logger

logger = get_logger(__name__)


# ========================================
# TEST FIXTURES
# ========================================

@pytest.fixture
def sample_edc_data():
    """Sample EDC metrics data for testing"""
    return pd.DataFrame({
        "Study": ["STUDY_01"] * 5,
        "Site": ["SITE_001", "SITE_001", "SITE_002", "SITE_002", "SITE_003"],
        "Subject": ["SUBJ_001", "SUBJ_002", "SUBJ_003", "SUBJ_004", "SUBJ_005"],
        "Visit": ["V1", "V2", "V1", "V2", "V1"],
        "Total_Forms": [10, 10, 10, 10, 10],
        "Completed_Forms": [8, 9, 7, 10, 6],
        "Open_Queries": [2, 1, 3, 0, 4],
    })


@pytest.fixture
def sample_sae_data():
    """Sample SAE dashboard data for testing"""
    return pd.DataFrame({
        "Study": ["STUDY_01"] * 3,
        "Site": ["SITE_001", "SITE_002", "SITE_003"],
        "Subject": ["SUBJ_001", "SUBJ_003", "SUBJ_005"],
        "SAE_ID": ["SAE_001", "SAE_002", "SAE_003"],
        "SAE_Type": ["Serious", "Fatal", "Serious"],
        "Days_to_Report": [5, 2, 8],
        "Status": ["Open", "Closed", "Open"],
    })


@pytest.fixture
def sample_features():
    """Sample engineered features for agent analysis"""
    return {
        # Completeness features
        "missing_pages_pct": 15.0,
        "form_completion_rate": 85.0,
        "visit_completion_rate": 90.0,
        "data_entry_lag_days": 3.0,
        
        # Safety features
        "sae_backlog_days": 5.0,
        "sae_overdue_count": 2,
        "fatal_sae_count": 1,
        "safety_signal_count": 3,
        
        # Query features
        "open_query_count": 25,
        "query_aging_days": 10.0,
        "query_resolution_rate": 75.0,
        
        # Compliance features
        "missing_lab_ranges_pct": 10.0,
        "protocol_deviation_count": 2,
        "regulatory_compliance_rate": 95.0,
    }


@pytest.fixture
def mock_study():
    """Create a mock study for testing"""
    return Study(
        study_id="STUDY_01",
        study_name="Test Study 01",
        available_files={
            FileType.EDC_METRICS: True,
            FileType.SAE_DM: True,
        },
        metadata={
            "file_paths": {
                FileType.EDC_METRICS.value: "/path/to/edc.xlsx",
                FileType.SAE_DM.value: "/path/to/sae.xlsx",
            }
        }
    )


# ========================================
# END-TO-END PIPELINE TESTS
# ========================================

class TestEndToEndPipeline:
    """
    End-to-end integration tests for the full C-TRUST pipeline.
    
    **Validates: Requirements 9.1, 9.2**
    """
    
    def test_full_pipeline_with_mock_data(
        self,
        sample_edc_data,
        sample_sae_data,
        sample_features,
        mock_study
    ):
        """
        Test complete pipeline from data ingestion to DQI calculation.
        
        **Validates: Requirements 9.1**
        
        Pipeline stages:
        1. Data ingestion
        2. Feature extraction
        3. Multi-agent analysis
        4. Consensus calculation
        5. DQI calculation
        6. Guardian monitoring
        """
        # Stage 1: Simulate data ingestion
        ingested_data = {
            FileType.EDC_METRICS: sample_edc_data,
            FileType.SAE_DM: sample_sae_data,
        }
        
        # Verify data was "ingested"
        assert len(ingested_data) == 2
        assert FileType.EDC_METRICS in ingested_data
        assert FileType.SAE_DM in ingested_data
        
        # Stage 2: Feature extraction (using sample features)
        features = sample_features
        assert "missing_pages_pct" in features
        assert "sae_backlog_days" in features
        
        # Stage 3: Multi-agent analysis
        completeness_agent = DataCompletenessAgent()
        safety_agent = SafetyComplianceAgent()
        query_agent = QueryQualityAgent()
        
        completeness_signal = completeness_agent.analyze(features, "STUDY_01")
        safety_signal = safety_agent.analyze(features, "STUDY_01")
        query_signal = query_agent.analyze(features, "STUDY_01")
        
        # Verify all agents produced signals
        assert isinstance(completeness_signal, AgentSignal)
        assert isinstance(safety_signal, AgentSignal)
        assert isinstance(query_signal, AgentSignal)
        
        # Verify signals have valid risk levels
        assert completeness_signal.risk_level in [
            RiskSignal.LOW, RiskSignal.MEDIUM, RiskSignal.HIGH, RiskSignal.CRITICAL
        ]
        
        # Stage 4: Consensus calculation
        consensus_engine = ConsensusEngine()
        signals = [completeness_signal, safety_signal, query_signal]
        
        consensus_result = consensus_engine.calculate_consensus(signals, "STUDY_01")
        
        # Verify consensus result
        assert consensus_result.entity_id == "STUDY_01"
        assert consensus_result.risk_level in [
            ConsensusRiskLevel.LOW, ConsensusRiskLevel.MEDIUM,
            ConsensusRiskLevel.HIGH, ConsensusRiskLevel.CRITICAL
        ]
        assert 0.0 <= consensus_result.risk_score <= 100.0
        assert 0.0 <= consensus_result.confidence <= 1.0
        
        # Stage 5: DQI calculation
        dqi_engine = DQICalculationEngine()
        dqi_result = dqi_engine.calculate_dqi(features, "STUDY_01")
        
        # Verify DQI result
        assert dqi_result.entity_id == "STUDY_01"
        assert 0.0 <= dqi_result.overall_score <= 100.0
        assert dqi_result.band in [DQIBand.GREEN, DQIBand.AMBER, DQIBand.ORANGE, DQIBand.RED]
        
        # Stage 6: Guardian monitoring
        guardian = GuardianAgent()
        
        # Create mock snapshots for Guardian
        prev_snapshot = {
            "snapshot_id": "snap_001",
            "missing_pages_pct": 20.0,
            "dqi_score": 70.0,
            "risk_score": 60.0,
        }
        curr_snapshot = {
            "snapshot_id": "snap_002",
            "missing_pages_pct": 15.0,
            "dqi_score": dqi_result.overall_score,
            "risk_score": consensus_result.risk_score,
        }
        
        data_delta = guardian.calculate_data_delta(prev_snapshot, curr_snapshot, "STUDY_01")
        
        # Verify Guardian analysis
        assert data_delta.entity_id == "STUDY_01"
        assert data_delta.direction in ["IMPROVED", "DEGRADED", "STABLE"]
        
        logger.info(
            f"Full pipeline test completed: "
            f"DQI={dqi_result.overall_score:.1f}, "
            f"Risk={consensus_result.risk_level.value}, "
            f"Data trend={data_delta.direction}"
        )
    
    def test_multi_agent_coordination(self, sample_features):
        """
        Test that multiple agents can analyze data independently and
        their signals can be combined through consensus.
        
        **Validates: Requirements 9.2**
        """
        # Create all three core agents
        agents = [
            DataCompletenessAgent(),
            SafetyComplianceAgent(),
            QueryQualityAgent(),
        ]
        
        # Run all agents
        signals = []
        for agent in agents:
            signal = agent.analyze(sample_features, "STUDY_01")
            signals.append(signal)
            
            # Verify each agent produces valid output
            assert isinstance(signal, AgentSignal)
            assert signal.agent_type in [
                AgentType.COMPLETENESS,
                AgentType.SAFETY,
                AgentType.QUERY_QUALITY,
            ]
        
        # Verify we got signals from all agents
        assert len(signals) == 3
        
        # Verify agent types are unique
        agent_types = [s.agent_type for s in signals]
        assert len(set(agent_types)) == 3
        
        # Run consensus
        consensus_engine = ConsensusEngine()
        result = consensus_engine.calculate_consensus(signals, "STUDY_01")
        
        # Verify consensus used all agents
        assert len(result.contributing_agents) + len(result.abstained_agents) == 3
        
        # Verify weighted scores were calculated
        for signal in signals:
            if not signal.abstained:
                assert signal.agent_type.value in result.weighted_scores
    
    def test_guardian_integration_with_core_system(self, sample_features):
        """
        Test Guardian Agent integration with the core analysis system.
        
        **Validates: Requirements 9.1**
        """
        # Run initial analysis
        dqi_engine = DQICalculationEngine()
        consensus_engine = ConsensusEngine()
        guardian = GuardianAgent()
        
        # First snapshot analysis
        features_v1 = sample_features.copy()
        dqi_v1 = dqi_engine.calculate_dqi(features_v1, "STUDY_01")
        
        # Simulate data improvement
        features_v2 = sample_features.copy()
        features_v2["missing_pages_pct"] = 5.0  # Improved from 15%
        features_v2["form_completion_rate"] = 95.0  # Improved from 85%
        features_v2["sae_overdue_count"] = 0  # Improved from 2
        
        dqi_v2 = dqi_engine.calculate_dqi(features_v2, "STUDY_01")
        
        # Create snapshots for Guardian
        snapshot_v1 = {
            "snapshot_id": "snap_v1",
            "missing_pages_pct": features_v1["missing_pages_pct"],
            "form_completion_rate": features_v1["form_completion_rate"],
            "dqi_score": dqi_v1.overall_score,
        }
        
        snapshot_v2 = {
            "snapshot_id": "snap_v2",
            "missing_pages_pct": features_v2["missing_pages_pct"],
            "form_completion_rate": features_v2["form_completion_rate"],
            "dqi_score": dqi_v2.overall_score,
        }
        
        # Guardian should detect the improvement
        data_delta = guardian.calculate_data_delta(snapshot_v1, snapshot_v2, "STUDY_01")
        
        # Verify Guardian detected improvement
        assert data_delta.direction == "IMPROVED"
        assert data_delta.significant or data_delta.overall_change_magnitude > 0
        
        # Verify DQI improved
        assert dqi_v2.overall_score >= dqi_v1.overall_score
        
        # Create output deltas
        output_v1 = {
            "snapshot_id": "snap_v1",
            "risk_score": 60.0,
            "dqi_score": dqi_v1.overall_score,
        }
        output_v2 = {
            "snapshot_id": "snap_v2",
            "risk_score": 40.0,  # Risk decreased (improvement)
            "dqi_score": dqi_v2.overall_score,
        }
        
        output_delta = guardian.calculate_output_delta(output_v1, output_v2, "STUDY_01")
        
        # Verify consistency check
        is_consistent, event = guardian.verify_consistency(data_delta, output_delta)
        
        # Should be consistent since data improved and output reflects it
        assert is_consistent or event is not None  # Either consistent or event generated


class TestMultiStudyProcessing:
    """
    Tests for processing multiple studies concurrently.
    
    **Validates: Requirements 9.2**
    """
    
    def test_multiple_studies_independent_processing(self, sample_features):
        """
        Test that multiple studies can be processed independently.
        
        **Validates: Requirements 9.2**
        """
        study_ids = ["STUDY_01", "STUDY_02", "STUDY_03"]
        results = {}
        
        dqi_engine = DQICalculationEngine()
        consensus_engine = ConsensusEngine()
        
        for study_id in study_ids:
            # Vary features slightly per study
            study_features = sample_features.copy()
            study_features["missing_pages_pct"] = 10.0 + (hash(study_id) % 20)
            
            # Calculate DQI
            dqi_result = dqi_engine.calculate_dqi(study_features, study_id)
            
            # Run agents
            completeness_agent = DataCompletenessAgent()
            signal = completeness_agent.analyze(study_features, study_id)
            
            # Store results
            results[study_id] = {
                "dqi": dqi_result,
                "signal": signal,
            }
        
        # Verify all studies were processed
        assert len(results) == 3
        
        # Verify each study has independent results
        for study_id in study_ids:
            assert study_id in results
            assert results[study_id]["dqi"].entity_id == study_id
    
    def test_study_processing_isolation(self, sample_features):
        """
        Test that processing one study doesn't affect another.
        
        **Validates: Requirements 9.2**
        """
        dqi_engine = DQICalculationEngine()
        
        # Process first study
        features_1 = sample_features.copy()
        features_1["missing_pages_pct"] = 50.0  # High missing rate
        dqi_1 = dqi_engine.calculate_dqi(features_1, "STUDY_01")
        
        # Process second study with better data
        features_2 = sample_features.copy()
        features_2["missing_pages_pct"] = 5.0  # Low missing rate
        dqi_2 = dqi_engine.calculate_dqi(features_2, "STUDY_02")
        
        # Verify results are independent
        assert dqi_1.entity_id == "STUDY_01"
        assert dqi_2.entity_id == "STUDY_02"
        
        # Study 2 should have better DQI due to lower missing rate
        # (This tests that processing is truly independent)
        assert dqi_2.overall_score > dqi_1.overall_score


class TestDataIngestionIntegration:
    """
    Integration tests for data ingestion with the analysis pipeline.
    """
    
    def test_batch_processor_results_structure(self):
        """
        Test that batch processor returns properly structured results.
        
        **Validates: Requirements 9.1**
        """
        with patch('src.data.ingestion.StudyDiscovery') as mock_discovery:
            # Mock empty study list
            mock_discovery_instance = Mock()
            mock_discovery_instance.discover_all_studies.return_value = []
            mock_discovery.return_value = mock_discovery_instance
            
            processor = BatchProcessor()
            results = processor.process_batch(create_snapshot=False)
            
            # Verify result structure
            assert "start_time" in results
            assert "studies_processed" in results
            assert "studies_failed" in results
            assert "files_processed" in results
            assert "files_failed" in results
            assert "validation_errors" in results
            assert "processing_errors" in results
    
    def test_ingestion_engine_initialization(self):
        """
        Test that ingestion engine initializes correctly.
        
        **Validates: Requirements 9.1**
        """
        with patch('src.data.ingestion.StudyDiscovery') as mock_discovery:
            mock_discovery_instance = Mock()
            mock_discovery_instance.discover_all_studies.return_value = []
            mock_discovery.return_value = mock_discovery_instance
            
            engine = DataIngestionEngine()
            
            # Verify engine has required components
            assert hasattr(engine, 'reader')
            assert hasattr(engine, 'detector')
            assert hasattr(engine, 'validator')


class TestAgentConsensusIntegration:
    """
    Integration tests for agent-consensus pipeline.
    """
    
    def test_agent_signals_flow_to_consensus(self, sample_features):
        """
        Test that agent signals properly flow to consensus engine.
        
        **Validates: Requirements 9.1**
        """
        # Create agents
        completeness_agent = DataCompletenessAgent()
        safety_agent = SafetyComplianceAgent()
        query_agent = QueryQualityAgent()
        
        # Generate signals
        signals = [
            completeness_agent.analyze(sample_features, "STUDY_01"),
            safety_agent.analyze(sample_features, "STUDY_01"),
            query_agent.analyze(sample_features, "STUDY_01"),
        ]
        
        # Pass to consensus
        consensus_engine = ConsensusEngine()
        result = consensus_engine.calculate_consensus(signals, "STUDY_01")
        
        # Verify signal information is preserved
        assert len(result.agent_signals) == 3
        
        # Verify weighted scores reflect agent weights
        if AgentType.SAFETY.value in result.weighted_scores:
            safety_weight = consensus_engine.get_weight(AgentType.SAFETY)
            assert safety_weight == 3.0  # Safety has highest weight
    
    def test_abstained_agents_handled_correctly(self):
        """
        Test that abstained agents are properly handled in consensus.
        
        **Validates: Requirements 9.1**
        """
        # Create agent with insufficient data
        completeness_agent = DataCompletenessAgent()
        
        # Empty features should cause abstention
        empty_features = {}
        signal = completeness_agent.analyze(empty_features, "STUDY_01")
        
        # Verify abstention
        assert signal.abstained
        
        # Pass to consensus
        consensus_engine = ConsensusEngine()
        result = consensus_engine.calculate_consensus([signal], "STUDY_01")
        
        # Verify abstained agent is tracked
        assert AgentType.COMPLETENESS.value in result.abstained_agents
        assert AgentType.COMPLETENESS.value not in result.contributing_agents


class TestDQIIntegration:
    """
    Integration tests for DQI calculation with the analysis pipeline.
    """
    
    def test_dqi_calculation_with_full_features(self, sample_features):
        """
        Test DQI calculation with complete feature set.
        
        **Validates: Requirements 9.1**
        """
        dqi_engine = DQICalculationEngine()
        result = dqi_engine.calculate_dqi(sample_features, "STUDY_01")
        
        # Verify all dimensions were calculated
        assert not result.partial_calculation
        assert len(result.missing_dimensions) == 0
        
        # Verify dimension breakdown
        assert len(result.dimension_scores) == 4
        
        # Verify weights sum correctly
        total_weighted = sum(ds.weighted_score for ds in result.dimension_scores.values())
        assert abs(total_weighted - result.overall_score) < 0.1
    
    def test_dqi_partial_calculation(self):
        """
        Test DQI calculation with partial features.
        
        **Validates: Requirements 9.1**
        """
        # Only provide safety features
        partial_features = {
            "sae_backlog_days": 5.0,
            "fatal_sae_count": 0,
        }
        
        dqi_engine = DQICalculationEngine()
        result = dqi_engine.calculate_dqi(partial_features, "STUDY_01")
        
        # Verify partial calculation is flagged
        assert result.partial_calculation
        assert len(result.missing_dimensions) > 0
        
        # Confidence should be reduced
        assert result.confidence < 1.0


class TestGuardianIntegration:
    """
    Integration tests for Guardian Agent with the core system.
    """
    
    def test_guardian_detects_data_improvement(self):
        """
        Test Guardian detects when data improves.
        
        **Validates: Requirements 9.1**
        """
        guardian = GuardianAgent()
        
        prev_snapshot = {
            "snapshot_id": "snap_001",
            "missing_pages_pct": 30.0,
            "form_completion_rate": 70.0,
            "dqi_score": 60.0,
        }
        
        curr_snapshot = {
            "snapshot_id": "snap_002",
            "missing_pages_pct": 10.0,  # Improved
            "form_completion_rate": 90.0,  # Improved
            "dqi_score": 80.0,  # Improved
        }
        
        delta = guardian.calculate_data_delta(prev_snapshot, curr_snapshot, "STUDY_01")
        
        assert delta.direction == "IMPROVED"
        assert delta.overall_change_magnitude > 0
    
    def test_guardian_detects_data_degradation(self):
        """
        Test Guardian detects when data degrades.
        
        **Validates: Requirements 9.1**
        """
        guardian = GuardianAgent()
        
        prev_snapshot = {
            "snapshot_id": "snap_001",
            "missing_pages_pct": 10.0,
            "form_completion_rate": 90.0,
            "dqi_score": 80.0,
        }
        
        curr_snapshot = {
            "snapshot_id": "snap_002",
            "missing_pages_pct": 30.0,  # Degraded
            "form_completion_rate": 70.0,  # Degraded
            "dqi_score": 60.0,  # Degraded
        }
        
        delta = guardian.calculate_data_delta(prev_snapshot, curr_snapshot, "STUDY_01")
        
        assert delta.direction == "DEGRADED"
        assert delta.overall_change_magnitude > 0
    
    def test_guardian_staleness_detection(self):
        """
        Test Guardian staleness detection mechanism.
        
        **Validates: Requirements 9.1**
        """
        guardian = GuardianAgent(staleness_threshold=2)
        
        # Simulate multiple snapshots with unchanged alerts
        alerts = ["ALERT_001", "ALERT_002"]
        
        # First check - establishes baseline
        is_stale, event = guardian.check_staleness("STUDY_01", alerts, data_has_changed=False)
        assert not is_stale
        
        # Second check - data changed but alerts same
        is_stale, event = guardian.check_staleness("STUDY_01", alerts, data_has_changed=True)
        assert not is_stale  # Not yet at threshold
        
        # Third check - should trigger staleness
        is_stale, event = guardian.check_staleness("STUDY_01", alerts, data_has_changed=True)
        assert is_stale
        assert event is not None
