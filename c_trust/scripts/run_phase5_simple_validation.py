"""
Phase 5 Simple Validation Script

This script runs a simplified validation of the C-TRUST system:
1. Validates that all components are working
2. Tests a subset of studies (3-5) for speed
3. Generates a validation summary

Usage:
    python scripts/run_phase5_simple_validation.py
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
import pandas as pd

# Add project root to path
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
from src.intelligence.consensus import ConsensusEngine
from src.intelligence.dqi_engine_agent_driven import calculate_dqi_from_agents
from src.core import get_logger

logger = get_logger(__name__)


class Phase5Validator:
    """Simple Phase 5 validation"""
    
    def __init__(self):
        self.discovery = StudyDiscovery()
        self.ingestion = DataIngestionEngine()
        self.feature_extractor = RealFeatureExtractor()
        self.consensus_engine = ConsensusEngine()
        
        self.agents = {
            "Safety": SafetyComplianceAgent(),
            "Completeness": DataCompletenessAgent(),
            "Coding": CodingReadinessAgent(),
            "Query Quality": QueryQualityAgent(),
            "EDC Quality": EDCQualityAgent(),
            "Temporal Drift": TemporalDriftAgent(),
            "Stability": StabilityAgent(),
        }
        
        self.results = []
    
    def run_validation(self, max_studies: int = 5):
        """Run validation on a subset of studies"""
        print("="*80)
        print("PHASE 5: SIMPLE VALIDATION")
        print("="*80)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Discover studies
        print("[1/4] Discovering studies...")
        studies = self.discovery.discover_all_studies()
        print(f"  Found {len(studies)} studies")
        
        # Test subset
        test_studies = studies[:max_studies]
        print(f"  Testing first {len(test_studies)} studies")
        print()
        
        # Process each study
        print(f"[2/4] Processing studies...")
        for i, study in enumerate(test_studies, 1):
            print(f"\n  [{i}/{len(test_studies)}] Processing {study.study_id}...")
            result = self._process_study(study)
            self.results.append(result)
            
            if result["success"]:
                print(f"    ✓ Success")
                print(f"      DQI: {result['dqi_score']:.1f}")
                print(f"      Risk: {result['risk_level']}")
                print(f"      Agents: {result['agent_count']}/7 active")
            else:
                print(f"    ✗ Failed: {result['error']}")
        
        # Generate summary
        print(f"\n[3/4] Generating summary...")
        self._generate_summary()
        
        # Validate results
        print(f"\n[4/4] Validating results...")
        validation_passed = self._validate_results()
        
        print("\n" + "="*80)
        print("VALIDATION COMPLETE")
        print("="*80)
        print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if validation_passed:
            print("\n✓ ALL VALIDATION CHECKS PASSED")
            return 0
        else:
            print("\n✗ SOME VALIDATION CHECKS FAILED")
            return 1
    
    def _process_study(self, study) -> Dict[str, Any]:
        """Process a single study"""
        try:
            # Ingest data
            data = self.ingestion.ingest_study(study, validate_data=False)
            
            # Extract features
            features = self.feature_extractor.extract_features(data, study.study_id)
            
            # Run agents
            agent_signals = []
            for agent_name, agent in self.agents.items():
                try:
                    signal = agent.analyze(features, study.study_id)
                    agent_signals.append(signal)
                except Exception as e:
                    logger.warning(f"Agent {agent_name} failed: {e}")
            
            # Calculate consensus
            consensus = self.consensus_engine.calculate_consensus(agent_signals, study.study_id)
            
            # Calculate DQI
            dqi = calculate_dqi_from_agents(agent_signals, consensus)
            
            return {
                "success": True,
                "study_id": study.study_id,
                "dqi_score": dqi.score,
                "risk_level": consensus.risk_level.name,
                "risk_score": consensus.risk_score,
                "confidence": consensus.confidence,
                "agent_count": len([a for a in agent_signals if not a.abstained]),
                "abstention_count": len([a for a in agent_signals if a.abstained]),
                "error": None
            }
        except Exception as e:
            return {
                "success": False,
                "study_id": study.study_id,
                "error": str(e)
            }
    
    def _generate_summary(self):
        """Generate validation summary"""
        successful = [r for r in self.results if r["success"]]
        failed = [r for r in self.results if not r["success"]]
        
        print(f"\n  Processed: {len(self.results)} studies")
        print(f"  Successful: {len(successful)}")
        print(f"  Failed: {len(failed)}")
        
        if successful:
            dqi_scores = [r["dqi_score"] for r in successful]
            avg_dqi = sum(dqi_scores) / len(dqi_scores)
            min_dqi = min(dqi_scores)
            max_dqi = max(dqi_scores)
            
            print(f"\n  DQI Statistics:")
            print(f"    Average: {avg_dqi:.1f}")
            print(f"    Min: {min_dqi:.1f}")
            print(f"    Max: {max_dqi:.1f}")
            
            agent_counts = [r["agent_count"] for r in successful]
            avg_agents = sum(agent_counts) / len(agent_counts)
            print(f"\n  Agent Statistics:")
            print(f"    Average active agents: {avg_agents:.1f}/7")
    
    def _validate_results(self) -> bool:
        """Validate results meet acceptance criteria"""
        successful = [r for r in self.results if r["success"]]
        
        if not successful:
            print("  ✗ No successful studies processed")
            return False
        
        # Check 1: Success rate >= 80%
        success_rate = len(successful) / len(self.results)
        check1 = success_rate >= 0.8
        print(f"  {'✓' if check1 else '✗'} Success rate: {success_rate:.1%} (target: >= 80%)")
        
        # Check 2: Average DQI >= 70
        dqi_scores = [r["dqi_score"] for r in successful]
        avg_dqi = sum(dqi_scores) / len(dqi_scores)
        check2 = avg_dqi >= 70
        print(f"  {'✓' if check2 else '✗'} Average DQI: {avg_dqi:.1f} (target: >= 70)")
        
        # Check 3: All DQI scores in valid range
        check3 = all(0 <= score <= 100 for score in dqi_scores)
        print(f"  {'✓' if check3 else '✗'} DQI scores in valid range [0, 100]")
        
        # Check 4: At least 5 agents active on average
        agent_counts = [r["agent_count"] for r in successful]
        avg_agents = sum(agent_counts) / len(agent_counts)
        check4 = avg_agents >= 5
        print(f"  {'✓' if check4 else '✗'} Average active agents: {avg_agents:.1f}/7 (target: >= 5)")
        
        return all([check1, check2, check3, check4])


def main():
    """Main entry point"""
    try:
        validator = Phase5Validator()
        exit_code = validator.run_validation(max_studies=5)
        sys.exit(exit_code)
    except Exception as e:
        print(f"\n✗ Validation failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
