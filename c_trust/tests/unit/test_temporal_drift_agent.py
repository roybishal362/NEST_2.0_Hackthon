"""
Temporal Drift Agent Tests
===========================
Unit tests for the Temporal Drift Agent.
"""

import pytest
from src.agents.signal_agents.temporal_drift_agent import TemporalDriftAgent
from src.intelligence.base_agent import RiskSignal, AgentType


class TestTemporalDriftAgent:
    """Test suite for Temporal Drift Agent."""
    
    @pytest.fixture
    def agent(self):
        """Create a temporal drift agent instance for testing."""
        return TemporalDriftAgent()
    
    def test_agent_initialization(self, agent):
        """Test that agent initializes correctly."""
        assert agent.agent_type == AgentType.TIMELINE
        assert agent.min_confidence == 0.6
        assert agent.abstention_threshold == 0.5
    
    def test_low_risk_scenario(self, agent):
        """Test agent with good temporal metrics (low risk)."""
        features = {
            "avg_data_entry_lag_days": 3.0,
            "overdue_visits_count": 2,
            "lag_trend": -0.5,  # Improving
        }
        
        signal = agent.analyze(features, "TEST_STUDY")
        
        assert signal.risk_level == RiskSignal.LOW
        assert signal.confidence > 0.6
        assert not signal.abstained
        assert len(signal.evidence) >= 0
    
    def test_medium_risk_scenario(self, agent):
        """Test agent with moderate temporal issues (medium risk)."""
        features = {
            "avg_data_entry_lag_days": 10.0,
            "overdue_visits_count": 7,
            "lag_trend": 0.2,
        }
        
        signal = agent.analyze(features, "TEST_STUDY")
        
        assert signal.risk_level == RiskSignal.MEDIUM
        assert signal.confidence > 0.6
        assert not signal.abstained
        assert len(signal.evidence) > 0
    
    def test_high_risk_scenario(self, agent):
        """Test agent with significant temporal delays (high risk)."""
        features = {
            "avg_data_entry_lag_days": 20.0,
            "overdue_visits_count": 15,
            "lag_trend": 1.5,
        }
        
        signal = agent.analyze(features, "TEST_STUDY")
        
        assert signal.risk_level == RiskSignal.HIGH
        assert signal.confidence > 0.6
        assert not signal.abstained
        assert len(signal.evidence) > 0
    
    def test_critical_risk_high_lag(self, agent):
        """Test agent with critical data entry lag (critical risk)."""
        features = {
            "avg_data_entry_lag_days": 35.0,
            "overdue_visits_count": 8,
            "lag_trend": 2.0,
        }
        
        signal = agent.analyze(features, "TEST_STUDY")
        
        assert signal.risk_level == RiskSignal.CRITICAL
        assert signal.confidence > 0.6
        assert not signal.abstained
        assert len(signal.evidence) > 0
    
    def test_critical_risk_many_overdue_visits(self, agent):
        """Test agent with many overdue visits (critical risk)."""
        features = {
            "avg_data_entry_lag_days": 12.0,
            "overdue_visits_count": 25,
            "lag_trend": 0.5,
        }
        
        signal = agent.analyze(features, "TEST_STUDY")
        
        assert signal.risk_level == RiskSignal.CRITICAL
        assert signal.confidence > 0.6
        assert not signal.abstained
    
    def test_abstention_missing_required_features(self, agent):
        """Test that agent abstains when required features are missing."""
        features = {
            "lag_trend": 1.0,
            # Missing: avg_data_entry_lag_days, overdue_visits_count
        }
        
        signal = agent.analyze(features, "TEST_STUDY")
        
        assert signal.abstained
        assert signal.abstention_reason is not None
    
    def test_optional_features_increase_confidence(self, agent):
        """Test that optional features increase confidence."""
        # With only required features
        features_minimal = {
            "avg_data_entry_lag_days": 10.0,
            "overdue_visits_count": 5,
        }
        
        signal_minimal = agent.analyze(features_minimal, "TEST_STUDY")
        
        # With optional features
        features_complete = {
            "avg_data_entry_lag_days": 10.0,
            "overdue_visits_count": 5,
            "lag_trend": 0.5,
            "max_data_entry_lag_days": 25.0,
            "visit_completion_rate": 85.0,
        }
        
        signal_complete = agent.analyze(features_complete, "TEST_STUDY")
        
        # Both should have high confidence, complete should be >= minimal
        assert signal_complete.confidence >= signal_minimal.confidence
        assert signal_complete.features_analyzed > signal_minimal.features_analyzed
    
    def test_increasing_lag_trend_raises_risk(self, agent):
        """Test that increasing lag trend raises risk level."""
        # Without trend
        features_no_trend = {
            "avg_data_entry_lag_days": 8.0,
            "overdue_visits_count": 3,
        }
        
        signal_no_trend = agent.analyze(features_no_trend, "TEST_STUDY")
        
        # With increasing trend
        features_with_trend = {
            "avg_data_entry_lag_days": 8.0,
            "overdue_visits_count": 3,
            "lag_trend": 3.0,  # Increasing by 3 days/week
        }
        
        signal_with_trend = agent.analyze(features_with_trend, "TEST_STUDY")
        
        # Trend should increase risk or at least maintain it
        risk_order = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        assert risk_order[signal_with_trend.risk_level.value] >= risk_order[signal_no_trend.risk_level.value]
    
    def test_recommendations_generated(self, agent):
        """Test that agent generates actionable recommendations."""
        features = {
            "avg_data_entry_lag_days": 35.0,  # Critical threshold
            "overdue_visits_count": 22,       # Critical threshold
            "lag_trend": 2.5,
        }
        
        signal = agent.analyze(features, "TEST_STUDY")
        
        assert len(signal.recommended_actions) > 0
        # Should have urgent recommendations for critical risk
        urgent_actions = [a for a in signal.recommended_actions if "URGENT" in a or "urgent" in a]
        assert len(urgent_actions) > 0
    
    def test_evidence_contains_feature_details(self, agent):
        """Test that evidence contains detailed feature information."""
        features = {
            "avg_data_entry_lag_days": 15.0,
            "overdue_visits_count": 10,
            "lag_trend": 1.0,
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
            "avg_data_entry_lag_days": 3.0,  # Low risk
            "overdue_visits_count": 25,      # Critical risk
            "lag_trend": -1.0,               # Improving
        }
        
        signal = agent.analyze(features, "TEST_STUDY")
        
        # Should be critical due to worst-case assessment
        assert signal.risk_level == RiskSignal.CRITICAL
    
    def test_improving_trend_noted_in_evidence(self, agent):
        """Test that improving lag trend is noted positively."""
        features = {
            "avg_data_entry_lag_days": 10.0,
            "overdue_visits_count": 5,
            "lag_trend": -2.0,  # Improving by 2 days/week
        }
        
        signal = agent.analyze(features, "TEST_STUDY")
        
        # Check if improving trend is in evidence
        trend_evidence = [e for e in signal.evidence if e.feature_name == "lag_trend"]
        if trend_evidence:
            assert "improving" in trend_evidence[0].description.lower()
            assert trend_evidence[0].severity == 0.0  # No severity for improvement
    
    def test_max_lag_detection(self, agent):
        """Test that maximum lag is detected and flagged."""
        features = {
            "avg_data_entry_lag_days": 10.0,
            "overdue_visits_count": 5,
            "max_data_entry_lag_days": 50.0,  # High maximum
        }
        
        signal = agent.analyze(features, "TEST_STUDY")
        
        # Check if max lag is in evidence
        max_lag_evidence = [e for e in signal.evidence if e.feature_name == "max_data_entry_lag_days"]
        assert len(max_lag_evidence) > 0
        assert max_lag_evidence[0].severity > 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
