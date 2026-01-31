"""
Unit Tests for Risk Assessment Engine
=====================================
Tests the risk assessment and decision engine functionality.

**Validates: Requirements 2.4**
"""

import pytest
from datetime import datetime

from src.intelligence.base_agent import AgentSignal, AgentType, RiskSignal
from src.consensus.consensus_engine import ConsensusEngine, ConsensusResult, ConsensusRiskLevel
from src.consensus.risk_assessment import (
    RiskAssessmentEngine,
    RiskDecision,
    RecommendedAction,
    ActionPriority,
    ActionType,
)


class TestRiskAssessmentEngine:
    """Unit tests for RiskAssessmentEngine"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.consensus_engine = ConsensusEngine()
        self.risk_engine = RiskAssessmentEngine()
    
    def _create_signal(
        self,
        agent_type: AgentType,
        risk_level: RiskSignal,
        confidence: float = 0.8
    ) -> AgentSignal:
        """Helper to create agent signals"""
        return AgentSignal(
            agent_type=agent_type,
            risk_level=risk_level,
            confidence=confidence,
            evidence=[],
            recommended_actions=[],
            abstained=False,
            abstention_reason=None,
        )
    
    def test_critical_high_confidence_produces_immediate_escalation(self):
        """Test that CRITICAL risk with high confidence produces immediate escalation"""
        # Create critical safety signal
        signal = self._create_signal(AgentType.SAFETY, RiskSignal.CRITICAL, 0.9)
        
        consensus = self.consensus_engine.calculate_consensus([signal], "TEST_SITE")
        decision = self.risk_engine.assess_risk(consensus, "SITE")
        
        assert decision.risk_level == ConsensusRiskLevel.CRITICAL
        assert len(decision.recommended_actions) > 0
        
        # First action should be immediate priority
        top_action = decision.recommended_actions[0]
        assert top_action.priority == ActionPriority.IMMEDIATE
        assert top_action.action_type in [ActionType.ESCALATE, ActionType.REVIEW]
    
    def test_high_risk_produces_high_priority_action(self):
        """Test that HIGH risk produces high priority action"""
        signal = self._create_signal(AgentType.COMPLETENESS, RiskSignal.HIGH, 0.8)
        
        consensus = self.consensus_engine.calculate_consensus([signal], "TEST_SITE")
        decision = self.risk_engine.assess_risk(consensus, "SITE")
        
        assert decision.risk_level in [ConsensusRiskLevel.HIGH, ConsensusRiskLevel.MEDIUM]
        assert len(decision.recommended_actions) > 0
        
        # Should have at least medium priority
        priorities = [a.priority for a in decision.recommended_actions]
        assert any(p in [ActionPriority.IMMEDIATE, ActionPriority.HIGH, ActionPriority.MEDIUM] for p in priorities)
    
    def test_low_risk_produces_routine_monitoring(self):
        """Test that LOW risk produces routine monitoring action"""
        signal = self._create_signal(AgentType.COMPLETENESS, RiskSignal.LOW, 0.9)
        
        consensus = self.consensus_engine.calculate_consensus([signal], "TEST_SITE")
        decision = self.risk_engine.assess_risk(consensus, "SITE")
        
        assert decision.risk_level == ConsensusRiskLevel.LOW
        assert len(decision.recommended_actions) > 0
        
        # Should have low priority monitoring
        top_action = decision.recommended_actions[0]
        assert top_action.priority == ActionPriority.LOW
        assert top_action.action_type == ActionType.MONITOR
    
    def test_low_confidence_triggers_review(self):
        """Test that low confidence triggers human review"""
        # Create high risk but low confidence signal
        signal = self._create_signal(AgentType.SAFETY, RiskSignal.HIGH, 0.3)
        
        consensus = self.consensus_engine.calculate_consensus([signal], "TEST_SITE")
        decision = self.risk_engine.assess_risk(consensus, "SITE")
        
        # Should recommend review due to low confidence
        action_types = [a.action_type for a in decision.recommended_actions]
        assert ActionType.REVIEW in action_types or ActionType.MONITOR in action_types
    
    def test_decision_contains_rationale(self):
        """Test that decision contains meaningful rationale"""
        signal = self._create_signal(AgentType.SAFETY, RiskSignal.MEDIUM, 0.7)
        
        consensus = self.consensus_engine.calculate_consensus([signal], "TEST_SITE")
        decision = self.risk_engine.assess_risk(consensus, "SITE")
        
        assert decision.decision_rationale is not None
        assert len(decision.decision_rationale) > 0
        assert "risk" in decision.decision_rationale.lower() or "Risk" in decision.decision_rationale
    
    def test_decision_contains_contributing_factors(self):
        """Test that decision lists contributing factors"""
        signals = [
            self._create_signal(AgentType.SAFETY, RiskSignal.HIGH, 0.8),
            self._create_signal(AgentType.COMPLETENESS, RiskSignal.MEDIUM, 0.7),
        ]
        
        consensus = self.consensus_engine.calculate_consensus(signals, "TEST_SITE")
        decision = self.risk_engine.assess_risk(consensus, "SITE")
        
        assert decision.contributing_factors is not None
        assert len(decision.contributing_factors) > 0
    
    def test_action_has_target_role(self):
        """Test that actions have assigned target roles"""
        signal = self._create_signal(AgentType.SAFETY, RiskSignal.CRITICAL, 0.9)
        
        consensus = self.consensus_engine.calculate_consensus([signal], "TEST_SITE")
        decision = self.risk_engine.assess_risk(consensus, "SITE")
        
        for action in decision.recommended_actions:
            assert action.target_role is not None
            assert action.target_role in ["STUDY_LEAD", "DATA_MANAGER", "CRA"]
    
    def test_action_has_due_within_hours(self):
        """Test that actions have due within hours set"""
        signal = self._create_signal(AgentType.SAFETY, RiskSignal.CRITICAL, 0.9)
        
        consensus = self.consensus_engine.calculate_consensus([signal], "TEST_SITE")
        decision = self.risk_engine.assess_risk(consensus, "SITE")
        
        for action in decision.recommended_actions:
            if action.priority != ActionPriority.INFORMATIONAL:
                assert action.due_within_hours is not None
                assert action.due_within_hours > 0
    
    def test_decision_to_dict_serialization(self):
        """Test that decision can be serialized to dict"""
        signal = self._create_signal(AgentType.SAFETY, RiskSignal.HIGH, 0.8)
        
        consensus = self.consensus_engine.calculate_consensus([signal], "TEST_SITE")
        decision = self.risk_engine.assess_risk(consensus, "SITE")
        
        decision_dict = decision.to_dict()
        
        assert "entity_id" in decision_dict
        assert "risk_level" in decision_dict
        assert "recommended_actions" in decision_dict
        assert "decision_rationale" in decision_dict
        assert decision_dict["entity_id"] == "TEST_SITE"
    
    def test_multiple_agents_generate_multiple_actions(self):
        """Test that multiple high-risk agents generate multiple actions"""
        signals = [
            self._create_signal(AgentType.SAFETY, RiskSignal.CRITICAL, 0.9),
            self._create_signal(AgentType.COMPLETENESS, RiskSignal.HIGH, 0.8),
            self._create_signal(AgentType.QUERY_QUALITY, RiskSignal.HIGH, 0.7),
        ]
        
        consensus = self.consensus_engine.calculate_consensus(signals, "TEST_SITE")
        decision = self.risk_engine.assess_risk(consensus, "SITE")
        
        # Should have multiple actions for different agents
        assert len(decision.recommended_actions) >= 2
    
    def test_unknown_risk_triggers_review(self):
        """Test that UNKNOWN risk (all abstained) triggers review"""
        # Create abstained signals
        signals = [
            AgentSignal(
                agent_type=AgentType.SAFETY,
                risk_level=RiskSignal.UNKNOWN,
                confidence=0.0,
                abstained=True,
                abstention_reason="Insufficient data",
            ),
        ]
        
        consensus = self.consensus_engine.calculate_consensus(signals, "TEST_SITE")
        decision = self.risk_engine.assess_risk(consensus, "SITE")
        
        assert decision.risk_level == ConsensusRiskLevel.UNKNOWN
        assert len(decision.recommended_actions) > 0
        
        # Should recommend review
        action_types = [a.action_type for a in decision.recommended_actions]
        assert ActionType.REVIEW in action_types


class TestRecommendedAction:
    """Unit tests for RecommendedAction"""
    
    def test_action_to_dict(self):
        """Test action serialization"""
        action = RecommendedAction(
            action_type=ActionType.ESCALATE,
            priority=ActionPriority.IMMEDIATE,
            description="Test action",
            target_role="STUDY_LEAD",
            due_within_hours=4,
            evidence_summary="Test evidence",
        )
        
        action_dict = action.to_dict()
        
        assert action_dict["action_type"] == "ESCALATE"
        assert action_dict["priority"] == "IMMEDIATE"
        assert action_dict["description"] == "Test action"
        assert action_dict["target_role"] == "STUDY_LEAD"
        assert action_dict["due_within_hours"] == 4


class TestIntegration:
    """Integration tests for consensus and risk assessment"""
    
    def test_full_pipeline_critical_risk(self):
        """Test full pipeline from signals to decision for critical risk"""
        # Create signals
        signals = [
            AgentSignal(
                agent_type=AgentType.SAFETY,
                risk_level=RiskSignal.CRITICAL,
                confidence=0.95,
                abstained=False,
                abstention_reason=None,
            ),
            AgentSignal(
                agent_type=AgentType.COMPLETENESS,
                risk_level=RiskSignal.HIGH,
                confidence=0.85,
                abstained=False,
                abstention_reason=None,
            ),
        ]
        
        # Run consensus
        consensus_engine = ConsensusEngine()
        consensus = consensus_engine.calculate_consensus(signals, "SITE_001")
        
        # Run risk assessment
        risk_engine = RiskAssessmentEngine()
        decision = risk_engine.assess_risk(consensus, "SITE")
        
        # Verify full pipeline
        assert decision.entity_id == "SITE_001"
        assert decision.risk_level == ConsensusRiskLevel.CRITICAL
        assert decision.confidence > 0.5
        assert len(decision.recommended_actions) > 0
        assert decision.recommended_actions[0].priority == ActionPriority.IMMEDIATE
    
    def test_full_pipeline_low_risk(self):
        """Test full pipeline from signals to decision for low risk"""
        signals = [
            AgentSignal(
                agent_type=AgentType.SAFETY,
                risk_level=RiskSignal.LOW,
                confidence=0.9,
                abstained=False,
                abstention_reason=None,
            ),
            AgentSignal(
                agent_type=AgentType.COMPLETENESS,
                risk_level=RiskSignal.LOW,
                confidence=0.85,
                abstained=False,
                abstention_reason=None,
            ),
        ]
        
        consensus_engine = ConsensusEngine()
        consensus = consensus_engine.calculate_consensus(signals, "SITE_002")
        
        risk_engine = RiskAssessmentEngine()
        decision = risk_engine.assess_risk(consensus, "SITE")
        
        assert decision.entity_id == "SITE_002"
        assert decision.risk_level == ConsensusRiskLevel.LOW
        assert decision.recommended_actions[0].priority == ActionPriority.LOW
        assert decision.recommended_actions[0].action_type == ActionType.MONITOR
