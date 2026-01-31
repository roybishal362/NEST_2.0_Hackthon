"""
EDC Quality Agent Tests
=======================
Unit tests for the EDC Quality Agent.
"""

import pytest
from src.agents.signal_agents.edc_quality_agent import EDCQualityAgent
from src.intelligence.base_agent import RiskSignal, AgentType


class TestEDCQualityAgent:
    """Test suite for EDC Quality Agent."""
    
    @pytest.fixture
    def agent(self):
        """Create an EDC quality agent instance for testing."""
        return EDCQualityAgent()
    
    def test_agent_initialization(self, agent):
        """Test that agent initializes correctly."""
        assert agent.agent_type == AgentType.OPERATIONS
        assert agent.min_confidence == 0.6
        assert agent.abstention_threshold == 0.5
    
    def test_low_risk_scenario(self, agent):
        """Test agent with good EDC quality metrics (low risk)."""
        features = {
            "form_completion_rate": 98.0,
            "data_entry_errors": 1,
            "missing_required_fields": 0,
        }
        
        signal = agent.analyze(features, "TEST_STUDY")
        
        assert signal.risk_level == RiskSignal.LOW
        assert signal.confidence > 0.6
        assert not signal.abstained
        assert len(signal.evidence) >= 0
    
    def test_medium_risk_scenario(self, agent):
        """Test agent with moderate EDC issues (medium risk)."""
        features = {
            "form_completion_rate": 92.0,
            "data_entry_errors": 3,
            "missing_required_fields": 7,
        }
        
        signal = agent.analyze(features, "TEST_STUDY")
        
        assert signal.risk_level == RiskSignal.MEDIUM
        assert signal.confidence > 0.6
        assert not signal.abstained
        assert len(signal.evidence) > 0
    
    def test_high_risk_scenario(self, agent):
        """Test agent with significant EDC problems (high risk)."""
        features = {
            "form_completion_rate": 85.0,
            "data_entry_errors": 8,
            "missing_required_fields": 15,
        }
        
        signal = agent.analyze(features, "TEST_STUDY")
        
        assert signal.risk_level == RiskSignal.HIGH
        assert signal.confidence > 0.6
        assert not signal.abstained
        assert len(signal.evidence) > 0
    
    def test_critical_risk_low_completion(self, agent):
        """Test agent with very low form completion (critical risk)."""
        features = {
            "form_completion_rate": 75.0,
            "data_entry_errors": 12,
            "missing_required_fields": 25,
        }
        
        signal = agent.analyze(features, "TEST_STUDY")
        
        assert signal.risk_level == RiskSignal.CRITICAL
        assert signal.confidence > 0.6
        assert not signal.abstained
        assert len(signal.evidence) > 0
    
    def test_critical_risk_many_errors(self, agent):
        """Test agent with many data entry errors (critical risk)."""
        features = {
            "form_completion_rate": 95.0,
            "data_entry_errors": 15,
            "missing_required_fields": 5,
        }
        
        signal = agent.analyze(features, "TEST_STUDY")
        
        assert signal.risk_level == RiskSignal.CRITICAL
        assert signal.confidence > 0.6
        assert not signal.abstained
    
    def test_abstention_missing_required_features(self, agent):
        """Test that agent abstains when required features are missing."""
        features = {
            "missing_required_fields": 5,
            # Missing: form_completion_rate, data_entry_errors
        }
        
        signal = agent.analyze(features, "TEST_STUDY")
        
        assert signal.abstained
        assert signal.abstention_reason is not None
    
    def test_optional_features_increase_confidence(self, agent):
        """Test that optional features increase confidence."""
        # With only required features
        features_minimal = {
            "form_completion_rate": 90.0,
            "data_entry_errors": 3,
        }
        
        signal_minimal = agent.analyze(features_minimal, "TEST_STUDY")
        
        # With optional features
        features_complete = {
            "form_completion_rate": 90.0,
            "data_entry_errors": 3,
            "missing_required_fields": 5,
            "edc_system_uptime": 99.5,
            "data_validation_failures": 2,
        }
        
        signal_complete = agent.analyze(features_complete, "TEST_STUDY")
        
        # Both should have high confidence, complete should be >= minimal
        assert signal_complete.confidence >= signal_minimal.confidence
        assert signal_complete.features_analyzed > signal_minimal.features_analyzed
    
    def test_recommendations_generated(self, agent):
        """Test that agent generates actionable recommendations."""
        features = {
            "form_completion_rate": 78.0,
            "data_entry_errors": 12,
            "missing_required_fields": 22,
        }
        
        signal = agent.analyze(features, "TEST_STUDY")
        
        assert len(signal.recommended_actions) > 0
        # Should have urgent recommendations for critical issues
        urgent_actions = [a for a in signal.recommended_actions if "URGENT" in a]
        assert len(urgent_actions) > 0
    
    def test_evidence_contains_feature_details(self, agent):
        """Test that evidence contains detailed feature information."""
        features = {
            "form_completion_rate": 88.0,
            "data_entry_errors": 6,
            "missing_required_fields": 8,
        }
        
        signal = agent.analyze(features, "TEST_STUDY")
        
        for evidence in signal.evidence:
            assert evidence.feature_name is not None
            assert evidence.feature_value is not None
            assert evidence.threshold is not None
            assert 0.0 <= evidence.severity <= 1.0
            assert evidence.description is not None
    
    def test_worst_case_risk_assessment(self, agent):
        """Test that agent uses worst-case risk assessment."""
        # One metric is critical, others are low
        features = {
            "form_completion_rate": 98.0,  # Low risk
            "data_entry_errors": 15,       # Critical risk
            "missing_required_fields": 2,  # Low risk
        }
        
        signal = agent.analyze(features, "TEST_STUDY")
        
        # Should be critical due to worst-case assessment
        assert signal.risk_level == RiskSignal.CRITICAL
    
    def test_system_uptime_evidence(self, agent):
        """Test that low system uptime is captured in evidence."""
        features = {
            "form_completion_rate": 95.0,
            "data_entry_errors": 2,
            "edc_system_uptime": 95.0,  # Below 99% threshold
        }
        
        signal = agent.analyze(features, "TEST_STUDY")
        
        # Check that system uptime is in evidence
        uptime_evidence = [e for e in signal.evidence if e.feature_name == "edc_system_uptime"]
        assert len(uptime_evidence) > 0
    
    def test_validation_failures_evidence(self, agent):
        """Test that validation failures are captured in evidence."""
        features = {
            "form_completion_rate": 95.0,
            "data_entry_errors": 2,
            "data_validation_failures": 15,
        }
        
        signal = agent.analyze(features, "TEST_STUDY")
        
        # Check that validation failures are in evidence
        validation_evidence = [e for e in signal.evidence if e.feature_name == "data_validation_failures"]
        assert len(validation_evidence) > 0
    
    def test_perfect_metrics_low_risk(self, agent):
        """Test that perfect metrics result in low risk."""
        features = {
            "form_completion_rate": 100.0,
            "data_entry_errors": 0,
            "missing_required_fields": 0,
        }
        
        signal = agent.analyze(features, "TEST_STUDY")
        
        assert signal.risk_level == RiskSignal.LOW
        assert signal.confidence > 0.6
        assert not signal.abstained


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
