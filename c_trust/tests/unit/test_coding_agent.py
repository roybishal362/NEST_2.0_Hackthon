"""
Coding Readiness Agent Tests
=============================
Unit tests for the Coding Readiness Agent.
"""

import pytest
from src.agents.signal_agents.coding_agent import CodingReadinessAgent
from src.intelligence.base_agent import RiskSignal, AgentType


class TestCodingReadinessAgent:
    """Test suite for Coding Readiness Agent."""
    
    @pytest.fixture
    def agent(self):
        """Create a coding agent instance for testing."""
        return CodingReadinessAgent()
    
    def test_agent_initialization(self, agent):
        """Test that agent initializes correctly."""
        assert agent.agent_type == AgentType.CODING
        assert agent.min_confidence == 0.6
        assert agent.abstention_threshold == 0.5
    
    def test_low_risk_scenario(self, agent):
        """Test agent with good coding metrics (low risk)."""
        features = {
            "coding_completion_rate": 98.0,
            "coding_backlog_days": 3.0,
            "uncoded_sae_count": 0,
        }
        
        signal = agent.analyze(features, "TEST_STUDY")
        
        assert signal.risk_level == RiskSignal.LOW
        assert signal.confidence > 0.6
        assert not signal.abstained
        assert len(signal.evidence) >= 0
    
    def test_medium_risk_scenario(self, agent):
        """Test agent with moderate coding issues (medium risk)."""
        features = {
            "coding_completion_rate": 92.0,
            "coding_backlog_days": 10.0,
            "uncoded_sae_count": 0,
        }
        
        signal = agent.analyze(features, "TEST_STUDY")
        
        assert signal.risk_level == RiskSignal.MEDIUM
        assert signal.confidence > 0.6
        assert not signal.abstained
        assert len(signal.evidence) > 0
    
    def test_high_risk_scenario(self, agent):
        """Test agent with significant coding delays (high risk)."""
        features = {
            "coding_completion_rate": 80.0,
            "coding_backlog_days": 20.0,
            "uncoded_sae_count": 0,
        }
        
        signal = agent.analyze(features, "TEST_STUDY")
        
        assert signal.risk_level == RiskSignal.HIGH
        assert signal.confidence > 0.6
        assert not signal.abstained
        assert len(signal.evidence) > 0
    
    def test_critical_risk_uncoded_sae(self, agent):
        """Test agent with uncoded SAEs (critical risk)."""
        features = {
            "coding_completion_rate": 95.0,
            "coding_backlog_days": 5.0,
            "uncoded_sae_count": 2,  # Any uncoded SAE is critical
        }
        
        signal = agent.analyze(features, "TEST_STUDY")
        
        assert signal.risk_level == RiskSignal.CRITICAL
        assert signal.confidence > 0.6
        assert not signal.abstained
        assert len(signal.evidence) > 0
        # Check that uncoded SAE is in evidence
        sae_evidence = [e for e in signal.evidence if e.feature_name == "uncoded_sae_count"]
        assert len(sae_evidence) > 0
        assert sae_evidence[0].severity == 1.0  # Maximum severity
    
    def test_critical_risk_low_completion(self, agent):
        """Test agent with very low completion rate (critical risk)."""
        features = {
            "coding_completion_rate": 65.0,
            "coding_backlog_days": 35.0,
            "uncoded_sae_count": 0,
        }
        
        signal = agent.analyze(features, "TEST_STUDY")
        
        assert signal.risk_level == RiskSignal.CRITICAL
        assert signal.confidence > 0.6
        assert not signal.abstained
    
    def test_abstention_missing_required_features(self, agent):
        """Test that agent abstains when required features are missing."""
        features = {
            "uncoded_sae_count": 0,
            # Missing: coding_completion_rate, coding_backlog_days
        }
        
        signal = agent.analyze(features, "TEST_STUDY")
        
        assert signal.abstained
        assert signal.abstention_reason is not None
    
    def test_optional_features_increase_confidence(self, agent):
        """Test that optional features increase confidence."""
        # With only required features
        features_minimal = {
            "coding_completion_rate": 90.0,
            "coding_backlog_days": 10.0,
        }
        
        signal_minimal = agent.analyze(features_minimal, "TEST_STUDY")
        
        # With optional features
        features_complete = {
            "coding_completion_rate": 90.0,
            "coding_backlog_days": 10.0,
            "uncoded_sae_count": 0,
            "coding_velocity": 1.2,
            "pending_queries_coding": 5,
        }
        
        signal_complete = agent.analyze(features_complete, "TEST_STUDY")
        
        # Both should have high confidence, complete should be >= minimal
        assert signal_complete.confidence >= signal_minimal.confidence
        assert signal_complete.features_analyzed > signal_minimal.features_analyzed
    
    def test_recommendations_generated(self, agent):
        """Test that agent generates actionable recommendations."""
        features = {
            "coding_completion_rate": 75.0,
            "coding_backlog_days": 25.0,
            "uncoded_sae_count": 1,
        }
        
        signal = agent.analyze(features, "TEST_STUDY")
        
        assert len(signal.recommended_actions) > 0
        # Should have urgent recommendation for uncoded SAE
        urgent_actions = [a for a in signal.recommended_actions if "CRITICAL" in a or "URGENT" in a]
        assert len(urgent_actions) > 0
    
    def test_evidence_contains_feature_details(self, agent):
        """Test that evidence contains detailed feature information."""
        features = {
            "coding_completion_rate": 85.0,
            "coding_backlog_days": 15.0,
            "uncoded_sae_count": 0,
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
            "coding_completion_rate": 98.0,  # Low risk
            "coding_backlog_days": 35.0,     # Critical risk
            "uncoded_sae_count": 0,
        }
        
        signal = agent.analyze(features, "TEST_STUDY")
        
        # Should be critical due to worst-case assessment
        assert signal.risk_level == RiskSignal.CRITICAL


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
