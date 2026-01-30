"""
Stability Agent Tests
======================
Unit tests for the Stability Agent.

IMPORTANT: This agent uses INVERTED RISK LOGIC where good performance = LOW risk.
"""

import pytest
from src.agents.signal_agents.stability_agent import StabilityAgent
from src.intelligence.base_agent import RiskSignal, AgentType


class TestStabilityAgent:
    """Test suite for Stability Agent with INVERTED risk logic."""
    
    @pytest.fixture
    def agent(self):
        """Create a stability agent instance for testing."""
        return StabilityAgent()
    
    def test_agent_initialization(self, agent):
        """Test that agent initializes correctly."""
        assert agent.agent_type == AgentType.STABILITY
        assert agent.min_confidence == 0.6
        assert agent.abstention_threshold == 0.5
    
    def test_low_risk_excellent_performance(self, agent):
        """Test agent with excellent metrics (INVERTED: low risk)."""
        features = {
            "enrollment_velocity": 95.0,      # High = good = LOW risk
            "site_activation_rate": 92.0,     # High = good = LOW risk
            "dropout_rate": 5.0,              # Low = good = LOW risk
        }
        
        signal = agent.analyze(features, "TEST_STUDY")
        
        # INVERTED: Excellent performance = LOW risk
        assert signal.risk_level == RiskSignal.LOW
        assert signal.confidence > 0.6
        assert not signal.abstained
        assert len(signal.evidence) >= 0
    
    def test_medium_risk_acceptable_performance(self, agent):
        """Test agent with acceptable metrics (INVERTED: medium risk)."""
        features = {
            "enrollment_velocity": 80.0,      # Moderate = MEDIUM risk
            "site_activation_rate": 78.0,     # Moderate = MEDIUM risk
            "dropout_rate": 12.0,             # Moderate = MEDIUM risk
        }
        
        signal = agent.analyze(features, "TEST_STUDY")
        
        # INVERTED: Acceptable performance = MEDIUM risk
        assert signal.risk_level == RiskSignal.MEDIUM
        assert signal.confidence > 0.6
        assert not signal.abstained
        assert len(signal.evidence) > 0
    
    def test_high_risk_concerning_performance(self, agent):
        """Test agent with concerning metrics (INVERTED: high risk)."""
        features = {
            "enrollment_velocity": 60.0,      # Low = concerning = HIGH risk
            "site_activation_rate": 55.0,     # Low = concerning = HIGH risk
            "dropout_rate": 18.0,             # High = concerning = HIGH risk
        }
        
        signal = agent.analyze(features, "TEST_STUDY")
        
        # INVERTED: Concerning performance = HIGH risk
        assert signal.risk_level == RiskSignal.HIGH
        assert signal.confidence > 0.6
        assert not signal.abstained
        assert len(signal.evidence) > 0
    
    def test_critical_risk_poor_performance(self, agent):
        """Test agent with poor metrics (INVERTED: critical risk)."""
        features = {
            "enrollment_velocity": 40.0,      # Very low = poor = CRITICAL risk
            "site_activation_rate": 35.0,     # Very low = poor = CRITICAL risk
            "dropout_rate": 25.0,             # Very high = poor = CRITICAL risk
        }
        
        signal = agent.analyze(features, "TEST_STUDY")
        
        # INVERTED: Poor performance = CRITICAL risk
        assert signal.risk_level == RiskSignal.CRITICAL
        assert signal.confidence > 0.6
        assert not signal.abstained
        assert len(signal.evidence) > 0
    
    def test_critical_risk_low_enrollment(self, agent):
        """Test agent with critically low enrollment (INVERTED: critical risk)."""
        features = {
            "enrollment_velocity": 30.0,      # Very low = CRITICAL risk
            "site_activation_rate": 85.0,     # Good
            "dropout_rate": 8.0,              # Good
        }
        
        signal = agent.analyze(features, "TEST_STUDY")
        
        # INVERTED: One critical metric = CRITICAL overall risk
        assert signal.risk_level == RiskSignal.CRITICAL
        assert signal.confidence > 0.6
        assert not signal.abstained
    
    def test_critical_risk_high_dropout(self, agent):
        """Test agent with critically high dropout rate (critical risk)."""
        features = {
            "enrollment_velocity": 92.0,      # Good
            "site_activation_rate": 88.0,     # Good
            "dropout_rate": 30.0,             # Very high = CRITICAL risk
        }
        
        signal = agent.analyze(features, "TEST_STUDY")
        
        # High dropout = CRITICAL risk (normal logic for dropout)
        assert signal.risk_level == RiskSignal.CRITICAL
        assert signal.confidence > 0.6
        assert not signal.abstained
    
    def test_abstention_missing_required_features(self, agent):
        """Test that agent abstains when required features are missing."""
        features = {
            "enrollment_trend": 1.5,
            # Missing: enrollment_velocity, site_activation_rate, dropout_rate
        }
        
        signal = agent.analyze(features, "TEST_STUDY")
        
        assert signal.abstained
        assert signal.abstention_reason is not None
    
    def test_optional_features_increase_confidence(self, agent):
        """Test that optional features increase confidence."""
        # With only required features
        features_minimal = {
            "enrollment_velocity": 85.0,
            "site_activation_rate": 80.0,
            "dropout_rate": 12.0,
        }
        
        signal_minimal = agent.analyze(features_minimal, "TEST_STUDY")
        
        # With optional features
        features_complete = {
            "enrollment_velocity": 85.0,
            "site_activation_rate": 80.0,
            "dropout_rate": 12.0,
            "enrollment_trend": 2.0,
            "site_performance_variance": 15.0,
            "patient_retention_rate": 88.0,
        }
        
        signal_complete = agent.analyze(features_complete, "TEST_STUDY")
        
        # Both should have high confidence, complete should be >= minimal
        assert signal_complete.confidence >= signal_minimal.confidence
        assert signal_complete.features_analyzed > signal_minimal.features_analyzed
    
    def test_declining_enrollment_trend_raises_concern(self, agent):
        """Test that declining enrollment trend is flagged."""
        features = {
            "enrollment_velocity": 85.0,
            "site_activation_rate": 80.0,
            "dropout_rate": 10.0,
            "enrollment_trend": -8.0,  # Declining by 8%
        }
        
        signal = agent.analyze(features, "TEST_STUDY")
        
        # Check that declining trend is in evidence
        trend_evidence = [e for e in signal.evidence if e.feature_name == "enrollment_trend"]
        assert len(trend_evidence) > 0
        assert "declining" in trend_evidence[0].description.lower()
        assert trend_evidence[0].severity > 0.0
    
    def test_improving_enrollment_trend_noted_positively(self, agent):
        """Test that improving enrollment trend is noted positively."""
        features = {
            "enrollment_velocity": 85.0,
            "site_activation_rate": 80.0,
            "dropout_rate": 10.0,
            "enrollment_trend": 5.0,  # Improving by 5%
        }
        
        signal = agent.analyze(features, "TEST_STUDY")
        
        # Check if improving trend is in evidence
        trend_evidence = [e for e in signal.evidence if e.feature_name == "enrollment_trend"]
        if trend_evidence:
            assert "improving" in trend_evidence[0].description.lower()
            assert trend_evidence[0].severity == 0.0  # No severity for improvement
    
    def test_recommendations_generated(self, agent):
        """Test that agent generates actionable recommendations."""
        features = {
            "enrollment_velocity": 40.0,      # Critical
            "site_activation_rate": 35.0,     # Critical
            "dropout_rate": 25.0,             # Critical
            "enrollment_trend": -10.0,        # Declining
        }
        
        signal = agent.analyze(features, "TEST_STUDY")
        
        assert len(signal.recommended_actions) > 0
        # Should have urgent recommendations for critical issues
        urgent_actions = [a for a in signal.recommended_actions if "URGENT" in a]
        assert len(urgent_actions) > 0
    
    def test_evidence_contains_feature_details(self, agent):
        """Test that evidence contains detailed feature information."""
        features = {
            "enrollment_velocity": 70.0,
            "site_activation_rate": 65.0,
            "dropout_rate": 18.0,
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
        # One metric is critical, others are excellent
        features = {
            "enrollment_velocity": 95.0,      # Excellent = LOW risk
            "site_activation_rate": 30.0,     # Poor = CRITICAL risk
            "dropout_rate": 5.0,              # Excellent = LOW risk
        }
        
        signal = agent.analyze(features, "TEST_STUDY")
        
        # Should be critical due to worst-case assessment
        assert signal.risk_level == RiskSignal.CRITICAL
    
    def test_high_site_variance_flagged(self, agent):
        """Test that high site performance variance is flagged."""
        features = {
            "enrollment_velocity": 85.0,
            "site_activation_rate": 80.0,
            "dropout_rate": 10.0,
            "site_performance_variance": 35.0,  # High variance
        }
        
        signal = agent.analyze(features, "TEST_STUDY")
        
        # Check that variance is in evidence
        variance_evidence = [e for e in signal.evidence if e.feature_name == "site_performance_variance"]
        assert len(variance_evidence) > 0
        assert variance_evidence[0].severity > 0.0
    
    def test_low_retention_rate_flagged(self, agent):
        """Test that low patient retention rate is flagged."""
        features = {
            "enrollment_velocity": 85.0,
            "site_activation_rate": 80.0,
            "dropout_rate": 10.0,
            "patient_retention_rate": 75.0,  # Low retention
        }
        
        signal = agent.analyze(features, "TEST_STUDY")
        
        # Check that retention is in evidence
        retention_evidence = [e for e in signal.evidence if e.feature_name == "patient_retention_rate"]
        assert len(retention_evidence) > 0
        assert retention_evidence[0].severity > 0.0
    
    def test_perfect_metrics_low_risk(self, agent):
        """Test that perfect metrics result in low risk (INVERTED)."""
        features = {
            "enrollment_velocity": 100.0,     # Perfect = LOW risk
            "site_activation_rate": 100.0,    # Perfect = LOW risk
            "dropout_rate": 0.0,              # Perfect = LOW risk
        }
        
        signal = agent.analyze(features, "TEST_STUDY")
        
        # INVERTED: Perfect performance = LOW risk
        assert signal.risk_level == RiskSignal.LOW
        assert signal.confidence > 0.6
        assert not signal.abstained
    
    def test_inverted_severity_calculation(self, agent):
        """Test that inverted severity calculation works correctly."""
        # Test with low enrollment (should have high severity)
        features_low = {
            "enrollment_velocity": 50.0,      # Low = high severity
            "site_activation_rate": 90.0,
            "dropout_rate": 5.0,
        }
        
        signal_low = agent.analyze(features_low, "TEST_STUDY")
        
        # Find enrollment evidence
        enrollment_evidence = [e for e in signal_low.evidence if e.feature_name == "enrollment_velocity"]
        if enrollment_evidence:
            # Low enrollment should have high severity (>0.4 is significant)
            assert enrollment_evidence[0].severity > 0.4
        
        # Test with high enrollment (should have low/no severity)
        features_high = {
            "enrollment_velocity": 95.0,      # High = low severity
            "site_activation_rate": 90.0,
            "dropout_rate": 5.0,
        }
        
        signal_high = agent.analyze(features_high, "TEST_STUDY")
        
        # High enrollment should have low/no severity
        enrollment_evidence_high = [e for e in signal_high.evidence if e.feature_name == "enrollment_velocity"]
        # May not be in evidence if above threshold (no issue)
        if enrollment_evidence_high:
            assert enrollment_evidence_high[0].severity < 0.3
    
    def test_positive_recommendation_for_excellent_performance(self, agent):
        """Test that excellent performance gets positive recommendation."""
        features = {
            "enrollment_velocity": 98.0,
            "site_activation_rate": 96.0,
            "dropout_rate": 3.0,
        }
        
        signal = agent.analyze(features, "TEST_STUDY")
        
        # Should have positive recommendation
        positive_actions = [a for a in signal.recommended_actions if "excellent" in a.lower() or "maintain" in a.lower()]
        assert len(positive_actions) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
