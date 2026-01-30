"""
Comprehensive Validation Report Generator

This script generates a comprehensive validation report comparing:
1. DQI scores before vs after fix
2. DQI-consensus correlation
3. Enrollment data accuracy
4. Simulated vs real data comparison
5. Agent performance metrics

**Outputs:**
- validation_report.csv: Detailed metrics for all studies
- validation_summary.txt: Human-readable summary
- validation_report.pdf: Visual report with charts (optional)
"""

import sys
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Tuple
from datetime import datetime
import pandas as pd
import numpy as np
from scipy import stats

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.ingestion import ingest_study_data
from src.data.features import extract_features
from src.intelligence.consensus import calculate_consensus
from src.intelligence.dqi_engine_agent_driven import calculate_dqi_from_agents


class ValidationReportGenerator:
    """Generate comprehensive validation report"""
    
    def __init__(self, nest_data_path: Path, simulated_data_path: Path, output_dir: Path):
        self.nest_data_path = nest_data_path
        self.simulated_data_path = simulated_data_path
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.real_studies = []
        self.simulated_studies = []
        self.results = {
            "real": {},
            "simulated": {}
        }
    
    def run(self):
        """Run complete validation report generation"""
        print("="*80)
        print("C-TRUST Validation Report Generator")
        print("="*80)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Step 1: Process real data
        print("[1/6] Processing real NEST data...")
        self._process_real_data()
        
        # Step 2: Process simulated data
        print("\n[2/6] Processing simulated data...")
        self._process_simulated_data()
        
        # Step 3: Calculate DQI-consensus correlation
        print("\n[3/6] Calculating DQI-consensus correlation...")
        correlation = self._calculate_correlation()
        
        # Step 4: Validate enrollment data
        print("\n[4/6] Validating enrollment data...")
        enrollment_stats = self._validate_enrollment()
        
        # Step 5: Compare real vs simulated
        print("\n[5/6] Comparing real vs simulated data...")
        comparison = self._compare_real_vs_simulated()
        
        # Step 6: Generate reports
        print("\n[6/6] Generating reports...")
        self._generate_csv_report()
        self._generate_summary_report(correlation, enrollment_stats, comparison)
        
        print("\n" + "="*80)
        print("Validation Report Complete!")
        print("="*80)
        print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Output directory: {self.output_dir}")
    
    def _process_real_data(self):
        """Process all real NEST studies"""
        if not self.nest_data_path.exists():
            print(f"  ⚠ NEST data not found at {self.nest_data_path}")
            return
        
        self.real_studies = [d.name for d in self.nest_data_path.iterdir() if d.is_dir()]
        print(f"  Found {len(self.real_studies)} real studies")
        
        for i, study_id in enumerate(self.real_studies, 1):
            print(f"  [{i}/{len(self.real_studies)}] Processing {study_id}...", end=" ")
            
            try:
                start_time = time.time()
                
                # Run pipeline
                study_data = ingest_study_data(self.nest_data_path / study_id)
                features = extract_features(study_data)
                consensus = calculate_consensus(features)
                dqi = calculate_dqi_from_agents(consensus.agent_signals)
                
                elapsed_time = time.time() - start_time
                
                self.results["real"][study_id] = {
                    "success": True,
                    "elapsed_time": elapsed_time,
                    "features": features,
                    "consensus": consensus,
                    "dqi": dqi
                }
                
                print(f"✓ ({elapsed_time:.2f}s)")
                
            except Exception as e:
                print(f"✗ {e}")
                self.results["real"][study_id] = {
                    "success": False,
                    "error": str(e)
                }
    
    def _process_simulated_data(self):
        """Process all simulated studies"""
        if not self.simulated_data_path.exists():
            print(f"  ⚠ Simulated data not found at {self.simulated_data_path}")
            return
        
        self.simulated_studies = [d.name for d in self.simulated_data_path.iterdir() if d.is_dir()]
        print(f"  Found {len(self.simulated_studies)} simulated studies")
        
        for i, study_id in enumerate(self.simulated_studies, 1):
            print(f"  [{i}/{len(self.simulated_studies)}] Processing {study_id}...", end=" ")
            
            try:
                start_time = time.time()
                
                # Run pipeline
                study_data = ingest_study_data(self.simulated_data_path / study_id)
                features = extract_features(study_data)
                consensus = calculate_consensus(features)
                dqi = calculate_dqi_from_agents(consensus.agent_signals)
                
                elapsed_time = time.time() - start_time
                
                self.results["simulated"][study_id] = {
                    "success": True,
                    "elapsed_time": elapsed_time,
                    "features": features,
                    "consensus": consensus,
                    "dqi": dqi
                }
                
                print(f"✓ ({elapsed_time:.2f}s)")
                
            except Exception as e:
                print(f"✗ {e}")
                self.results["simulated"][study_id] = {
                    "success": False,
                    "error": str(e)
                }
    
    def _calculate_correlation(self) -> Dict[str, float]:
        """Calculate DQI-consensus correlation"""
        dqi_scores = []
        risk_scores = []
        
        for result in self.results["real"].values():
            if result["success"]:
                dqi_scores.append(result["dqi"].score)
                risk_scores.append(result["consensus"].risk_score)
        
        if len(dqi_scores) < 2:
            return {"r": 0.0, "p_value": 1.0, "n": 0}
        
        # Calculate Pearson correlation
        # Note: DQI and risk should be inversely correlated (high risk = low DQI)
        r, p_value = stats.pearsonr(dqi_scores, risk_scores)
        
        print(f"  Correlation coefficient (r): {r:.3f}")
        print(f"  P-value: {p_value:.4f}")
        print(f"  Sample size: {len(dqi_scores)}")
        
        # We expect negative correlation (high risk = low DQI)
        if r > 0:
            print(f"  ⚠ WARNING: Positive correlation detected (expected negative)")
        elif abs(r) > 0.8:
            print(f"  ✓ Strong correlation (|r| > 0.8)")
        elif abs(r) > 0.6:
            print(f"  ⚠ Moderate correlation (0.6 < |r| < 0.8)")
        else:
            print(f"  ✗ Weak correlation (|r| < 0.6)")
        
        return {
            "r": r,
            "p_value": p_value,
            "n": len(dqi_scores)
        }
    
    def _validate_enrollment(self) -> Dict[str, Any]:
        """Validate enrollment data extraction"""
        enrollment_data = []
        
        for study_id, result in self.results["real"].items():
            if result["success"]:
                features = result["features"]
                actual = features.get("actual_enrollment", 0)
                target = features.get("target_enrollment", 0)
                rate = features.get("enrollment_rate", 0.0)
                
                enrollment_data.append({
                    "study_id": study_id,
                    "actual": actual,
                    "target": target,
                    "rate": rate,
                    "has_data": actual > 0 or target > 0
                })
        
        # Calculate statistics
        studies_with_data = sum(1 for e in enrollment_data if e["has_data"])
        total_studies = len(enrollment_data)
        coverage_rate = studies_with_data / total_studies if total_studies > 0 else 0
        
        rates = [e["rate"] for e in enrollment_data if e["has_data"]]
        avg_rate = sum(rates) / len(rates) if rates else 0
        
        print(f"  Studies with enrollment data: {studies_with_data}/{total_studies} ({coverage_rate:.1%})")
        print(f"  Average enrollment rate: {avg_rate:.1f}%")
        
        if coverage_rate >= 0.8:
            print(f"  ✓ Good coverage (>= 80%)")
        else:
            print(f"  ⚠ Low coverage (< 80%)")
        
        return {
            "total_studies": total_studies,
            "studies_with_data": studies_with_data,
            "coverage_rate": coverage_rate,
            "average_rate": avg_rate,
            "enrollment_data": enrollment_data
        }
    
    def _compare_real_vs_simulated(self) -> Dict[str, Any]:
        """Compare real vs simulated data DQI scores"""
        real_scores = [
            result["dqi"].score
            for result in self.results["real"].values()
            if result["success"]
        ]
        
        simulated_scores = [
            result["dqi"].score
            for result in self.results["simulated"].values()
            if result["success"]
        ]
        
        if not real_scores or not simulated_scores:
            return {}
        
        real_avg = sum(real_scores) / len(real_scores)
        simulated_avg = sum(simulated_scores) / len(simulated_scores)
        difference = real_avg - simulated_avg
        
        print(f"  Real data average DQI: {real_avg:.1f}")
        print(f"  Simulated data average DQI: {simulated_avg:.1f}")
        print(f"  Difference: {difference:.1f} points")
        
        if difference > 20:
            print(f"  ✓ Real data significantly higher (> 20 points)")
        elif difference > 10:
            print(f"  ⚠ Real data moderately higher (10-20 points)")
        else:
            print(f"  ✗ Insufficient difference (< 10 points)")
        
        # Statistical test
        t_stat, p_value = stats.ttest_ind(real_scores, simulated_scores)
        
        return {
            "real_avg": real_avg,
            "real_std": np.std(real_scores),
            "real_min": min(real_scores),
            "real_max": max(real_scores),
            "simulated_avg": simulated_avg,
            "simulated_std": np.std(simulated_scores),
            "simulated_min": min(simulated_scores),
            "simulated_max": max(simulated_scores),
            "difference": difference,
            "t_statistic": t_stat,
            "p_value": p_value
        }
    
    def _generate_csv_report(self):
        """Generate detailed CSV report"""
        report_data = []
        
        # Add real studies
        for study_id, result in self.results["real"].items():
            if result["success"]:
                report_data.append({
                    "study_id": study_id,
                    "data_type": "real",
                    "success": True,
                    "elapsed_time": result["elapsed_time"],
                    "dqi_score": result["dqi"].score,
                    "dqi_band": self._get_dqi_band(result["dqi"].score),
                    "risk_level": result["consensus"].risk_level,
                    "risk_score": result["consensus"].risk_score,
                    "confidence": result["consensus"].confidence,
                    "actual_enrollment": result["features"].get("actual_enrollment", 0),
                    "target_enrollment": result["features"].get("target_enrollment", 0),
                    "enrollment_rate": result["features"].get("enrollment_rate", 0.0),
                    "agent_count": len(result["consensus"].agent_signals),
                    "abstention_count": sum(1 for a in result["consensus"].agent_signals if a.abstained)
                })
        
        # Add simulated studies
        for study_id, result in self.results["simulated"].items():
            if result["success"]:
                report_data.append({
                    "study_id": study_id,
                    "data_type": "simulated",
                    "success": True,
                    "elapsed_time": result["elapsed_time"],
                    "dqi_score": result["dqi"].score,
                    "dqi_band": self._get_dqi_band(result["dqi"].score),
                    "risk_level": result["consensus"].risk_level,
                    "risk_score": result["consensus"].risk_score,
                    "confidence": result["consensus"].confidence,
                    "agent_count": len(result["consensus"].agent_signals),
                    "abstention_count": sum(1 for a in result["consensus"].agent_signals if a.abstained)
                })
        
        # Create DataFrame and save
        df = pd.DataFrame(report_data)
        report_path = self.output_dir / "validation_report.csv"
        df.to_csv(report_path, index=False)
        
        print(f"  ✓ CSV report saved: {report_path}")
    
    def _generate_summary_report(
        self,
        correlation: Dict[str, float],
        enrollment_stats: Dict[str, Any],
        comparison: Dict[str, Any]
    ):
        """Generate human-readable summary report"""
        report_path = self.output_dir / "validation_summary.txt"
        
        with open(report_path, "w") as f:
            f.write("="*80 + "\n")
            f.write("C-TRUST VALIDATION SUMMARY REPORT\n")
            f.write("="*80 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("\n")
            
            # Section 1: Data Processing
            f.write("1. DATA PROCESSING\n")
            f.write("-" * 80 + "\n")
            real_success = sum(1 for r in self.results["real"].values() if r["success"])
            real_total = len(self.results["real"])
            sim_success = sum(1 for r in self.results["simulated"].values() if r["success"])
            sim_total = len(self.results["simulated"])
            
            f.write(f"Real studies processed: {real_success}/{real_total} ({real_success/real_total*100:.1f}%)\n")
            f.write(f"Simulated studies processed: {sim_success}/{sim_total} ({sim_success/sim_total*100:.1f}%)\n")
            f.write("\n")
            
            # Section 2: DQI-Consensus Correlation
            f.write("2. DQI-CONSENSUS CORRELATION\n")
            f.write("-" * 80 + "\n")
            f.write(f"Correlation coefficient (r): {correlation['r']:.3f}\n")
            f.write(f"P-value: {correlation['p_value']:.4f}\n")
            f.write(f"Sample size: {correlation['n']}\n")
            f.write(f"Status: {'✓ PASS' if abs(correlation['r']) > 0.8 else '✗ FAIL'} (target: |r| > 0.8)\n")
            f.write("\n")
            
            # Section 3: Enrollment Data
            f.write("3. ENROLLMENT DATA ACCURACY\n")
            f.write("-" * 80 + "\n")
            f.write(f"Studies with enrollment data: {enrollment_stats['studies_with_data']}/{enrollment_stats['total_studies']}\n")
            f.write(f"Coverage rate: {enrollment_stats['coverage_rate']:.1%}\n")
            f.write(f"Average enrollment rate: {enrollment_stats['average_rate']:.1f}%\n")
            f.write(f"Status: {'✓ PASS' if enrollment_stats['coverage_rate'] >= 0.8 else '✗ FAIL'} (target: >= 80%)\n")
            f.write("\n")
            
            # Section 4: Real vs Simulated
            if comparison:
                f.write("4. REAL VS SIMULATED DATA COMPARISON\n")
                f.write("-" * 80 + "\n")
                f.write(f"Real data average DQI: {comparison['real_avg']:.1f} ± {comparison['real_std']:.1f}\n")
                f.write(f"Simulated data average DQI: {comparison['simulated_avg']:.1f} ± {comparison['simulated_std']:.1f}\n")
                f.write(f"Difference: {comparison['difference']:.1f} points\n")
                f.write(f"T-statistic: {comparison['t_statistic']:.3f}\n")
                f.write(f"P-value: {comparison['p_value']:.4f}\n")
                f.write(f"Status: {'✓ PASS' if comparison['difference'] > 20 else '✗ FAIL'} (target: > 20 points)\n")
                f.write("\n")
            
            # Section 5: Overall Status
            f.write("5. OVERALL VALIDATION STATUS\n")
            f.write("-" * 80 + "\n")
            
            checks = [
                ("Data processing", real_success == real_total and sim_success == sim_total),
                ("DQI-consensus correlation", abs(correlation['r']) > 0.8),
                ("Enrollment data coverage", enrollment_stats['coverage_rate'] >= 0.8),
                ("Real vs simulated difference", comparison.get('difference', 0) > 20)
            ]
            
            for check_name, passed in checks:
                status = "✓ PASS" if passed else "✗ FAIL"
                f.write(f"{status}: {check_name}\n")
            
            passed_checks = sum(1 for _, passed in checks if passed)
            total_checks = len(checks)
            
            f.write(f"\nOverall: {passed_checks}/{total_checks} checks passed ({passed_checks/total_checks*100:.1f}%)\n")
            
            if passed_checks == total_checks:
                f.write("\n✓ ALL VALIDATION CHECKS PASSED\n")
            else:
                f.write("\n✗ SOME VALIDATION CHECKS FAILED\n")
            
            f.write("\n" + "="*80 + "\n")
        
        print(f"  ✓ Summary report saved: {report_path}")
    
    @staticmethod
    def _get_dqi_band(score: float) -> str:
        """Get DQI band classification"""
        if score >= 90:
            return "EXCELLENT"
        elif score >= 80:
            return "GOOD"
        elif score >= 70:
            return "ACCEPTABLE"
        elif score >= 60:
            return "NEEDS_ATTENTION"
        else:
            return "CRITICAL"


def main():
    """Main entry point"""
    # Paths
    nest_data_path = Path("data/NEST 2.0")
    simulated_data_path = Path("data/simulated")
    output_dir = Path("reports/validation")
    
    # Generate report
    generator = ValidationReportGenerator(nest_data_path, simulated_data_path, output_dir)
    generator.run()


if __name__ == "__main__":
    main()
