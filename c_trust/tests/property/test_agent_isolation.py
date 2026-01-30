"""
Property-Based Tests for Agent Isolation and Independence
========================================
Tests Property 2: Agent Isolation and Independence

**Property 2: Agent Isolation and Independence**
*For any* agent in the multi-agent system, modifying the input or behavior 
of one agent should not affect the analysis or outputs of other agents, 
ensuring true independence.

**Validates: Requirements 2.2**

This test uses Hypothesis to generate various feature dictionaries and
verify that agents operate in complete isolation from each other.
"""

import copy
from typing import Any, Dict, List
from datetime import datetime

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck

from src.intelligence.base_agent import (
    BaseAgent,
    AgentType,
    RiskSignal,
    FeatureEvidence,
    AgentSignal,
    AgentRegistry,
    AgentOrchestrator,
)


# ========================================
# AGENT IMPLEMENTATIONS FOR TESTING
# ========================================

class CompletenessAgentImpl(BaseAgent):
    """Agent that analyzes completeness features"""
    
    REQUIRED_FEATURES = ["missing_pages_pct", "form_completion_rate"]
    
    def __init__(self):
        super().__init__(
            agent_type=AgentType.COMPLETENESS,
            min_confidence=0.6,
            abstention_threshold=0.5
        )
    
    def analyze(self, features: Dict[str, Any], study_id: str) -> AgentSignal:
        """Analyze completeness features"""
        should_abstain, reason = self._should_abstain(features, self.REQUIRED_FEATURES)
        
        if should_abstain:
            return self._create_abstention_signal(reason)
        
        # Calculate risk based on missing pages
        missing_pct = features.get("missing_pages_pct", 0)
        completion_rate = features.get("form_completion_rate", 100)
        
        # Modify features to test isolation (should not affect other agents)
        features["_modified_by_completeness"] = True
        features["missing_pages_pct"] = missing_pct * 2  # Intentional modification
        
        risk_level = self._assess_risk(missing_pct, completion_rate)
        confidence = self._calculate_confidence(features)
        
        return AgentSignal(
            agent_type=self.agent_type,
            risk_level=risk_level,
            confidence=confidence,
            evidence=[
                FeatureEvidence(
                    feature_name="missing_pages_pct",
                    feature_value=missing_pct,
                    severity=min(missing_pct / 100, 1.0),
                    description=f"Missing {missing_pct}% of pages"
                )
            ],
            features_analyzed=len(self.REQUIRED_FEATURES)
        )
    
    def _assess_risk(self, missing_pct: float, completion_rate: float) -> RiskSignal:
        """Assess risk based on completeness metrics"""
        if missing_pct > 30 or completion_rate < 50:
            return RiskSignal.HIGH
        elif missing_pct > 15 or completion_rate < 70:
            return RiskSignal.MEDIUM
        else:
            return RiskSignal.LOW
    
    def _calculate_confidence(self, features: Dict[str, Any]) -> float:
        """Calculate confidence based on data availability"""
        available = sum(1 for f in self.REQUIRED_FEATURES if f in features and features[f] is not None)
        return available / len(self.REQUIRED_FEATURES)


class SafetyAgentImpl(BaseAgent):
    """Agent that analyzes safety features"""
    
    REQUIRED_FEATURES = ["sae_backlog_days", "fatal_sae_count"]
    
    def __init__(self):
        super().__init__(
            agent_type=AgentType.SAFETY,
            min_confidence=0.6,
            abstention_threshold=0.5
        )
    
    def analyze(self, features: Dict[str, Any], study_id: str) -> AgentSignal:
        """Analyze safety features"""
        should_abstain, reason = self._should_abstain(features, self.REQUIRED_FEATURES)
        
        if should_abstain:
            return self._create_abstention_signal(reason)
        
        sae_backlog = features.get("sae_backlog_days", 0)
        fatal_count = features.get("fatal_sae_count", 0)
        
        # Modify features to test isolation (should not affect other agents)
        features["_modified_by_safety"] = True
        features["sae_backlog_days"] = sae_backlog + 100  # Intentional modification
        
        risk_level = self._assess_risk(sae_backlog, fatal_count)
        confidence = self._calculate_confidence(features)
        
        return AgentSignal(
            agent_type=self.agent_type,
            risk_level=risk_level,
            confidence=confidence,
            evidence=[
                FeatureEvidence(
                    feature_name="sae_backlog_days",
                    feature_value=sae_backlog,
                    severity=min(sae_backlog / 30, 1.0),
                    description=f"SAE backlog: {sae_backlog} days"
                )
            ],
            features_analyzed=len(self.REQUIRED_FEATURES)
        )
    
    def _assess_risk(self, sae_backlog: float, fatal_count: int) -> RiskSignal:
        """Assess risk based on safety metrics"""
        if fatal_count > 0 or sae_backlog > 14:
            return RiskSignal.CRITICAL
        elif sae_backlog > 7:
            return RiskSignal.HIGH
        elif sae_backlog > 3:
            return RiskSignal.MEDIUM
        else:
            return RiskSignal.LOW
    
    def _calculate_confidence(self, features: Dict[str, Any]) -> float:
        """Calculate confidence based on data availability"""
        available = sum(1 for f in self.REQUIRED_FEATURES if f in features and features[f] is not None)
        return available / len(self.REQUIRED_FEATURES)


class QueryAgentImpl(BaseAgent):
    """Agent that analyzes query quality features"""
    
    REQUIRED_FEATURES = ["open_query_count", "query_aging_days"]
    
    def __init__(self):
        super().__init__(
            agent_type=AgentType.QUERY_QUALITY,
            min_confidence=0.6,
            abstention_threshold=0.5
        )
    
    def analyze(self, features: Dict[str, Any], study_id: str) -> AgentSignal:
        """Analyze query quality features"""
        should_abstain, reason = self._should_abstain(features, self.REQUIRED_FEATURES)
        
        if should_abstain:
            return self._create_abstention_signal(reason)
        
        query_count = features.get("open_query_count", 0)
        query_aging = features.get("query_aging_days", 0)
        
        # Modify features to test isolation (should not affect other agents)
        features["_modified_by_query"] = True
        features["open_query_count"] = query_count * 10  # Intentional modification
        
        risk_level = self._assess_risk(query_count, query_aging)
        confidence = self._calculate_confidence(features)
        
        return AgentSignal(
            agent_type=self.agent_type,
            risk_level=risk_level,
            confidence=confidence,
            evidence=[
                FeatureEvidence(
                    feature_name="open_query_count",
                    feature_value=query_count,
                    severity=min(query_count / 100, 1.0),
                    description=f"Open queries: {query_count}"
                )
            ],
            features_analyzed=len(self.REQUIRED_FEATURES)
        )
    
    def _assess_risk(self, query_count: int, query_aging: float) -> RiskSignal:
        """Assess risk based on query metrics"""
        if query_count > 100 or query_aging > 30:
            return RiskSignal.HIGH
        elif query_count > 50 or query_aging > 14:
            return RiskSignal.MEDIUM
        else:
            return RiskSignal.LOW
    
    def _calculate_confidence(self, features: Dict[str, Any]) -> float:
        """Calculate confidence based on data availability"""
        available = sum(1 for f in self.REQUIRED_FEATURES if f in features and features[f] is not None)
        return available / len(self.REQUIRED_FEATURES)


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
def feature_dict_strategy(draw):
    """Generate feature dictionaries for testing"""
    features = {
        # Completeness features
        "missing_pages_pct": draw(st.floats(min_value=0, max_value=100, allow_nan=False)),
        "form_completion_rate": draw(st.floats(min_value=0, max_value=100, allow_nan=False)),
        
        # Safety features
        "sae_backlog_days": draw(st.floats(min_value=0, max_value=365, allow_nan=False)),
        "fatal_sae_count": draw(st.integers(min_value=0, max_value=10)),
        
        # Query features
        "open_query_count": draw(st.integers(min_value=0, max_value=500)),
        "query_aging_days": draw(st.floats(min_value=0, max_value=90, allow_nan=False)),
        
        # Additional features
        "study_id": draw(st.text(min_size=5, max_size=15, alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")),
    }
    return features


@st.composite
def partial_feature_dict_strategy(draw):
    """Generate feature dictionaries with some missing features"""
    all_features = [
        "missing_pages_pct", "form_completion_rate",
        "sae_backlog_days", "fatal_sae_count",
        "open_query_count", "query_aging_days"
    ]
    
    # Randomly select which features to include
    included_features = draw(st.lists(
        st.sampled_from(all_features),
        min_size=1,
        max_size=len(all_features),
        unique=True
    ))
    
    features = {"study_id": "TEST_STUDY"}
    
    for feature in included_features:
        if feature in ["missing_pages_pct", "form_completion_rate"]:
            features[feature] = draw(st.floats(min_value=0, max_value=100, allow_nan=False))
        elif feature == "sae_backlog_days":
            features[feature] = draw(st.floats(min_value=0, max_value=365, allow_nan=False))
        elif feature == "fatal_sae_count":
            features[feature] = draw(st.integers(min_value=0, max_value=10))
        elif feature == "open_query_count":
            features[feature] = draw(st.integers(min_value=0, max_value=500))
        elif feature == "query_aging_days":
            features[feature] = draw(st.floats(min_value=0, max_value=90, allow_nan=False))
    
    return features


# ========================================
# PROPERTY TESTS
# ========================================

class TestAgentIsolationProperty:
    """
    Property-based tests for agent isolation and independence.
    
    Feature: clinical-ai-system, Property 2: Agent Isolation and Independence
    """
    
    @given(features=feature_dict_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_agent_isolation_property(self, features):
        """
        Feature: clinical-ai-system, Property 2: Agent Isolation and Independence
        Validates: Requirements 2.2
        
        Property: For any agent in the multi-agent system, modifying the input 
        or behavior of one agent should not affect the analysis or outputs of 
        other agents, ensuring true independence.
        """
        registry = create_fresh_registry()
        
        # Register test agents
        completeness_agent = CompletenessAgentImpl()
        safety_agent = SafetyAgentImpl()
        query_agent = QueryAgentImpl()
        
        registry.register(completeness_agent, weight=1.0)
        registry.register(safety_agent, weight=3.0)  # Higher weight for safety
        registry.register(query_agent, weight=1.0)
        
        # Create orchestrator
        orchestrator = AgentOrchestrator(registry)
        
        # Store original feature values
        original_features = copy.deepcopy(features)
        
        # Run all agents
        signals = orchestrator.run_all_agents(features, "TEST_STUDY")
        
        # PROPERTY VERIFICATION 1: Original features should be unchanged
        # (Orchestrator provides isolation via deep copy)
        assert features == original_features, \
            "Original features were modified by agent execution"
        
        # PROPERTY VERIFICATION 2: Each agent should produce independent output
        assert len(signals) == 3, "Expected 3 agent signals"
        
        # PROPERTY VERIFICATION 3: Agent types should be unique
        agent_types = [s.agent_type for s in signals]
        assert len(set(agent_types)) == len(agent_types), \
            "Duplicate agent types in signals"
        
        # PROPERTY VERIFICATION 4: Run agents individually and compare
        # Results should be identical to batch run
        individual_signals = []
        for agent_type in [AgentType.COMPLETENESS, AgentType.SAFETY, AgentType.QUERY_QUALITY]:
            signal = orchestrator.run_single_agent(
                agent_type,
                copy.deepcopy(original_features),
                "TEST_STUDY"
            )
            if signal:
                individual_signals.append(signal)
        
        # Compare batch vs individual results
        for batch_signal in signals:
            matching_individual = next(
                (s for s in individual_signals if s.agent_type == batch_signal.agent_type),
                None
            )
            if matching_individual:
                assert batch_signal.risk_level == matching_individual.risk_level, \
                    f"Risk level mismatch for {batch_signal.agent_type}"
                assert abs(batch_signal.confidence - matching_individual.confidence) < 0.01, \
                    f"Confidence mismatch for {batch_signal.agent_type}"
        
        # Cleanup
        registry.clear()
    
    @given(features=feature_dict_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_agent_modification_isolation(self, features):
        """
        Feature: clinical-ai-system, Property 2: Agent Isolation and Independence
        Validates: Requirements 2.2
        
        Property: Modifications made by one agent to its feature copy should 
        not be visible to other agents.
        """
        registry = create_fresh_registry()
        
        # Register agents that intentionally modify their input
        completeness_agent = CompletenessAgentImpl()
        safety_agent = SafetyAgentImpl()
        
        registry.register(completeness_agent)
        registry.register(safety_agent)
        
        orchestrator = AgentOrchestrator(registry)
        
        # Store original values
        original_missing_pct = features.get("missing_pages_pct", 0)
        original_sae_backlog = features.get("sae_backlog_days", 0)
        
        # Run all agents
        signals = orchestrator.run_all_agents(features, "TEST_STUDY")
        
        # PROPERTY VERIFICATION: Original features unchanged
        assert features.get("missing_pages_pct") == original_missing_pct
        assert features.get("sae_backlog_days") == original_sae_backlog
        
        # PROPERTY VERIFICATION: No cross-contamination markers
        assert "_modified_by_completeness" not in features
        assert "_modified_by_safety" not in features
        
        # PROPERTY VERIFICATION: Each signal reflects original values
        for signal in signals:
            if signal.agent_type == AgentType.COMPLETENESS and not signal.abstained:
                # Evidence should reflect original value, not modified
                for evidence in signal.evidence:
                    if evidence.feature_name == "missing_pages_pct":
                        assert evidence.feature_value == original_missing_pct
            
            elif signal.agent_type == AgentType.SAFETY and not signal.abstained:
                for evidence in signal.evidence:
                    if evidence.feature_name == "sae_backlog_days":
                        assert evidence.feature_value == original_sae_backlog
        
        # Cleanup
        registry.clear()
    
    @given(features=partial_feature_dict_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_agent_independence_with_partial_data(self, features):
        """
        Feature: clinical-ai-system, Property 2: Agent Isolation and Independence
        Validates: Requirements 2.2
        
        Property: Agents should operate independently even when some features 
        are missing - one agent's abstention should not affect others.
        """
        registry = create_fresh_registry()
        
        # Register all test agents
        registry.register(CompletenessAgentImpl())
        registry.register(SafetyAgentImpl())
        registry.register(QueryAgentImpl())
        
        orchestrator = AgentOrchestrator(registry)
        
        # Run all agents
        signals = orchestrator.run_all_agents(features, "TEST_STUDY")
        
        # PROPERTY VERIFICATION: All agents should produce signals
        assert len(signals) == 3
        
        # PROPERTY VERIFICATION: Abstention of one agent doesn't affect others
        abstained_agents = [s for s in signals if s.abstained]
        non_abstained_agents = [s for s in signals if not s.abstained]
        
        # If some agents abstained, others should still produce valid signals
        for signal in non_abstained_agents:
            assert signal.risk_level != RiskSignal.UNKNOWN
            assert signal.confidence > 0
        
        # Abstained agents should have proper abstention signals
        for signal in abstained_agents:
            assert signal.risk_level == RiskSignal.UNKNOWN
            assert signal.confidence == 0.0
            assert signal.abstention_reason is not None
        
        # Cleanup
        registry.clear()
    
    @given(features=feature_dict_strategy())
    @settings(max_examples=50, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_registry_isolation(self, features):
        """
        Feature: clinical-ai-system, Property 2: Agent Isolation and Independence
        Validates: Requirements 2.2
        
        Property: Agent registry operations should not affect running agents.
        """
        registry = create_fresh_registry()
        
        # Register initial agents
        registry.register(CompletenessAgentImpl())
        registry.register(SafetyAgentImpl())
        
        orchestrator = AgentOrchestrator(registry)
        
        # Run first batch
        signals_before = orchestrator.run_all_agents(features, "TEST_STUDY")
        
        # Modify registry (add new agent)
        registry.register(QueryAgentImpl())
        
        # Run second batch with same features
        signals_after = orchestrator.run_all_agents(features, "TEST_STUDY")
        
        # PROPERTY VERIFICATION: Original agents should produce same results
        for signal_before in signals_before:
            matching_after = next(
                (s for s in signals_after if s.agent_type == signal_before.agent_type),
                None
            )
            assert matching_after is not None
            assert signal_before.risk_level == matching_after.risk_level
            assert abs(signal_before.confidence - matching_after.confidence) < 0.01
        
        # Cleanup
        registry.clear()


# ========================================
# UNIT TESTS
# ========================================

class TestAgentIsolationUnit:
    """Unit tests for agent isolation mechanisms"""
    
    def test_deep_copy_isolation(self):
        """Test that deep copy provides true isolation"""
        features = {
            "missing_pages_pct": 10.0,
            "nested": {"value": 100}
        }
        
        # Create deep copy
        copied = copy.deepcopy(features)
        
        # Modify copy
        copied["missing_pages_pct"] = 50.0
        copied["nested"]["value"] = 999
        
        # Original should be unchanged
        assert features["missing_pages_pct"] == 10.0
        assert features["nested"]["value"] == 100
    
    def test_orchestrator_provides_isolation(self):
        """Test that orchestrator provides isolation between agents"""
        registry = create_fresh_registry()
        
        registry.register(CompletenessAgentImpl())
        registry.register(SafetyAgentImpl())
        
        orchestrator = AgentOrchestrator(registry)
        
        features = {
            "missing_pages_pct": 10.0,
            "form_completion_rate": 90.0,
            "sae_backlog_days": 5.0,
            "fatal_sae_count": 0
        }
        
        original = copy.deepcopy(features)
        
        # Run agents
        signals = orchestrator.run_all_agents(features, "TEST")
        
        # Features should be unchanged
        assert features == original
        
        registry.clear()
    
    def test_agent_failure_isolation(self):
        """Test that one agent's failure doesn't affect others"""
        
        class FailingAgent(BaseAgent):
            def __init__(self):
                super().__init__(AgentType.OPERATIONS)
            
            def analyze(self, features, study_id):
                raise RuntimeError("Intentional failure")
            
            def _calculate_confidence(self, features):
                return 1.0
        
        registry = create_fresh_registry()
        
        registry.register(CompletenessAgentImpl())
        registry.register(FailingAgent())
        registry.register(SafetyAgentImpl())
        
        orchestrator = AgentOrchestrator(registry)
        
        features = {
            "missing_pages_pct": 10.0,
            "form_completion_rate": 90.0,
            "sae_backlog_days": 5.0,
            "fatal_sae_count": 0
        }
        
        # Should not raise, should return signals for all agents
        signals = orchestrator.run_all_agents(features, "TEST")
        
        assert len(signals) == 3
        
        # Find the failing agent's signal
        failing_signal = next(s for s in signals if s.agent_type == AgentType.OPERATIONS)
        assert failing_signal.abstained
        assert "failed" in failing_signal.abstention_reason.lower()
        
        # Other agents should have valid signals
        other_signals = [s for s in signals if s.agent_type != AgentType.OPERATIONS]
        for signal in other_signals:
            assert not signal.abstained or signal.abstention_reason is not None
        
        registry.clear()
