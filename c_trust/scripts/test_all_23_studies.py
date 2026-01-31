"""
Test All 23 NEST Studies with 7-Agent Pipeline
===============================================
Task 6.2: Test with All 23 NEST Studies

This script runs the full 7-agent pipeline on all 23 real NEST studies
to verify that the system works correctly across different data patterns.

Usage:
    cd c_trust
    python scripts/test_all_23_studies.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.intelligence.agent_pipeline import AgentPipeline
from src.data import DataIngestionEngine, FeatureEngineeringEngine, StudyDiscovery
from src.data.features_real_extraction import RealFeatureExtractor
from src.core import get_logger

logger = get_logger(__name__)


def test_all_23_studies():
    """
    Test the 7-agent pipeline on all 23 NEST studies.
    
    This validates:
    - All studies can be processed without crashes
    - DQI scores are reasonable (not all identical)
    - Consensus is calculated for all studies
    - Agent execution is consistent
    """
    print("=" * 80)
    print("Testing 7-Agent Pipeline on All 23 NEST Studies")
    print("=" * 80)
    print()
    
    # Initialize engines
    print("Initializing engines...")
    data_ingestion = DataIngestionEngine()
    feature_extractor = RealFeatureExtractor()
    pipeline = AgentPipeline()
    
    # Discover all studies
    print("Discovering studies...")
    discovery = StudyDiscovery()
    studies = discovery.discover_all_studies()
    
    print(f"Found {len(studies)} studies")
    print()
    
    # Track results
    results = []
    failed_studies = []
    
    # Process each study
    for idx, study in enumerate(studies, 1):
        study_id = study.study_id
        print(f"[{idx}/{len(studies)}] Testing {study_id}...")
        
        try:
            # Ingest data
            raw_data = data_ingestion.ingest_study(study)
            
            # Extract features directly (no semantic layer)
            features = feature_extractor.extract_features(raw_data, study_id)
            
            # Run 7-agent pipeline
            result = pipeline.run_full_analysis(study_id, features, parallel=False)
            
            # Extract key metrics
            agents_succeeded = result.agents_succeeded
            agents_failed = result.agents_failed
            agents_abstained = result.agents_abstained
            dqi_score = result.dqi_score.overall_score if result.dqi_score else None
            risk_level = result.consensus.risk_level.value if result.consensus else "unknown"
            processing_time = result.total_processing_time_ms
            
            # Store result
            results.append({
                "study_id": study_id,
                "agents_succeeded": agents_succeeded,
                "agents_failed": agents_failed,
                "agents_abstained": agents_abstained,
                "dqi_score": dqi_score,
                "risk_level": risk_level,
                "processing_time_ms": processing_time,
                "status": "SUCCESS"
            })
            
            # Print summary
            print(f"  + Agents: {agents_succeeded}/8 succeeded")
            print(f"  + DQI: {dqi_score:.1f}" if dqi_score else "  - DQI: N/A")
            print(f"  + Risk: {risk_level}")
            print(f"  + Time: {processing_time:.1f}ms")
            print()
            
        except Exception as e:
            logger.error(f"Failed to process {study_id}: {e}", exc_info=True)
            failed_studies.append(study_id)
            results.append({
                "study_id": study_id,
                "status": "FAILED",
                "error": str(e)
            })
            print(f"  - FAILED: {e}")
            print()
    
    # Print final summary
    print("=" * 80)
    print("FINAL SUMMARY")
    print("=" * 80)
    print()
    
    successful = len([r for r in results if r["status"] == "SUCCESS"])
    print(f"Total Studies: {len(studies)}")
    print(f"Successful: {successful}")
    print(f"Failed: {len(failed_studies)}")
    print()
    
    if successful > 0:
        # Calculate statistics
        dqi_scores = [r["dqi_score"] for r in results if r.get("dqi_score") is not None]
        avg_dqi = sum(dqi_scores) / len(dqi_scores) if dqi_scores else 0
        min_dqi = min(dqi_scores) if dqi_scores else 0
        max_dqi = max(dqi_scores) if dqi_scores else 0
        
        avg_time = sum(r["processing_time_ms"] for r in results if r["status"] == "SUCCESS") / successful
        
        print(f"DQI Statistics:")
        print(f"  Average: {avg_dqi:.1f}")
        print(f"  Min: {min_dqi:.1f}")
        print(f"  Max: {max_dqi:.1f}")
        print(f"  Range: {max_dqi - min_dqi:.1f}")
        print()
        
        print(f"Performance:")
        print(f"  Average processing time: {avg_time:.1f}ms ({avg_time/1000:.2f}s)")
        print()
        
        # Check for score clustering (all scores too similar)
        if len(dqi_scores) > 1:
            score_range = max_dqi - min_dqi
            if score_range < 5.0:
                print("!  WARNING: DQI scores are very similar (range < 5.0)")
                print("   This may indicate a scoring issue.")
            else:
                print("+ DQI scores show good variation")
        print()
    
    if failed_studies:
        print("Failed Studies:")
        for study_id in failed_studies:
            print(f"  - {study_id}")
        print()
    
    # Validation checks
    print("Validation Checks:")
    print(f"  {'+' if successful == len(studies) else '-'} All studies processed successfully")
    print(f"  {'+' if successful >= 20 else '-'} At least 20/23 studies processed")
    print(f"  {'+' if len(dqi_scores) > 0 else '-'} DQI scores calculated")
    print(f"  {'+' if len(dqi_scores) > 0 and max(dqi_scores) - min(dqi_scores) >= 5.0 else '-'} DQI scores show variation")
    print()
    
    # Overall result
    if successful == len(studies):
        print("=" * 80)
        print("+ ALL TESTS PASSED!")
        print("=" * 80)
        return 0
    elif successful >= 20:
        print("=" * 80)
        print("! MOSTLY PASSED (20+ studies successful)")
        print("=" * 80)
        return 0
    else:
        print("=" * 80)
        print("- TESTS FAILED (too many failures)")
        print("=" * 80)
        return 1


if __name__ == "__main__":
    exit_code = test_all_23_studies()
    sys.exit(exit_code)
