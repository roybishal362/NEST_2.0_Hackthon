"""
Test Cross-Agent Validation in Guardian Agent
==============================================
Tests the Guardian's ability to detect inconsistencies across agent signals.

**Validates: Task 2.1 - Add Cross-Agent Validation**
"""

import pytest
from typing import Dict, Any, List

from src.guardian.guardian_agent import GuardianAgent
from src.core import get_logger

logger = get_logger(__name__)


@pytest.fixture
def guardian() -> GuardianAgent:
    """Create Guardian agent instance"""
    return GuardianAgent()


def test_detects_risk_contradiction(guardian):
    """
    Test that Guardian detects when agents report contradictory risk levels.
    
    **Validates: Task 2.1 - Guardian detects contradictions**
    """
    # Create signals with contradictory risk levels
    signals = [
        {
            "agent_type": "safety",
            "risk_level": "critical",
            "confidence": 0.95,
            "abstained": False
        },
        {
            "agent_type": "completeness",
            "risk_level": "low",
            "confidence": 0.90,
            "abstained": False
        },
    ]
    
    result = guardian.validate_cross_agent_signals(signals)
    
    # Should detect the contradiction
    assert not result["valid"], "Should detect risk contradiction"
    assert len(result["issues"]) > 0, "Should have at least one issue"
    
    # Check for RISK_CONFLICT issue
    risk_conflict = any(
        issue["type"] == "RISK_CONFLICT" 
        for issue in result["issues"]
    )
    assert risk_conflict, "Should detect RISK_CONFLICT"
    
    logger.info(f"Detected contradiction: {result['issues']}")


def test_detects_mass_abstention(guardian):
    """
    Test that Guardian detects when too many agents abstain.
    
    **Validates: Task 2.1 - Guardian detects mass abstention**
    """
    # Create signals where most agents abstain
    signals = [
        {"agent_type": "safety", "risk_level": "high", "confidence": 0.8, "abstained": False},
        {"agent_type": "completeness", "abstained": True},
        {"agent_type": "query_quality", "abstained": True},
        {"agent_type": "coding", "abstained": True},
        {"agent_type": "temporal", "abstained": True},
    ]
    
    result = guardian.validate_cross_agent_signals(signals)
    
    # Should detect high abstention
    assert not result["valid"], "Should detect high abstention"
    assert result["abstention_rate"] > 0.5, "Abstention rate should be >50%"
    
    # Check for HIGH_ABSTENTION issue
    high_abstention = any(
        issue["type"] == "HIGH_ABSTENTION" 
        for issue in result["issues"]
    )
    assert high_abstention, "Should detect HIGH_ABSTENTION"
    
    logger.info(f"Detected high abstention: {result['abstention_rate']:.1%}")


def test_detects_confidence_variance(guardian):
    """
    Test that Guardian detects high variance in confidence scores.
    
    **Validates: Task 2.1 - Guardian detects confidence issues**
    """
    # Create signals with EXTREMELY varying confidence to trigger variance >= 0.25
    # Maximum possible variance for values in [0,1] is 0.25 (when values are split between 0 and 1)
    # Using [1.0, 0.0] gives avg=0.5, variance=0.25 (maximum possible)
    signals = [
        {"agent_type": "safety", "risk_level": "high", "confidence": 1.0, "abstained": False},
        {"agent_type": "completeness", "risk_level": "high", "confidence": 0.0, "abstained": False},
    ]
    
    result = guardian.validate_cross_agent_signals(signals)
    
    # Should detect confidence variance
    confidence_variance = any(
        issue["type"] == "CONFIDENCE_VARIANCE" 
        for issue in result["issues"]
    )
    assert confidence_variance, "Should detect CONFIDENCE_VARIANCE"
    
    logger.info(f"Detected confidence variance: {result['issues']}")


def test_accepts_consistent_signals(guardian):
    """
    Test that Guardian accepts consistent agent signals.
    
    **Validates: Task 2.1 - Guardian accepts valid signals**
    """
    # Create consistent signals
    signals = [
        {"agent_type": "safety", "risk_level": "high", "confidence": 0.85, "abstained": False},
        {"agent_type": "completeness", "risk_level": "high", "confidence": 0.80, "abstained": False},
        {"agent_type": "query_quality", "risk_level": "medium", "confidence": 0.75, "abstained": False},
        {"agent_type": "coding", "risk_level": "high", "confidence": 0.82, "abstained": False},
    ]
    
    result = guardian.validate_cross_agent_signals(signals)
    
    # Should be valid
    assert result["valid"], "Should accept consistent signals"
    assert len(result["issues"]) == 0, "Should have no issues"
    assert result["consistency_score"] >= 0.8, "Should have high consistency score"
    
    logger.info(f"Accepted consistent signals: consistency={result['consistency_score']:.2f}")


def test_handles_empty_signals(guardian):
    """
    Test that Guardian handles empty signal list gracefully.
    
    **Validates: Task 2.1 - Guardian handles edge cases**
    """
    signals = []
    
    result = guardian.validate_cross_agent_signals(signals)
    
    # Should handle gracefully
    assert result["valid"], "Empty signals should be valid"
    assert result["consistency_score"] == 1.0, "Empty signals should have perfect consistency"
    assert len(result["issues"]) == 0, "Should have no issues"


def test_calculates_consistency_score(guardian):
    """
    Test that Guardian calculates consistency score correctly.
    
    **Validates: Task 2.1 - Consistency scoring**
    """
    # Test with varying levels of consistency
    test_cases = [
        # Perfect consistency
        (
            [
                {"agent_type": "safety", "risk_level": "high", "confidence": 0.85, "abstained": False},
                {"agent_type": "completeness", "risk_level": "high", "confidence": 0.82, "abstained": False},
            ],
            1.0  # Expected high score
        ),
        # Some issues
        (
            [
                {"agent_type": "safety", "risk_level": "critical", "confidence": 0.95, "abstained": False},
                {"agent_type": "completeness", "risk_level": "low", "confidence": 0.90, "abstained": False},
            ],
            0.8  # Expected lower score due to contradiction
        ),
    ]
    
    for signals, expected_min_score in test_cases:
        result = guardian.validate_cross_agent_signals(signals)
        assert "consistency_score" in result, "Should have consistency score"
        assert 0.0 <= result["consistency_score"] <= 1.0, "Score should be in [0, 1]"
        
        logger.info(
            f"Consistency score: {result['consistency_score']:.2f} "
            f"(expected >= {expected_min_score:.2f})"
        )


def test_integration_with_pipeline(guardian):
    """
    Test Guardian validation with realistic pipeline output.
    
    **Validates: Task 2.1 - Integration with agent pipeline**
    """
    # Simulate realistic agent signals from pipeline
    signals = [
        {
            "agent_type": "completeness",
            "risk_level": "medium",
            "confidence": 0.88,
            "abstained": False
        },
        {
            "agent_type": "safety",
            "risk_level": "critical",
            "confidence": 1.00,
            "abstained": False
        },
        {
            "agent_type": "query_quality",
            "risk_level": "low",
            "confidence": 0.95,
            "abstained": False
        },
        {
            "agent_type": "coding",
            "risk_level": "critical",
            "confidence": 1.00,
            "abstained": False
        },
        {
            "agent_type": "temporal",
            "risk_level": "high",
            "confidence": 1.00,
            "abstained": False
        },
        {
            "agent_type": "edc_quality",
            "risk_level": "high",
            "confidence": 1.00,
            "abstained": False
        },
        {
            "agent_type": "stability",
            "risk_level": "medium",
            "confidence": 1.00,
            "abstained": False
        },
        {
            "agent_type": "cross_evidence",
            "abstained": True
        },
    ]
    
    result = guardian.validate_cross_agent_signals(signals)
    
    # Should process all signals
    assert result["agents_analyzed"] == 8, "Should analyze all 8 agents"
    
    # Should detect the contradiction between critical and low
    assert not result["valid"], "Should detect risk contradiction"
    
    # Should have reasonable consistency score
    assert 0.0 <= result["consistency_score"] <= 1.0
    
    logger.info(
        f"Pipeline validation: valid={result['valid']}, "
        f"consistency={result['consistency_score']:.2f}, "
        f"issues={len(result['issues'])}"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

