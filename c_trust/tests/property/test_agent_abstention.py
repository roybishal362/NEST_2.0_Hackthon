"""
Property-Based Tests for Agent Abstention Consistency
========================================
Tests Property 3: Agent Abstention Consistency

**Property 3: Agent Abstention Consistency**
*For any* agent lacking sufficient data quality or completeness, the agent 
should abstain from providing output rather than generating unreliable signals, 
and abstention should be properly logged and handled.

**Validates: Requirements 2.3**

This test uses Hypothesis to generate various feature dictionaries with
missing or null values to verify agents properly abstain when data is insufficient.
"""

import copy
from typing import Any, Dict, List, Optional
from datetime import datetime

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck, assume

from src.intelligence.base_agent import (
    BaseAgent,
    AgentType,
    RiskSignal,
    FeatureEvidence,
    AgentSignal,
    AgentRegistry,
    AgentOrchestrator,
)
from src.agents.signal_agents import (
    DataCompletenessAgent,
    SafetyComplianceAgent,
    QueryQualityAgent,
)


# ========================================
# HELPER FUNCTIONS
# ========================================

def create_fresh_registry():
    """Create a fresh registry for testing (bypasses singleton)"""
    registry = AgentRegistry()
    registry.clear()
    return registry


# ========================================
# TEST STRATEGIES
# ========================================

@st.composite
def complete_feature_dict_strategy(draw):
    """Generate complete feature dictionaries with all required features"""
    features = {
        # Completeness features (required for DataCompletenessAgent)
        "missing_pages_pct": draw(st.floats(min_value=0, max_value=100, allow_nan=False)),
        "form_completion_rate": draw(st.floats(min_value=0, max_value=100, allow_nan=False)),
        
        # Safety features (required for SafetyComplianceAgent)
        "sae_backlog_days": draw(st.floats(min_value=0, max_value=365, allow_nan=False)),
        "fatal_sae_count": draw(st.integers(min_value=0, max_value=10)),
        
        # Query features (required for QueryQualityAgent)
        "open_query_count": draw(st.integers(min_value=0, max_value=500)),
        "query_aging_days": draw(st.floats(min_value=0, max_value=90, allow_nan=False)),
    }
    return features


@st.composite
def missing_completeness_features_strategy(draw):
    """Generate features missing completeness agent requirements"""
    # Include safety and query features, but missing completeness
    features = {
        "sae_backlog_days": draw(st.floats(min_value=0, max_value=365, allow_nan=False)),
        "fatal_sae_count": draw(st.integers(min_value=0, max_value=10)),
        "open_query_count": draw(st.integers(min_value=0, max_value=500)),
        "query_aging_days": draw(st.floats(min_value=0, max_value=90, allow_nan=False)),
    }
    
    # Optionally include one completeness feature (but not both)
    include_partial = draw(st.booleans())
    if include_partial:
        which_one = draw(st.booleans())
        if which_one:
            features["missing_pages_pct"] = draw(st.floats(min_value=0, max_value=100, allow_nan=False))
        else:
            features["form_completion_rate"] = draw(st.floats(min_value=0, max_value=100, allow_nan=False))
    
    return features


@st.composite
def missing_safety_features_strategy(draw):
    """Generate features missing safety agent requirements"""
    # Include completeness and query features, but missing safety
    features = {
        "missing_pages_pct": draw(st.floats(min_value=0, max_value=100, allow_nan=False)),
        "form_completion_rate": draw(st.floats(min_value=0, max_value=100, allow_nan=False)),
        "open_query_count": draw(st.integers(min_value=0, max_value=500)),
        "query_aging_days": draw(st.floats(min_value=0, max_value=90, allow_nan=False)),
    }
    
    # Optionally include one safety feature (but not both)
    include_partial = draw(st.booleans())
    if include_partial:
        which_one = draw(st.booleans())
        if which_one:
            features["sae_backlog_days"] = draw(st.floats(min_value=0, max_value=365, allow_nan=False))
        else:
            features["fatal_sae_count"] = draw(st.integers(min_value=0, max_value=10))
    
    return features


@st.composite
def missing_query_features_strategy(draw):
    """Generate features missing query agent requirements"""
    # Include completeness and safety features, but missing query
    features = {
        "missing_pages_pct": draw(st.floats(min_value=0, max_value=100, allow_nan=False)),
        "form_completion_rate": draw(st.floats(min_value=0, max_value=100, allow_nan=False)),
        "sae_backlog_days": draw(st.floats(min_value=0, max_value=365, allow_nan=False)),
        "fatal_sae_count": draw(st.integers(min_value=0, max_value=10)),
    }
    
    # Optionally include one query feature (but not both)
    include_partial = draw(st.booleans())
    if include_partial:
        which_one = draw(st.booleans())
        if which_one:
            features["open_query_count"] = draw(st.integers(min_value=0, max_value=500))
        else:
            features["query_aging_days"] = draw(st.floats(min_value=0, max_value=90, allow_nan=False))
    
    return features


@st.composite
def null_features_strategy(draw):
    """Generate features with some null values"""
    features = {}
    
    # Randomly set features to actual values or None
    if draw(st.booleans()):
        features["missing_pages_pct"] = draw(st.one_of(
            st.floats(min_value=0, max_value=100, allow_nan=False),
            st.none()
        ))
    
    if draw(st.booleans()):
        features["form_completion_rate"] = draw(st.one_of(
            st.floats(min_value=0, max_value=100, allow_nan=False),
            st.none()
        ))
    
    if draw(st.booleans()):
        features["sae_backlog_days"] = draw(st.one_of(
            st.floats(min_value=0, max_value=365, allow_nan=False),
            st.none()
        ))
    
    if draw(st.booleans()):
        features["fatal_sae_count"] = draw(st.one_of(
            st.integers(min_value=0, max_value=10),
            st.none()
        ))
    
    if draw(st.booleans()):
        features["open_query_count"] = draw(st.one_of(
            st.integers(min_value=0, max_value=500),
            st.none()
        ))
    
    if draw(st.booleans()):
        features["query_aging_days"] = draw(st.one_of(
            st.floats(min_value=0, max_value=90, allow_nan=False),
            st.none()
        ))
    
    return features


@st.composite
def empty_features_strategy(draw):
    """Generate empty or near-empty feature dictionaries"""
    # Either completely empty or with just study_id
    if draw(st.booleans()):
        return {}
    else:
        return {"study_id": "TEST_STUDY"}


# ========================================
# PROPERTY TESTS
# ========================================

class TestAgentAbstentionProperty:
    """
    Property-based tests for agent abstention consistency.
    
    Feature: clinical-ai-system, Property 3: Agent Abstention Consistency
    """
    
    @given(features=complete_feature_dict_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_agents_do_not_abstain_with_complete_data(self, features):
        """
        Feature: clinical-ai-system, Property 3: Agent Abstention Consistency
        Validates: Requirements 2.3
        
        Property: When all required features are present and valid, 
        agents should NOT abstain and should produce valid signals.
        """
        registry = create_fresh_registry()
        
        registry.register(DataCompletenessAgent())
        registry.register(SafetyComplianceAgent())
        registry.register(QueryQualityAgent())
        
        orchestrator = AgentOrchestrator(registry)
        signals = orchestrator.run_all_agents(features, "TEST_STUDY")
        
        # PROPERTY VERIFICATION: No agent should abstain with complete data
        for signal in signals:
            assert not signal.abstained, \
                f"Agent {signal.agent_type.value} abstained with complete data"
            assert signal.risk_level != RiskSignal.UNKNOWN, \
                f"Agent {signal.agent_type.value} returned UNKNOWN risk with complete data"
            assert signal.confidence > 0, \
                f"Agent {signal.agent_type.value} has zero confidence with complete data"
        
        registry.clear()
    
    @given(features=missing_completeness_features_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_completeness_agent_abstains_with_missing_features(self, features):
        """
        Feature: clinical-ai-system, Property 3: Agent Abstention Consistency
        Validates: Requirements 2.3
        
        Property: DataCompletenessAgent should abstain when required features 
        (missing_pages_pct, form_completion_rate) are missing.
        """
        registry = create_fresh_registry()
        
        completeness_agent = DataCompletenessAgent()
        safety_agent = SafetyComplianceAgent()
        query_agent = QueryQualityAgent()
        
        registry.register(completeness_agent)
        registry.register(safety_agent)
        registry.register(query_agent)
        
        orchestrator = AgentOrchestrator(registry)
        signals = orchestrator.run_all_agents(features, "TEST_STUDY")
        
        # Find completeness signal
        completeness_signal = next(
            s for s in signals if s.agent_type == AgentType.COMPLETENESS
        )
        
        # Check if both required features are present
        has_missing_pages = "missing_pages_pct" in features and features["missing_pages_pct"] is not None
        has_form_completion = "form_completion_rate" in features and features["form_completion_rate"] is not None
        
        if not (has_missing_pages and has_form_completion):
            # PROPERTY VERIFICATION: Should abstain when missing required features
            assert completeness_signal.abstained, \
                "Completeness agent should abstain when missing required features"
            assert completeness_signal.risk_level == RiskSignal.UNKNOWN
            assert completeness_signal.confidence == 0.0
            assert completeness_signal.abstention_reason is not None
        
        # Other agents should still work (they have their features)
        safety_signal = next(s for s in signals if s.agent_type == AgentType.SAFETY)
        query_signal = next(s for s in signals if s.agent_type == AgentType.QUERY_QUALITY)
        
        assert not safety_signal.abstained, "Safety agent should not abstain"
        assert not query_signal.abstained, "Query agent should not abstain"
        
        registry.clear()
    
    @given(features=missing_safety_features_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_safety_agent_abstains_with_missing_features(self, features):
        """
        Feature: clinical-ai-system, Property 3: Agent Abstention Consistency
        Validates: Requirements 2.3
        
        Property: SafetyComplianceAgent should abstain when required features 
        (sae_backlog_days, fatal_sae_count) are missing.
        """
        registry = create_fresh_registry()
        
        registry.register(DataCompletenessAgent())
        registry.register(SafetyComplianceAgent())
        registry.register(QueryQualityAgent())
        
        orchestrator = AgentOrchestrator(registry)
        signals = orchestrator.run_all_agents(features, "TEST_STUDY")
        
        # Find safety signal
        safety_signal = next(s for s in signals if s.agent_type == AgentType.SAFETY)
        
        # Check if both required features are present
        has_sae_backlog = "sae_backlog_days" in features and features["sae_backlog_days"] is not None
        has_fatal_count = "fatal_sae_count" in features and features["fatal_sae_count"] is not None
        
        if not (has_sae_backlog and has_fatal_count):
            # PROPERTY VERIFICATION: Should abstain when missing required features
            assert safety_signal.abstained, \
                "Safety agent should abstain when missing required features"
            assert safety_signal.risk_level == RiskSignal.UNKNOWN
            assert safety_signal.confidence == 0.0
            assert safety_signal.abstention_reason is not None
        
        # Other agents should still work
        completeness_signal = next(s for s in signals if s.agent_type == AgentType.COMPLETENESS)
        query_signal = next(s for s in signals if s.agent_type == AgentType.QUERY_QUALITY)
        
        assert not completeness_signal.abstained, "Completeness agent should not abstain"
        assert not query_signal.abstained, "Query agent should not abstain"
        
        registry.clear()
    
    @given(features=missing_query_features_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_query_agent_abstains_with_missing_features(self, features):
        """
        Feature: clinical-ai-system, Property 3: Agent Abstention Consistency
        Validates: Requirements 2.3
        
        Property: QueryQualityAgent should abstain when required features 
        (open_query_count, query_aging_days) are missing.
        """
        registry = create_fresh_registry()
        
        registry.register(DataCompletenessAgent())
        registry.register(SafetyComplianceAgent())
        registry.register(QueryQualityAgent())
        
        orchestrator = AgentOrchestrator(registry)
        signals = orchestrator.run_all_agents(features, "TEST_STUDY")
        
        # Find query signal
        query_signal = next(s for s in signals if s.agent_type == AgentType.QUERY_QUALITY)
        
        # Check if both required features are present
        has_query_count = "open_query_count" in features and features["open_query_count"] is not None
        has_query_aging = "query_aging_days" in features and features["query_aging_days"] is not None
        
        if not (has_query_count and has_query_aging):
            # PROPERTY VERIFICATION: Should abstain when missing required features
            assert query_signal.abstained, \
                "Query agent should abstain when missing required features"
            assert query_signal.risk_level == RiskSignal.UNKNOWN
            assert query_signal.confidence == 0.0
            assert query_signal.abstention_reason is not None
        
        # Other agents should still work
        completeness_signal = next(s for s in signals if s.agent_type == AgentType.COMPLETENESS)
        safety_signal = next(s for s in signals if s.agent_type == AgentType.SAFETY)
        
        assert not completeness_signal.abstained, "Completeness agent should not abstain"
        assert not safety_signal.abstained, "Safety agent should not abstain"
        
        registry.clear()
    
    @given(features=empty_features_strategy())
    @settings(max_examples=50, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_all_agents_abstain_with_empty_features(self, features):
        """
        Feature: clinical-ai-system, Property 3: Agent Abstention Consistency
        Validates: Requirements 2.3
        
        Property: All agents should abstain when given empty feature dictionaries.
        """
        registry = create_fresh_registry()
        
        registry.register(DataCompletenessAgent())
        registry.register(SafetyComplianceAgent())
        registry.register(QueryQualityAgent())
        
        orchestrator = AgentOrchestrator(registry)
        signals = orchestrator.run_all_agents(features, "TEST_STUDY")
        
        # PROPERTY VERIFICATION: All agents should abstain with empty features
        for signal in signals:
            assert signal.abstained, \
                f"Agent {signal.agent_type.value} should abstain with empty features"
            assert signal.risk_level == RiskSignal.UNKNOWN
            assert signal.confidence == 0.0
            assert signal.abstention_reason is not None
            assert len(signal.abstention_reason) > 0
        
        registry.clear()
    
    @given(features=null_features_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_abstention_signal_structure(self, features):
        """
        Feature: clinical-ai-system, Property 3: Agent Abstention Consistency
        Validates: Requirements 2.3
        
        Property: Abstention signals should have consistent structure:
        - risk_level = UNKNOWN
        - confidence = 0.0
        - abstained = True
        - abstention_reason is not None and not empty
        """
        registry = create_fresh_registry()
        
        registry.register(DataCompletenessAgent())
        registry.register(SafetyComplianceAgent())
        registry.register(QueryQualityAgent())
        
        orchestrator = AgentOrchestrator(registry)
        signals = orchestrator.run_all_agents(features, "TEST_STUDY")
        
        # PROPERTY VERIFICATION: Check abstention signal structure
        for signal in signals:
            if signal.abstained:
                # Abstention signals must have consistent structure
                assert signal.risk_level == RiskSignal.UNKNOWN, \
                    f"Abstained agent {signal.agent_type.value} should have UNKNOWN risk"
                assert signal.confidence == 0.0, \
                    f"Abstained agent {signal.agent_type.value} should have 0.0 confidence"
                assert signal.abstention_reason is not None, \
                    f"Abstained agent {signal.agent_type.value} must have abstention_reason"
                assert len(signal.abstention_reason) > 0, \
                    f"Abstained agent {signal.agent_type.value} abstention_reason cannot be empty"
            else:
                # Non-abstained signals should have valid values
                assert signal.risk_level != RiskSignal.UNKNOWN, \
                    f"Non-abstained agent {signal.agent_type.value} should not have UNKNOWN risk"
                assert signal.confidence > 0, \
                    f"Non-abstained agent {signal.agent_type.value} should have positive confidence"
                assert signal.abstention_reason is None, \
                    f"Non-abstained agent {signal.agent_type.value} should not have abstention_reason"
        
        registry.clear()


# ========================================
# UNIT TESTS
# ========================================

class TestAgentAbstentionUnit:
    """Unit tests for agent abstention behavior"""
    
    def test_completeness_agent_abstention_reason_format(self):
        """Test that abstention reason contains useful information"""
        agent = DataCompletenessAgent()
        
        # Missing all required features
        signal = agent.analyze({}, "TEST_STUDY")
        
        assert signal.abstained
        assert "missing" in signal.abstention_reason.lower() or "feature" in signal.abstention_reason.lower()
    
    def test_safety_agent_abstention_reason_format(self):
        """Test that abstention reason contains useful information"""
        agent = SafetyComplianceAgent()
        
        # Missing all required features
        signal = agent.analyze({}, "TEST_STUDY")
        
        assert signal.abstained
        assert "missing" in signal.abstention_reason.lower() or "feature" in signal.abstention_reason.lower()
    
    def test_query_agent_abstention_reason_format(self):
        """Test that abstention reason contains useful information"""
        agent = QueryQualityAgent()
        
        # Missing all required features
        signal = agent.analyze({}, "TEST_STUDY")
        
        assert signal.abstained
        assert "missing" in signal.abstention_reason.lower() or "feature" in signal.abstention_reason.lower()
    
    def test_partial_features_abstention(self):
        """Test abstention with partial features"""
        agent = DataCompletenessAgent()
        
        # Only one of two required features
        signal = agent.analyze({"missing_pages_pct": 10.0}, "TEST_STUDY")
        
        assert signal.abstained
        assert "form_completion_rate" in signal.abstention_reason
    
    def test_null_features_treated_as_missing(self):
        """Test that null feature values are treated as missing"""
        agent = DataCompletenessAgent()
        
        # Features present but null
        signal = agent.analyze({
            "missing_pages_pct": None,
            "form_completion_rate": None
        }, "TEST_STUDY")
        
        assert signal.abstained
    
    def test_abstention_does_not_affect_other_agents(self):
        """Test that one agent's abstention doesn't affect others"""
        registry = create_fresh_registry()
        
        registry.register(DataCompletenessAgent())
        registry.register(SafetyComplianceAgent())
        registry.register(QueryQualityAgent())
        
        orchestrator = AgentOrchestrator(registry)
        
        # Features that cause completeness to abstain but others to work
        features = {
            # Missing completeness features
            "sae_backlog_days": 5.0,
            "fatal_sae_count": 0,
            "open_query_count": 50,
            "query_aging_days": 10.0,
        }
        
        signals = orchestrator.run_all_agents(features, "TEST_STUDY")
        
        completeness_signal = next(s for s in signals if s.agent_type == AgentType.COMPLETENESS)
        safety_signal = next(s for s in signals if s.agent_type == AgentType.SAFETY)
        query_signal = next(s for s in signals if s.agent_type == AgentType.QUERY_QUALITY)
        
        assert completeness_signal.abstained
        assert not safety_signal.abstained
        assert not query_signal.abstained
        
        # Non-abstained agents should have valid risk assessments
        assert safety_signal.risk_level in [RiskSignal.LOW, RiskSignal.MEDIUM, RiskSignal.HIGH, RiskSignal.CRITICAL]
        assert query_signal.risk_level in [RiskSignal.LOW, RiskSignal.MEDIUM, RiskSignal.HIGH, RiskSignal.CRITICAL]
        
        registry.clear()
