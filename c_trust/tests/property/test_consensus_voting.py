"""
Property-Based Tests for Consensus Weighted Voting Accuracy
===========================================================
Tests Property 4: Consensus Weighted Voting Accuracy

**Property 4: Consensus Weighted Voting Accuracy**
*For any* combination of agent signals, the consensus engine should apply 
correct weighted voting according to predefined agent weights, with Safety 
Agent having highest priority and Stability Agent providing negative weighting.

**Validates: Requirements 2.4**

This test uses Hypothesis to generate various combinations of agent signals
and verify that the consensus engine correctly applies weighted voting.
"""

from datetime import datetime
from typing import Any, Dict, List

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck, assume

from src.intelligence.base_agent import AgentSignal, AgentType, RiskSignal
from src.consensus.consensus_engine import (
    ConsensusEngine,
    ConsensusResult,
    ConsensusRiskLevel,
)


# ========================================
# TEST STRATEGIES
# ========================================

@st.composite
def agent_signal_strategy(draw, agent_type: AgentType = None):
    """Generate a valid AgentSignal"""
    if agent_type is None:
        agent_type = draw(st.sampled_from([
            AgentType.SAFETY,
            AgentType.COMPLETENESS,
            AgentType.QUERY_QUALITY,
            AgentType.CODING,
            AgentType.COMPLIANCE,
        ]))
    
    risk_level = draw(st.sampled_from([
        RiskSignal.LOW,
        RiskSignal.MEDIUM,
        RiskSignal.HIGH,
        RiskSignal.CRITICAL,
    ]))
    
    confidence = draw(st.floats(min_value=0.1, max_value=1.0, allow_nan=False))
    
    return AgentSignal(
        agent_type=agent_type,
        risk_level=risk_level,
        confidence=confidence,
        evidence=[],
        recommended_actions=[],
        abstained=False,
        abstention_reason=None,
        features_analyzed=draw(st.integers(min_value=1, max_value=10)),
    )


@st.composite
def abstained_signal_strategy(draw, agent_type: AgentType = None):
    """Generate an abstained AgentSignal"""
    if agent_type is None:
        agent_type = draw(st.sampled_from([
            AgentType.SAFETY,
            AgentType.COMPLETENESS,
            AgentType.QUERY_QUALITY,
        ]))
    
    return AgentSignal(
        agent_type=agent_type,
        risk_level=RiskSignal.UNKNOWN,
        confidence=0.0,
        evidence=[],
        recommended_actions=[],
        abstained=True,
        abstention_reason="Insufficient data for analysis",
        features_analyzed=0,
    )


@st.composite
def multiple_signals_strategy(draw, min_signals: int = 1, max_signals: int = 5):
    """Generate multiple unique agent signals (one per agent type)"""
    available_types = [
        AgentType.SAFETY,
        AgentType.COMPLETENESS,
        AgentType.QUERY_QUALITY,
        AgentType.CODING,
        AgentType.COMPLIANCE,
    ]
    
    num_signals = draw(st.integers(min_value=min_signals, max_value=min(max_signals, len(available_types))))
    selected_types = draw(st.permutations(available_types).map(lambda x: list(x)[:num_signals]))
    
    signals = []
    for agent_type in selected_types:
        signal = draw(agent_signal_strategy(agent_type=agent_type))
        signals.append(signal)
    
    return signals


@st.composite
def mixed_signals_strategy(draw):
    """Generate a mix of abstained and non-abstained signals"""
    available_types = [
        AgentType.SAFETY,
        AgentType.COMPLETENESS,
        AgentType.QUERY_QUALITY,
    ]
    
    signals = []
    for agent_type in available_types:
        is_abstained = draw(st.booleans())
        if is_abstained:
            signal = draw(abstained_signal_strategy(agent_type=agent_type))
        else:
            signal = draw(agent_signal_strategy(agent_type=agent_type))
        signals.append(signal)
    
    return signals


# ========================================
# PROPERTY TESTS
# ========================================

class TestConsensusWeightedVotingProperty:
    """
    Property-based tests for consensus weighted voting accuracy.
    
    Feature: clinical-ai-system, Property 4: Consensus Weighted Voting Accuracy
    """
    
    @given(signals=multiple_signals_strategy(min_signals=1, max_signals=5))
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_weighted_scores_use_correct_weights(self, signals: List[AgentSignal]):
        """
        Feature: clinical-ai-system, Property 4: Consensus Weighted Voting Accuracy
        Validates: Requirements 2.4
        
        Property: For any set of agent signals, the weighted scores should be
        calculated using the correct predefined weights for each agent type.
        """
        engine = ConsensusEngine()
        result = engine.calculate_consensus(signals, "TEST_ENTITY")
        
        # Verify weighted scores are calculated correctly
        for signal in signals:
            if not signal.abstained:
                agent_key = signal.agent_type.value
                expected_weight = engine.weights.get(agent_key, 1.0)
                base_score = engine.RISK_SCORES[signal.risk_level]
                expected_weighted = base_score * expected_weight * signal.confidence
                
                actual_weighted = result.weighted_scores.get(agent_key, 0.0)
                
                assert abs(actual_weighted - expected_weighted) < 0.01, \
                    f"Weighted score mismatch for {agent_key}: " \
                    f"expected {expected_weighted:.2f}, got {actual_weighted:.2f}"
    
    @given(signals=multiple_signals_strategy(min_signals=2, max_signals=5))
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_safety_agent_has_highest_weight(self, signals: List[AgentSignal]):
        """
        Feature: clinical-ai-system, Property 4: Consensus Weighted Voting Accuracy
        Validates: Requirements 2.4
        
        Property: Safety agent should have the highest weight (3.0x) among all agents.
        """
        engine = ConsensusEngine()
        
        # Verify safety weight is highest
        safety_weight = engine.get_weight(AgentType.SAFETY)
        
        for agent_type in [AgentType.COMPLETENESS, AgentType.QUERY_QUALITY, 
                          AgentType.CODING, AgentType.COMPLIANCE]:
            other_weight = engine.get_weight(agent_type)
            assert safety_weight >= other_weight, \
                f"Safety weight ({safety_weight}) should be >= {agent_type.value} weight ({other_weight})"
        
        # Verify safety weight is 3.0
        assert safety_weight == 3.0, f"Safety weight should be 3.0, got {safety_weight}"
    
    @given(signals=multiple_signals_strategy(min_signals=1, max_signals=5))
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_risk_score_in_valid_range(self, signals: List[AgentSignal]):
        """
        Feature: clinical-ai-system, Property 4: Consensus Weighted Voting Accuracy
        Validates: Requirements 2.4
        
        Property: For any combination of signals, the final risk score should
        be in the valid range [0, 100].
        """
        engine = ConsensusEngine()
        result = engine.calculate_consensus(signals, "TEST_ENTITY")
        
        assert 0.0 <= result.risk_score <= 100.0, \
            f"Risk score {result.risk_score} out of valid range [0, 100]"
    
    @given(signals=multiple_signals_strategy(min_signals=1, max_signals=5))
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_confidence_in_valid_range(self, signals: List[AgentSignal]):
        """
        Feature: clinical-ai-system, Property 4: Consensus Weighted Voting Accuracy
        Validates: Requirements 2.4
        
        Property: For any combination of signals, the confidence score should
        be in the valid range [0, 1].
        """
        engine = ConsensusEngine()
        result = engine.calculate_consensus(signals, "TEST_ENTITY")
        
        assert 0.0 <= result.confidence <= 1.0, \
            f"Confidence {result.confidence} out of valid range [0, 1]"
    
    @given(signals=multiple_signals_strategy(min_signals=1, max_signals=5))
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_risk_level_matches_score_thresholds(self, signals: List[AgentSignal]):
        """
        Feature: clinical-ai-system, Property 4: Consensus Weighted Voting Accuracy
        Validates: Requirements 2.4
        
        Property: The risk level classification should match the risk score
        according to defined thresholds.
        """
        engine = ConsensusEngine()
        result = engine.calculate_consensus(signals, "TEST_ENTITY")
        
        score = result.risk_score
        level = result.risk_level
        
        # Verify classification matches thresholds
        if score >= engine.risk_thresholds["critical"]:
            assert level == ConsensusRiskLevel.CRITICAL, \
                f"Score {score} should be CRITICAL, got {level}"
        elif score >= engine.risk_thresholds["high"]:
            assert level == ConsensusRiskLevel.HIGH, \
                f"Score {score} should be HIGH, got {level}"
        elif score >= engine.risk_thresholds["medium"]:
            assert level == ConsensusRiskLevel.MEDIUM, \
                f"Score {score} should be MEDIUM, got {level}"
        else:
            assert level == ConsensusRiskLevel.LOW, \
                f"Score {score} should be LOW, got {level}"
    
    @given(signals=mixed_signals_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_abstained_agents_excluded_from_voting(self, signals: List[AgentSignal]):
        """
        Feature: clinical-ai-system, Property 4: Consensus Weighted Voting Accuracy
        Validates: Requirements 2.4
        
        Property: Abstained agents should be excluded from weighted voting
        and not contribute to the final risk score.
        """
        engine = ConsensusEngine()
        result = engine.calculate_consensus(signals, "TEST_ENTITY")
        
        # Verify abstained agents are tracked
        abstained_types = [s.agent_type.value for s in signals if s.abstained]
        contributing_types = [s.agent_type.value for s in signals if not s.abstained]
        
        assert set(result.abstained_agents) == set(abstained_types), \
            "Abstained agents list mismatch"
        assert set(result.contributing_agents) == set(contributing_types), \
            "Contributing agents list mismatch"
        
        # Verify abstained agents have no weighted scores
        for agent_type in abstained_types:
            assert agent_type not in result.weighted_scores, \
                f"Abstained agent {agent_type} should not have weighted score"
    
    @given(st.data())
    @settings(max_examples=50, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_all_abstained_returns_unknown(self, data):
        """
        Feature: clinical-ai-system, Property 4: Consensus Weighted Voting Accuracy
        Validates: Requirements 2.4
        
        Property: When all agents abstain, the consensus should return
        UNKNOWN risk level with zero confidence.
        """
        # Generate all abstained signals
        signals = [
            data.draw(abstained_signal_strategy(agent_type=AgentType.SAFETY)),
            data.draw(abstained_signal_strategy(agent_type=AgentType.COMPLETENESS)),
            data.draw(abstained_signal_strategy(agent_type=AgentType.QUERY_QUALITY)),
        ]
        
        engine = ConsensusEngine()
        result = engine.calculate_consensus(signals, "TEST_ENTITY")
        
        assert result.risk_level == ConsensusRiskLevel.UNKNOWN, \
            "All abstained should result in UNKNOWN risk level"
        assert result.confidence == 0.0, \
            "All abstained should result in zero confidence"
        assert result.risk_score == 0.0, \
            "All abstained should result in zero risk score"
        assert len(result.contributing_agents) == 0, \
            "All abstained should have no contributing agents"
    
    @given(signals=multiple_signals_strategy(min_signals=2, max_signals=5))
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_agreement_ratio_in_valid_range(self, signals: List[AgentSignal]):
        """
        Feature: clinical-ai-system, Property 4: Consensus Weighted Voting Accuracy
        Validates: Requirements 2.4
        
        Property: Agreement ratio should be in valid range [0, 1].
        """
        engine = ConsensusEngine()
        result = engine.calculate_consensus(signals, "TEST_ENTITY")
        
        assert 0.0 <= result.agreement_ratio <= 1.0, \
            f"Agreement ratio {result.agreement_ratio} out of valid range [0, 1]"
    
    @given(st.data())
    @settings(max_examples=50, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_single_agent_full_agreement(self, data):
        """
        Feature: clinical-ai-system, Property 4: Consensus Weighted Voting Accuracy
        Validates: Requirements 2.4
        
        Property: A single contributing agent should have agreement ratio of 1.0.
        """
        signal = data.draw(agent_signal_strategy(agent_type=AgentType.SAFETY))
        
        engine = ConsensusEngine()
        result = engine.calculate_consensus([signal], "TEST_ENTITY")
        
        assert result.agreement_ratio == 1.0, \
            "Single agent should have agreement ratio of 1.0"


# ========================================
# UNIT TESTS
# ========================================

class TestConsensusEngineUnit:
    """Unit tests for consensus engine"""
    
    def test_default_weights_configured(self):
        """Test that default weights are properly configured"""
        engine = ConsensusEngine()
        
        assert engine.get_weight(AgentType.SAFETY) == 3.0
        assert engine.get_weight(AgentType.COMPLETENESS) == 1.5
        assert engine.get_weight(AgentType.QUERY_QUALITY) == 1.5
    
    def test_custom_weights(self):
        """Test custom weight configuration"""
        custom_weights = {
            AgentType.SAFETY.value: 5.0,
            AgentType.COMPLETENESS.value: 2.0,
        }
        
        engine = ConsensusEngine(weights=custom_weights)
        
        assert engine.get_weight(AgentType.SAFETY) == 5.0
        assert engine.get_weight(AgentType.COMPLETENESS) == 2.0
    
    def test_risk_score_mapping(self):
        """Test risk signal to score mapping"""
        engine = ConsensusEngine()
        
        assert engine.RISK_SCORES[RiskSignal.CRITICAL] == 100.0
        assert engine.RISK_SCORES[RiskSignal.HIGH] == 75.0
        assert engine.RISK_SCORES[RiskSignal.MEDIUM] == 50.0
        assert engine.RISK_SCORES[RiskSignal.LOW] == 25.0
    
    def test_critical_signal_produces_high_score(self):
        """Test that critical signals produce high risk scores"""
        engine = ConsensusEngine()
        
        signal = AgentSignal(
            agent_type=AgentType.SAFETY,
            risk_level=RiskSignal.CRITICAL,
            confidence=1.0,
            abstained=False,
            abstention_reason=None,
        )
        
        result = engine.calculate_consensus([signal], "TEST_ENTITY")
        
        # With safety weight 3.0 and critical score 100, normalized should be 100
        assert result.risk_score >= 85.0, \
            f"Critical safety signal should produce high score, got {result.risk_score}"
        assert result.risk_level == ConsensusRiskLevel.CRITICAL
    
    def test_low_signal_produces_low_score(self):
        """Test that low signals produce low risk scores"""
        engine = ConsensusEngine()
        
        signal = AgentSignal(
            agent_type=AgentType.COMPLETENESS,
            risk_level=RiskSignal.LOW,
            confidence=1.0,
            abstained=False,
            abstention_reason=None,
        )
        
        result = engine.calculate_consensus([signal], "TEST_ENTITY")
        
        assert result.risk_score < 40.0, \
            f"Low signal should produce low score, got {result.risk_score}"
        assert result.risk_level == ConsensusRiskLevel.LOW
    
    def test_result_contains_all_fields(self):
        """Test that consensus result contains all required fields"""
        engine = ConsensusEngine()
        
        signal = AgentSignal(
            agent_type=AgentType.SAFETY,
            risk_level=RiskSignal.MEDIUM,
            confidence=0.8,
            abstained=False,
            abstention_reason=None,
        )
        
        result = engine.calculate_consensus([signal], "TEST_ENTITY")
        
        assert result.entity_id == "TEST_ENTITY"
        assert result.risk_level is not None
        assert result.risk_score is not None
        assert result.confidence is not None
        assert result.contributing_agents is not None
        assert result.abstained_agents is not None
        assert result.weighted_scores is not None
        assert result.timestamp is not None
    
    def test_to_dict_serialization(self):
        """Test that result can be serialized to dict"""
        engine = ConsensusEngine()
        
        signal = AgentSignal(
            agent_type=AgentType.SAFETY,
            risk_level=RiskSignal.HIGH,
            confidence=0.9,
            abstained=False,
            abstention_reason=None,
        )
        
        result = engine.calculate_consensus([signal], "TEST_ENTITY")
        result_dict = result.to_dict()
        
        assert "entity_id" in result_dict
        assert "risk_level" in result_dict
        assert "risk_score" in result_dict
        assert "confidence" in result_dict
        assert result_dict["entity_id"] == "TEST_ENTITY"
