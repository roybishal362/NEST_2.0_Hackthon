"""Integration Test for Full 7-Agent Pipeline"""
import pytest
from typing import Dict, Any
from src.intelligence.agent_pipeline import AgentPipeline, PipelineResult
from src.intelligence.base_agent import AgentType, RiskSignal
from src.core import get_logger

logger = get_logger(__name__)

@pytest.fixture
def comprehensive_features() -> Dict[str, Any]:
    return {
        "missing_pages_pct": 12.0,
        "form_completion_rate": 88.0,
        "visit_completion_rate": 92.0,
        "data_entry_lag_days": 4.0,
        "missing_required_fields": 15,
        "sae_backlog_days": 6.0,
        "sae_overdue_count": 3,
        "fatal_sae_count": 1,
        "safety_signal_count": 4,
        "overdue_sae_reviews": 2,
        "sae_reporting_compliance_rate": 92.0,
        "open_query_count": 45,
        "query_aging_days": 12.0,
        "query_resolution_rate": 78.0,
        "critical_queries_open": 5,
        "coding_completion_rate": 82.0,
        "coding_backlog_days": 18.0,
        "uncoded_sae_count": 4,
        "meddra_coding_rate": 85.0,
        "whodd_coding_rate": 80.0,
        "avg_data_entry_lag_days": 8.0,
        "overdue_visits_count": 12,
        "data_freshness_score": 75.0,
        "temporal_consistency_score": 80.0,
        "data_entry_errors": 8,
        "edc_validation_pass_rate": 90.0,
        "data_quality_score": 85.0,
        "enrollment_velocity": 0.85,
        "site_activation_rate": 0.90,
        "dropout_rate": 0.12,
        "site_performance_score": 88.0,
        "data_consistency_score": 92.0,
        "multi_source_agreement": 0.88,
        "validation_pass_rate": 90.0,
        "edc_sae_consistency_score": 0.92,
        "visit_projection_deviation": 0.08,
    }

def test_all_7_agents_execute(comprehensive_features):
    pipeline = AgentPipeline()
    assert len(pipeline.agents) == 8
    result = pipeline.run_full_analysis(study_id="STUDY_01", features=comprehensive_features, parallel=False)
    assert isinstance(result, PipelineResult)
    assert result.study_id == "STUDY_01"
    assert result.agents_succeeded >= 6
    assert result.consensus is not None
    assert result.dqi_score is not None
    assert 0.0 <= result.dqi_score.overall_score <= 100.0
    assert len(result.agent_results) == 8
    agent_types = set([r.agent_type for r in result.agent_results])
    expected_types = {AgentType.COMPLETENESS, AgentType.SAFETY, AgentType.QUERY_QUALITY, AgentType.CODING, AgentType.TIMELINE, AgentType.OPERATIONS, AgentType.STABILITY, AgentType.COMPLIANCE}
    assert agent_types == expected_types
    logger.info(f"Pipeline test: Succeeded={result.agents_succeeded}, DQI={result.dqi_score.overall_score:.1f}")
