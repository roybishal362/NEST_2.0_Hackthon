"""
Simple Simulated Data Validation Script
========================================
Validates that simulated studies produce DQI scores < 65.

Usage:
    python scripts/validate_simulated_data_simple.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from typing import Dict, List
import json
from datetime import datetime

from src.data.ingestion import DataIngestionEngine
from src.data.models import Study
from src.data.features_real_extraction import RealFeatureExtractor
from src.intelligence.dqi_engine_agent_driven import calculate_dqi_from_agents
from src.intelligence.consensus import ConsensusEngine
from src.agents.signal_agents.safety_agent import SafetyComplianceAgent
from src.agents.signal_agents.completeness_agent import DataCompletenessAgent
from src.agents.signal_agents.coding_agent import CodingReadinessAgent
from src.agents.signal_agents.query_agent import QueryQualityAgent
from src.agents.signal_agents.edc_quality_agent import EDCQualityAgent
from src.agents.signal_agents.temporal_drift_agent import TemporalDriftAgent
from src.agents.signal_agents.stability_agent import StabilityAgent


def validate_simulated_studies():
    """Validate all simulated studies"""
    
    print(f"\n{'='*80}")
    print("SIMULATED DATA VALIDATION")
    print(f"{'='*80}\n")
    
    # Initialize components
    ingestion_engine = DataIngestionEngine()
    feature_extractor = RealFeatureExtractor()
    consensus_engine = ConsensusEngine()
    
    # Initialize agents
    agents = [
        SafetyComplianceAgent(),
        DataCompletenessAgent(),
        CodingReadinessAgent(),
        QueryQualityAgent(),
        EDCQualityAgent(),
        TemporalDriftAgent(),
        StabilityAgent()
    ]
    
    # Find simulated studies
    simulated_dir = Path("data/simulated")
    if not simulated_dir.exists():
        print("⚠️  No simulated studies found. Run generate_simulated_data.py first.")
        return
    
    simulated_studies = [d.name for d in simulated_dir.iterdir() if d.is_dir()]
    
    if not simulated_studies:
        print("⚠️  No simulated studies found.")
        return
    
    print(f"Found {len(simulated_studies)} simulated studies\n")
    
    results = []
    
    for study_id in sorted(simulated_studies):
        print(f"Validating {study_id}...")
        
        try:
            # Create Study object
            study = Study(study_id=study_id)
            
            # Ingest study data
            raw_data = ingestion_engine.ingest_study(study)
            
            # Extract features
            features = feature_extractor.extract_features(raw_data, study_id)
            
            # Run agents
            agent_signals = []
            for agent in agents:
                signal = agent.analyze(features, study_id)
                if signal:
                    agent_signals.append(signal)
            
            # Calculate consensus
            consensus = consensus_engine.calculate_consensus(agent_signals)
            
            # Calculate DQI
            dqi = calculate_dqi_from_agents(agent_signals, consensus)
            
            result = {
                'study_id': study_id,
                'dqi_score': dqi.overall_score,
                'dqi_band': dqi.risk_level,
                'consensus_risk_level': consensus.risk_level,
                'consensus_risk_score': consensus.risk_score,
                'consensus_confidence': consensus.confidence,
                'agent_count': len(agent_signals),
                'abstained_count': len(agents) - len(agent_signals),
                'passes_validation': dqi.overall_score < 65,
                'timestamp': datetime.now().isoformat()
            }
            
            results.append(result)
            
            # Print result
            dqi_score = result['dqi_score']
            dqi_band = result['dqi_band']
            status = "✓ PASS" if dqi_score < 65 else "✗ FAIL"
            print(f"  DQI: {dqi_score:.1f} ({dqi_band}) - {status}\n")
        
        except Exception as e:
            print(f"  ✗ ERROR: {e}\n")
            results.append({
                'study_id': study_id,
                'dqi_score': None,
                'dqi_band': None,
                'error': str(e)
            })
    
    # Create DataFrame
    df = pd.DataFrame(results)
    
    # Print summary
    print(f"\n{'='*80}")
    print("VALIDATION SUMMARY")
    print(f"{'='*80}\n")
    
    passed = df[df['passes_validation'] == True]
    failed = df[df['passes_validation'] == False]
    errors = df[df['dqi_score'].isna()]
    
    print(f"Total studies: {len(df)}")
    print(f"Passed (DQI < 65): {len(passed)}")
    print(f"Failed (DQI >= 65): {len(failed)}")
    print(f"Errors: {len(errors)}")
    
    if len(passed) > 0:
        print(f"\nAverage DQI (passed): {passed['dqi_score'].mean():.1f}")
        print(f"Min DQI: {passed['dqi_score'].min():.1f}")
        print(f"Max DQI: {passed['dqi_score'].max():.1f}")
    
    # Save report
    output_file = Path("c_trust/exports/simulated_validation_report.csv")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_file, index=False)
    print(f"\n✓ Report saved to: {output_file}")
    
    # Save JSON
    json_file = Path("c_trust/exports/simulated_validation_report.json")
    with open(json_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"✓ JSON saved to: {json_file}")
    
    print(f"\n{'='*80}\n")
    
    return df


if __name__ == "__main__":
    validate_simulated_studies()
