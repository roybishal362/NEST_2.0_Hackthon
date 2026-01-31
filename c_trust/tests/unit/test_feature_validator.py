"""
Unit Tests for Feature Validator
=================================

Tests the FeatureValidator class that validates extracted features
against agent requirements.

Test Coverage:
- Basic validation with complete features
- Validation with missing features
- 50% threshold behavior
- Edge cases (empty features, all missing, etc.)
- Helper methods (get_all_required_features, etc.)
- Detailed validation output

Author: C-TRUST Team
Date: 2025
"""

import pytest
from c_trust.src.data.feature_validator import (
    FeatureValidator,
    ValidationResult,
    AgentValidationResult
)


class TestFeatureValidator:
    """Test suite for FeatureValidator class."""
    
    @pytest.fixture
    def validator(self):
        """Create a FeatureValidator instance for testing."""
        return FeatureValidator()
    
    @pytest.fixture
    def complete_features(self):
        """Complete feature set with all required features."""
        return {
            # Completeness agent features
            'form_completion_rate': 0.85,
            'visit_completion_rate': 0.90,
            'missing_pages_pct': 0.05,
            
            # Safety agent features
            'sae_dm_open_discrepancies': 3,
            'sae_dm_avg_age_days': 12.5,
            
            # Query quality agent features
            'open_query_count': 15,
            'query_aging_days': 8.2,
            
            # Coding agent features
            'coding_completion_rate': 0.92,
            'uncoded_terms_count': 5,
            'coding_backlog_days': 3.5,
            
            # Temporal drift agent features
            'avg_data_entry_lag_days': 2.1,
            'visit_date_count': 120,
            
            # EDC quality agent features
            'verified_forms': 450,
            'total_forms': 500,
            
            # Stability agent features
            'completed_visits': 95,
            'total_planned_visits': 100
        }
    
    @pytest.fixture
    def partial_features(self):
        """Partial feature set with some missing features."""
        return {
            # Completeness: 2/3 features (67% - can run)
            'form_completion_rate': 0.85,
            'visit_completion_rate': 0.90,
            # missing_pages_pct is None
            
            # Safety: 1/2 features (50% - can run)
            'sae_dm_open_discrepancies': 3,
            # sae_dm_avg_age_days is None
            
            # Query quality: 0/2 features (0% - cannot run)
            # Both features missing
            
            # Coding: 2/3 features (67% - can run)
            'coding_completion_rate': 0.92,
            'uncoded_terms_count': 5,
            # coding_backlog_days is None
            
            # Temporal drift: 1/2 features (50% - can run)
            'avg_data_entry_lag_days': 2.1,
            # visit_date_count is None
            
            # EDC quality: 2/2 features (100% - can run)
            'verified_forms': 450,
            'total_forms': 500,
            
            # Stability: 1/2 features (50% - can run)
            'completed_visits': 95,
            # total_planned_visits is None
        }
    
    # ========================================================================
    # Basic Validation Tests
    # ========================================================================
    
    def test_validate_complete_features(self, validator, complete_features):
        """Test validation with all features available."""
        result = validator.validate(complete_features)
        
        # All agents should be able to run
        assert result.total_agents == 7
        assert result.agents_can_run == 7
        assert result.agents_cannot_run == 0
        assert result.overall_readiness == 1.0
        
        # Check each agent
        for agent_name, agent_result in result.agent_results.items():
            assert agent_result.can_run, f"{agent_name} should be able to run"
            assert agent_result.availability_rate == 1.0
            assert len(agent_result.missing_features) == 0
    
    def test_validate_partial_features(self, validator, partial_features):
        """Test validation with some missing features."""
        result = validator.validate(partial_features)
        
        # Check overall results
        assert result.total_agents == 7
        assert result.agents_can_run == 6  # All except query_quality
        assert result.agents_cannot_run == 1
        assert result.overall_readiness == pytest.approx(6/7, rel=0.01)
        
        # Check specific agents
        assert result.agent_results['completeness'].can_run
        assert result.agent_results['safety'].can_run
        assert not result.agent_results['query_quality'].can_run
        assert result.agent_results['coding'].can_run
        assert result.agent_results['temporal_drift'].can_run
        assert result.agent_results['edc_quality'].can_run
        assert result.agent_results['stability'].can_run
    
    def test_validate_empty_features(self, validator):
        """Test validation with no features available."""
        result = validator.validate({})
        
        # No agents should be able to run
        assert result.total_agents == 7
        assert result.agents_can_run == 0
        assert result.agents_cannot_run == 7
        assert result.overall_readiness == 0.0
        
        # All agents should have 0% availability
        for agent_result in result.agent_results.values():
            assert not agent_result.can_run
            assert agent_result.availability_rate == 0.0
            assert len(agent_result.available_features) == 0
    
    def test_validate_with_none_values(self, validator):
        """Test that None values are treated as missing features."""
        features = {
            'form_completion_rate': 0.85,
            'visit_completion_rate': None,  # Explicitly None
            'missing_pages_pct': 0.05,
        }
        
        result = validator.validate(features)
        completeness_result = result.agent_results['completeness']
        
        # Should have 2/3 features (67% - can run)
        assert completeness_result.can_run
        assert completeness_result.availability_rate == pytest.approx(2/3, rel=0.01)
        assert 'visit_completion_rate' in completeness_result.missing_features
        assert 'form_completion_rate' in completeness_result.available_features
        assert 'missing_pages_pct' in completeness_result.available_features
    
    def test_validate_with_zero_values(self, validator):
        """Test that zero values are treated as valid (not missing)."""
        features = {
            'sae_dm_open_discrepancies': 0,  # Zero is valid
            'sae_dm_avg_age_days': 0.0,      # Zero is valid
        }
        
        result = validator.validate(features)
        safety_result = result.agent_results['safety']
        
        # Should have 2/2 features (100% - can run)
        assert safety_result.can_run
        assert safety_result.availability_rate == 1.0
        assert len(safety_result.missing_features) == 0
        assert 'sae_dm_open_discrepancies' in safety_result.available_features
        assert 'sae_dm_avg_age_days' in safety_result.available_features
    
    # ========================================================================
    # Threshold Tests
    # ========================================================================
    
    def test_threshold_exactly_50_percent(self, validator):
        """Test that exactly 50% availability allows agent to run."""
        # Safety agent has 2 required features
        features = {
            'sae_dm_open_discrepancies': 3,  # 1/2 = 50%
        }
        
        result = validator.validate(features)
        safety_result = result.agent_results['safety']
        
        assert safety_result.availability_rate == 0.5
        assert safety_result.can_run  # Exactly 50% should allow running
    
    def test_threshold_just_below_50_percent(self, validator):
        """Test that just below 50% prevents agent from running."""
        # Completeness agent has 3 required features
        features = {
            'form_completion_rate': 0.85,  # 1/3 = 33% < 50%
        }
        
        result = validator.validate(features)
        completeness_result = result.agent_results['completeness']
        
        assert completeness_result.availability_rate == pytest.approx(1/3, rel=0.01)
        assert not completeness_result.can_run  # Below 50% should prevent running
    
    def test_threshold_just_above_50_percent(self, validator):
        """Test that just above 50% allows agent to run."""
        # Completeness agent has 3 required features
        features = {
            'form_completion_rate': 0.85,
            'visit_completion_rate': 0.90,  # 2/3 = 67% > 50%
        }
        
        result = validator.validate(features)
        completeness_result = result.agent_results['completeness']
        
        assert completeness_result.availability_rate == pytest.approx(2/3, rel=0.01)
        assert completeness_result.can_run  # Above 50% should allow running
    
    # ========================================================================
    # Helper Method Tests
    # ========================================================================
    
    def test_get_all_required_features(self, validator):
        """Test getting all required features across all agents."""
        all_features = validator.get_all_required_features()
        
        # Should have all unique features
        assert len(all_features) > 0
        assert isinstance(all_features, list)
        assert all_features == sorted(all_features)  # Should be sorted
        
        # Check some expected features
        assert 'form_completion_rate' in all_features
        assert 'sae_dm_open_discrepancies' in all_features
        assert 'open_query_count' in all_features
        
        # Should have no duplicates
        assert len(all_features) == len(set(all_features))
    
    def test_get_agent_requirements(self, validator):
        """Test getting requirements for specific agents."""
        # Test completeness agent
        completeness_features = validator.get_agent_requirements('completeness')
        assert completeness_features is not None
        assert 'form_completion_rate' in completeness_features
        assert 'visit_completion_rate' in completeness_features
        assert 'missing_pages_pct' in completeness_features
        
        # Test safety agent
        safety_features = validator.get_agent_requirements('safety')
        assert safety_features is not None
        assert 'sae_dm_open_discrepancies' in safety_features
        assert 'sae_dm_avg_age_days' in safety_features
        
        # Test non-existent agent
        unknown_features = validator.get_agent_requirements('unknown_agent')
        assert unknown_features is None
    
    def test_get_feature_coverage(self, validator, complete_features):
        """Test getting feature coverage statistics."""
        coverage = validator.get_feature_coverage(complete_features)
        
        assert 'total_required' in coverage
        assert 'available' in coverage
        assert 'missing' in coverage
        assert 'overall_coverage' in coverage
        assert 'available_features' in coverage
        assert 'missing_features' in coverage
        
        # With complete features, should have 100% coverage
        assert coverage['overall_coverage'] == 1.0
        assert coverage['available'] == coverage['total_required']
        assert coverage['missing'] == 0
    
    def test_get_feature_coverage_partial(self, validator, partial_features):
        """Test feature coverage with partial features."""
        coverage = validator.get_feature_coverage(partial_features)
        
        # Should have some but not all features
        assert 0 < coverage['overall_coverage'] < 1.0
        assert coverage['available'] > 0
        assert coverage['missing'] > 0
        assert coverage['available'] + coverage['missing'] == coverage['total_required']
    
    def test_validate_with_details(self, validator, complete_features):
        """Test detailed validation output for API responses."""
        details = validator.validate_with_details(complete_features)
        
        # Check structure
        assert 'overall_readiness' in details
        assert 'agents_can_run' in details
        assert 'agents_cannot_run' in details
        assert 'total_agents' in details
        assert 'feature_coverage' in details
        assert 'agents' in details
        
        # Check values
        assert details['overall_readiness'] == 1.0
        assert details['agents_can_run'] == 7
        assert details['agents_cannot_run'] == 0
        
        # Check agent details
        for agent_name, agent_details in details['agents'].items():
            assert 'can_run' in agent_details
            assert 'availability_rate' in agent_details
            assert 'available_features' in agent_details
            assert 'missing_features' in agent_details
            assert 'required_features' in agent_details
    
    # ========================================================================
    # Result Object Tests
    # ========================================================================
    
    def test_validation_result_properties(self, validator, partial_features):
        """Test ValidationResult computed properties."""
        result = validator.validate(partial_features)
        
        # Test properties
        assert result.total_agents == len(result.agent_results)
        assert result.agents_can_run + result.agents_cannot_run == result.total_agents
        assert 0 <= result.overall_readiness <= 1.0
    
    def test_validation_result_get_agent_result(self, validator, complete_features):
        """Test getting specific agent results."""
        result = validator.validate(complete_features)
        
        # Test getting existing agent
        completeness_result = result.get_agent_result('completeness')
        assert completeness_result is not None
        assert completeness_result.agent_name == 'completeness'
        
        # Test getting non-existent agent
        unknown_result = result.get_agent_result('unknown_agent')
        assert unknown_result is None
    
    def test_agent_validation_result_str(self):
        """Test string representation of AgentValidationResult."""
        result = AgentValidationResult(
            agent_name='test_agent',
            required_features=['feat1', 'feat2', 'feat3'],
            available_features=['feat1', 'feat2'],
            missing_features=['feat3'],
            can_run=True,
            availability_rate=2/3
        )
        
        result_str = str(result)
        assert 'test_agent' in result_str
        assert 'CAN RUN' in result_str
        assert '2/3' in result_str
    
    def test_validation_result_str(self, validator, partial_features):
        """Test string representation of ValidationResult."""
        result = validator.validate(partial_features)
        
        result_str = str(result)
        assert 'Feature Validation Result' in result_str
        assert 'Overall Readiness' in result_str
        assert 'Agent Status' in result_str
        
        # Should include agent names
        for agent_name in validator.required_features_by_agent.keys():
            assert agent_name in result_str
    
    # ========================================================================
    # Edge Cases
    # ========================================================================
    
    def test_validate_with_extra_features(self, validator, complete_features):
        """Test that extra features (not required by any agent) are ignored."""
        features_with_extra = complete_features.copy()
        features_with_extra['extra_feature_1'] = 123
        features_with_extra['extra_feature_2'] = 'test'
        
        result = validator.validate(features_with_extra)
        
        # Should still validate successfully
        assert result.overall_readiness == 1.0
        assert result.agents_can_run == 7
    
    def test_validate_with_mixed_types(self, validator):
        """Test validation with various data types."""
        features = {
            'form_completion_rate': 0.85,      # float
            'visit_completion_rate': 1,        # int
            'missing_pages_pct': 0,            # zero int
            'sae_dm_open_discrepancies': 3,    # int
            'sae_dm_avg_age_days': 12.5,       # float
        }
        
        result = validator.validate(features)
        
        # Should handle different types correctly
        completeness_result = result.agent_results['completeness']
        assert completeness_result.can_run
        assert completeness_result.availability_rate == 1.0
    
    def test_validator_initialization(self):
        """Test validator initializes with correct agent requirements."""
        validator = FeatureValidator()
        
        # Should have 7 agents
        assert len(validator.required_features_by_agent) == 7
        
        # Check agent names
        expected_agents = [
            'completeness', 'safety', 'query_quality', 'coding',
            'temporal_drift', 'edc_quality', 'stability'
        ]
        for agent in expected_agents:
            assert agent in validator.required_features_by_agent
        
        # Check threshold
        assert validator.availability_threshold == 0.5
    
    def test_validate_single_agent_all_features_missing(self, validator):
        """Test validation when a single agent has all features missing."""
        features = {
            # Only provide features for other agents, not completeness
            'sae_dm_open_discrepancies': 3,
            'sae_dm_avg_age_days': 12.5,
        }
        
        result = validator.validate(features)
        completeness_result = result.agent_results['completeness']
        
        assert not completeness_result.can_run
        assert completeness_result.availability_rate == 0.0
        assert len(completeness_result.available_features) == 0
        assert len(completeness_result.missing_features) == 3


# ============================================================================
# Integration Tests
# ============================================================================

class TestFeatureValidatorIntegration:
    """Integration tests for FeatureValidator with realistic scenarios."""
    
    def test_realistic_study_scenario(self):
        """Test with realistic study data scenario."""
        validator = FeatureValidator()
        
        # Simulate a study with good completeness but poor safety tracking
        features = {
            # Completeness: excellent
            'form_completion_rate': 0.95,
            'visit_completion_rate': 0.92,
            'missing_pages_pct': 0.03,
            
            # Safety: poor (missing data)
            'sae_dm_open_discrepancies': None,
            'sae_dm_avg_age_days': None,
            
            # Query quality: moderate
            'open_query_count': 25,
            'query_aging_days': None,
            
            # Coding: good
            'coding_completion_rate': 0.88,
            'uncoded_terms_count': 8,
            'coding_backlog_days': 5.2,
            
            # Temporal: moderate
            'avg_data_entry_lag_days': 3.5,
            'visit_date_count': None,
            
            # EDC quality: excellent
            'verified_forms': 480,
            'total_forms': 500,
            
            # Stability: good
            'completed_visits': 92,
            'total_planned_visits': 100
        }
        
        result = validator.validate(features)
        
        # Should have most agents able to run
        assert result.agents_can_run >= 5
        assert result.overall_readiness >= 0.7
        
        # Specific checks
        assert result.agent_results['completeness'].can_run
        assert not result.agent_results['safety'].can_run  # Both features missing
        assert result.agent_results['edc_quality'].can_run
    
    def test_minimal_viable_study(self):
        """Test with minimal data that still allows some agents to run."""
        validator = FeatureValidator()
        
        # Provide exactly 50% of features for each agent
        features = {
            'form_completion_rate': 0.85,  # Completeness: 1/3 = 33%
            'sae_dm_open_discrepancies': 3,  # Safety: 1/2 = 50%
            'open_query_count': 15,  # Query: 1/2 = 50%
            'coding_completion_rate': 0.92,  # Coding: 1/3 = 33%
            'avg_data_entry_lag_days': 2.1,  # Temporal: 1/2 = 50%
            'verified_forms': 450,  # EDC: 1/2 = 50%
            'completed_visits': 95,  # Stability: 1/2 = 50%
        }
        
        result = validator.validate(features)
        
        # Agents with 50% should be able to run
        assert result.agent_results['safety'].can_run
        assert result.agent_results['query_quality'].can_run
        assert result.agent_results['temporal_drift'].can_run
        assert result.agent_results['edc_quality'].can_run
        assert result.agent_results['stability'].can_run
        
        # Agents with <50% should not run
        assert not result.agent_results['completeness'].can_run
        assert not result.agent_results['coding'].can_run


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
