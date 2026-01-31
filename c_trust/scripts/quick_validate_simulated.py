"""
Quick Simulated Data Validation
================================
Simple validation that simulated studies were generated correctly.
"""

import sys
from pathlib import Path
import pandas as pd

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def validate_simulated_studies():
    """Quick validation of simulated studies"""
    
    print(f"\n{'='*80}")
    print("SIMULATED DATA VALIDATION - QUICK CHECK")
    print(f"{'='*80}\n")
    
    simulated_dir = Path("data/simulated")
    
    if not simulated_dir.exists():
        print("❌ Simulated data directory not found!")
        return False
    
    # Expected studies
    expected_studies = [f"SIM-{i:03d}" for i in range(1, 7)]
    
    # Expected files per study
    expected_files = [
        "EDC_Metrics.xlsx",
        "SAE_Dashboard.xlsx",
        "Visit_Projection_Tracker.xlsx",
        "Coding_Reports.xlsx",
        "EDRR.xlsx",
        "Missing_Lab_Ranges.xlsx"
    ]
    
    all_passed = True
    
    for study_id in expected_studies:
        study_dir = simulated_dir / study_id
        
        if not study_dir.exists():
            print(f"❌ {study_id}: Directory not found")
            all_passed = False
            continue
        
        print(f"✓ {study_id}: Directory exists")
        
        # Check files
        missing_files = []
        for file_name in expected_files:
            file_path = study_dir / f"{study_id}_{file_name}"
            if not file_path.exists():
                missing_files.append(file_name)
        
        if missing_files:
            print(f"  ❌ Missing files: {', '.join(missing_files)}")
            all_passed = False
        else:
            print(f"  ✓ All 6 files present")
        
        # Try to read one file to verify it's valid Excel
        try:
            test_file = study_dir / f"{study_id}_EDC_Metrics.xlsx"
            df = pd.read_excel(test_file)
            print(f"  ✓ Files are readable ({len(df)} rows in EDC_Metrics)")
        except Exception as e:
            print(f"  ❌ Error reading files: {e}")
            all_passed = False
    
    print(f"\n{'='*80}")
    if all_passed:
        print("✅ ALL VALIDATION CHECKS PASSED")
        print(f"{'='*80}\n")
        return True
    else:
        print("❌ SOME VALIDATION CHECKS FAILED")
        print(f"{'='*80}\n")
        return False


if __name__ == "__main__":
    success = validate_simulated_studies()
    sys.exit(0 if success else 1)
