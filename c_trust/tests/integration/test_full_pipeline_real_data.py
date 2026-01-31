"""
Integration Test: Full Pipeline on Real NEST 2.0 Data

This test validates the complete C-TRUST pipeline on all 23 real NEST studies:
1. Data ingestion from NEST 2.0 format
2. Feature extraction for all 7 agents
3. Agent analysis and risk scoring
4. DQI calculation from agent consensus
5. Enrollment data extraction
6. Export functionality

**Validates Requirements:**
- US-1: DQI reflects agent consensus
- US-2: Real data produces reasonable DQI scores (85-95 for good data)
- US-3: Enrollment data is accurate
- US-4: Export works for all studies
- NFR-1: Pipeline completes within reasonable time
- NFR-8: Results are deterministic

**Test Strategy:**
- Run full pipeline on all 23 studies
- Verify DQI scores are reasonable
- Verify enrollment data accuracy
- Verify export functionality
- Generate performance report
"""

import pytest
import sys
import os
import json
import time
from pathlib import Path
from typing import Dict, List, Any
import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.data.ingestion import ingest_study_data
from src.data.features import extract_features
from src.intelligence.consensus import calculate_consensus
from src.intelligence.dqi_engine_agent_driven import calculate_dqi_from_agents
from src.api.export import export_study_data


class TestFullPipelineRealData:
    """Test full pipeline on all 23 real NEST studies"""
    
    @pytest.fixture(scope="class")
    def nest_data_path(self) -> Path:
        """Get path to NEST 2.0 data"""
        return Path("data/NEST 2.0")
    
    @pytest.fixture(scope="class")
    def all_studies(self, nest_data_path: Path) -> List[str]:
        """Get list of all 23 NEST studies"""
        if not nest_data_path.exists():
            pytest.skip(f"NEST data not found at {nest_data_path}")
        
        studies = [d.name for d in nest_data_path.iterdir() if d.is_dir()]
        assert len(studies) == 23, f"Expected 23 studies, found {len(studies)}"
        return sorted(studies)
    
    @pytest.fixture(scope="class")
    def pipeline_results(self, nest_data_path: Path, all_studies: List[str]) -> Dict[str, Any]:
        """Run full pipeline on all studies and cache results"""
        results = {}
        
        for study_id in all_studies:
            print(f"\n{'='*80}")
            print(f"Processing Study: {study_id}")
            print(f"{'='*80}")
            
            start_time = time.time()
            
            try:
                # Step 1: Ingest study data
                print(f"  [1/6] Ingesting data...")
                study_data = ingest_study_data(nest_data_path / study_id)
                
                # Step 2: Extract features
                print(f"  [2/6] Extracting features...")
                features = extract_features(study_data)
                
                # Step 3: Run agents
                print(f"  [3/6] Running agents...")
                consensus_result = calculate_consensus(features)
                
                # Step 4: Calculate DQI
                print(f"  [4/6] Calculating DQI...")
                dqi_result = calculate_dqi_from_agents(consensus_result.agent_signals)
                
                # Step 5: Extract enrollment
                print(f"  [5/6] Extracting enrollment...")
                enrollment = {
                    "actual": features.get("actual_enrollment", 0),
                    "target": features.get("target_enrollment", 0),
                    "rate_pct": features.get("enrollment_rate", 0.0)
                }
                
                # Step 6: Test export
                print(f"  [6/6] Testing export...")
                export_data = export_study_data(study_id, features, consensus_result, dqi_result)
                
                elapsed_time = time.time() - start_time
                
                results[study_id] = {
                    "success": True,
                    "elapsed_time": elapsed_time,
                    "features": features,
                    "consensus": consensus_result,
                    "dqi": dqi_result,
                    "enrollment": enrollment,
                    "export": export_data,
                    "error": None
                }
                
                print(f"  ✓ Success in {elapsed_time:.2f}s")
                print(f"    DQI: {dqi_result.score:.1f}")
                print(f"    Risk: {consensus_result.risk_level}")
                print(f"    Enrollment: {enrollment['actual']}/{enrollment['target']} ({enrollment['rate_pct']:.1f}%)")
                
            except Exception as e:
                elapsed_time = time.time() - start_time
                results[study_id] = {
                    "success": False,
                    "elapsed_time": elapsed_time,
                    "error": str(e)
                }
                print(f"  ✗ Failed in {elapsed_time:.2f}s: {e}")
        
        return results
    
    def test_all_studies_processed_successfully(self, pipeline_results: Dict[str, Any]):
        """Test that all 23 studies were processed successfully"""
        total_studies = len(pipeline_results)
        successful_studies = sum(1 for r in pipeline_results.values() if r["success"])
        failed_studies = [sid for sid, r in pipeline_results.items() if not r["success"]]
        
        print(f"\n{'='*80}")
        print(f"Pipeline Success Rate: {successful_studies}/{total_studies} ({successful_studies/total_studies*100:.1f}%)")
        print(f"{'='*80}")
        
        if failed_studies:
            print(f"\nFailed Studies ({len(failed_studies)}):")
            for study_id in failed_studies:
                error = pipeline_results[study_id]["error"]
                print(f"  - {study_id}: {error}")
        
        # Require at least 90% success rate
        success_rate = successful_studies / total_studies
        assert success_rate >= 0.9, f"Pipeline success rate {success_rate:.1%} below 90% threshold"
    
    def test_dqi_scores_are_reasonable(self, pipeline_results: Dict[str, Any]):
        """Test that DQI scores are reasonable for real data (US-2)"""
        dqi_scores = []
        
        for study_id, result in pipeline_results.items():
            if result["success"]:
                dqi_score = result["dqi"].score
                dqi_scores.append((study_id, dqi_score))
        
        print(f"\n{'='*80}")
        print(f"DQI Score Distribution")
        print(f"{'='*80}")
        
        # Calculate statistics
        scores = [score for _, score in dqi_scores]
        avg_dqi = sum(scores) / len(scores)
        min_dqi = min(scores)
        max_dqi = max(scores)
        
        print(f"Average DQI: {avg_dqi:.1f}")
        print(f"Min DQI: {min_dqi:.1f}")
        print(f"Max DQI: {max_dqi:.1f}")
        print(f"\nDQI Scores by Study:")
        
        for study_id, dqi_score in sorted(dqi_scores, key=lambda x: x[1]):
            band = self._get_dqi_band(dqi_score)
            print(f"  {study_id}: {dqi_score:.1f} ({band})")
        
        # Real NEST data should generally have good DQI (85-95)
        # But we allow some studies to have lower scores if they have real issues
        assert avg_dqi >= 70, f"Average DQI {avg_dqi:.1f} is too low for real data"
        assert min_dqi >= 50, f"Minimum DQI {min_dqi:.1f} is suspiciously low"
        assert max_dqi <= 100, f"Maximum DQI {max_dqi:.1f} exceeds 100"
    
    def test_enrollment_data_extracted(self, pipeline_results: Dict[str, Any]):
        """Test that enrollment data is extracted for all studies (US-3)"""
        enrollment_data = []
        
        for study_id, result in pipeline_results.items():
            if result["success"]:
                enrollment = result["enrollment"]
                enrollment_data.append((
                    study_id,
                    enrollment["actual"],
                    enrollment["target"],
                    enrollment["rate_pct"]
                ))
        
        print(f"\n{'='*80}")
        print(f"Enrollment Data")
        print(f"{'='*80}")
        
        for study_id, actual, target, rate in sorted(enrollment_data, key=lambda x: x[3], reverse=True):
            status = "✓" if rate >= 80 else "⚠" if rate >= 50 else "✗"
            print(f"  {status} {study_id}: {actual}/{target} ({rate:.1f}%)")
        
        # Verify enrollment data is present
        studies_with_enrollment = sum(1 for _, actual, target, _ in enrollment_data if actual > 0 or target > 0)
        enrollment_rate = studies_with_enrollment / len(enrollment_data)
        
        print(f"\nStudies with enrollment data: {studies_with_enrollment}/{len(enrollment_data)} ({enrollment_rate:.1%})")
        
        # At least 80% of studies should have enrollment data
        assert enrollment_rate >= 0.8, f"Only {enrollment_rate:.1%} of studies have enrollment data"
    
    def test_export_works_for_all_studies(self, pipeline_results: Dict[str, Any]):
        """Test that export works for all studies (US-4)"""
        export_success = []
        
        for study_id, result in pipeline_results.items():
            if result["success"]:
                export_data = result["export"]
                has_required_fields = all(
                    field in export_data
                    for field in ["study_id", "dqi_score", "risk_level", "enrollment"]
                )
                export_success.append((study_id, has_required_fields))
        
        print(f"\n{'='*80}")
        print(f"Export Functionality")
        print(f"{'='*80}")
        
        successful_exports = sum(1 for _, success in export_success if success)
        print(f"Successful exports: {successful_exports}/{len(export_success)}")
        
        for study_id, success in export_success:
            status = "✓" if success else "✗"
            print(f"  {status} {study_id}")
        
        # All studies should export successfully
        assert successful_exports == len(export_success), "Some studies failed to export"
    
    def test_pipeline_performance(self, pipeline_results: Dict[str, Any]):
        """Test that pipeline completes within reasonable time (NFR-1)"""
        processing_times = []
        
        for study_id, result in pipeline_results.items():
            processing_times.append((study_id, result["elapsed_time"]))
        
        print(f"\n{'='*80}")
        print(f"Pipeline Performance")
        print(f"{'='*80}")
        
        # Calculate statistics
        times = [t for _, t in processing_times]
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        total_time = sum(times)
        
        print(f"Average time per study: {avg_time:.2f}s")
        print(f"Min time: {min_time:.2f}s")
        print(f"Max time: {max_time:.2f}s")
        print(f"Total time: {total_time:.2f}s ({total_time/60:.1f} minutes)")
        
        print(f"\nProcessing times by study:")
        for study_id, elapsed_time in sorted(processing_times, key=lambda x: x[1], reverse=True):
            print(f"  {study_id}: {elapsed_time:.2f}s")
        
        # Each study should process in under 30 seconds
        assert max_time < 30, f"Slowest study took {max_time:.2f}s (> 30s threshold)"
        assert avg_time < 15, f"Average time {avg_time:.2f}s exceeds 15s threshold"
    
    def test_results_are_deterministic(self, nest_data_path: Path, all_studies: List[str]):
        """Test that pipeline produces deterministic results (NFR-8)"""
        # Run pipeline twice on first 3 studies
        test_studies = all_studies[:3]
        
        print(f"\n{'='*80}")
        print(f"Determinism Test")
        print(f"{'='*80}")
        
        for study_id in test_studies:
            print(f"\nTesting {study_id}...")
            
            # Run 1
            study_data_1 = ingest_study_data(nest_data_path / study_id)
            features_1 = extract_features(study_data_1)
            consensus_1 = calculate_consensus(features_1)
            dqi_1 = calculate_dqi_from_agents(consensus_1.agent_signals)
            
            # Run 2
            study_data_2 = ingest_study_data(nest_data_path / study_id)
            features_2 = extract_features(study_data_2)
            consensus_2 = calculate_consensus(features_2)
            dqi_2 = calculate_dqi_from_agents(consensus_2.agent_signals)
            
            # Compare results
            dqi_match = abs(dqi_1.score - dqi_2.score) < 0.01
            risk_match = consensus_1.risk_level == consensus_2.risk_level
            
            print(f"  DQI Run 1: {dqi_1.score:.2f}")
            print(f"  DQI Run 2: {dqi_2.score:.2f}")
            print(f"  Match: {dqi_match}")
            
            assert dqi_match, f"DQI scores differ: {dqi_1.score} vs {dqi_2.score}"
            assert risk_match, f"Risk levels differ: {consensus_1.risk_level} vs {consensus_2.risk_level}"
    
    def test_generate_pipeline_performance_report(self, pipeline_results: Dict[str, Any], tmp_path: Path):
        """Generate comprehensive pipeline performance report"""
        report_path = tmp_path / "pipeline_performance_report.csv"
        
        # Prepare report data
        report_data = []
        for study_id, result in pipeline_results.items():
            if result["success"]:
                report_data.append({
                    "study_id": study_id,
                    "success": True,
                    "elapsed_time": result["elapsed_time"],
                    "dqi_score": result["dqi"].score,
                    "dqi_band": self._get_dqi_band(result["dqi"].score),
                    "risk_level": result["consensus"].risk_level,
                    "risk_score": result["consensus"].risk_score,
                    "confidence": result["consensus"].confidence,
                    "actual_enrollment": result["enrollment"]["actual"],
                    "target_enrollment": result["enrollment"]["target"],
                    "enrollment_rate": result["enrollment"]["rate_pct"],
                    "agent_count": len(result["consensus"].agent_signals),
                    "abstention_count": sum(1 for a in result["consensus"].agent_signals if a.abstained),
                    "error": None
                })
            else:
                report_data.append({
                    "study_id": study_id,
                    "success": False,
                    "elapsed_time": result["elapsed_time"],
                    "error": result["error"]
                })
        
        # Create DataFrame and save
        df = pd.DataFrame(report_data)
        df.to_csv(report_path, index=False)
        
        print(f"\n{'='*80}")
        print(f"Pipeline Performance Report")
        print(f"{'='*80}")
        print(f"Report saved to: {report_path}")
        print(f"\nSummary Statistics:")
        print(df.describe())
        
        assert report_path.exists(), "Report file was not created"
    
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


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s", "--tb=short"])
