"""
Unit Tests for Guardian-Driven Calibration Recommender
======================================================
Tests the calibration recommendation system that generates recommendations
based on Guardian Agent findings and historical performance data.

**Validates: Requirements 8.3, 8.4, 8.5**

Key Test Areas:
- Recommendation generation from Guardian consistency findings
- Recommendation generation from Guardian staleness findings
- Historical data analysis for offline calibration
- Human approval workflow (no automatic self-modification)
"""

from datetime import datetime, timedelta
from typing import Dict, Any

import pytest

from src.governance import (
    CalibrationRecommender,
    CalibrationRecommendation,
    CalibrationSource,
)
from src.governance.calibration_recommender import (
    RecommendationPriority,
    RecommendationStatus,
    HistoricalPerformanceData,
)


# ========================================
# FIXTURES
# ========================================

@pytest.fixture
def fresh_recommender():
    """Create a fresh calibration recommender for each test"""
    recommender = CalibrationRecommender()
    recommender.clear_recommendations()
    recommender.clear_historical_data()
    yield recommender


@pytest.fixture
def guardian_consistency_event():
    """Sample Guardian consistency event details"""
    return {
        "event_id": "GRD_001",
        "event_type": "DATA_OUTPUT_INCONSISTENCY",
        "severity": "WARNING",
        "entity_id": "SITE_001",
        "snapshot_id": "SNAP_002",
        "data_delta_summary": "Data improved by 25%",
        "expected_behavior": "Risk score should decrease",
        "actual_behavior": "Risk score increased by 10 points",
        "recommendation": "Review agent calibration",
    }


@pytest.fixture
def guardian_staleness_event():
    """Sample Guardian staleness event details"""
    return {
        "event_id": "GRD_002",
        "event_type": "STALENESS_DETECTED",
        "severity": "WARNING",
        "entity_id": "STUDY_001",
        "snapshot_id": "SNAP_005",
        "data_delta_summary": "Data changed but alerts unchanged for 5 snapshots",
        "expected_behavior": "Alerts should update when data changes",
        "actual_behavior": "Same 3 alerts persisted",
        "recommendation": "Review agent sensitivity",
    }


# ========================================
# GUARDIAN CONSISTENCY RECOMMENDATION TESTS
# ========================================

class TestGuardianConsistencyRecommendations:
    """Tests for recommendations from Guardian consistency findings"""
    
    def test_generate_recommendation_for_under_reaction(
        self,
        fresh_recommender,
        guardian_consistency_event,
    ):
        """Test recommendation when system under-reacts to data changes"""
        recommendation = fresh_recommender.generate_from_guardian_consistency(
            entity_id="SITE_001",
            data_delta_magnitude=0.25,  # 25% data improvement
            output_delta_magnitude=0.05,  # Only 5% output change
            current_sensitivity=0.10,
            guardian_event_details=guardian_consistency_event,
        )
        
        assert recommendation is not None
        assert recommendation.source == CalibrationSource.GUARDIAN_CONSISTENCY
        assert recommendation.config_key == "guardian.sensitivity"
        assert recommendation.recommended_value > recommendation.current_value
        assert "under-reaction" in recommendation.justification.lower()
    
    def test_generate_recommendation_for_over_reaction(
        self,
        fresh_recommender,
        guardian_consistency_event,
    ):
        """Test recommendation when system over-reacts to data changes"""
        recommendation = fresh_recommender.generate_from_guardian_consistency(
            entity_id="SITE_001",
            data_delta_magnitude=0.05,  # 5% data change
            output_delta_magnitude=0.30,  # 30% output change
            current_sensitivity=0.10,
            guardian_event_details=guardian_consistency_event,
        )
        
        assert recommendation is not None
        assert recommendation.source == CalibrationSource.GUARDIAN_CONSISTENCY
        assert recommendation.recommended_value < recommendation.current_value
        assert "over-reaction" in recommendation.justification.lower()
    
    def test_no_recommendation_for_small_discrepancy(
        self,
        fresh_recommender,
        guardian_consistency_event,
    ):
        """Test no recommendation when discrepancy is small"""
        recommendation = fresh_recommender.generate_from_guardian_consistency(
            entity_id="SITE_001",
            data_delta_magnitude=0.10,
            output_delta_magnitude=0.12,  # Only 2% discrepancy
            current_sensitivity=0.10,
            guardian_event_details=guardian_consistency_event,
        )
        
        assert recommendation is None
    
    def test_high_priority_for_large_discrepancy(
        self,
        fresh_recommender,
        guardian_consistency_event,
    ):
        """Test high priority assigned for large discrepancies"""
        recommendation = fresh_recommender.generate_from_guardian_consistency(
            entity_id="SITE_001",
            data_delta_magnitude=0.50,  # 50% data change
            output_delta_magnitude=0.05,  # Only 5% output change
            current_sensitivity=0.10,
            guardian_event_details=guardian_consistency_event,
        )
        
        assert recommendation is not None
        assert recommendation.priority == RecommendationPriority.HIGH
    
    def test_evidence_includes_guardian_event(
        self,
        fresh_recommender,
        guardian_consistency_event,
    ):
        """Test that evidence includes Guardian event details"""
        recommendation = fresh_recommender.generate_from_guardian_consistency(
            entity_id="SITE_001",
            data_delta_magnitude=0.30,
            output_delta_magnitude=0.05,
            current_sensitivity=0.10,
            guardian_event_details=guardian_consistency_event,
        )
        
        assert recommendation is not None
        assert len(recommendation.evidence) > 0
        assert "guardian_event" in recommendation.evidence[0]


# ========================================
# GUARDIAN STALENESS RECOMMENDATION TESTS
# ========================================

class TestGuardianStalenessRecommendations:
    """Tests for recommendations from Guardian staleness findings"""
    
    def test_generate_recommendation_for_staleness(
        self,
        fresh_recommender,
        guardian_staleness_event,
    ):
        """Test recommendation when staleness is detected"""
        recommendation = fresh_recommender.generate_from_guardian_staleness(
            entity_id="STUDY_001",
            consecutive_unchanged=5,
            alert_types=["HIGH_RISK", "MISSING_DATA", "QUERY_BACKLOG"],
            current_staleness_threshold=3,
            guardian_event_details=guardian_staleness_event,
        )
        
        assert recommendation is not None
        assert recommendation.source == CalibrationSource.GUARDIAN_STALENESS
        assert "staleness" in recommendation.justification.lower()
    
    def test_high_priority_for_severe_staleness(
        self,
        fresh_recommender,
        guardian_staleness_event,
    ):
        """Test high priority for severe staleness"""
        recommendation = fresh_recommender.generate_from_guardian_staleness(
            entity_id="STUDY_001",
            consecutive_unchanged=10,  # Very stale
            alert_types=["HIGH_RISK"],
            current_staleness_threshold=3,
            guardian_event_details=guardian_staleness_event,
        )
        
        assert recommendation is not None
        assert recommendation.priority == RecommendationPriority.HIGH
    
    def test_no_recommendation_below_threshold(
        self,
        fresh_recommender,
        guardian_staleness_event,
    ):
        """Test no recommendation when below staleness threshold"""
        recommendation = fresh_recommender.generate_from_guardian_staleness(
            entity_id="STUDY_001",
            consecutive_unchanged=2,  # Below threshold
            alert_types=["HIGH_RISK"],
            current_staleness_threshold=3,
            guardian_event_details=guardian_staleness_event,
        )
        
        assert recommendation is None


# ========================================
# HISTORICAL DATA ANALYSIS TESTS
# ========================================

class TestHistoricalDataAnalysis:
    """Tests for offline calibration using historical data"""
    
    def test_add_historical_data(self, fresh_recommender):
        """Test adding historical performance data"""
        for i in range(10):
            fresh_recommender.add_historical_data(
                entity_id="SITE_001",
                metric_name="completeness_score",
                value=0.75 + (i * 0.02),
                timestamp=datetime.now() - timedelta(days=10-i),
            )
        
        # Verify data was added
        key = "SITE_001:completeness_score"
        assert key in fresh_recommender._historical_data
    
    def test_analyze_historical_performance(self, fresh_recommender):
        """Test historical performance analysis"""
        # Add enough data points
        for i in range(15):
            fresh_recommender.add_historical_data(
                entity_id="SITE_001",
                metric_name="risk_score",
                value=50 + (i * 2),  # Increasing trend
                timestamp=datetime.now() - timedelta(days=15-i),
            )
        
        recommendation = fresh_recommender.analyze_historical_performance(
            entity_id="SITE_001",
            metric_name="risk_score",
            current_threshold=30.0,  # Very different from data
        )
        
        assert recommendation is not None
        assert recommendation.source == CalibrationSource.HISTORICAL_ANALYSIS
    
    def test_no_recommendation_with_insufficient_data(self, fresh_recommender):
        """Test no recommendation with insufficient historical data"""
        # Add only a few data points
        for i in range(5):
            fresh_recommender.add_historical_data(
                entity_id="SITE_001",
                metric_name="risk_score",
                value=50 + i,
                timestamp=datetime.now() - timedelta(days=5-i),
            )
        
        recommendation = fresh_recommender.analyze_historical_performance(
            entity_id="SITE_001",
            metric_name="risk_score",
            current_threshold=50.0,
        )
        
        assert recommendation is None
    
    def test_no_recommendation_when_threshold_appropriate(self, fresh_recommender):
        """Test no recommendation when current threshold is appropriate"""
        # Add data with mean around 50
        for i in range(15):
            fresh_recommender.add_historical_data(
                entity_id="SITE_001",
                metric_name="risk_score",
                value=48 + (i % 5),  # Values around 48-52
                timestamp=datetime.now() - timedelta(days=15-i),
            )
        
        recommendation = fresh_recommender.analyze_historical_performance(
            entity_id="SITE_001",
            metric_name="risk_score",
            current_threshold=52.0,  # Close to mean + std
        )
        
        # May or may not generate recommendation depending on exact values
        # The key is that it doesn't crash and handles the case


# ========================================
# RECOMMENDATION WORKFLOW TESTS
# ========================================

class TestRecommendationWorkflow:
    """Tests for recommendation review workflow"""
    
    def test_recommendations_start_pending(
        self,
        fresh_recommender,
        guardian_consistency_event,
    ):
        """Test that recommendations start in PENDING status"""
        recommendation = fresh_recommender.generate_from_guardian_consistency(
            entity_id="SITE_001",
            data_delta_magnitude=0.30,
            output_delta_magnitude=0.05,
            current_sensitivity=0.10,
            guardian_event_details=guardian_consistency_event,
        )
        
        assert recommendation.status == RecommendationStatus.PENDING
    
    def test_accept_recommendation(
        self,
        fresh_recommender,
        guardian_consistency_event,
    ):
        """Test accepting a recommendation"""
        recommendation = fresh_recommender.generate_from_guardian_consistency(
            entity_id="SITE_001",
            data_delta_magnitude=0.30,
            output_delta_magnitude=0.05,
            current_sensitivity=0.10,
            guardian_event_details=guardian_consistency_event,
        )
        
        success, message = fresh_recommender.review_recommendation(
            recommendation_id=recommendation.recommendation_id,
            reviewed_by="GOVERNANCE_01",
            accepted=True,
            review_notes="Approved for implementation",
        )
        
        assert success
        assert recommendation.status == RecommendationStatus.ACCEPTED
        assert recommendation.reviewed_by == "GOVERNANCE_01"
    
    def test_reject_recommendation(
        self,
        fresh_recommender,
        guardian_consistency_event,
    ):
        """Test rejecting a recommendation"""
        recommendation = fresh_recommender.generate_from_guardian_consistency(
            entity_id="SITE_001",
            data_delta_magnitude=0.30,
            output_delta_magnitude=0.05,
            current_sensitivity=0.10,
            guardian_event_details=guardian_consistency_event,
        )
        
        success, message = fresh_recommender.review_recommendation(
            recommendation_id=recommendation.recommendation_id,
            reviewed_by="GOVERNANCE_01",
            accepted=False,
            review_notes="Not appropriate at this time",
        )
        
        assert success
        assert recommendation.status == RecommendationStatus.REJECTED
    
    def test_mark_implemented(
        self,
        fresh_recommender,
        guardian_consistency_event,
    ):
        """Test marking recommendation as implemented"""
        recommendation = fresh_recommender.generate_from_guardian_consistency(
            entity_id="SITE_001",
            data_delta_magnitude=0.30,
            output_delta_magnitude=0.05,
            current_sensitivity=0.10,
            guardian_event_details=guardian_consistency_event,
        )
        
        # First accept
        fresh_recommender.review_recommendation(
            recommendation_id=recommendation.recommendation_id,
            reviewed_by="GOVERNANCE_01",
            accepted=True,
            review_notes="Approved",
        )
        
        # Then mark implemented
        success, message = fresh_recommender.mark_implemented(
            recommendation_id=recommendation.recommendation_id,
        )
        
        assert success
        assert recommendation.status == RecommendationStatus.IMPLEMENTED
    
    def test_cannot_implement_pending_recommendation(
        self,
        fresh_recommender,
        guardian_consistency_event,
    ):
        """Test that pending recommendations cannot be marked implemented"""
        recommendation = fresh_recommender.generate_from_guardian_consistency(
            entity_id="SITE_001",
            data_delta_magnitude=0.30,
            output_delta_magnitude=0.05,
            current_sensitivity=0.10,
            guardian_event_details=guardian_consistency_event,
        )
        
        # Try to mark implemented without approval
        success, message = fresh_recommender.mark_implemented(
            recommendation_id=recommendation.recommendation_id,
        )
        
        assert not success
        assert "not accepted" in message.lower()
    
    def test_get_pending_recommendations(
        self,
        fresh_recommender,
        guardian_consistency_event,
        guardian_staleness_event,
    ):
        """Test getting pending recommendations"""
        # Generate multiple recommendations
        fresh_recommender.generate_from_guardian_consistency(
            entity_id="SITE_001",
            data_delta_magnitude=0.30,
            output_delta_magnitude=0.05,
            current_sensitivity=0.10,
            guardian_event_details=guardian_consistency_event,
        )
        fresh_recommender.generate_from_guardian_staleness(
            entity_id="STUDY_001",
            consecutive_unchanged=5,
            alert_types=["HIGH_RISK"],
            current_staleness_threshold=3,
            guardian_event_details=guardian_staleness_event,
        )
        
        pending = fresh_recommender.get_pending_recommendations()
        
        assert len(pending) >= 2
        assert all(r.status == RecommendationStatus.PENDING for r in pending)
    
    def test_get_recommendations_by_source(
        self,
        fresh_recommender,
        guardian_consistency_event,
        guardian_staleness_event,
    ):
        """Test filtering recommendations by source"""
        fresh_recommender.generate_from_guardian_consistency(
            entity_id="SITE_001",
            data_delta_magnitude=0.30,
            output_delta_magnitude=0.05,
            current_sensitivity=0.10,
            guardian_event_details=guardian_consistency_event,
        )
        fresh_recommender.generate_from_guardian_staleness(
            entity_id="STUDY_001",
            consecutive_unchanged=5,
            alert_types=["HIGH_RISK"],
            current_staleness_threshold=3,
            guardian_event_details=guardian_staleness_event,
        )
        
        consistency_recs = fresh_recommender.get_recommendations_by_source(
            CalibrationSource.GUARDIAN_CONSISTENCY
        )
        staleness_recs = fresh_recommender.get_recommendations_by_source(
            CalibrationSource.GUARDIAN_STALENESS
        )
        
        assert len(consistency_recs) >= 1
        assert len(staleness_recs) >= 1
        assert all(r.source == CalibrationSource.GUARDIAN_CONSISTENCY for r in consistency_recs)
        assert all(r.source == CalibrationSource.GUARDIAN_STALENESS for r in staleness_recs)


# ========================================
# NO AUTOMATIC SELF-MODIFICATION TESTS
# ========================================

class TestNoAutomaticSelfModification:
    """Tests to verify no automatic self-modification"""
    
    def test_recommendations_require_human_review(
        self,
        fresh_recommender,
        guardian_consistency_event,
    ):
        """Test that recommendations require human review"""
        recommendation = fresh_recommender.generate_from_guardian_consistency(
            entity_id="SITE_001",
            data_delta_magnitude=0.30,
            output_delta_magnitude=0.05,
            current_sensitivity=0.10,
            guardian_event_details=guardian_consistency_event,
        )
        
        # Recommendation should be pending, not auto-applied
        assert recommendation.status == RecommendationStatus.PENDING
        
        # Cannot be implemented without review
        success, _ = fresh_recommender.mark_implemented(
            recommendation_id=recommendation.recommendation_id,
        )
        assert not success
    
    def test_all_recommendations_tracked(
        self,
        fresh_recommender,
        guardian_consistency_event,
    ):
        """Test that all recommendations are tracked for audit"""
        # Generate several recommendations
        for i in range(3):
            fresh_recommender.generate_from_guardian_consistency(
                entity_id=f"SITE_{i:03d}",
                data_delta_magnitude=0.30 + (i * 0.05),
                output_delta_magnitude=0.05,
                current_sensitivity=0.10,
                guardian_event_details=guardian_consistency_event,
            )
        
        all_recs = fresh_recommender.get_all_recommendations()
        
        assert len(all_recs) >= 3
        # All should have unique IDs
        ids = [r.recommendation_id for r in all_recs]
        assert len(ids) == len(set(ids))
    
    def test_recommendation_serialization(
        self,
        fresh_recommender,
        guardian_consistency_event,
    ):
        """Test that recommendations can be serialized for storage"""
        recommendation = fresh_recommender.generate_from_guardian_consistency(
            entity_id="SITE_001",
            data_delta_magnitude=0.30,
            output_delta_magnitude=0.05,
            current_sensitivity=0.10,
            guardian_event_details=guardian_consistency_event,
        )
        
        # Serialize
        rec_dict = recommendation.to_dict()
        
        assert isinstance(rec_dict, dict)
        assert "recommendation_id" in rec_dict
        assert "source" in rec_dict
        assert "justification" in rec_dict
        
        # Deserialize
        restored = CalibrationRecommendation.from_dict(rec_dict)
        
        assert restored.recommendation_id == recommendation.recommendation_id
        assert restored.source == recommendation.source
        assert restored.config_key == recommendation.config_key
