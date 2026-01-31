"""
Batch Agent Validation Script - All 23 NEST Studies
====================================================
Phase 0 Task 1.2: Run all 7 agents on all 23 NEST studies to identify patterns
and issues before integrating agents with DQI.

This script:
1. Runs all 7 agents on all 23 NEST studies
2. Generates comprehensive performance report
3. Identifies studies where agents abstain
4. Identifies missing features causing abstentions
5. Exports results as CSV and JSON

**Validates: Requirements US-0 (Phase 0 Acceptance Criteria)**

Usage:
    cd c_trust
    python scripts/run_agents_all_studies.py
"""

import sys
from pathlib import Path
import pandas as pd
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from collections import defaultdict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

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
# CONFIGURATION
# ========================================

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

# Risk level to numeric score mapping
RISK_TO_SCORE = {
    RiskSignal.CRITICAL: 90,
    RiskSignal.HIGH: 70,
    RiskSignal.MEDIUM: 50,
    RiskSignal.LOW: 20,
    RiskSignal.UNKNOWN: 0,
}

# Output directory
OUTPUT_DIR = Path("c_trust/reports/agent_validation")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ========================================
# HELPER FUNCTIONS
# ========================================

def risk_to_score(risk_level: RiskSignal) -> int:
    """Convert risk level to numeric score (0-100)."""
    return RISK_TO_SCORE.get(risk_level, 0)


def load_study_data(study_id: str, discovery, ingestion) -> Dict[str, pd.DataFrame]:
    """
    Load raw NEST data for a study.
    
    Args:
        study_id: Study identifier (e.g., "STUDY_01")
        discovery: StudyDiscovery instance
        ingestion: DataIngestionEngine instance
    
    Returns:
        Dictionary of DataFrames by file type
    """
    try:
        # Find the study
        studies = discovery.discover_all_studies()
        study_obj = None
        
        for study in studies:
            if study.study_id == study_id:
                study_obj = study
                break
        
        if study_obj is None:
            logger.error(f"Study {study_id} not found")
            return {}
        
        # Load data
        logger.info(f"Loading data for {study_id}")
        data = ingestion.ingest_study(study_obj, validate_data=False)
        
        return data
    except Exception as e:
        logger.error(f"Failed to load data for {study_id}: {e}")
        return {}


def extract_study_features(study_id: str, data: Dict[str, pd.DataFrame], 
                          feature_extractor) -> Dict[str, Any]:
    """
    Extract features for a study.
    
    Args:
        study_id: Study identifier
        data: Raw study data
        feature_extractor: RealFeatureExtractor instance
    
    Returns:
        Dictionary of extracted features
    """
    try:
        if not data:
            logger.error(f"No data loaded for {study_id}")
            return {}
        
        logger.info(f"Extracting features for {study_id}")
        features = feature_extractor.extract_features(data, study_id)
        
        logger.info(f"Extracted {len(features)} features for {study_id}")
        return features
    except Exception as e:
        logger.error(f"Failed to extract features for {study_id}: {e}")
        return {}


def run_agent(agent_class, features: Dict[str, Any], study_id: str) -> Optional[AgentSignal]:
    """
    Run a single agent on features.
    
    Args:
        agent_class: Agent class to instantiate
        features: Extracted features
        study_id: Study identifier
    
    Returns:
        AgentSignal from the agent, or None if error
    """
    try:
        agent = agent_class()
        signal = agent.analyze(features, study_id)
        return signal
    except Exception as e:
        logger.error(f"Failed to run {agent_class.__name__} on {study_id}: {e}")
        return None


def run_all_agents_on_study(study_id: str, discovery, ingestion, 
                            feature_extractor) -> Dict[str, Any]:
    """
    Run all 7 agents on a single study.
    
    Args:
        study_id: Study identifier
        discovery: StudyDiscovery instance
        ingestion: DataIngestionEngine instance
        feature_extractor: RealFeatureExtractor instance
    
    Returns:
        Dictionary with study results
    """
    logger.info(f"\n{'='*80}")
    logger.info(f"Processing Study: {study_id}")
    logger.info(f"{'='*80}")
    
    result = {
        "study_id": study_id,
        "timestamp": datetime.now().isoformat(),
        "status": "success",
        "error": None,
        "features_extracted": 0,
        "agents": {}
    }
    
    try:
        # Load data
        data = load_study_data(study_id, discovery, ingestion)
        if not data:
            result["status"] = "failed"
            result["error"] = "Failed to load study data"
            return result
        
        # Extract features
        features = extract_study_features(study_id, data, feature_extractor)
        if not features:
            result["status"] = "failed"
            result["error"] = "Failed to extract features"
            return result
        
        result["features_extracted"] = len(features)
        
        # Run all agents
        for agent_name, agent_class in ALL_AGENTS.items():
            logger.info(f"Running {agent_name} agent...")
            
            signal = run_agent(agent_class, features, study_id)
            
            if signal is None:
                result["agents"][agent_name] = {
                    "status": "error",
                    "error": "Agent execution failed"
                }
                continue
            
            # Store agent results
            result["agents"][agent_name] = {
                "status": "success",
                "abstained": signal.abstained,
                "abstention_reason": signal.abstention_reason if signal.abstained else None,
                "risk_level": signal.risk_level.value if not signal.abstained else None,
                "risk_score": risk_to_score(signal.risk_level) if not signal.abstained else None,
                "confidence": signal.confidence,
                "features_analyzed": signal.features_analyzed,
                "evidence_count": len(signal.evidence),
                "actions_count": len(signal.recommended_actions),
            }
            
            # Log summary
            if signal.abstained:
                logger.warning(f"  {agent_name}: ABSTAINED - {signal.abstention_reason}")
            else:
                logger.info(f"  {agent_name}: {signal.risk_level.value.upper()} "
                          f"(score={risk_to_score(signal.risk_level)}, "
                          f"confidence={signal.confidence:.2f})")
        
        logger.info(f"✓ Completed {study_id}")
        
    except Exception as e:
        logger.error(f"Error processing {study_id}: {e}")
        result["status"] = "failed"
        result["error"] = str(e)
    
    return result


# ========================================
# MAIN EXECUTION
# ========================================

def main():
    """Main execution function."""
    logger.info("="*80)
    logger.info("BATCH AGENT VALIDATION - ALL 23 NEST STUDIES")
    logger.info("="*80)
    logger.info(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Output directory: {OUTPUT_DIR}")
    logger.info("")
    
    # Initialize engines
    logger.info("Initializing data engines...")
    discovery = StudyDiscovery()
    ingestion = DataIngestionEngine()
    feature_extractor = RealFeatureExtractor()
    
    # Discover all studies
    logger.info("Discovering studies...")
    all_studies = discovery.discover_all_studies()
    study_ids = [study.study_id for study in all_studies]
    
    logger.info(f"Found {len(study_ids)} studies")
    logger.info(f"Studies: {', '.join(study_ids[:5])}...")
    logger.info("")
    
    # Run agents on all studies
    all_results = []
    
    for i, study_id in enumerate(study_ids, 1):
        logger.info(f"\n[{i}/{len(study_ids)}] Processing {study_id}...")
        
        result = run_all_agents_on_study(study_id, discovery, ingestion, feature_extractor)
        all_results.append(result)
    
    # Generate reports
    logger.info("\n" + "="*80)
    logger.info("GENERATING REPORTS")
    logger.info("="*80)
    
    generate_reports(all_results)
    
    logger.info("\n" + "="*80)
    logger.info("BATCH VALIDATION COMPLETE")
    logger.info("="*80)
    logger.info(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Reports saved to: {OUTPUT_DIR}")


def generate_reports(all_results: List[Dict[str, Any]]):
    """
    Generate comprehensive reports from all results.
    
    Args:
        all_results: List of study results
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # ========================================
    # 1. OVERALL STATISTICS
    # ========================================
    
    total_studies = len(all_results)
    successful_studies = sum(1 for r in all_results if r["status"] == "success")
    failed_studies = total_studies - successful_studies
    
    logger.info(f"\nOverall Statistics:")
    logger.info(f"  Total Studies: {total_studies}")
    logger.info(f"  Successful: {successful_studies}")
    logger.info(f"  Failed: {failed_studies}")
    
    # ========================================
    # 2. AGENT ABSTENTION ANALYSIS
    # ========================================
    
    logger.info(f"\nAgent Abstention Analysis:")
    
    # Count abstentions per agent across all studies
    abstention_counts = defaultdict(int)
    abstention_reasons = defaultdict(list)
    total_agent_runs = 0
    
    for result in all_results:
        if result["status"] != "success":
            continue
        
        for agent_name, agent_data in result["agents"].items():
            if agent_data["status"] == "success":
                total_agent_runs += 1
                
                if agent_data["abstained"]:
                    abstention_counts[agent_name] += 1
                    abstention_reasons[agent_name].append({
                        "study_id": result["study_id"],
                        "reason": agent_data["abstention_reason"]
                    })
    
    # Calculate abstention rates
    for agent_name in ALL_AGENTS.keys():
        count = abstention_counts[agent_name]
        rate = (count / successful_studies * 100) if successful_studies > 0 else 0
        
        logger.info(f"  {agent_name}: {count}/{successful_studies} studies ({rate:.1f}%)")
        
        if count > 0:
            # Show sample reasons
            reasons = abstention_reasons[agent_name]
            unique_reasons = set(r["reason"] for r in reasons)
            logger.info(f"    Reasons: {', '.join(list(unique_reasons)[:3])}")
    
    # Overall abstention rate
    total_abstentions = sum(abstention_counts.values())
    overall_abstention_rate = (total_abstentions / total_agent_runs * 100) if total_agent_runs > 0 else 0
    
    logger.info(f"\n  Overall Abstention Rate: {overall_abstention_rate:.1f}% "
               f"({total_abstentions}/{total_agent_runs} agent runs)")
    
    # ========================================
    # 3. RISK SCORE DISTRIBUTION
    # ========================================
    
    logger.info(f"\nRisk Score Distribution:")
    
    risk_distribution = defaultdict(lambda: defaultdict(int))
    
    for result in all_results:
        if result["status"] != "success":
            continue
        
        for agent_name, agent_data in result["agents"].items():
            if agent_data["status"] == "success" and not agent_data["abstained"]:
                risk_level = agent_data["risk_level"]
                risk_distribution[agent_name][risk_level] += 1
    
    for agent_name in ALL_AGENTS.keys():
        dist = risk_distribution[agent_name]
        total = sum(dist.values())
        
        if total == 0:
            logger.info(f"  {agent_name}: No active runs")
            continue
        
        logger.info(f"  {agent_name}:")
        for risk_level in ["critical", "high", "medium", "low"]:
            count = dist.get(risk_level, 0)
            pct = (count / total * 100) if total > 0 else 0
            logger.info(f"    {risk_level.upper()}: {count} ({pct:.1f}%)")
    
    # ========================================
    # 4. CONFIDENCE STATISTICS
    # ========================================
    
    logger.info(f"\nConfidence Statistics:")
    
    confidence_stats = defaultdict(list)
    
    for result in all_results:
        if result["status"] != "success":
            continue
        
        for agent_name, agent_data in result["agents"].items():
            if agent_data["status"] == "success":
                confidence_stats[agent_name].append(agent_data["confidence"])
    
    for agent_name in ALL_AGENTS.keys():
        confidences = confidence_stats[agent_name]
        
        if not confidences:
            logger.info(f"  {agent_name}: No data")
            continue
        
        avg = sum(confidences) / len(confidences)
        min_conf = min(confidences)
        max_conf = max(confidences)
        
        logger.info(f"  {agent_name}: avg={avg:.2f}, min={min_conf:.2f}, max={max_conf:.2f}")
    
    # ========================================
    # 5. EXPORT CSV REPORT
    # ========================================
    
    logger.info(f"\nExporting CSV report...")
    
    csv_rows = []
    
    for result in all_results:
        for agent_name in ALL_AGENTS.keys():
            if result["status"] != "success":
                row = {
                    "study_id": result["study_id"],
                    "agent_name": agent_name,
                    "status": "study_failed",
                    "error": result.get("error", "Unknown error"),
                    "abstained": None,
                    "abstention_reason": None,
                    "risk_level": None,
                    "risk_score": None,
                    "confidence": None,
                    "features_analyzed": None,
                    "evidence_count": None,
                    "actions_count": None,
                }
            else:
                agent_data = result["agents"].get(agent_name, {})
                
                if agent_data.get("status") != "success":
                    row = {
                        "study_id": result["study_id"],
                        "agent_name": agent_name,
                        "status": "agent_failed",
                        "error": agent_data.get("error", "Unknown error"),
                        "abstained": None,
                        "abstention_reason": None,
                        "risk_level": None,
                        "risk_score": None,
                        "confidence": None,
                        "features_analyzed": None,
                        "evidence_count": None,
                        "actions_count": None,
                    }
                else:
                    row = {
                        "study_id": result["study_id"],
                        "agent_name": agent_name,
                        "status": "success",
                        "error": None,
                        "abstained": agent_data["abstained"],
                        "abstention_reason": agent_data["abstention_reason"],
                        "risk_level": agent_data["risk_level"],
                        "risk_score": agent_data["risk_score"],
                        "confidence": agent_data["confidence"],
                        "features_analyzed": agent_data["features_analyzed"],
                        "evidence_count": agent_data["evidence_count"],
                        "actions_count": agent_data["actions_count"],
                    }
            
            csv_rows.append(row)
    
    df = pd.DataFrame(csv_rows)
    csv_path = OUTPUT_DIR / f"agent_validation_all_studies_{timestamp}.csv"
    df.to_csv(csv_path, index=False)
    
    logger.info(f"  ✓ CSV report saved: {csv_path}")
    
    # ========================================
    # 6. EXPORT JSON REPORT
    # ========================================
    
    logger.info(f"\nExporting JSON report...")
    
    json_report = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "total_studies": total_studies,
            "successful_studies": successful_studies,
            "failed_studies": failed_studies,
            "total_agents": len(ALL_AGENTS),
            "total_agent_runs": total_agent_runs,
        },
        "statistics": {
            "abstention_counts": dict(abstention_counts),
            "overall_abstention_rate": overall_abstention_rate,
            "risk_distribution": {
                agent: dict(dist) for agent, dist in risk_distribution.items()
            },
            "confidence_stats": {
                agent: {
                    "average": sum(confs) / len(confs) if confs else 0,
                    "min": min(confs) if confs else 0,
                    "max": max(confs) if confs else 0,
                    "count": len(confs),
                }
                for agent, confs in confidence_stats.items()
            },
        },
        "abstention_details": {
            agent: reasons for agent, reasons in abstention_reasons.items()
        },
        "study_results": all_results,
    }
    
    json_path = OUTPUT_DIR / f"agent_validation_all_studies_{timestamp}.json"
    with open(json_path, "w") as f:
        json.dump(json_report, f, indent=2)
    
    logger.info(f"  ✓ JSON report saved: {json_path}")
    
    # ========================================
    # 7. EXPORT SUMMARY REPORT
    # ========================================
    
    logger.info(f"\nExporting summary report...")
    
    summary_lines = []
    summary_lines.append("="*80)
    summary_lines.append("AGENT VALIDATION SUMMARY - ALL 23 NEST STUDIES")
    summary_lines.append("="*80)
    summary_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    summary_lines.append("")
    
    summary_lines.append("OVERALL STATISTICS")
    summary_lines.append("-"*80)
    summary_lines.append(f"Total Studies: {total_studies}")
    summary_lines.append(f"Successful: {successful_studies}")
    summary_lines.append(f"Failed: {failed_studies}")
    summary_lines.append(f"Total Agent Runs: {total_agent_runs}")
    summary_lines.append(f"Total Abstentions: {total_abstentions}")
    summary_lines.append(f"Overall Abstention Rate: {overall_abstention_rate:.1f}%")
    summary_lines.append("")
    
    summary_lines.append("AGENT ABSTENTION RATES")
    summary_lines.append("-"*80)
    for agent_name in ALL_AGENTS.keys():
        count = abstention_counts[agent_name]
        rate = (count / successful_studies * 100) if successful_studies > 0 else 0
        summary_lines.append(f"{agent_name:<20} {count:>3}/{successful_studies:<3} ({rate:>5.1f}%)")
    summary_lines.append("")
    
    summary_lines.append("ACCEPTANCE CRITERIA STATUS")
    summary_lines.append("-"*80)
    
    # Check acceptance criteria
    criteria = []
    
    # 1. All 7 agents run successfully on all 23 studies
    all_agents_ran = all(
        agent_name in result.get("agents", {})
        for result in all_results if result["status"] == "success"
        for agent_name in ALL_AGENTS.keys()
    )
    criteria.append(("All 7 agents run on all studies", all_agents_ran))
    
    # 2. Agent abstention rate < 10%
    abstention_ok = overall_abstention_rate < 10
    criteria.append((f"Abstention rate < 10% (actual: {overall_abstention_rate:.1f}%)", abstention_ok))
    
    # 3. Agent risk scores are reasonable
    all_risk_scores = [
        agent_data["risk_score"]
        for result in all_results if result["status"] == "success"
        for agent_data in result["agents"].values()
        if agent_data["status"] == "success" and not agent_data["abstained"]
    ]
    risk_scores_ok = len(set(all_risk_scores)) > 1 if all_risk_scores else False
    criteria.append(("Risk scores are diverse (not all same)", risk_scores_ok))
    
    # 4. Agent confidence scores are reasonable
    all_confidences = [
        agent_data["confidence"]
        for result in all_results if result["status"] == "success"
        for agent_data in result["agents"].values()
        if agent_data["status"] == "success"
    ]
    avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0
    confidence_ok = avg_confidence > 0.5
    criteria.append((f"Average confidence > 0.5 (actual: {avg_confidence:.2f})", confidence_ok))
    
    for criterion, passed in criteria:
        status = "[PASS]" if passed else "[FAIL]"
        summary_lines.append(f"{status} {criterion}")
    
    summary_lines.append("")
    summary_lines.append("="*80)
    
    summary_text = "\n".join(summary_lines)
    
    summary_path = OUTPUT_DIR / f"agent_validation_summary_{timestamp}.txt"
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(summary_text)
    
    logger.info(f"  ✓ Summary report saved: {summary_path}")
    
    # Print summary to console
    print("\n" + summary_text)


if __name__ == "__main__":
    main()
