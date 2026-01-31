"""
Unit Tests for DQI Change Explanation System
============================================
Tests the DQI change explanation functionality.

**Validates: Requirements 4.3, 4.5**
"""

import pytest
from datetime import datetime

from src.dqi import (
    DQICalculationEngine,
    DQIChangeExplanationEngine,
    DQIChangeExplanation,
    DimensionChange,
    ChangeDirection,
    ChangeSeverity,
)
from src.core import DQIBand


class TestDQIChangeExplanationEngine:
    """Tests for DQI change explanation engine"""
    
    @pytest.fixture
    def dqi_engine(self):
        """Create DQI calculation engine"""
        return DQICalculationEngine()
    
    @pytest.fixture
    def change_engine(self):
        """Create change explanation engine"""
        return DQIChangeExplanationEngine()
    
    def test_explain_improvement(self, dqi_engine, change_engine):
        """Test explanation for DQI improvement"""
        # Previous: poor features
        prev_features = {
            "sae_backlog_days": 15,
            "sae_overdue_count": 3,
            "visit_completion_rate": 70,
            "query_aging_days": 20,
        }
        
        # Current: improved features
        curr_features = {
            "sae_backlog_days": 5,
            "sae_overdue_count": 1,
            "visit_completion_rate": 90,
            "query_aging_days": 5,
        }
        
        prev_result = dqi_engine.calculate_dqi(prev_features, "STUDY_1")
        curr_result = dqi_engine.calculate_dqi(curr_features, "STUDY_1")
        
        explanation = change_engine.explain_change(prev_result, curr_result)
        
        assert explanation.direction == ChangeDirection.IMPROVED
        assert explanation.overall_delta > 0
        assert len(explanation.primary_drivers) > 0
        assert "improved" in explanation.explanation.lower()
    
    def test_explain_decline(self, dqi_engine, change_engine):
        """Test explanation for DQI decline"""
        # Previous: good features
        prev_features = {
            "sae_backlog_days": 2,
            "sae_overdue_count": 0,
            "visit_completion_rate": 95,
            "query_aging_days": 3,
        }
        
        # Current: worse features
        curr_features = {
            "sae_backlog_days": 20,
            "sae_overdue_count": 5,
            "visit_completion_rate": 60,
            "query_aging_days": 30,
        }
        
        prev_result = dqi_engine.calculate_dqi(prev_features, "STUDY_1")
        curr_result = dqi_engine.calculate_dqi(curr_features, "STUDY_1")
        
        explanation = change_engine.explain_change(prev_result, curr_result)
        
        assert explanation.direction == ChangeDirection.DECLINED
        assert explanation.overall_delta < 0
        assert len(explanation.primary_drivers) > 0
        assert "declined" in explanation.explanation.lower()
    
    def test_explain_stable(self, dqi_engine, change_engine):
        """Test explanation for stable DQI"""
        # Same features
        features = {
            "sae_backlog_days": 5,
            "visit_completion_rate": 85,
            "query_aging_days": 10,
        }
        
        prev_result = dqi_engine.calculate_dqi(features, "STUDY_1")
        curr_result = dqi_engine.calculate_dqi(features, "STUDY_1")
        
        explanation = change_engine.explain_change(prev_result, curr_result)
        
        assert explanation.direction == ChangeDirection.STABLE
        assert abs(explanation.overall_delta) < 1.0
        assert "stable" in explanation.explanation.lower()
    
    def test_band_change_detection(self, dqi_engine, change_engine):
        """Test detection of band changes"""
        # Previous: AMBER band
        prev_features = {
            "sae_backlog_days": 10,
            "visit_completion_rate": 75,
        }
        
        # Current: GREEN band
        curr_features = {
            "sae_backlog_days": 0,
            "visit_completion_rate": 100,
        }
        
        prev_result = dqi_engine.calculate_dqi(prev_features, "STUDY_1")
        curr_result = dqi_engine.calculate_dqi(curr_features, "STUDY_1")
        
        explanation = change_engine.explain_change(prev_result, curr_result)
        
        # Should detect band change
        if prev_result.band != curr_result.band:
            assert explanation.severity in [ChangeSeverity.SIGNIFICANT, ChangeSeverity.CRITICAL]
            assert "band" in explanation.explanation.lower() or \
                   prev_result.band.value in explanation.explanation or \
                   curr_result.band.value in explanation.explanation
    
    def test_primary_drivers_identified(self, dqi_engine, change_engine):
        """Test that primary drivers are correctly identified"""
        # Significant change in safety
        prev_features = {
            "sae_backlog_days": 0,
            "sae_overdue_count": 0,
            "fatal_sae_count": 0,
            "visit_completion_rate": 90,
        }
        
        curr_features = {
            "sae_backlog_days": 20,
            "sae_overdue_count": 5,
            "fatal_sae_count": 2,
            "visit_completion_rate": 90,  # Same
        }
        
        prev_result = dqi_engine.calculate_dqi(prev_features, "STUDY_1")
        curr_result = dqi_engine.calculate_dqi(curr_features, "STUDY_1")
        
        explanation = change_engine.explain_change(prev_result, curr_result)
        
        # Safety should be a primary driver
        assert len(explanation.primary_drivers) > 0
        safety_mentioned = any("safety" in driver.lower() for driver in explanation.primary_drivers)
        assert safety_mentioned, "Safety should be identified as primary driver"
    
    def test_dimension_changes_tracked(self, dqi_engine, change_engine):
        """Test that dimension changes are tracked"""
        prev_features = {
            "sae_backlog_days": 10,
            "visit_completion_rate": 80,
            "query_aging_days": 15,
        }
        
        curr_features = {
            "sae_backlog_days": 5,
            "visit_completion_rate": 90,
            "query_aging_days": 5,
        }
        
        prev_result = dqi_engine.calculate_dqi(prev_features, "STUDY_1")
        curr_result = dqi_engine.calculate_dqi(curr_features, "STUDY_1")
        
        explanation = change_engine.explain_change(prev_result, curr_result)
        
        # Should have dimension changes
        assert len(explanation.dimension_changes) > 0
        
        # Each dimension change should have required fields
        for dim, change in explanation.dimension_changes.items():
            assert change.dimension is not None
            assert change.previous_score is not None
            assert change.current_score is not None
            assert change.direction is not None
            assert change.explanation is not None
    
    def test_to_dict_serialization(self, dqi_engine, change_engine):
        """Test that explanation can be serialized to dict"""
        prev_features = {"sae_backlog_days": 10, "visit_completion_rate": 80}
        curr_features = {"sae_backlog_days": 5, "visit_completion_rate": 90}
        
        prev_result = dqi_engine.calculate_dqi(prev_features, "STUDY_1")
        curr_result = dqi_engine.calculate_dqi(curr_features, "STUDY_1")
        
        explanation = change_engine.explain_change(prev_result, curr_result)
        result_dict = explanation.to_dict()
        
        assert "entity_id" in result_dict
        assert "previous_score" in result_dict
        assert "current_score" in result_dict
        assert "overall_delta" in result_dict
        assert "direction" in result_dict
        assert "severity" in result_dict
        assert "primary_drivers" in result_dict
        assert "dimension_changes" in result_dict
    
    def test_partial_calculation_noted(self, dqi_engine, change_engine):
        """Test that partial calculations are noted in explanation"""
        # Only safety features (partial)
        prev_features = {"sae_backlog_days": 10}
        curr_features = {"sae_backlog_days": 5}
        
        prev_result = dqi_engine.calculate_dqi(prev_features, "STUDY_1")
        curr_result = dqi_engine.calculate_dqi(curr_features, "STUDY_1")
        
        explanation = change_engine.explain_change(prev_result, curr_result)
        
        # Should note partial calculation
        if curr_result.partial_calculation:
            assert "partial" in explanation.explanation.lower() or \
                   "confidence" in explanation.explanation.lower()
    
    def test_severity_classification(self, dqi_engine, change_engine):
        """Test severity classification for different change magnitudes"""
        # Test negligible change
        features = {"sae_backlog_days": 5, "visit_completion_rate": 85}
        prev_result = dqi_engine.calculate_dqi(features, "STUDY_1")
        curr_result = dqi_engine.calculate_dqi(features, "STUDY_1")
        
        explanation = change_engine.explain_change(prev_result, curr_result)
        assert explanation.severity == ChangeSeverity.NEGLIGIBLE
    
    def test_entity_id_preserved(self, dqi_engine, change_engine):
        """Test that entity ID is preserved in explanation"""
        features = {"sae_backlog_days": 5}
        
        prev_result = dqi_engine.calculate_dqi(features, "STUDY_123")
        curr_result = dqi_engine.calculate_dqi(features, "STUDY_123")
        
        explanation = change_engine.explain_change(prev_result, curr_result)
        
        assert explanation.entity_id == "STUDY_123"
    
    def test_custom_entity_id(self, dqi_engine, change_engine):
        """Test that custom entity ID can be provided"""
        features = {"sae_backlog_days": 5}
        
        prev_result = dqi_engine.calculate_dqi(features, "STUDY_1")
        curr_result = dqi_engine.calculate_dqi(features, "STUDY_2")
        
        explanation = change_engine.explain_change(
            prev_result, curr_result, entity_id="CUSTOM_ID"
        )
        
        assert explanation.entity_id == "CUSTOM_ID"


class TestChangeSeverity:
    """Tests for change severity classification"""
    
    def test_critical_severity_for_red_band_change(self):
        """Test that RED band changes are critical"""
        engine = DQIChangeExplanationEngine()
        
        # Change to RED band
        severity = engine._determine_severity(
            delta=-30, prev_band=DQIBand.AMBER, curr_band=DQIBand.RED
        )
        assert severity == ChangeSeverity.CRITICAL
        
        # Change from RED band
        severity = engine._determine_severity(
            delta=30, prev_band=DQIBand.RED, curr_band=DQIBand.AMBER
        )
        assert severity == ChangeSeverity.CRITICAL
    
    def test_significant_severity_for_band_change(self):
        """Test that band changes are significant"""
        engine = DQIChangeExplanationEngine()
        
        severity = engine._determine_severity(
            delta=10, prev_band=DQIBand.AMBER, curr_band=DQIBand.GREEN
        )
        assert severity == ChangeSeverity.SIGNIFICANT
    
    def test_moderate_severity_for_medium_delta(self):
        """Test moderate severity for medium delta"""
        engine = DQIChangeExplanationEngine()
        
        severity = engine._determine_severity(
            delta=7, prev_band=DQIBand.AMBER, curr_band=DQIBand.AMBER
        )
        assert severity == ChangeSeverity.MODERATE
    
    def test_minor_severity_for_small_delta(self):
        """Test minor severity for small delta"""
        engine = DQIChangeExplanationEngine()
        
        severity = engine._determine_severity(
            delta=2, prev_band=DQIBand.GREEN, curr_band=DQIBand.GREEN
        )
        assert severity == ChangeSeverity.MINOR
    
    def test_negligible_severity_for_tiny_delta(self):
        """Test negligible severity for tiny delta"""
        engine = DQIChangeExplanationEngine()
        
        severity = engine._determine_severity(
            delta=0.5, prev_band=DQIBand.GREEN, curr_band=DQIBand.GREEN
        )
        assert severity == ChangeSeverity.NEGLIGIBLE


class TestChangeDirection:
    """Tests for change direction determination"""
    
    def test_improved_direction(self):
        """Test improved direction for positive delta"""
        engine = DQIChangeExplanationEngine()
        
        direction = engine._determine_direction(5.0)
        assert direction == ChangeDirection.IMPROVED
    
    def test_declined_direction(self):
        """Test declined direction for negative delta"""
        engine = DQIChangeExplanationEngine()
        
        direction = engine._determine_direction(-5.0)
        assert direction == ChangeDirection.DECLINED
    
    def test_stable_direction(self):
        """Test stable direction for small delta"""
        engine = DQIChangeExplanationEngine()
        
        direction = engine._determine_direction(0.5)
        assert direction == ChangeDirection.STABLE
        
        direction = engine._determine_direction(-0.5)
        assert direction == ChangeDirection.STABLE
