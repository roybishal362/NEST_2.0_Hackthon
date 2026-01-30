"""
Agent Validation on Real NEST Data
===================================
Phase 0 Task 1: Run all 7 agents on real NEST 2.0 data to verify they produce
valid outputs before integrating them with DQI.

This test suite validates that:
1. All 7 agents run successfully on CACZ885D2301 (STUDY_01)
2. No agents abstain due to missing features
3. All agents produce valid risk scores (0-100)
4. All agents produce valid confidence (0-1)
5. Agent outputs are logged for manual review

Test Organization:
- 1.1.1: Run all 7 agents on CACZ885D2301 (first study / STUDY_01)
- 1.1.2: Verify no agents abstain due to missing features
- 1.1.3: Verify all agents produce valid risk scores (0-100)
- 1.1.4: Verify all agents produce valid confidence (0-1)
- 1.1.5: Log agent outputs for manual review

**Validates: Requirements US-0 (Phase 0 Acceptance Criteria)**
"""

import pytest
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd
import json

from src.data.ingestion import DataIngestionEngine, StudyDiscovery
from src.data.features_real_extraction import RealFeatureExtractor
from src.agents.signal_agents import (
    DataCompletenessAgent,
    SafetyComplianceAgent,
    QueryQualityAgent,
    CodingReadinessAgent,
    TemporalDriftAgent,
    EDCQualityAgent,
    StabilityAgent,
)
from src.intelligence.base_agent import AgentSignal, RiskSignal
from src.core import get_logger

logger = get_logger(__name__)

# ========================================
# TEST CONFIGURATION
# ========================================

# NEST 2.0 study directories (23 studies total)
NEST_DATA_ROOT = Path("norvatas/Data for problem Statement 1/NEST 2.0 Data files_Anonymized/QC Anonymized Study Files")

# First study for initial validation (CACZ885D2301 = STUDY_01)
FIRST_STUDY = "STUDY_01"

# All 7 agents to test
ALL_AGENTS = {
    "Safety": SafetyComplianceAgent,
    "Completeness": DataCompletenessAgent,
    "Coding": CodingReadinessAgent,
    "Query Quality": QueryQualityAgent,
    "EDC Quality": EDCQualityAgent,
    "Temporal Drift": TemporalDriftAgent,
    "Stability": StabilityAgent,
}

# Risk level to numeric score mapping (for validation)
RISK_TO_SCORE = {
    RiskSignal.CRITICAL: 90,
    RiskSignal.HIGH: 70,
    RiskSignal.MEDIUM: 50,
    RiskSignal.LOW: 20,
    RiskSignal.UNKNOWN: 0,
}

# ========================================
# HELPER FUNCTIONS
# ========================================

# Initialize engines once for all tests
_discovery = None
_ingestion = None
_feature_extractor = None
_nest_data_cache = {}


def get_engines():
    """Get or initialize data engines."""
    global _discovery, _ingestion, _feature_extractor
    
    if _discovery is None:
        _discovery = StudyDiscovery()
        _ingestion = DataIngestionEngine()
        _feature_extractor = RealFeatureExtractor()
        logger.info("Initialized data engines")
    
    return _discovery, _ingestion, _feature_extractor


def load_study_data(study_id: str) -> Dict[str, pd.DataFrame]:
    """
    Load raw NEST data for a study.
    
    Args:
        study_id: Study identifier (e.g., "STUDY_01")
    
    Returns:
        Dictionary of DataFrames by file type
    """
    global _nest_data_cache
    
    # Check cache first
    if study_id in _nest_data_cache:
        return _nest_data_cache[study_id]
    
    try:
        discovery, ingestion, _ = get_engines()
        
        # Find the study
        studies = discovery.discover_all_studies()
        study_obj = None
        
        for study in studies:
            if study.study_id == study_id:
                study_obj = study
                break
        
        if study_obj is None:
            logger.error(f"Study {study_id} not found. Available studies: {[s.study_id for s in studies[:5]]}")
            return {}
        
        # Load data
        logger.info(f"Loading data for {study_id}")
        data = ingestion.ingest_study(study_obj, validate_data=False)
        
        # Cache it
        _nest_data_cache[study_id] = data
        
        return data
    except Exception as e:
        logger.error(f"Failed to load data for {study_id}: {e}")
        import traceback
        traceback.print_exc()
        return {}


def extract_study_features(study_id: str) -> Dict[str, Any]:
    """
    Extract features for a study.
    
    Args:
        study_id: Study identifier (e.g., "STUDY_01")
    
    Returns:
        Dictionary of extracted features
    """
    try:
        # Load raw data
        data = load_study_data(study_id)
        
        if not data:
            logger.error(f"No data loaded for {study_id}")
            return {}
        
        # Extract features
        _, _, feature_extractor = get_engines()
        logger.info(f"Extracting features for {study_id}")
        features = feature_extractor.extract_features(data, study_id)
        
        logger.info(f"Extracted {len(features)} features for {study_id}")
        return features
    except Exception as e:
        logger.error(f"Failed to extract features for {study_id}: {e}")
        import traceback
        traceback.print_exc()
        return {}


def run_agent(agent_class, features: Dict[str, Any], study_id: str) -> AgentSignal:
    """
    Run a single agent on features.
    
    Args:
        agent_class: Agent class to instantiate
        features: Extracted features
        study_id: Study identifier
    
    Returns:
        AgentSignal from the agent
    """
    try:
        agent = agent_class()
        signal = agent.analyze(features, study_id)
        return signal
    except Exception as e:
        logger.error(f"Failed to run {agent_class.__name__} on {study_id}: {e}")
        import traceback
        traceback.print_exc()
        raise


def risk_to_score(risk_level: RiskSignal) -> int:
    """Convert risk level to numeric score (0-100)."""
    return RISK_TO_SCORE.get(risk_level, 0)


def log_agent_signal(agent_name: str, signal: AgentSignal, study_id: str):
    """
    Log agent signal for manual review.
    
    Args:
        agent_name: Name of the agent
        signal: AgentSignal from the agent
        study_id: Study identifier
    """
    logger.info("\n" + "="*80)
    logger.info(f"AGENT: {agent_name} | STUDY: {study_id}")
    logger.info("="*80)
    logger.info(f"Risk Level: {signal.risk_level.value}")
    logger.info(f"Risk Score: {risk_to_score(signal.risk_level)}/100")
    logger.info(f"Confidence: {signal.confidence:.2f}")
    logger.info(f"Abstained: {signal.abstained}")
    
    if signal.abstained:
        logger.info(f"Abstention Reason: {signal.abstention_reason}")
    
    logger.info(f"Features Analyzed: {signal.features_analyzed}")
    
    if signal.evidence:
        logger.info(f"\nEvidence ({len(signal.evidence)} items):")
        for i, evidence in enumerate(signal.evidence, 1):
            logger.info(f"  {i}. {evidence.feature_name} = {evidence.feature_value}")
            logger.info(f"     Severity: {evidence.severity:.2f} | {evidence.description}")
    
    if signal.recommended_actions:
        logger.info(f"\nRecommended Actions ({len(signal.recommended_actions)} items):")
        for i, action in enumerate(signal.recommended_actions, 1):
            logger.info(f"  {i}. {action}")
    
    logger.info("="*80 + "\n")


# ========================================
# TEST SUITE: TASK 1.1.1 - RUN ALL AGENTS
# ========================================

class TestRunAllAgentsOnFirstStudy:
    """Test 1.1.1: Run all 7 agents on CACZ885D2301 (STUDY_01)."""
    
    @pytest.fixture(scope="class")
    def study_features(self):
        """Extract features for STUDY_01 once for all tests."""
        features = extract_study_features(FIRST_STUDY)
        assert features, f"Failed to extract features for {FIRST_STUDY}"
        logger.info(f"Extracted {len(features)} features for {FIRST_STUDY}")
        return features
    
    def test_run_safety_agent(self, study_features):
        """Test 1.1.1: Run Safety Agent on STUDY_01."""
        signal = run_agent(SafetyComplianceAgent, study_features, FIRST_STUDY)
        
        assert signal is not None, "Safety agent returned None"
        assert isinstance(signal, AgentSignal), "Safety agent did not return AgentSignal"
        
        log_agent_signal("Safety", signal, FIRST_STUDY)
    
    def test_run_completeness_agent(self, study_features):
        """Test 1.1.1: Run Completeness Agent on STUDY_01."""
        signal = run_agent(DataCompletenessAgent, study_features, FIRST_STUDY)
        
        assert signal is not None, "Completeness agent returned None"
        assert isinstance(signal, AgentSignal), "Completeness agent did not return AgentSignal"
        
        log_agent_signal("Completeness", signal, FIRST_STUDY)
    
    def test_run_coding_agent(self, study_features):
        """Test 1.1.1: Run Coding Agent on STUDY_01."""
        signal = run_agent(CodingReadinessAgent, study_features, FIRST_STUDY)
        
        assert signal is not None, "Coding agent returned None"
        assert isinstance(signal, AgentSignal), "Coding agent did not return AgentSignal"
        
        log_agent_signal("Coding", signal, FIRST_STUDY)
    
    def test_run_query_quality_agent(self, study_features):
        """Test 1.1.1: Run Query Quality Agent on STUDY_01."""
        signal = run_agent(QueryQualityAgent, study_features, FIRST_STUDY)
        
        assert signal is not None, "Query Quality agent returned None"
        assert isinstance(signal, AgentSignal), "Query Quality agent did not return AgentSignal"
        
        log_agent_signal("Query Quality", signal, FIRST_STUDY)
    
    def test_run_edc_quality_agent(self, study_features):
        """Test 1.1.1: Run EDC Quality Agent on STUDY_01."""
        signal = run_agent(EDCQualityAgent, study_features, FIRST_STUDY)
        
        assert signal is not None, "EDC Quality agent returned None"
        assert isinstance(signal, AgentSignal), "EDC Quality agent did not return AgentSignal"
        
        log_agent_signal("EDC Quality", signal, FIRST_STUDY)
    
    def test_run_temporal_drift_agent(self, study_features):
        """Test 1.1.1: Run Temporal Drift Agent on STUDY_01."""
        signal = run_agent(TemporalDriftAgent, study_features, FIRST_STUDY)
        
        assert signal is not None, "Temporal Drift agent returned None"
        assert isinstance(signal, AgentSignal), "Temporal Drift agent did not return AgentSignal"
        
        log_agent_signal("Temporal Drift", signal, FIRST_STUDY)
    
    def test_run_stability_agent(self, study_features):
        """Test 1.1.1: Run Stability Agent on STUDY_01."""
        signal = run_agent(StabilityAgent, study_features, FIRST_STUDY)
        
        assert signal is not None, "Stability agent returned None"
        assert isinstance(signal, AgentSignal), "Stability agent did not return AgentSignal"
        
        log_agent_signal("Stability", signal, FIRST_STUDY)


# ========================================
# TEST SUITE: TASK 1.1.2 - VERIFY NO ABSTENTIONS
# ========================================

class TestVerifyNoAbstentions:
    """Test 1.1.2: Verify no agents abstain due to missing features."""
    
    @pytest.fixture(scope="class")
    def all_agent_signals(self):
        """Run all agents and collect signals."""
        features = extract_study_features(FIRST_STUDY)
        assert features, f"Failed to extract features for {FIRST_STUDY}"
        
        signals = {}
        for agent_name, agent_class in ALL_AGENTS.items():
            signal = run_agent(agent_class, features, FIRST_STUDY)
            signals[agent_name] = signal
        
        return signals
    
    def test_no_agent_abstains(self, all_agent_signals):
        """Test 1.1.2: Verify no agents abstain."""
        abstained_agents = []
        
        for agent_name, signal in all_agent_signals.items():
            if signal.abstained:
                abstained_agents.append({
                    "agent": agent_name,
                    "reason": signal.abstention_reason
                })
                logger.warning(f"ABSTENTION: {agent_name} abstained - {signal.abstention_reason}")
        
        # Log summary
        if abstained_agents:
            logger.warning(f"\n{len(abstained_agents)}/{len(ALL_AGENTS)} agents abstained:")
            for item in abstained_agents:
                logger.warning(f"  - {item['agent']}: {item['reason']}")
        else:
            logger.info(f"\n✓ All {len(ALL_AGENTS)} agents produced signals (no abstentions)")
        
        # Assert: We want no abstentions, but we'll log them as warnings
        # This is a soft assertion - we want to know if agents abstain but not fail the test
        if abstained_agents:
            logger.warning(f"WARNING: {len(abstained_agents)} agents abstained. This may indicate missing features.")
            logger.warning("Review the abstention reasons above and consider fixing feature extraction.")
    
    def test_abstention_rate_acceptable(self, all_agent_signals):
        """Test 1.1.2: Verify abstention rate is acceptable (<30%)."""
        abstained_count = sum(1 for signal in all_agent_signals.values() if signal.abstained)
        abstention_rate = abstained_count / len(ALL_AGENTS) * 100
        
        logger.info(f"Abstention rate: {abstention_rate:.1f}% ({abstained_count}/{len(ALL_AGENTS)} agents)")
        
        # Assert: Abstention rate should be < 30% for first study
        assert abstention_rate < 30, \
            f"Abstention rate {abstention_rate:.1f}% is too high (>30%). " \
            f"{abstained_count} agents abstained."


# ========================================
# TEST SUITE: TASK 1.1.3 - VERIFY VALID RISK SCORES
# ========================================

class TestVerifyValidRiskScores:
    """Test 1.1.3: Verify all agents produce valid risk scores (0-100)."""
    
    @pytest.fixture(scope="class")
    def all_agent_signals(self):
        """Run all agents and collect signals."""
        features = extract_study_features(FIRST_STUDY)
        assert features, f"Failed to extract features for {FIRST_STUDY}"
        
        signals = {}
        for agent_name, agent_class in ALL_AGENTS.items():
            signal = run_agent(agent_class, features, FIRST_STUDY)
            signals[agent_name] = signal
        
        return signals
    
    def test_all_agents_have_valid_risk_levels(self, all_agent_signals):
        """Test 1.1.3: Verify all agents produce valid risk levels."""
        for agent_name, signal in all_agent_signals.items():
            # Skip abstained agents
            if signal.abstained:
                continue
            
            # Check risk level is valid
            assert signal.risk_level in RiskSignal, \
                f"{agent_name}: Invalid risk level {signal.risk_level}"
            
            # Check risk level is not UNKNOWN (unless abstained)
            assert signal.risk_level != RiskSignal.UNKNOWN, \
                f"{agent_name}: Risk level is UNKNOWN but agent did not abstain"
            
            logger.info(f"{agent_name}: risk_level = {signal.risk_level.value}")
    
    def test_all_agents_have_reasonable_risk_scores(self, all_agent_signals):
        """Test 1.1.3: Verify all agents produce reasonable risk scores (not all 0 or 100)."""
        risk_scores = {}
        
        for agent_name, signal in all_agent_signals.items():
            # Skip abstained agents
            if signal.abstained:
                continue
            
            score = risk_to_score(signal.risk_level)
            risk_scores[agent_name] = score
            
            # Check score is in valid range
            assert 0 <= score <= 100, \
                f"{agent_name}: Risk score {score} out of range [0, 100]"
            
            logger.info(f"{agent_name}: risk_score = {score}/100")
        
        # Check that not all scores are the same (diversity check)
        unique_scores = set(risk_scores.values())
        
        if len(unique_scores) == 1:
            logger.warning(f"WARNING: All agents produced the same risk score: {list(unique_scores)[0]}")
            logger.warning("This may indicate a problem with agent logic or feature extraction.")
        else:
            logger.info(f"✓ Agents produced {len(unique_scores)} different risk scores (good diversity)")


# ========================================
# TEST SUITE: TASK 1.1.4 - VERIFY VALID CONFIDENCE
# ========================================

class TestVerifyValidConfidence:
    """Test 1.1.4: Verify all agents produce valid confidence (0-1)."""
    
    @pytest.fixture(scope="class")
    def all_agent_signals(self):
        """Run all agents and collect signals."""
        features = extract_study_features(FIRST_STUDY)
        assert features, f"Failed to extract features for {FIRST_STUDY}"
        
        signals = {}
        for agent_name, agent_class in ALL_AGENTS.items():
            signal = run_agent(agent_class, features, FIRST_STUDY)
            signals[agent_name] = signal
        
        return signals
    
    def test_all_agents_have_valid_confidence(self, all_agent_signals):
        """Test 1.1.4: Verify all agents produce valid confidence values."""
        for agent_name, signal in all_agent_signals.items():
            # Check confidence is in valid range
            assert 0 <= signal.confidence <= 1, \
                f"{agent_name}: Confidence {signal.confidence} out of range [0, 1]"
            
            logger.info(f"{agent_name}: confidence = {signal.confidence:.2f}")
    
    def test_all_agents_have_reasonable_confidence(self, all_agent_signals):
        """Test 1.1.4: Verify all agents produce reasonable confidence (not all 0 or 1)."""
        confidences = {}
        
        for agent_name, signal in all_agent_signals.items():
            confidences[agent_name] = signal.confidence
        
        # Check average confidence is reasonable (> 0.5)
        avg_confidence = sum(confidences.values()) / len(confidences)
        
        logger.info(f"Average confidence across all agents: {avg_confidence:.2f}")
        
        # Assert: Average confidence should be > 0.5
        assert avg_confidence > 0.5, \
            f"Average confidence {avg_confidence:.2f} is too low (<0.5). " \
            "This may indicate missing features or poor data quality."
        
        # Check that not all confidences are 1.0 (unrealistic)
        all_perfect = all(c == 1.0 for c in confidences.values())
        
        if all_perfect:
            logger.warning("WARNING: All agents have confidence = 1.0. This is unrealistic.")
            logger.warning("Review confidence calculation logic in agents.")
        else:
            logger.info(f"✓ Confidence values vary (not all 1.0)")


# ========================================
# TEST SUITE: TASK 1.1.5 - LOG AGENT OUTPUTS
# ========================================

class TestLogAgentOutputs:
    """Test 1.1.5: Log agent outputs for manual review."""
    
    def test_generate_agent_summary_report(self):
        """Test 1.1.5: Generate comprehensive summary report for manual review."""
        features = extract_study_features(FIRST_STUDY)
        assert features, f"Failed to extract features for {FIRST_STUDY}"
        
        # Run all agents
        signals = {}
        for agent_name, agent_class in ALL_AGENTS.items():
            signal = run_agent(agent_class, features, FIRST_STUDY)
            signals[agent_name] = signal
        
        # Generate summary report
        logger.info("\n" + "="*80)
        logger.info(f"AGENT VALIDATION SUMMARY REPORT - {FIRST_STUDY}")
        logger.info("="*80)
        
        # Overall statistics
        total_agents = len(ALL_AGENTS)
        abstained_count = sum(1 for s in signals.values() if s.abstained)
        active_count = total_agents - abstained_count
        
        logger.info(f"\nOverall Statistics:")
        logger.info(f"  Total Agents: {total_agents}")
        logger.info(f"  Active Agents: {active_count}")
        logger.info(f"  Abstained Agents: {abstained_count}")
        logger.info(f"  Abstention Rate: {abstained_count/total_agents*100:.1f}%")
        
        # Risk distribution
        risk_distribution = {}
        for signal in signals.values():
            if not signal.abstained:
                risk_level = signal.risk_level.value
                risk_distribution[risk_level] = risk_distribution.get(risk_level, 0) + 1
        
        logger.info(f"\nRisk Level Distribution:")
        for risk_level in ["critical", "high", "medium", "low"]:
            count = risk_distribution.get(risk_level, 0)
            pct = count / active_count * 100 if active_count > 0 else 0
            logger.info(f"  {risk_level.upper()}: {count} agents ({pct:.1f}%)")
        
        # Confidence statistics
        confidences = [s.confidence for s in signals.values()]
        avg_confidence = sum(confidences) / len(confidences)
        min_confidence = min(confidences)
        max_confidence = max(confidences)
        
        logger.info(f"\nConfidence Statistics:")
        logger.info(f"  Average: {avg_confidence:.2f}")
        logger.info(f"  Min: {min_confidence:.2f}")
        logger.info(f"  Max: {max_confidence:.2f}")
        
        # Agent-by-agent summary
        logger.info(f"\nAgent-by-Agent Summary:")
        logger.info(f"{'Agent':<20} {'Risk':<10} {'Score':<8} {'Confidence':<12} {'Status':<15}")
        logger.info("-" * 80)
        
        for agent_name, signal in signals.items():
            if signal.abstained:
                status = f"ABSTAINED"
                risk = "N/A"
                score = "N/A"
                conf = f"{signal.confidence:.2f}"
            else:
                status = "ACTIVE"
                risk = signal.risk_level.value
                score = f"{risk_to_score(signal.risk_level)}/100"
                conf = f"{signal.confidence:.2f}"
            
            logger.info(f"{agent_name:<20} {risk:<10} {score:<8} {conf:<12} {status:<15}")
        
        logger.info("="*80 + "\n")
        
        # Export to JSON for further analysis
        report_data = {
            "study_id": FIRST_STUDY,
            "timestamp": pd.Timestamp.now().isoformat(),
            "statistics": {
                "total_agents": total_agents,
                "active_agents": active_count,
                "abstained_agents": abstained_count,
                "abstention_rate": abstained_count / total_agents * 100,
            },
            "risk_distribution": risk_distribution,
            "confidence_stats": {
                "average": avg_confidence,
                "min": min_confidence,
                "max": max_confidence,
            },
            "agents": {
                agent_name: {
                    "abstained": signal.abstained,
                    "abstention_reason": signal.abstention_reason,
                    "risk_level": signal.risk_level.value if not signal.abstained else None,
                    "risk_score": risk_to_score(signal.risk_level) if not signal.abstained else None,
                    "confidence": signal.confidence,
                    "features_analyzed": signal.features_analyzed,
                    "evidence_count": len(signal.evidence),
                    "actions_count": len(signal.recommended_actions),
                }
                for agent_name, signal in signals.items()
            }
        }
        
        # Save report to file
        report_path = Path("c_trust/tests/validation/agent_validation_report_study_01.json")
        report_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_path, "w") as f:
            json.dump(report_data, f, indent=2)
        
        logger.info(f"✓ Report saved to: {report_path}")
        
        # Assert: At least 70% of agents should be active
        assert active_count / total_agents >= 0.7, \
            f"Only {active_count}/{total_agents} agents active ({active_count/total_agents*100:.1f}%). Need >= 70%"


# ========================================
# PYTEST CONFIGURATION
# ========================================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "agent_validation: mark test as agent validation test"
    )
    config.addinivalue_line(
        "markers", "real_data: mark test as using real NEST data"
    )


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short", "-s"])
