"""
Test DQI Consistency Validation in Guardian Agent
==================================================
Tests the Guardian's ability to detect inconsistencies between DQI scores
and underlying feature values.

**Validates: Task 2.2 - Add DQI Consistency Validation**
"""

import pytest
from typing import Dict, Any

from src.guardian.guardian_agent import GuardianAgent
from src.core import get_logger

logger = get_logger(__name__)


@pytest.fixture
def guardian() -> GuardianAgent:
    """Create Guardian agent instance"""
    return GuardianAgent()


def test_detects_high_dqi_with_many_queries(guardian):
    """
    Test that Guardian detects high DQI with many open queries.
    
    **Validates: Task 2.2 - DQI-Query mismatch detection**
    """
    dqi_score = 75.0
    features = {
        "open_queries": 250,  # Many queries
        "completeness_rate": 0.85,
    }
    
    result = guardian.validate_dqi_consistency(dqi_score, features)
    
    # Should detect the mismatch
    assert not result["valid"], "Should detect DQI-query mismatch"
    assert len(result["issues"]) > 0, "Should have at least one issue"
    
    # Check for DQI_QUERY_MISMATCH issue
    query_mismatch = any(
        issue["type"] == "DQI_QUERY_MISMATCH"
        for issue in result["issues"]
    )
    assert query_mismatch, "Should detect DQI_QUERY_MISMATCH"
    
    logger.info(f"Detected DQI-query mismatch: {result['issues']}")


def test_detects_high_dqi_with_overdue_saes(guardian):
    """
    Test that Guardian detects high DQI with overdue SAE reviews.
    
    **Validates: Task 2.2 - DQI-Safety mismatch detection**
    """
    dqi_score = 85.0
    features = {
        "overdue_sae_reviews": 15,  # Many overdue SAEs
        "completeness_rate": 0.90,
    }
    
    result = guardian.validate_dqi_consistency(dqi_score, features)
    
    # Should detect the critical mismatch
    assert not result["valid"], "Should detect DQI-safety mismatch"
    
    # Check for DQI_SAFETY_MISMATCH issue with CRITICAL severity
    safety_mismatch = any(
        issue["type"] == "DQI_SAFETY_MISMATCH" and issue["severity"] == "CRITICAL"
        for issue in result["issues"]
    )
    assert safety_mismatch, "Should detect CRITICAL DQI_SAFETY_MISMATCH"
    
    logger.info(f"Detected DQI-safety mismatch: {result['issues']}")


def test_detects_low_dqi_with_high_completeness(guardian):
    """
    Test that Guardian detects low DQI with excellent completeness.
    
    **Validates: Task 2.2 - DQI underestimate detection**
    """
    dqi_score = 45.0
    features = {
        "completeness_rate": 0.97,  # Excellent completeness
        "open_queries": 50,
    }
    
    result = guardian.validate_dqi_consistency(dqi_score, features)
    
    # Should detect the underestimate
    assert not result["valid"], "Should detect DQI underestimate"
    
    # Check for DQI_UNDERESTIMATE issue
    underestimate = any(
        issue["type"] == "DQI_UNDERESTIMATE"
        for issue in result["issues"]
    )
    assert underestimate, "Should detect DQI_UNDERESTIMATE"
    
    logger.info(f"Detected DQI underestimate: {result['issues']}")


def test_detects_high_dqi_with_low_completeness(guardian):
    """
    Test that Guardian detects high DQI with low completeness.
    
    **Validates: Task 2.2 - DQI-Completeness mismatch detection**
    """
    dqi_score = 85.0
    features = {
        "completeness_rate": 0.65,  # Low completeness
        "open_queries": 30,
    }
    
    result = guardian.validate_dqi_consistency(dqi_score, features)
    
    # Should detect the mismatch
    assert not result["valid"], "Should detect DQI-completeness mismatch"
    
    # Check for DQI_COMPLETENESS_MISMATCH issue
    completeness_mismatch = any(
        issue["type"] == "DQI_COMPLETENESS_MISMATCH"
        for issue in result["issues"]
    )
    assert completeness_mismatch, "Should detect DQI_COMPLETENESS_MISMATCH"
    
    logger.info(f"Detected DQI-completeness mismatch: {result['issues']}")


def test_detects_high_dqi_with_missing_fields(guardian):
    """
    Test that Guardian detects high DQI with many missing required fields.
    
    **Validates: Task 2.2 - DQI-Missing data mismatch detection**
    """
    dqi_score = 80.0
    features = {
        "missing_required_fields": 75,  # Many missing fields
        "completeness_rate": 0.80,
    }
    
    result = guardian.validate_dqi_consistency(dqi_score, features)
    
    # Should detect the mismatch
    assert not result["valid"], "Should detect DQI-missing data mismatch"
    
    # Check for DQI_MISSING_DATA_MISMATCH issue
    missing_data_mismatch = any(
        issue["type"] == "DQI_MISSING_DATA_MISMATCH"
        for issue in result["issues"]
    )
    assert missing_data_mismatch, "Should detect DQI_MISSING_DATA_MISMATCH"
    
    logger.info(f"Detected DQI-missing data mismatch: {result['issues']}")


def test_accepts_consistent_dqi(guardian):
    """
    Test that Guardian accepts consistent DQI score.
    
    **Validates: Task 2.2 - Guardian accepts valid DQI**
    """
    dqi_score = 75.0
    features = {
        "open_queries": 50,  # Reasonable
        "overdue_sae_reviews": 2,  # Low
        "completeness_rate": 0.85,  # Good
        "missing_required_fields": 10,  # Low
    }
    
    result = guardian.validate_dqi_consistency(dqi_score, features)
    
    # Should be valid
    assert result["valid"], "Should accept consistent DQI"
    assert len(result["issues"]) == 0, "Should have no issues"
    assert result["dqi_score"] == dqi_score
    
    logger.info(f"Accepted consistent DQI: {dqi_score}")


def test_handles_missing_features(guardian):
    """
    Test that Guardian handles missing features gracefully.
    
    **Validates: Task 2.2 - Guardian handles edge cases**
    """
    dqi_score = 70.0
    features = {}  # No features provided
    
    result = guardian.validate_dqi_consistency(dqi_score, features)
    
    # Should handle gracefully (no issues since no features to check)
    assert result["valid"], "Should handle missing features gracefully"
    assert len(result["issues"]) == 0, "Should have no issues"
    assert result["features_checked"] == 0
    
    logger.info("Handled missing features gracefully")


def test_multiple_issues_detected(guardian):
    """
    Test that Guardian detects multiple issues simultaneously.
    
    **Validates: Task 2.2 - Multiple issue detection**
    """
    dqi_score = 85.0
    features = {
        "open_queries": 250,  # Too many
        "overdue_sae_reviews": 12,  # Too many
        "completeness_rate": 0.65,  # Too low
        "missing_required_fields": 60,  # Too many
    }
    
    result = guardian.validate_dqi_consistency(dqi_score, features)
    
    # Should detect multiple issues
    assert not result["valid"], "Should detect multiple issues"
    assert len(result["issues"]) >= 3, "Should have at least 3 issues"
    
    # Check that different issue types are detected
    issue_types = {issue["type"] for issue in result["issues"]}
    assert "DQI_QUERY_MISMATCH" in issue_types
    assert "DQI_SAFETY_MISMATCH" in issue_types
    assert "DQI_COMPLETENESS_MISMATCH" in issue_types
    
    logger.info(f"Detected {len(result['issues'])} issues: {issue_types}")


def test_severity_levels(guardian):
    """
    Test that Guardian assigns correct severity levels.
    
    **Validates: Task 2.2 - Severity assignment**
    """
    # Test CRITICAL severity for safety issues
    result1 = guardian.validate_dqi_consistency(
        85.0,
        {"overdue_sae_reviews": 15}
    )
    critical_issue = next(
        (i for i in result1["issues"] if i["type"] == "DQI_SAFETY_MISMATCH"),
        None
    )
    assert critical_issue is not None
    assert critical_issue["severity"] == "CRITICAL", "Safety issues should be CRITICAL"
    
    # Test WARNING severity for query issues
    result2 = guardian.validate_dqi_consistency(
        75.0,
        {"open_queries": 250}
    )
    warning_issue = next(
        (i for i in result2["issues"] if i["type"] == "DQI_QUERY_MISMATCH"),
        None
    )
    assert warning_issue is not None
    assert warning_issue["severity"] == "WARNING", "Query issues should be WARNING"
    
    # Test INFO severity for underestimate
    result3 = guardian.validate_dqi_consistency(
        45.0,
        {"completeness_rate": 0.97}
    )
    info_issue = next(
        (i for i in result3["issues"] if i["type"] == "DQI_UNDERESTIMATE"),
        None
    )
    assert info_issue is not None
    assert info_issue["severity"] == "INFO", "Underestimate should be INFO"
    
    logger.info("Verified severity levels: CRITICAL, WARNING, INFO")


def test_recommendations_provided(guardian):
    """
    Test that Guardian provides actionable recommendations.
    
    **Validates: Task 2.2 - Recommendations included**
    """
    dqi_score = 85.0
    features = {
        "overdue_sae_reviews": 15,
    }
    
    result = guardian.validate_dqi_consistency(dqi_score, features)
    
    # Should have recommendations
    assert len(result["issues"]) > 0
    for issue in result["issues"]:
        assert "recommendation" in issue, "Each issue should have a recommendation"
        assert len(issue["recommendation"]) > 0, "Recommendation should not be empty"
    
    logger.info(f"Recommendations provided: {[i['recommendation'] for i in result['issues']]}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
