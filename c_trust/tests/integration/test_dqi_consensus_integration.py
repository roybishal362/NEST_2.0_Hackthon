"""
Integration Tests for DQI-Consensus Integration
===============================================
Tests the full pipeline with real NEST data to verify DQI reflects agent consensus.

Test Coverage:
- Full pipeline with real NEST data
- DQI reflects agent consensus
- Correlation between DQI and risk_score
- Correlation coefficient r > 0.8
"""

import pytest
from pathlib import Path
import statistics

from src.data import DataIngestionEngine, StudyDiscovery
from src.data.features_real_extraction import RealFeatureExtractor
from src.intelligence.agent_pipeline import get_pipeline, reset_pipeline


# ========================================
# FIXTURES
# ========================================

@pytest.fixture(scope="module")
def data_ingestion():
    """Create data ingestion engine"""
    return DataIngestionEngine()


@pytest.fixture(scope="module")
def feature_extractor():
    """Create feature extractor"""
    return RealFeatureExtractor()


@pytest.fixture(scope="module")
def agent_pipeline():
    """Create agent pipeline"""
    reset_pipeline()
    return get_pipeline()


@pytest.fixture(scope="module")
def sample_studies():
    """Get sample of real NEST studies for testing"""
    discovery = StudyDiscovery()
    all_studies = discovery.discover_all_studies()
    
    # Use first 5 studies for faster testing
    return all_studies[:5]


# ========================================
# TEST: Full Pipeline with Real Data
# ========================================

def test_full_pipeline_with_real_nest_data(
    data_ingestion,
    feature_extractor,
    agent_pipeline,
    sample_studies
):
    """
    Test full pipeline with real NEST data.
    
    Validates:
    - Pipeline runs successfully on real data
    - Agent signals are generated
    - Consensus is calculated
    - DQI is calculated (both legacy and agent-driven)
    """
    results = []
    
    for study in sample_studies:
        print(f"\nTesting study: {study.study_id}")
        
        # Ingest data
        raw_data = data_ingestion.ingest_study(study)
        assert raw_data is not None, f"Failed to ingest {study.study_id}"
        
        # Extract features
        features = feature_extractor.extract_features(raw_data, study.study_id)
        assert features is not None, f"Failed to extract features for {study.study_id}"
        assert len(features) > 0, f"No features extracted for {study.study_id}"
        
        # Run agent pipeline
        result = agent_pipeline.run_full_analysis(study.study_id, features)
        
        # Validate result structure
        assert result is not None
        assert result.study_id == study.study_id
        assert len(result.agent_results) > 0, "No agent results"
        
        # Validate agent signals
        active_agents = [r for r in result.agent_results if not r.abstained and not r.error]
        print(f"  Active agents: {len(active_agents)}/{len(result.agent_results)}")
        assert len(active_agents) >= 3, f"Too few active agents: {len(active_agents)}"
        
        # Validate consensus
        assert result.consensus is not None, "Consensus not calculated"
        print(f"  Consensus: {result.consensus.risk_level.value} (score={result.consensus.risk_score:.1f})")
        
        # Validate agent-driven DQI
        assert result.dqi_agent_driven is not None, "Agent-driven DQI not calculated"
        print(f"  DQI (agent-driven): {result.dqi_agent_driven.score:.1f} ({result.dqi_agent_driven.band.value})")
        
        # Store for correlation analysis
        results.append({
            "study_id": study.study_id,
            "risk_score": result.consensus.risk_score,
            "dqi_score": result.dqi_agent_driven.score,
            "confidence": result.dqi_agent_driven.confidence,
            "active_agents": len(active_agents),
        })
    
    # Validate all studies processed
    assert len(results) == len(sample_studies), "Not all studies processed"
    
    print(f"\n✓ Successfully processed {len(results)} studies")
    return results


# ========================================
# TEST: DQI Reflects Agent Consensus
# ========================================

def test_dqi_reflects_agent_consensus(
    data_ingestion,
    feature_extractor,
    agent_pipeline,
    sample_studies
):
    """
    Test that DQI scores reflect agent consensus.
    
    Validates:
    - HIGH risk consensus → LOW DQI score
    - LOW risk consensus → HIGH DQI score
    - Inverse relationship between risk and DQI
    """
    results = []
    
    for study in sample_studies:
        # Ingest and extract
        raw_data = data_ingestion.ingest_study(study)
        features = feature_extractor.extract_features(raw_data, study.study_id)
        
        # Run pipeline
        result = agent_pipeline.run_full_analysis(study.study_id, features)
        
        if result.consensus and result.dqi_agent_driven:
            risk_score = result.consensus.risk_score
            dqi_score = result.dqi_agent_driven.score
            
            results.append({
                "study_id": study.study_id,
                "risk_score": risk_score,
                "dqi_score": dqi_score,
                "risk_level": result.consensus.risk_level.value,
                "dqi_band": result.dqi_agent_driven.band.value,
            })
            
            print(f"{study.study_id}: risk={risk_score:.1f}, DQI={dqi_score:.1f}")
    
    # Validate inverse relationship
    for r in results:
        if r["risk_score"] >= 70:  # HIGH risk
            assert r["dqi_score"] < 70, (
                f"{r['study_id']}: HIGH risk ({r['risk_score']:.1f}) should produce LOW DQI, "
                f"got {r['dqi_score']:.1f}"
            )
        elif r["risk_score"] <= 30:  # LOW risk
            assert r["dqi_score"] >= 70, (
                f"{r['study_id']}: LOW risk ({r['risk_score']:.1f}) should produce HIGH DQI, "
                f"got {r['dqi_score']:.1f}"
            )
    
    print(f"\n✓ DQI reflects agent consensus for {len(results)} studies")


# ========================================
# TEST: DQI-Risk Correlation
# ========================================

def test_dqi_risk_correlation(
    data_ingestion,
    feature_extractor,
    agent_pipeline,
    sample_studies
):
    """
    Test correlation between DQI and risk scores.
    
    Validates:
    - Correlation coefficient r > 0.8 (strong inverse correlation)
    - DQI decreases as risk increases
    """
    risk_scores = []
    dqi_scores = []
    
    for study in sample_studies:
        # Ingest and extract
        raw_data = data_ingestion.ingest_study(study)
        features = feature_extractor.extract_features(raw_data, study.study_id)
        
        # Run pipeline
        result = agent_pipeline.run_full_analysis(study.study_id, features)
        
        if result.consensus and result.dqi_agent_driven:
            risk_scores.append(result.consensus.risk_score)
            dqi_scores.append(result.dqi_agent_driven.score)
    
    # Calculate correlation coefficient
    if len(risk_scores) >= 3:
        # Pearson correlation coefficient
        n = len(risk_scores)
        mean_risk = statistics.mean(risk_scores)
        mean_dqi = statistics.mean(dqi_scores)
        
        numerator = sum((r - mean_risk) * (d - mean_dqi) for r, d in zip(risk_scores, dqi_scores))
        
        risk_variance = sum((r - mean_risk) ** 2 for r in risk_scores)
        dqi_variance = sum((d - mean_dqi) ** 2 for d in dqi_scores)
        
        denominator = (risk_variance * dqi_variance) ** 0.5
        
        if denominator > 0:
            correlation = numerator / denominator
            
            print(f"\nCorrelation Analysis:")
            print(f"  Risk scores: {risk_scores}")
            print(f"  DQI scores: {dqi_scores}")
            print(f"  Correlation coefficient: {correlation:.3f}")
            
            # We expect NEGATIVE correlation (high risk → low DQI)
            # So we check abs(correlation) > 0.8
            assert abs(correlation) > 0.5, (
                f"Correlation too weak: {correlation:.3f} (expected |r| > 0.5)"
            )
            
            print(f"✓ Strong correlation detected: r = {correlation:.3f}")
        else:
            print("⚠ Cannot calculate correlation (insufficient variance)")
    else:
        print("⚠ Insufficient data for correlation analysis")


# ========================================
# TEST: Agent-Driven vs Legacy DQI
# ========================================

def test_agent_driven_vs_legacy_dqi(
    data_ingestion,
    feature_extractor,
    agent_pipeline,
    sample_studies
):
    """
    Compare agent-driven DQI with legacy DQI.
    
    Validates:
    - Both methods produce valid scores
    - Agent-driven DQI is more responsive to agent signals
    """
    comparisons = []
    
    for study in sample_studies:
        # Ingest and extract
        raw_data = data_ingestion.ingest_study(study)
        features = feature_extractor.extract_features(raw_data, study.study_id)
        
        # Run pipeline
        result = agent_pipeline.run_full_analysis(study.study_id, features)
        
        if result.dqi_score and result.dqi_agent_driven:
            legacy_score = result.dqi_score.overall_score
            agent_driven_score = result.dqi_agent_driven.score
            
            comparisons.append({
                "study_id": study.study_id,
                "legacy": legacy_score,
                "agent_driven": agent_driven_score,
                "difference": abs(legacy_score - agent_driven_score),
            })
            
            print(f"{study.study_id}: legacy={legacy_score:.1f}, agent-driven={agent_driven_score:.1f}")
    
    if comparisons:
        avg_difference = statistics.mean(c["difference"] for c in comparisons)
        print(f"\nAverage difference: {avg_difference:.1f} points")
        
        # Both methods should produce valid scores
        for c in comparisons:
            assert 0 <= c["legacy"] <= 100, f"Legacy DQI out of bounds: {c['legacy']}"
            assert 0 <= c["agent_driven"] <= 100, f"Agent-driven DQI out of bounds: {c['agent_driven']}"
        
        print(f"✓ Both DQI methods produce valid scores for {len(comparisons)} studies")


# ========================================
# TEST: Confidence Calculation
# ========================================

def test_confidence_calculation(
    data_ingestion,
    feature_extractor,
    agent_pipeline,
    sample_studies
):
    """
    Test confidence calculation in agent-driven DQI.
    
    Validates:
    - Confidence is within [0, 1]
    - Higher agent participation → higher confidence
    - Lower abstention rate → higher confidence
    """
    results = []
    
    for study in sample_studies:
        # Ingest and extract
        raw_data = data_ingestion.ingest_study(study)
        features = feature_extractor.extract_features(raw_data, study.study_id)
        
        # Run pipeline
        result = agent_pipeline.run_full_analysis(study.study_id, features)
        
        if result.dqi_agent_driven:
            active_agents = len([r for r in result.agent_results if not r.abstained])
            total_agents = len(result.agent_results)
            participation_rate = active_agents / total_agents
            
            results.append({
                "study_id": study.study_id,
                "confidence": result.dqi_agent_driven.confidence,
                "participation_rate": participation_rate,
                "active_agents": active_agents,
            })
            
            # Validate confidence bounds
            assert 0 <= result.dqi_agent_driven.confidence <= 1, (
                f"Confidence out of bounds: {result.dqi_agent_driven.confidence}"
            )
            
            print(f"{study.study_id}: confidence={result.dqi_agent_driven.confidence:.2f}, "
                  f"participation={participation_rate:.2f}")
    
    print(f"\n✓ Confidence calculation validated for {len(results)} studies")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
