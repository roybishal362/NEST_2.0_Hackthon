"""
Simulated Data Validation Script
=================================
Validates that simulated studies produce DQI scores < 65 and that
real NEST data produces higher DQI than simulated data.

Phase 3, Task 14: Validate Simulated Data

Usage:
    python scripts/validate_simulated_data.py
    python scripts/validate_simulated_data.py --verbose
"""

import argparse
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple
import json
from datetime import datetime

from src.data.ingestion import DataIngestionEngine
from src.data.features_real_extraction import RealFeatureExtractor
from src.intelligence.dqi_engine_agent_driven import calculate_dqi_from_agents, DQIResult
from src.intelligence.consensus import ConsensusEngine
from src.agents.signal_agents.safety_agent import SafetyAgent
from src.agents.signal_agents.completeness_agent import CompletenessAgent
from src.agents.signal_agents.coding_agent import CodingAgent
from src.agents.signal_agents.query_quality_agent import QueryQualityAgent
from src.agents.signal_agents.edc_quality_agent import EDCQualityAgent
from src.agents.signal_agents.temporal_drift_agent import TemporalDriftAgent
from src.agents.signal_agents.stability_agent import StabilityAgent
from src.intelligence.consensus import ConsensusEngine


class SimulatedDataValidator:
    """Validates simulated data produces expected DQI scores"""
    
    def __init__(self):
        self.ingestion_engine = DataIngestionEngine()
        self.feature_extractor = RealFeatureExtractor()
        self.dqi_engine = DQIEngine()
        self.consensus_engine = ConsensusEngine()
        
        # Initialize agents
        self.agents = [
            SafetyAgent(),
            CompletenessAgent(),
            CodingAgent(),
            QueryQualityAgent(),
            EDCQualityAgent(),
            TemporalDriftAgent(),
            StabilityAgent()
        ]
        
        self.simulated_dir = Path("c_trust/data/simulated")
        self.results = []
    
    def validate_all_simulated_studies(self) -> pd.DataFrame:
        """
        Validate all simulated studies.
        
        Returns:
            DataFrame with validation results
        """
        print(f"\n{'='*80}")
        print("SIMULATED DATA VALIDATION")
        print(f"{'='*80}\n")
        
        # Find all simulated studies
        simulated_studies = [d.name for d in self.simulated_dir.iterdir() if d.is_dir()]
        
        if not simulated_studies:
            print("⚠️  No simulated studies found. Run generate_simulated_data.py first.")
            return pd.DataFrame()
        
        print(f"Found {len(simulated_studies)} simulated studies\n")
        
        for study_id in sorted(simulated_studies):
            print(f"Validating {study_id}...")
            result = self.validate_study(study_id)
            self.results.append(result)
            
            # Print result
            dqi_score = result['dqi_score']
            dqi_band = result['dqi_band']
            status = "✓ PASS" if dqi_score < 65 else "✗ FAIL"
            print(f"  DQI: {dqi_score:.1f} ({dqi_band}) - {status}\n")
        
        # Create DataFrame
        df = pd.DataFrame(self.results)
        
        # Generate summary
        self._print_summary(df)
        
        # Save report
        self._save_report(df)
        
        return df
    
    def validate_study(self, study_id: str) -> Dict:
        """
        Validate a single simulated study.
        
        Args:
            study_id: Study identifier (e.g., "SIM-001")
        
        Returns:
            Dictionary with validation results
        """
        try:
            # Ingest study data
            study_dir = self.simulated_dir / study_id
            raw_data = self.ingestion_engine.ingest_study(str(study_dir))
            
            # Extract features
            features = self.feature_extractor.extract_features(raw_data, study_id)
            
            # Run agents
            agent_signals = []
            for agent in self.agents:
                signal = agent.analyze(features, study_id)
                if signal:
                    agent_signals.append(signal)
            
            # Calculate consensus
            consensus = self.consensus_engine.calculate_consensus(agent_signals)
            
            # Calculate DQI
            dqi = self.dqi_engine.calculate_dqi(features, study_id)
            
            return {
                'study_id': study_id,
                'dqi_score': dqi.overall_score,
                'dqi_band': dqi.risk_level,
                'consensus_risk_level': consensus.risk_level,
                'consensus_risk_score': consensus.risk_score,
                'consensus_confidence': consensus.confidence,
                'agent_count': len(agent_signals),
                'abstained_count': len(self.agents) - len(agent_signals),
                'passes_validation': dqi.overall_score < 65,
                'timestamp': datetime.now().isoformat()
            }
        
        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            return {
                'study_id': study_id,
                'dqi_score': None,
                'dqi_band': None,
                'consensus_risk_level': None,
                'consensus_risk_score': None,
                'consensus_confidence': None,
                'agent_count': 0,
                'abstained_count': len(self.agents),
                'passes_validation': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def compare_real_vs_simulated(self) -> Tuple[float, float]:
        """
        Compare DQI scores: real NEST data vs simulated data.
        
        Returns:
            Tuple of (avg_real_dqi, avg_simulated_dqi)
        """
        print(f"\n{'='*80}")
        print("REAL vs SIMULATED COMPARISON")
        print(f"{'='*80}\n")
        
        # Get real NEST data DQI scores
        print("Loading real NEST data DQI scores...")
        cache_file = Path("data_cache.json")
        
        if not cache_file.exists():
            print("⚠️  No data cache found. Run regenerate_cache.py first.")
            return 0.0, 0.0
        
        with open(cache_file, 'r') as f:
            cache_data = json.load(f)
        
        real_dqi_scores = [
            data['overall_score'] 
            for data in cache_data.values() 
            if data.get('overall_score') is not None
        ]
        
        # Get simulated data DQI scores
        simulated_dqi_scores = [
            result['dqi_score'] 
            for result in self.results 
            if result.get('dqi_score') is not None
        ]
        
        if not real_dqi_scores or not simulated_dqi_scores:
            print("⚠️  Insufficient data for comparison")
            return 0.0, 0.0
        
        avg_real = sum(real_dqi_scores) / len(real_dqi_scores)
        avg_simulated = sum(simulated_dqi_scores) / len(simulated_dqi_scores)
        
        print(f"Real NEST data:")
        print(f"  Studies: {len(real_dqi_scores)}")
        print(f"  Average DQI: {avg_real:.1f}")
        print(f"  Min DQI: {min(real_dqi_scores):.1f}")
        print(f"  Max DQI: {max(real_dqi_scores):.1f}\n")
        
        print(f"Simulated data:")
        print(f"  Studies: {len(simulated_dqi_scores)}")
        print(f"  Average DQI: {avg_simulated:.1f}")
        print(f"  Min DQI: {min(simulated_dqi_scores):.1f}")
        print(f"  Max DQI: {max(simulated_dqi_scores):.1f}\n")
        
        # Validation
        if avg_real > avg_simulated:
            print(f"✓ PASS: Real data DQI ({avg_real:.1f}) > Simulated data DQI ({avg_simulated:.1f})")
        else:
            print(f"✗ FAIL: Real data DQI ({avg_real:.1f}) ≤ Simulated data DQI ({avg_simulated:.1f})")
        
        print(f"{'='*80}\n")
        
        return avg_real, avg_simulated
    
    def _print_summary(self, df: pd.DataFrame):
        """Print validation summary"""
        print(f"{'='*80}")
        print("VALIDATION SUMMARY")
        print(f"{'='*80}\n")
        
        total_studies = len(df)
        passed_studies = df['passes_validation'].sum()
        failed_studies = total_studies - passed_studies
        
        print(f"Total simulated studies: {total_studies}")
        print(f"Passed validation (DQI < 65): {passed_studies}")
        print(f"Failed validation (DQI ≥ 65): {failed_studies}")
        print(f"Pass rate: {(passed_studies / total_studies * 100):.1f}%\n")
        
        if failed_studies > 0:
            print("⚠️  Failed studies:")
            failed_df = df[~df['passes_validation']]
            for _, row in failed_df.iterrows():
                print(f"  - {row['study_id']}: DQI = {row['dqi_score']:.1f}")
            print()
        
        # DQI distribution
        print("DQI Score Distribution:")
        print(f"  Mean: {df['dqi_score'].mean():.1f}")
        print(f"  Median: {df['dqi_score'].median():.1f}")
        print(f"  Min: {df['dqi_score'].min():.1f}")
        print(f"  Max: {df['dqi_score'].max():.1f}")
        print(f"  Std Dev: {df['dqi_score'].std():.1f}\n")
        
        # Band distribution
        print("DQI Band Distribution:")
        band_counts = df['dqi_band'].value_counts()
        for band, count in band_counts.items():
            print(f"  {band}: {count} ({count / total_studies * 100:.1f}%)")
        print()
        
        print(f"{'='*80}\n")
    
    def _save_report(self, df: pd.DataFrame):
        """Save validation report"""
        output_dir = Path("c_trust/tests/integration")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save CSV
        csv_path = output_dir / "simulated_data_validation_report.csv"
        df.to_csv(csv_path, index=False)
        print(f"Report saved to: {csv_path}\n")
        
        # Save JSON
        json_path = output_dir / "simulated_data_validation_report.json"
        with open(json_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"JSON report saved to: {json_path}\n")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Validate simulated clinical trial data')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--compare', action='store_true', help='Compare real vs simulated data')
    
    args = parser.parse_args()
    
    validator = SimulatedDataValidator()
    
    # Validate simulated studies
    df = validator.validate_all_simulated_studies()
    
    # Compare real vs simulated
    if args.compare and not df.empty:
        validator.compare_real_vs_simulated()


if __name__ == "__main__":
    main()
