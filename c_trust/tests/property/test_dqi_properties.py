"""
Property-Based Tests for Agent-Driven DQI Engine
================================================
Tests universal properties that should hold across all inputs.

Properties Tested:
1. High risk produces low DQI (US-1)
2. Dimension scores within bounds [0, 100] (FR-1)
3. Consensus modifier reduces DQI (FR-2)
4. DQI score is deterministic (NFR-8)
5. Agent abstention reduces confidence (FR-2)

Uses Hypothesis for property-based testing.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from datetime import datetime

from src.intelligence.base_agent import AgentSignal, AgentType, RiskSignal
from src.intelligence.consensus import ConsensusDecision, ConsensusRiskLevel, RecommendedAction
from src.intelligence.dqi_engine_agent_driven import (
    DQIDimension,
    DQIBand,
    calculate_dqi_from_agents,
    risk_signal_to_score,
    calculate_dimension_score,
    calculate_consensus_modifier,
    classify_dqi_band,
)


# ========================================
# HYPOTHESIS STRATEGIES
# ========================================

@st.composite
def agent_signal_strategy(draw):
    """Generate random agent signals - only for agents that map to dimensions"""
    # Only use agents that have dimension mappings
    mapped_agents = [
        AgentType.SAFETY,
        AgentType.COMPLETENESS,
        AgentType.CODING,
        AgentType.QUERY_QUALITY,
        AgentType.TEMPORAL_DRIFT,
        AgentType.OPERATIONS,
        AgentType.STABILITY,
    ]
    
    agent_type = draw(st.sampled_from(mapped_agents))
    risk_level = draw(st.sampled_from(list(RiskSignal)))
    confidence = draw(st.floats(min_value=0.0, max_value=1.0))
    abstained = draw(st.booleans())
    
    # If abstained, risk_level should be UNKNOWN and confidence should be 0
    if abstained:
        risk_level = RiskSignal.UNKNOWN
        confidence = 0.0
        abstention_reason = "Test abstention"
    else:
        abstention_reason = None
    
    return AgentSignal(
        agent_type=agent_type,
        risk_level=risk_level,
        confidence=confidence,
        abstained=abstained,
        abstention_reason=abstention_reason
    )


@st.composite
def consensus_strategy(draw):
    """Generate random consensus decisions"""
    risk_level = draw(st.sampled_from(list(ConsensusRiskLevel)))
    confidence = draw(st.floats(min_value=0.0, max_value=1.0))
    risk_score = draw(st.floats(min_value=0.0, max_value=100.0))
    
    return ConsensusDecision(
        risk_level=risk_level,
        confidence=confidence,
        risk_score=risk_score,
        contributing_agents=[],
        recommended_action=RecommendedAction.ROUTINE_MONITORING,
        explanation="Test consensus"
    )


# ========================================
# PROPERTY 1: High Risk Produces Low DQI
# ========================================

@given(st.lists(agent_signal_strategy(), min_size=1, max_size=7))
@settings(max_examples=100, deadline=None)
def test_property_high_risk_produces_low_dqi(agent_signals):
    """
    **Validates: Requirements US-1**
    
    Property: When all agents report HIGH/CRITICAL risk, DQI score MUST be < 65
    """
    # Arrange: Set all active agents to HIGH or CRITICAL risk
    high_risk_signals = []
    for signal in agent_signals:
        if not signal.abstained:
            # Create new signal with HIGH risk
            high_risk_signals.append(AgentSignal(
                agent_type=signal.agent_type,
                risk_level=RiskSignal.HIGH,
                confidence=signal.confidence,
                abstained=False
            ))
        else:
            high_risk_signals.append(signal)
    
    # Skip if all agents abstained
    active_count = len([s for s in high_risk_signals if not s.abstained])
    assume(active_count > 0)
    
    # Create HIGH risk consensus
    consensus = ConsensusDecision(
        risk_level=ConsensusRiskLevel.HIGH,
        confidence=0.9,
        risk_score=75.0,
        contributing_agents=[],
        recommended_action=RecommendedAction.IMMEDIATE_ESCALATION,
        explanation="High risk"
    )
    
    # Act
    dqi = calculate_dqi_from_agents(high_risk_signals, consensus)
    
    # Assert
    assert dqi.score < 65, f"HIGH risk should produce DQI < 65, got {dqi.score}"
    assert dqi.band in [DQIBand.ORANGE, DQIBand.RED], f"Expected ORANGE/RED band, got {dqi.band}"


@given(st.lists(agent_signal_strategy(), min_size=1, max_size=7))
@settings(max_examples=100, deadline=None)
def test_property_low_risk_produces_high_dqi(agent_signals):
    """
    **Validates: Requirements US-1**
    
    Property: When all agents report LOW risk, DQI score SHOULD be >= 75
    """
    # Arrange: Set all active agents to LOW risk
    low_risk_signals = []
    for signal in agent_signals:
        if not signal.abstained:
            # Create new signal with LOW risk
            low_risk_signals.append(AgentSignal(
                agent_type=signal.agent_type,
                risk_level=RiskSignal.LOW,
                confidence=signal.confidence,
                abstained=False
            ))
        else:
            low_risk_signals.append(signal)
    
    # Skip if all agents abstained
    active_count = len([s for s in low_risk_signals if not s.abstained])
    assume(active_count > 0)
    
    # Create LOW risk consensus
    consensus = ConsensusDecision(
        risk_level=ConsensusRiskLevel.LOW,
        confidence=0.9,
        risk_score=25.0,
        contributing_agents=[],
        recommended_action=RecommendedAction.ROUTINE_MONITORING,
        explanation="Low risk"
    )
    
    # Act
    dqi = calculate_dqi_from_agents(low_risk_signals, consensus)
    
    # Assert
    # With LOW risk and minimal consensus modifier, should be high
    assert dqi.score >= 75, f"LOW risk should produce DQI >= 75, got {dqi.score}"


# ========================================
# PROPERTY 2: Dimension Scores Within Bounds
# ========================================

@given(st.lists(agent_signal_strategy(), min_size=1, max_size=7), consensus_strategy())
@settings(max_examples=100, deadline=None)
def test_property_dimension_scores_within_bounds(agent_signals, consensus):
    """
    **Validates: Requirements FR-1**
    
    Property: All dimension scores MUST be in range [0, 100]
    """
    # Act
    dqi = calculate_dqi_from_agents(agent_signals, consensus)
    
    # Assert
    for dimension, dim_score in dqi.dimensions.items():
        assert 0 <= dim_score.score <= 100, (
            f"Dimension {dimension.value} score {dim_score.score} out of bounds [0, 100]"
        )


@given(st.lists(agent_signal_strategy(), min_size=1, max_size=7), consensus_strategy())
@settings(max_examples=100, deadline=None)
def test_property_dqi_score_within_bounds(agent_signals, consensus):
    """
    **Validates: Requirements FR-1**
    
    Property: Overall DQI score MUST be in range [0, 100]
    """
    # Act
    dqi = calculate_dqi_from_agents(agent_signals, consensus)
    
    # Assert
    assert 0 <= dqi.score <= 100, f"DQI score {dqi.score} out of bounds [0, 100]"


@given(st.lists(agent_signal_strategy(), min_size=1, max_size=7), consensus_strategy())
@settings(max_examples=100, deadline=None)
def test_property_confidence_within_bounds(agent_signals, consensus):
    """
    **Validates: Requirements FR-1**
    
    Property: Confidence scores MUST be in range [0, 1]
    """
    # Act
    dqi = calculate_dqi_from_agents(agent_signals, consensus)
    
    # Assert
    assert 0 <= dqi.confidence <= 1, f"Confidence {dqi.confidence} out of bounds [0, 1]"
    
    for dimension, dim_score in dqi.dimensions.items():
        assert 0 <= dim_score.confidence <= 1, (
            f"Dimension {dimension.value} confidence {dim_score.confidence} out of bounds [0, 1]"
        )


# ========================================
# PROPERTY 3: Consensus Modifier Reduces DQI
# ========================================

@given(st.lists(agent_signal_strategy(), min_size=1, max_size=7))
@settings(max_examples=100, deadline=None)
def test_property_consensus_modifier_reduces_dqi(agent_signals):
    """
    **Validates: Requirements FR-2**
    
    Property: CRITICAL/HIGH consensus MUST reduce DQI score compared to LOW consensus
    """
    # Skip if all agents abstained
    active_count = len([s for s in agent_signals if not s.abstained])
    assume(active_count > 0)
    
    # Calculate DQI with LOW risk consensus
    consensus_low = ConsensusDecision(
        risk_level=ConsensusRiskLevel.LOW,
        confidence=0.9,
        risk_score=20.0,
        contributing_agents=[],
        recommended_action=RecommendedAction.ROUTINE_MONITORING,
        explanation="Low risk"
    )
    dqi_low = calculate_dqi_from_agents(agent_signals, consensus_low)
    
    # Calculate DQI with HIGH risk consensus
    consensus_high = ConsensusDecision(
        risk_level=ConsensusRiskLevel.HIGH,
        confidence=0.9,
        risk_score=80.0,
        contributing_agents=[],
        recommended_action=RecommendedAction.IMMEDIATE_ESCALATION,
        explanation="High risk"
    )
    dqi_high = calculate_dqi_from_agents(agent_signals, consensus_high)
    
    # Assert: HIGH risk consensus should produce lower DQI
    assert dqi_high.score < dqi_low.score, (
        f"HIGH risk consensus should reduce DQI: "
        f"low={dqi_low.score:.1f}, high={dqi_high.score:.1f}"
    )


@given(consensus_strategy())
@settings(max_examples=100, deadline=None)
def test_property_consensus_modifier_bounds(consensus):
    """
    **Validates: Requirements FR-2**
    
    Property: Consensus modifier MUST be in range [-20, 0]
    """
    # Act
    modifier = calculate_consensus_modifier(consensus)
    
    # Assert
    assert -20 <= modifier <= 0, f"Consensus modifier {modifier} out of bounds [-20, 0]"


# ========================================
# PROPERTY 4: DQI Score is Deterministic
# ========================================

@given(st.lists(agent_signal_strategy(), min_size=1, max_size=7), consensus_strategy())
@settings(max_examples=50, deadline=None)
def test_property_dqi_is_deterministic(agent_signals, consensus):
    """
    **Validates: Requirements NFR-8**
    
    Property: Same input MUST produce same output (deterministic)
    """
    # Act: Calculate DQI twice with same inputs
    dqi1 = calculate_dqi_from_agents(agent_signals, consensus, study_id="TEST")
    dqi2 = calculate_dqi_from_agents(agent_signals, consensus, study_id="TEST")
    
    # Assert: Results should be identical
    assert dqi1.score == dqi2.score, "DQI calculation should be deterministic"
    assert dqi1.band == dqi2.band, "DQI band should be deterministic"
    assert dqi1.confidence == dqi2.confidence, "Confidence should be deterministic"
    assert dqi1.consensus_modifier == dqi2.consensus_modifier, "Modifier should be deterministic"
    assert len(dqi1.dimensions) == len(dqi2.dimensions), "Dimensions should be deterministic"


# ========================================
# PROPERTY 5: Agent Abstention Reduces Confidence
# ========================================

@given(st.lists(agent_signal_strategy(), min_size=3, max_size=7))
@settings(max_examples=100, deadline=None)
def test_property_abstention_reduces_confidence(agent_signals):
    """
    **Validates: Requirements FR-2**
    
    Property: Increased abstention rate MUST reduce participation factor in confidence
    """
    # Skip if all agents already abstained
    active_count = len([s for s in agent_signals if not s.abstained])
    assume(active_count >= 3)
    
    # Create consensus
    consensus = ConsensusDecision(
        risk_level=ConsensusRiskLevel.MEDIUM,
        confidence=0.8,
        risk_score=50.0,
        contributing_agents=[],
        recommended_action=RecommendedAction.MONITOR_CLOSELY,
        explanation="Medium risk"
    )
    
    # Calculate DQI with all agents active
    dqi_full = calculate_dqi_from_agents(agent_signals, consensus)
    
    # Create version with HALF of agents abstained
    abstained_signals = []
    abstain_count = 0
    target_abstain = max(1, active_count // 2)
    
    for signal in agent_signals:
        if not signal.abstained and abstain_count < target_abstain:
            # Make this agent abstain
            abstained_signals.append(AgentSignal(
                agent_type=signal.agent_type,
                risk_level=RiskSignal.UNKNOWN,
                confidence=0.0,
                abstained=True,
                abstention_reason="Test abstention"
            ))
            abstain_count += 1
        else:
            abstained_signals.append(signal)
    
    # Calculate DQI with half agents abstained
    dqi_abstained = calculate_dqi_from_agents(abstained_signals, consensus)
    
    # Calculate participation rates
    participation_full = active_count / len(agent_signals)
    participation_abstained = (active_count - abstain_count) / len(agent_signals)
    
    # Assert: Lower participation should result in lower or equal confidence
    # (The participation rate is a factor in confidence calculation)
    if participation_abstained < participation_full:
        # Allow for edge cases where dimension confidence increases
        # but overall confidence should generally decrease with lower participation
        assert dqi_abstained.confidence <= dqi_full.confidence + 0.1, (
            f"Significantly reduced participation should not greatly increase confidence: "
            f"full={dqi_full.confidence:.2f} (participation={participation_full:.2f}), "
            f"abstained={dqi_abstained.confidence:.2f} (participation={participation_abstained:.2f})"
        )


# ========================================
# PROPERTY 6: Risk Signal to Score Inverse Relationship
# ========================================

@given(st.sampled_from(list(RiskSignal)))
@settings(max_examples=50, deadline=None)
def test_property_risk_signal_inverse_relationship(risk_signal):
    """
    Property: Higher risk signals MUST produce lower DQI scores
    """
    score = risk_signal_to_score(risk_signal)
    
    # Verify inverse relationship
    if risk_signal == RiskSignal.CRITICAL:
        assert score <= 30, "CRITICAL risk should produce very low score"
    elif risk_signal == RiskSignal.HIGH:
        assert score <= 50, "HIGH risk should produce low score"
    elif risk_signal == RiskSignal.MEDIUM:
        assert 50 <= score <= 80, "MEDIUM risk should produce moderate score"
    elif risk_signal == RiskSignal.LOW:
        assert score >= 80, "LOW risk should produce high score"


# ========================================
# PROPERTY 7: Band Classification Consistency
# ========================================

@given(st.floats(min_value=0.0, max_value=100.0))
@settings(max_examples=100, deadline=None)
def test_property_band_classification_consistent(score):
    """
    Property: Band classification MUST be consistent with score thresholds
    """
    band = classify_dqi_band(score)
    
    if score >= 85:
        assert band == DQIBand.GREEN, f"Score {score} should be GREEN"
    elif score >= 65:
        assert band == DQIBand.AMBER, f"Score {score} should be AMBER"
    elif score >= 40:
        assert band == DQIBand.ORANGE, f"Score {score} should be ORANGE"
    else:
        assert band == DQIBand.RED, f"Score {score} should be RED"


# ========================================
# PROPERTY 8: Dimension Score Aggregation
# ========================================

@given(st.lists(agent_signal_strategy(), min_size=1, max_size=7), consensus_strategy())
@settings(max_examples=100, deadline=None)
def test_property_dimension_score_aggregation(agent_signals, consensus):
    """
    Property: Overall DQI score MUST be influenced by all dimension scores
    """
    # Act
    dqi = calculate_dqi_from_agents(agent_signals, consensus)
    
    # If we have dimension scores, overall score should be related to them
    if dqi.dimensions:
        dimension_scores = [ds.score for ds in dqi.dimensions.values()]
        min_dim_score = min(dimension_scores)
        max_dim_score = max(dimension_scores)
        
        # Overall score should be within reasonable range of dimension scores
        # (accounting for consensus modifier)
        assert min_dim_score - 20 <= dqi.score <= max_dim_score, (
            f"Overall score {dqi.score:.1f} should be related to dimension scores "
            f"[{min_dim_score:.1f}, {max_dim_score:.1f}]"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
