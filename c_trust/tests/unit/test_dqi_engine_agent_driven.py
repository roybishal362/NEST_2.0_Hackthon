"""
Unit Tests for Agent-Driven DQI Engine
======================================
Tests the agent-driven DQI calculation logic.

Test Coverage:
- Dimension score calculation
- Consensus modifier application
- Confidence calculation
- Band classification
- Null handling (missing agents)
- Edge cases (all agents abstain, zero confidence)
"""

import pytest
from datetime import datetime

from src.intelligence.base_agent import AgentSignal, AgentType, RiskSignal
from src.intelligence.consensus import ConsensusDecision, ConsensusRiskLevel, AgentContribution, RecommendedAction
from src.intelligence.dqi_engine_agent_driven import (
    DQIDimension,
    DQIBand,
    DimensionScore,
    DQIResult,
    calculate_dqi_from_agents,
    risk_signal_to_score,
    calculate_dimension_score,
    calculate_consensus_modifier,
    calculate_overall_confidence,
    classify_dqi_band,
)


# ========================================
# FIXTURES
# ========================================

@pytest.fixture
def sample_agent_signals():
    """Create sample agent signals for testing"""
    return [
        AgentSignal(
            agent_type=AgentType.SAFETY,
            risk_level=RiskSignal.LOW,
            confidence=0.9,
            abstained=False
        ),
        AgentSignal(
            agent_type=AgentType.COMPLETENESS,
            risk_level=RiskSignal.MEDIUM,
            confidence=0.85,
            abstained=False
        ),
        AgentSignal(
            agent_type=AgentType.CODING,
            risk_level=RiskSignal.LOW,
            confidence=0.88,
            abstained=False
        ),
        AgentSignal(
            agent_type=AgentType.QUERY_QUALITY,
            risk_level=RiskSignal.MEDIUM,
            confidence=0.82,
            abstained=False
        ),
        AgentSignal(
            agent_type=AgentType.TEMPORAL_DRIFT,
            risk_level=RiskSignal.LOW,
            confidence=0.90,
            abstained=False
        ),
        AgentSignal(
            agent_type=AgentType.OPERATIONS,
            risk_level=RiskSignal.LOW,
            confidence=0.87,
            abstained=False
        ),
        AgentSignal(
            agent_type=AgentType.STABILITY,
            risk_level=RiskSignal.LOW,
            confidence=0.91,
            abstained=False
        ),
    ]


@pytest.fixture
def high_risk_agent_signals():
    """Create high-risk agent signals for testing"""
    return [
        AgentSignal(
            agent_type=AgentType.SAFETY,
            risk_level=RiskSignal.HIGH,
            confidence=0.9,
            abstained=False
        ),
        AgentSignal(
            agent_type=AgentType.COMPLETENESS,
            risk_level=RiskSignal.HIGH,
            confidence=0.85,
            abstained=False
        ),
        AgentSignal(
            agent_type=AgentType.CODING,
            risk_level=RiskSignal.CRITICAL,
            confidence=0.88,
            abstained=False
        ),
    ]


@pytest.fixture
def sample_consensus():
    """Create sample consensus decision"""
    return ConsensusDecision(
        risk_level=ConsensusRiskLevel.LOW,
        confidence=0.88,
        risk_score=30.0,
        contributing_agents=[],
        recommended_action=RecommendedAction.ROUTINE_MONITORING,
        explanation="Low risk consensus"
    )


@pytest.fixture
def high_risk_consensus():
    """Create high-risk consensus decision"""
    return ConsensusDecision(
        risk_level=ConsensusRiskLevel.HIGH,
        confidence=0.90,
        risk_score=75.0,
        contributing_agents=[],
        recommended_action=RecommendedAction.IMMEDIATE_ESCALATION,
        explanation="High risk consensus"
    )


# ========================================
# TEST: Risk Signal to Score Conversion
# ========================================

def test_risk_signal_to_score_critical():
    """Test that CRITICAL risk produces low DQI score"""
    score = risk_signal_to_score(RiskSignal.CRITICAL)
    assert score == 20.0, "CRITICAL risk should produce score of 20"


def test_risk_signal_to_score_high():
    """Test that HIGH risk produces low DQI score"""
    score = risk_signal_to_score(RiskSignal.HIGH)
    assert score == 40.0, "HIGH risk should produce score of 40"


def test_risk_signal_to_score_medium():
    """Test that MEDIUM risk produces moderate DQI score"""
    score = risk_signal_to_score(RiskSignal.MEDIUM)
    assert score == 70.0, "MEDIUM risk should produce score of 70"


def test_risk_signal_to_score_low():
    """Test that LOW risk produces high DQI score"""
    score = risk_signal_to_score(RiskSignal.LOW)
    assert score == 90.0, "LOW risk should produce score of 90"


def test_risk_signal_to_score_unknown():
    """Test that UNKNOWN risk produces neutral DQI score"""
    score = risk_signal_to_score(RiskSignal.UNKNOWN)
    assert score == 50.0, "UNKNOWN risk should produce score of 50"


# ========================================
# TEST: Dimension Score Calculation
# ========================================

def test_calculate_dimension_score_single_agent(sample_agent_signals):
    """Test dimension score calculation with single contributing agent"""
    # Safety dimension has only Safety Agent
    dim_score = calculate_dimension_score(DQIDimension.SAFETY, sample_agent_signals)
    
    assert dim_score is not None
    assert dim_score.dimension == DQIDimension.SAFETY
    assert dim_score.score == 90.0  # LOW risk → 90 score
    assert dim_score.confidence == 0.9
    assert AgentType.SAFETY in dim_score.contributing_agents


def test_calculate_dimension_score_multiple_agents(sample_agent_signals):
    """Test dimension score calculation with multiple contributing agents"""
    # Timeliness dimension has Query Quality + Temporal Drift agents
    dim_score = calculate_dimension_score(DQIDimension.TIMELINESS, sample_agent_signals)
    
    assert dim_score is not None
    assert dim_score.dimension == DQIDimension.TIMELINESS
    # Both agents have MEDIUM (70) and LOW (90) risk
    # Weighted average should be between 70 and 90
    assert 70 <= dim_score.score <= 90
    assert len(dim_score.contributing_agents) == 2


def test_calculate_dimension_score_no_agents():
    """Test dimension score calculation with no contributing agents"""
    # Create signals that don't map to ACCURACY dimension
    signals = [
        AgentSignal(
            agent_type=AgentType.SAFETY,
            risk_level=RiskSignal.LOW,
            confidence=0.9,
            abstained=False
        )
    ]
    
    # ACCURACY dimension should have no score (no Coding Agent)
    dim_score = calculate_dimension_score(DQIDimension.ACCURACY, signals)
    assert dim_score is None


def test_calculate_dimension_score_abstained_agents():
    """Test that abstained agents don't contribute to dimension scores"""
    signals = [
        AgentSignal(
            agent_type=AgentType.SAFETY,
            risk_level=RiskSignal.UNKNOWN,
            confidence=0.0,
            abstained=True,
            abstention_reason="Missing features"
        ),
        AgentSignal(
            agent_type=AgentType.COMPLETENESS,
            risk_level=RiskSignal.LOW,
            confidence=0.9,
            abstained=False
        )
    ]
    
    # Safety dimension should have no score (Safety Agent abstained)
    dim_score = calculate_dimension_score(DQIDimension.SAFETY, signals)
    assert dim_score is None
    
    # Completeness dimension should have score (Completeness Agent active)
    dim_score = calculate_dimension_score(DQIDimension.COMPLETENESS, signals)
    assert dim_score is not None
    assert dim_score.score == 90.0


# ========================================
# TEST: Consensus Modifier
# ========================================

def test_consensus_modifier_critical():
    """Test consensus modifier for CRITICAL risk"""
    consensus = ConsensusDecision(
        risk_level=ConsensusRiskLevel.CRITICAL,
        confidence=1.0,
        risk_score=95.0,
        contributing_agents=[],
        recommended_action=RecommendedAction.IMMEDIATE_ESCALATION,
        explanation="Critical"
    )
    
    modifier = calculate_consensus_modifier(consensus)
    assert modifier == -20.0, "CRITICAL consensus should produce -20 modifier"


def test_consensus_modifier_high():
    """Test consensus modifier for HIGH risk"""
    consensus = ConsensusDecision(
        risk_level=ConsensusRiskLevel.HIGH,
        confidence=1.0,
        risk_score=75.0,
        contributing_agents=[],
        recommended_action=RecommendedAction.IMMEDIATE_ESCALATION,
        explanation="High"
    )
    
    modifier = calculate_consensus_modifier(consensus)
    assert modifier == -15.0, "HIGH consensus should produce -15 modifier"


def test_consensus_modifier_medium():
    """Test consensus modifier for MEDIUM risk"""
    consensus = ConsensusDecision(
        risk_level=ConsensusRiskLevel.MEDIUM,
        confidence=1.0,
        risk_score=50.0,
        contributing_agents=[],
        recommended_action=RecommendedAction.MONITOR_CLOSELY,
        explanation="Medium"
    )
    
    modifier = calculate_consensus_modifier(consensus)
    assert modifier == -10.0, "MEDIUM consensus should produce -10 modifier"


def test_consensus_modifier_low():
    """Test consensus modifier for LOW risk"""
    consensus = ConsensusDecision(
        risk_level=ConsensusRiskLevel.LOW,
        confidence=1.0,
        risk_score=25.0,
        contributing_agents=[],
        recommended_action=RecommendedAction.ROUTINE_MONITORING,
        explanation="Low"
    )
    
    modifier = calculate_consensus_modifier(consensus)
    assert modifier == -5.0, "LOW consensus should produce -5 modifier"


def test_consensus_modifier_low_confidence():
    """Test that low confidence reduces modifier magnitude"""
    consensus = ConsensusDecision(
        risk_level=ConsensusRiskLevel.HIGH,
        confidence=0.5,  # Low confidence
        risk_score=75.0,
        contributing_agents=[],
        recommended_action=RecommendedAction.HUMAN_REVIEW_REQUIRED,
        explanation="High risk, low confidence"
    )
    
    modifier = calculate_consensus_modifier(consensus)
    # Should be -15 * 0.5 = -7.5
    assert modifier == -7.5, "Low confidence should reduce modifier magnitude"


# ========================================
# TEST: Overall Confidence Calculation
# ========================================

def test_calculate_overall_confidence_full_coverage(sample_agent_signals, sample_consensus):
    """Test confidence calculation with full dimension coverage"""
    # Calculate dimension scores for all dimensions
    dimension_scores = {}
    for dimension in DQIDimension:
        dim_score = calculate_dimension_score(dimension, sample_agent_signals)
        if dim_score:
            dimension_scores[dimension] = dim_score
    
    confidence = calculate_overall_confidence(
        dimension_scores, sample_agent_signals, sample_consensus
    )
    
    # With full coverage and high agent confidence, should be high
    assert 0.7 <= confidence <= 1.0


def test_calculate_overall_confidence_partial_coverage():
    """Test confidence calculation with partial dimension coverage"""
    signals = [
        AgentSignal(
            agent_type=AgentType.SAFETY,
            risk_level=RiskSignal.LOW,
            confidence=0.9,
            abstained=False
        )
    ]
    
    consensus = ConsensusDecision(
        risk_level=ConsensusRiskLevel.LOW,
        confidence=0.9,
        risk_score=25.0,
        contributing_agents=[],
        recommended_action=RecommendedAction.ROUTINE_MONITORING,
        explanation="Low"
    )
    
    dimension_scores = {
        DQIDimension.SAFETY: DimensionScore(
            dimension=DQIDimension.SAFETY,
            score=90.0,
            contributing_agents=[AgentType.SAFETY],
            confidence=0.9
        )
    }
    
    confidence = calculate_overall_confidence(dimension_scores, signals, consensus)
    
    # With only 1/6 dimensions covered, confidence should be moderate
    # (coverage factor is low but other factors are high)
    assert 0.0 <= confidence <= 0.8


def test_calculate_overall_confidence_high_abstention():
    """Test confidence calculation with high abstention rate"""
    signals = [
        AgentSignal(
            agent_type=AgentType.SAFETY,
            risk_level=RiskSignal.LOW,
            confidence=0.9,
            abstained=False
        ),
        AgentSignal(
            agent_type=AgentType.COMPLETENESS,
            risk_level=RiskSignal.UNKNOWN,
            confidence=0.0,
            abstained=True,
            abstention_reason="Missing features"
        ),
        AgentSignal(
            agent_type=AgentType.CODING,
            risk_level=RiskSignal.UNKNOWN,
            confidence=0.0,
            abstained=True,
            abstention_reason="Missing features"
        ),
    ]
    
    consensus = ConsensusDecision(
        risk_level=ConsensusRiskLevel.UNKNOWN,
        confidence=0.3,
        risk_score=0.0,
        contributing_agents=[],
        recommended_action=RecommendedAction.HUMAN_REVIEW_REQUIRED,
        explanation="High abstention"
    )
    
    dimension_scores = {
        DQIDimension.SAFETY: DimensionScore(
            dimension=DQIDimension.SAFETY,
            score=90.0,
            contributing_agents=[AgentType.SAFETY],
            confidence=0.9
        )
    }
    
    confidence = calculate_overall_confidence(dimension_scores, signals, consensus)
    
    # With 2/3 agents abstained, confidence should be low
    assert confidence < 0.5


# ========================================
# TEST: Band Classification
# ========================================

def test_classify_dqi_band_green():
    """Test GREEN band classification"""
    assert classify_dqi_band(100.0) == DQIBand.GREEN
    assert classify_dqi_band(90.0) == DQIBand.GREEN
    assert classify_dqi_band(85.0) == DQIBand.GREEN


def test_classify_dqi_band_amber():
    """Test AMBER band classification"""
    assert classify_dqi_band(84.9) == DQIBand.AMBER
    assert classify_dqi_band(75.0) == DQIBand.AMBER
    assert classify_dqi_band(65.0) == DQIBand.AMBER


def test_classify_dqi_band_orange():
    """Test ORANGE band classification"""
    assert classify_dqi_band(64.9) == DQIBand.ORANGE
    assert classify_dqi_band(50.0) == DQIBand.ORANGE
    assert classify_dqi_band(40.0) == DQIBand.ORANGE


def test_classify_dqi_band_red():
    """Test RED band classification"""
    assert classify_dqi_band(39.9) == DQIBand.RED
    assert classify_dqi_band(20.0) == DQIBand.RED
    assert classify_dqi_band(0.0) == DQIBand.RED


# ========================================
# TEST: Full DQI Calculation
# ========================================

def test_calculate_dqi_from_agents_low_risk(sample_agent_signals, sample_consensus):
    """Test DQI calculation with low-risk agents"""
    result = calculate_dqi_from_agents(
        sample_agent_signals,
        sample_consensus,
        study_id="TEST_001"
    )
    
    assert result.agent_driven is True
    assert result.study_id == "TEST_001"
    # Low risk agents should produce high DQI
    assert result.score >= 75.0
    assert result.band in [DQIBand.GREEN, DQIBand.AMBER]
    assert 0.0 <= result.confidence <= 1.0
    assert -20.0 <= result.consensus_modifier <= 0.0
    assert len(result.dimensions) > 0


def test_calculate_dqi_from_agents_high_risk(high_risk_agent_signals, high_risk_consensus):
    """Test DQI calculation with high-risk agents"""
    result = calculate_dqi_from_agents(
        high_risk_agent_signals,
        high_risk_consensus,
        study_id="TEST_002"
    )
    
    assert result.agent_driven is True
    # High risk agents should produce low DQI
    assert result.score < 65.0
    assert result.band in [DQIBand.ORANGE, DQIBand.RED]
    # Consensus modifier should be negative
    assert result.consensus_modifier < 0.0


def test_calculate_dqi_from_agents_all_abstained():
    """Test DQI calculation when all agents abstain"""
    signals = [
        AgentSignal(
            agent_type=AgentType.SAFETY,
            risk_level=RiskSignal.UNKNOWN,
            confidence=0.0,
            abstained=True,
            abstention_reason="Missing features"
        ),
        AgentSignal(
            agent_type=AgentType.COMPLETENESS,
            risk_level=RiskSignal.UNKNOWN,
            confidence=0.0,
            abstained=True,
            abstention_reason="Missing features"
        ),
    ]
    
    consensus = ConsensusDecision(
        risk_level=ConsensusRiskLevel.UNKNOWN,
        confidence=0.0,
        risk_score=0.0,
        contributing_agents=[],
        recommended_action=RecommendedAction.HUMAN_REVIEW_REQUIRED,
        explanation="All agents abstained"
    )
    
    result = calculate_dqi_from_agents(signals, consensus, study_id="TEST_003")
    
    # Should return minimal result
    assert result.score == 50.0
    assert result.band == DQIBand.ORANGE
    assert result.confidence == 0.0
    assert len(result.dimensions) == 0


def test_calculate_dqi_from_agents_mixed_signals():
    """Test DQI calculation with mixed risk signals"""
    signals = [
        AgentSignal(
            agent_type=AgentType.SAFETY,
            risk_level=RiskSignal.LOW,
            confidence=0.9,
            abstained=False
        ),
        AgentSignal(
            agent_type=AgentType.COMPLETENESS,
            risk_level=RiskSignal.HIGH,
            confidence=0.85,
            abstained=False
        ),
        AgentSignal(
            agent_type=AgentType.CODING,
            risk_level=RiskSignal.MEDIUM,
            confidence=0.88,
            abstained=False
        ),
    ]
    
    consensus = ConsensusDecision(
        risk_level=ConsensusRiskLevel.MEDIUM,
        confidence=0.85,
        risk_score=50.0,
        contributing_agents=[],
        recommended_action=RecommendedAction.MONITOR_CLOSELY,
        explanation="Mixed signals"
    )
    
    result = calculate_dqi_from_agents(signals, consensus, study_id="TEST_004")
    
    # Should produce moderate DQI
    assert 40.0 <= result.score <= 80.0
    assert result.band in [DQIBand.AMBER, DQIBand.ORANGE]


def test_dqi_result_to_dict(sample_agent_signals, sample_consensus):
    """Test DQI result serialization to dictionary"""
    result = calculate_dqi_from_agents(
        sample_agent_signals,
        sample_consensus,
        study_id="TEST_005"
    )
    
    result_dict = result.to_dict()
    
    assert "score" in result_dict
    assert "band" in result_dict
    assert "confidence" in result_dict
    assert "dimensions" in result_dict
    assert "consensus_modifier" in result_dict
    assert "agent_driven" in result_dict
    assert "study_id" in result_dict
    assert "timestamp" in result_dict
    
    assert result_dict["agent_driven"] is True
    assert result_dict["study_id"] == "TEST_005"


# ========================================
# TEST: Edge Cases
# ========================================

def test_dqi_score_bounds():
    """Test that DQI score stays within [0, 100] bounds"""
    # Create extreme high-risk signals
    signals = [
        AgentSignal(
            agent_type=AgentType.SAFETY,
            risk_level=RiskSignal.CRITICAL,
            confidence=1.0,
            abstained=False
        ),
        AgentSignal(
            agent_type=AgentType.COMPLETENESS,
            risk_level=RiskSignal.CRITICAL,
            confidence=1.0,
            abstained=False
        ),
    ]
    
    consensus = ConsensusDecision(
        risk_level=ConsensusRiskLevel.CRITICAL,
        confidence=1.0,
        risk_score=100.0,
        contributing_agents=[],
        recommended_action=RecommendedAction.IMMEDIATE_ESCALATION,
        explanation="Critical"
    )
    
    result = calculate_dqi_from_agents(signals, consensus)
    
    # Score should be >= 0 even with maximum negative modifier
    assert 0.0 <= result.score <= 100.0


def test_zero_confidence_agents():
    """Test handling of agents with zero confidence"""
    signals = [
        AgentSignal(
            agent_type=AgentType.SAFETY,
            risk_level=RiskSignal.LOW,
            confidence=0.0,  # Zero confidence
            abstained=False
        ),
        AgentSignal(
            agent_type=AgentType.COMPLETENESS,
            risk_level=RiskSignal.LOW,
            confidence=0.0,  # Zero confidence
            abstained=False
        ),
    ]
    
    consensus = ConsensusDecision(
        risk_level=ConsensusRiskLevel.LOW,
        confidence=0.0,
        risk_score=25.0,
        contributing_agents=[],
        recommended_action=RecommendedAction.ROUTINE_MONITORING,
        explanation="Low confidence"
    )
    
    result = calculate_dqi_from_agents(signals, consensus)
    
    # Should still produce valid result
    assert 0.0 <= result.score <= 100.0
    # Overall confidence should be low (but not necessarily 0 due to coverage factor)
    assert result.confidence < 0.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
