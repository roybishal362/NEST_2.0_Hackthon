"""
Phase 5 Integration Test Runner

This script runs all Phase 5 integration tests in sequence:
1. Full pipeline on real data (23 studies)
2. Full pipeline on simulated data (6 studies)
3. Generate comprehensive validation report

Usage:
    python scripts/run_phase5_integration_tests.py
"""

import sys
import subprocess
from pathlib import Path
from datetime import datetime


def run_command(cmd: list, description: str) -> bool:
    """Run a command and return success status"""
    print(f"\n{'='*80}")
    print(f"{description}")
    print(f"{'='*80}")
    print(f"Command: {' '.join(cmd)}")
    print()
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=False, text=True)
        print(f"\n✓ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n✗ {description} failed with exit code {e.returncode}")
        return False


def main():
    """Main entry point"""
    print("="*80)
    print("PHASE 5: INTEGRATION TESTING AND VALIDATION")
    print("="*80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Change to c_trust directory
    c_trust_dir = Path(__file__).parent.parent
    
    results = []
    
    # Test 1: Full pipeline on real data
    results.append(run_command(
        ["python", "-m", "pytest", "tests/integration/test_full_pipeline_real_data.py", "-v", "-s"],
        "Test 1: Full Pipeline on Real Data (23 studies)"
    ))
    
    # Test 2: Full pipeline on simulated data
    results.append(run_command(
        ["python", "-m", "pytest", "tests/integration/test_full_pipeline_simulated_data.py", "-v", "-s"],
        "Test 2: Full Pipeline on Simulated Data (6 studies)"
    ))
    
    # Test 3: Generate validation report
    results.append(run_command(
        ["python", "scripts/generate_validation_report.py"],
        "Test 3: Generate Comprehensive Validation Report"
    ))
    
    # Summary
    print("\n" + "="*80)
    print("PHASE 5 INTEGRATION TESTING SUMMARY")
    print("="*80)
    
    test_names = [
        "Full Pipeline on Real Data",
        "Full Pipeline on Simulated Data",
        "Validation Report Generation"
    ]
    
    for i, (name, success) in enumerate(zip(test_names, results), 1):
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: Test {i} - {name}")
    
    passed = sum(results)
    total = len(results)
    
    print(f"\nOverall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # Exit with appropriate code
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
