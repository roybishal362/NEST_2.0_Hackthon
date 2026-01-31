"""
Test Simulated Data Discovery
=============================
Quick test to verify simulated studies are discovered and files are recognized.

Usage:
    python scripts/test_simulated_discovery.py
"""

import re
from pathlib import Path
import yaml


def load_file_patterns():
    """Load file patterns from system config"""
    config_path = Path("c_trust/config/system_config.yaml")
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config['data_sources']['file_patterns']


def detect_file_type(filename: str, patterns: dict) -> str:
    """Detect file type based on patterns"""
    filename_lower = filename.lower()
    
    for file_type, pattern_list in patterns.items():
        for pattern in pattern_list:
            # Convert glob pattern to regex
            regex_pattern = pattern.replace('*', '.*').replace('.xlsx', r'\.xlsx')
            if re.search(regex_pattern, filename_lower, re.IGNORECASE):
                return file_type
    
    return 'unknown'


def test_discovery():
    """Test study discovery for simulated data"""
    
    print(f"\n{'='*80}")
    print("TESTING SIMULATED DATA DISCOVERY")
    print(f"{'='*80}\n")
    
    # Data root
    data_root = Path("E:/novaryis - Copy - Copy/norvatas/Data for problem Statement 1/NEST 2.0 Data files_Anonymized/QC Anonymized Study Files")
    
    print(f"Data Root: {data_root}\n")
    
    if not data_root.exists():
        print(f"❌ Data root not found: {data_root}")
        return
    
    # Load file patterns
    patterns = load_file_patterns()
    
    # Find simulated study folders
    study_pattern = re.compile(r"^study[\s_]+\d+.*sim", re.IGNORECASE)
    
    sim_folders = []
    for item in data_root.iterdir():
        if item.is_dir() and study_pattern.match(item.name):
            sim_folders.append(item)
    
    print(f"Simulated study folders found: {len(sim_folders)}\n")
    
    if not sim_folders:
        print("❌ No simulated study folders found!")
        print("Expected: Study 101_SIM through Study 108_SIM")
        return
    
    # Analyze each study
    print("Simulated Studies:")
    print("-" * 80)
    
    for folder in sorted(sim_folders):
        study_id = folder.name
        
        # Find Excel files
        excel_files = list(folder.glob("*.xlsx"))
        
        print(f"\n{study_id}:")
        print(f"  Files found: {len(excel_files)}")
        
        # Detect file types
        file_types = {}
        unknown_files = []
        
        for file_path in excel_files:
            file_type = detect_file_type(file_path.name, patterns)
            file_types[file_type] = file_types.get(file_type, 0) + 1
            
            if file_type == 'unknown':
                unknown_files.append(file_path.name)
        
        print(f"  File types:")
        for ftype, count in sorted(file_types.items()):
            print(f"    - {ftype}: {count}")
        
        # Check for unknown types
        if unknown_files:
            print(f"  ⚠️  {len(unknown_files)} files with unknown type!")
            print(f"  Unknown files:")
            for filename in unknown_files:
                print(f"    - {filename}")
    
    print(f"\n{'='*80}")
    print("DISCOVERY TEST COMPLETE")
    print(f"{'='*80}\n")
    
    # Summary
    expected_studies = ['Study 101_SIM', 'Study 102_SIM', 'Study 103_SIM', 'Study 104_SIM',
                       'Study 105_SIM', 'Study 106_SIM', 'Study 107_SIM', 'Study 108_SIM']
    
    found_names = [f.name for f in sim_folders]
    
    print("Expected vs Found:")
    for expected in expected_studies:
        status = "✓" if expected in found_names else "❌"
        print(f"  {status} {expected}")
    
    print()


if __name__ == "__main__":
    test_discovery()
