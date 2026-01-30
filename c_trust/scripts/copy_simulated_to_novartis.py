"""
Copy Simulated Data to Novartis Folder
======================================
Copies generated simulated data files to the Novartis data folder
with proper naming convention (Study 101_SIM, Study 102_SIM, etc.)

Usage:
    python scripts/copy_simulated_to_novartis.py
"""

import shutil
from pathlib import Path


def copy_simulated_data():
    """Copy simulated data to Novartis folder"""
    
    # Source directory
    source_dir = Path("c_trust/data/simulated")
    
    # Target directory (from .env)
    target_base = Path("E:/novaryis - Copy - Copy/norvatas/Data for problem Statement 1/NEST 2.0 Data files_Anonymized/QC Anonymized Study Files")
    
    if not target_base.exists():
        print(f"❌ Target directory not found: {target_base}")
        print("Please update the path in this script to match your system.")
        return
    
    # Mapping: SIM-001 -> Study 101_SIM, etc.
    study_mapping = {
        'SIM-001': 'Study 101_SIM',
        'SIM-002': 'Study 102_SIM',
        'SIM-003': 'Study 103_SIM',
        'SIM-004': 'Study 104_SIM',
        'SIM-005': 'Study 105_SIM',
        'SIM-006': 'Study 106_SIM',
        'SIM-007': 'Study 107_SIM',
        'SIM-008': 'Study 108_SIM',
    }
    
    print(f"\n{'='*80}")
    print("COPYING SIMULATED DATA TO NOVARTIS FOLDER")
    print(f"{'='*80}\n")
    print(f"Source: {source_dir}")
    print(f"Target: {target_base}\n")
    
    copied_count = 0
    
    for sim_id, study_name in study_mapping.items():
        source_study_dir = source_dir / sim_id
        target_study_dir = target_base / study_name
        
        if not source_study_dir.exists():
            print(f"⚠️  Source not found: {sim_id}")
            continue
        
        # Create target directory
        target_study_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy all files
        files_copied = 0
        for source_file in source_study_dir.glob("*.xlsx"):
            # Rename file: SIM-001_xxx.xlsx -> Study 101_SIM_xxx.xlsx
            new_filename = source_file.name.replace(sim_id, study_name.replace(' ', '_'))
            target_file = target_study_dir / new_filename
            
            shutil.copy2(source_file, target_file)
            files_copied += 1
        
        print(f"✓ {sim_id} -> {study_name} ({files_copied} files)")
        copied_count += 1
    
    print(f"\n{'='*80}")
    print(f"Copied {copied_count} simulated studies to Novartis folder")
    print(f"{'='*80}\n")
    
    print("Next steps:")
    print("1. Run the backend normally: python c_trust/run.py")
    print("2. Check that simulated studies are discovered")
    print("3. Verify DQI scores match expected targets:")
    print("   - SIM-001 (Study 101_SIM): target DQI 45")
    print("   - SIM-002 (Study 102_SIM): target DQI 50")
    print("   - SIM-003 (Study 103_SIM): target DQI 55")
    print("   - SIM-004 (Study 104_SIM): target DQI 52")
    print("   - SIM-005 (Study 105_SIM): target DQI 60")
    print("   - SIM-006 (Study 106_SIM): target DQI 64")
    print("   - SIM-007 (Study 107_SIM): target DQI 25 (catastrophic)")
    print("   - SIM-008 (Study 108_SIM): target DQI 20 (critical)")
    print()


if __name__ == "__main__":
    copy_simulated_data()
