#!/usr/bin/env python3
"""
C-TRUST Novartis NEST 2.0 Data Validation Script
=================================================

Task 13.1: Process all 23 Novartis studies from real dataset

This script:
1. Loads data from the NEST 2.0 anonymized study files
2. Processes all study folders (Study 1 through Study 25)
3. Ingests all file types: EDC_Metrics, SAE_Dashboard, EDRR, MedDRA, WHODD, Missing_Pages, Visit_Projection
4. Validates data ingestion for all 23 anonymized studies
5. Stores processed results in database

Requirements: 1.1, 1.2, 1.3, 1.4
"""

import sys
import json
import re
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import traceback

import pandas as pd
from openpyxl import load_workbook

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core import initialize_core_system, get_logger, db_manager
from src.core.database import ClinicalSnapshotTable

logger = get_logger(__name__)


class FlexibleFileTypeDetector:
    """
    Flexible file type detector that handles varied Novartis file naming conventions.
    
    Uses keyword-based matching instead of strict patterns.
    """
    
    # File type keywords (case-insensitive)
    FILE_TYPE_KEYWORDS = {
        "edc_metrics": ["edc", "metrics", "cpid_edc"],
        "sae_dm": ["sae", "dashboard", "safety", "esae"],
        "edrr": ["edrr", "edit_data", "compiled_edrr"],
        "meddra": ["meddra", "medra", "medDRA"],
        "whodd": ["whodd", "whodrug", "who_drug", "whodr"],
        "missing_pages": ["missing_page", "missing page", "global_missing"],
        "visit_projection": ["visit", "projection", "tracker"],
        "inactivated": ["inactivated", "inactive"],
        "missing_lab": ["missing_lab", "lab_name", "missing_range"],
    }
    
    def detect_file_type(self, filename: str) -> Optional[str]:
        """
        Detect file type from filename using keyword matching.
        
        Args:
            filename: Name of the file
        
        Returns:
            File type string or None if no match
        """
        filename_lower = filename.lower()
        
        # Check each file type's keywords
        for file_type, keywords in self.FILE_TYPE_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in filename_lower:
                    return file_type
        
        return None


class DirectExcelReader:
    """
    Direct Excel file reader that handles various file formats.
    """
    
    def read_file(self, file_path: Path, file_type: str = None) -> Optional[pd.DataFrame]:
        """
        Read Excel file with multiple fallback strategies.
        
        Args:
            file_path: Path to Excel file
            file_type: Type of file (edc_metrics, sae_dm, etc.) for special handling
        
        Returns:
            DataFrame if successful, None if failed
        """
        if not file_path.exists():
            return None
        
        # Special handling for EDC_Metrics files which have multi-row headers
        # Row 0: High-level categories
        # Row 1: Sub-categories  
        # Row 2: Detailed column names (the ones we want)
        # Row 3: Responsible parties
        # Row 4+: Data
        if file_type == "edc_metrics":
            try:
                # Read with header at row 2 (0-indexed) to get detailed column names
                df = pd.read_excel(file_path, engine="openpyxl", header=2)
                if df is not None and not df.empty:
                    # Skip the "Responsible LF for action" row (row 3 in original, now row 0)
                    # Filter to only rows with actual data
                    if len(df) > 1:
                        # Check if first row is metadata
                        first_val = str(df.iloc[0, 0]).lower() if pd.notna(df.iloc[0, 0]) else ""
                        if "responsible" in first_val or "action" in first_val:
                            df = df.iloc[1:].reset_index(drop=True)
                    return df
            except Exception as e:
                pass  # Fall through to default strategies
        
        # Try different reading strategies
        strategies = [
            ("openpyxl", {"engine": "openpyxl"}),
            ("default", {}),
            ("xlrd", {"engine": "xlrd"}),
        ]
        
        for strategy_name, kwargs in strategies:
            try:
                df = pd.read_excel(file_path, **kwargs)
                if df is not None and not df.empty:
                    return df
            except Exception as e:
                continue
        
        return None


class NovartisDataValidator:
    """
    Validates and processes all 23 Novartis NEST 2.0 studies.
    
    Uses flexible file detection to handle varied naming conventions.
    """
    
    # Expected data path (relative to workspace root)
    DATA_ROOT = Path(__file__).parent.parent.parent / "norvatas/Data for problem Statement 1/NEST 2.0 Data files_Anonymized/QC Anonymized Study Files"
    
    def __init__(self, data_root: Optional[Path] = None):
        """
        Initialize the validator.
        
        Args:
            data_root: Override data root path (uses default if not provided)
        """
        self.data_root = data_root or self.DATA_ROOT
        self.file_detector = FlexibleFileTypeDetector()
        self.excel_reader = DirectExcelReader()
        self.results = {
            "start_time": None,
            "end_time": None,
            "studies_discovered": 0,
            "studies_processed": 0,
            "studies_failed": 0,
            "files_processed": 0,
            "files_failed": 0,
            "total_rows_ingested": 0,
            "study_details": {},
            "errors": [],
            "warnings": [],
        }
        
        print(f"NovartisDataValidator initialized with data root: {self.data_root}")
    
    def initialize(self) -> bool:
        """
        Initialize the validation system.
        
        Returns:
            True if initialization successful
        """
        print("Initializing Novartis data validation system...")
        
        try:
            # Initialize core system
            if not initialize_core_system():
                print("Failed to initialize core system")
                return False
            
            # Verify data path exists
            if not self.data_root.exists():
                print(f"Data root path does not exist: {self.data_root}")
                return False
            
            print("Validation system initialized successfully")
            return True
            
        except Exception as e:
            print(f"Initialization failed: {e}")
            traceback.print_exc()
            return False
    
    def discover_studies(self) -> List[Path]:
        """
        Discover all study folders in the NEST 2.0 dataset.
        
        Returns:
            List of study folder paths
        """
        print("Discovering studies in NEST 2.0 dataset...")
        
        study_folders = []
        study_pattern = re.compile(r"^study[\s_]+\d+", re.IGNORECASE)
        
        for item in self.data_root.iterdir():
            if item.is_dir() and study_pattern.match(item.name):
                study_folders.append(item)
        
        # Sort by study number
        def extract_number(folder: Path) -> int:
            match = re.search(r"\d+", folder.name)
            return int(match.group()) if match else 0
        
        study_folders.sort(key=extract_number)
        
        self.results["studies_discovered"] = len(study_folders)
        print(f"Discovered {len(study_folders)} studies")
        
        return study_folders
    
    def process_all_studies(self, study_folders: List[Path]) -> Dict[str, Dict[str, pd.DataFrame]]:
        """
        Process all discovered studies.
        
        Args:
            study_folders: List of study folder paths
        
        Returns:
            Dictionary of study_id -> file_type -> DataFrame
        """
        self.results["start_time"] = datetime.now()
        print(f"\nStarting processing of {len(study_folders)} studies...")
        
        all_study_data = {}
        
        for i, study_folder in enumerate(study_folders, 1):
            study_id = self._normalize_study_id(study_folder.name)
            print(f"\nProcessing study {i}/{len(study_folders)}: {study_id}")
            
            try:
                study_data, study_stats = self._process_single_study(study_folder, study_id)
                
                if study_data:
                    all_study_data[study_id] = study_data
                    self.results["studies_processed"] += 1
                    self.results["study_details"][study_id] = study_stats
                    
                    print(
                        f"  [OK] {study_id}: {study_stats['files_processed']} files, "
                        f"{study_stats['total_rows']:,} rows"
                    )
                else:
                    self.results["studies_failed"] += 1
                    print(f"  [FAIL] {study_id}: No data processed")
                    
            except Exception as e:
                self.results["studies_failed"] += 1
                self.results["errors"].append({
                    "study_id": study_id,
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                })
                print(f"  [ERROR] {study_id}: {e}")
        
        self.results["end_time"] = datetime.now()
        self.results["processing_time_seconds"] = (
            self.results["end_time"] - self.results["start_time"]
        ).total_seconds()
        
        return all_study_data
    
    def _normalize_study_id(self, folder_name: str) -> str:
        """Normalize study ID to consistent format."""
        match = re.search(r"study[\s_]+(\d+)", folder_name, re.IGNORECASE)
        if match:
            study_number = int(match.group(1))
            return f"STUDY_{study_number:02d}"
        return folder_name
    
    def _process_single_study(
        self,
        study_folder: Path,
        study_id: str
    ) -> Tuple[Optional[Dict[str, pd.DataFrame]], Dict[str, Any]]:
        """
        Process a single study folder.
        
        Args:
            study_folder: Path to study folder
            study_id: Normalized study ID
        
        Returns:
            Tuple of (study_data, statistics)
        """
        stats = {
            "study_id": study_id,
            "files_processed": 0,
            "files_failed": 0,
            "total_rows": 0,
            "file_details": {},
        }
        
        study_data = {}
        
        # Find all Excel files
        excel_files = list(study_folder.glob("*.xlsx")) + list(study_folder.glob("*.xls"))
        
        for excel_file in excel_files:
            try:
                # Detect file type
                file_type = self.file_detector.detect_file_type(excel_file.name)
                
                if file_type is None:
                    print(f"    [SKIP] Unknown file type: {excel_file.name}")
                    continue
                
                # Read file (pass file_type for special handling)
                df = self.excel_reader.read_file(excel_file, file_type=file_type)
                
                if df is not None and not df.empty:
                    row_count = len(df)
                    col_count = len(df.columns)
                    
                    study_data[file_type] = df
                    stats["files_processed"] += 1
                    stats["total_rows"] += row_count
                    stats["file_details"][file_type] = {
                        "filename": excel_file.name,
                        "rows": row_count,
                        "columns": col_count,
                    }
                    
                    self.results["files_processed"] += 1
                    self.results["total_rows_ingested"] += row_count
                    
                    print(f"    [OK] {file_type}: {row_count} rows, {col_count} cols")
                else:
                    stats["files_failed"] += 1
                    self.results["files_failed"] += 1
                    print(f"    [FAIL] Could not read: {excel_file.name}")
                    
            except Exception as e:
                stats["files_failed"] += 1
                self.results["files_failed"] += 1
                print(f"    [ERROR] {excel_file.name}: {e}")
        
        return study_data if study_data else None, stats
    
    def store_results_in_database(
        self,
        all_study_data: Dict[str, Dict[str, pd.DataFrame]]
    ) -> bool:
        """
        Store processed results in the database.
        
        Args:
            all_study_data: Dictionary of study_id -> file_type -> DataFrame
        
        Returns:
            True if storage successful
        """
        print("\nStoring processed results in database...")
        
        try:
            session = db_manager.get_session()
            
            # Create a snapshot for this processing run
            snapshot_id = f"novartis_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            for study_id, study_data in all_study_data.items():
                # Create snapshot record
                snapshot = ClinicalSnapshotTable(
                    snapshot_id=f"{snapshot_id}_{study_id}",
                    study_id=study_id,
                    timestamp=datetime.now(),
                    processing_status="COMPLETED",
                    data_sources=json.dumps({
                        ft: True for ft in study_data.keys()
                    }),
                    snapshot_metadata=json.dumps(
                        self.results["study_details"].get(study_id, {})
                    ),
                )
                session.add(snapshot)
            
            session.commit()
            print(f"Stored {len(all_study_data)} study snapshots in database")
            return True
            
        except Exception as e:
            print(f"Failed to store results in database: {e}")
            traceback.print_exc()
            session.rollback()
            return False
        finally:
            session.close()
    
    def generate_summary_report(self) -> str:
        """
        Generate a summary report of the validation.
        
        Returns:
            Formatted summary report string
        """
        report_lines = [
            "=" * 70,
            "NOVARTIS NEST 2.0 DATA VALIDATION REPORT",
            "=" * 70,
            "",
            f"Validation Time: {self.results.get('start_time', 'N/A')}",
            f"Processing Duration: {self.results.get('processing_time_seconds', 0):.1f} seconds",
            "",
            "SUMMARY",
            "-" * 40,
            f"Studies Discovered: {self.results['studies_discovered']}",
            f"Studies Processed: {self.results['studies_processed']}",
            f"Studies Failed: {self.results['studies_failed']}",
            f"Files Processed: {self.results['files_processed']}",
            f"Files Failed: {self.results['files_failed']}",
            f"Total Rows Ingested: {self.results['total_rows_ingested']:,}",
            "",
        ]
        
        # Study details
        if self.results["study_details"]:
            report_lines.extend([
                "STUDY DETAILS",
                "-" * 40,
            ])
            
            for study_id, details in sorted(self.results["study_details"].items()):
                report_lines.append(
                    f"  {study_id}: {details['files_processed']} files, "
                    f"{details['total_rows']:,} rows"
                )
                
                # Show file types processed
                if "file_details" in details:
                    for file_type, file_info in details["file_details"].items():
                        report_lines.append(
                            f"    - {file_type}: {file_info['rows']} rows"
                        )
            
            report_lines.append("")
        
        # Errors
        if self.results["errors"]:
            report_lines.extend([
                "ERRORS",
                "-" * 40,
            ])
            for error in self.results["errors"]:
                report_lines.append(f"  {error['study_id']}: {error['error']}")
            report_lines.append("")
        
        report_lines.extend([
            "=" * 70,
            "VALIDATION COMPLETE",
            "=" * 70,
        ])
        
        return "\n".join(report_lines)
    
    def run_full_validation(self) -> Tuple[bool, Dict[str, Dict[str, pd.DataFrame]]]:
        """
        Run the complete validation pipeline.
        
        Returns:
            Tuple of (success, all_study_data)
        """
        print("=" * 70)
        print("STARTING NOVARTIS NEST 2.0 DATA VALIDATION")
        print("=" * 70)
        
        # Step 1: Initialize
        if not self.initialize():
            print("Initialization failed")
            return False, {}
        
        # Step 2: Discover studies
        study_folders = self.discover_studies()
        
        if not study_folders:
            print("No studies discovered")
            return False, {}
        
        # Step 3: Process all studies
        all_study_data = self.process_all_studies(study_folders)
        
        # Step 4: Store results in database
        self.store_results_in_database(all_study_data)
        
        # Step 5: Generate and print report
        report = self.generate_summary_report()
        print("\n" + report)
        
        # Save report to file
        report_path = Path("c_trust/exports/novartis_validation_report.txt")
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report, encoding='utf-8')
        print(f"\nReport saved to: {report_path}")
        
        # Save detailed results as JSON
        json_path = Path("c_trust/exports/novartis_validation_results.json")
        
        # Convert results to JSON-serializable format
        json_results = {
            "start_time": str(self.results.get("start_time", "")),
            "end_time": str(self.results.get("end_time", "")),
            "processing_time_seconds": self.results.get("processing_time_seconds", 0),
            "studies_discovered": self.results["studies_discovered"],
            "studies_processed": self.results["studies_processed"],
            "studies_failed": self.results["studies_failed"],
            "files_processed": self.results["files_processed"],
            "files_failed": self.results["files_failed"],
            "total_rows_ingested": self.results["total_rows_ingested"],
            "study_details": self.results["study_details"],
            "errors": self.results["errors"],
            "warnings": self.results["warnings"],
        }
        
        json_path.write_text(json.dumps(json_results, indent=2), encoding='utf-8')
        print(f"Detailed results saved to: {json_path}")
        
        success = self.results["studies_processed"] > 0
        return success, all_study_data


def main():
    """Main entry point for Novartis data validation."""
    print("\n" + "=" * 70)
    print("C-TRUST NOVARTIS NEST 2.0 DATA VALIDATION")
    print("Task 13.1: Process all 23 Novartis studies from real dataset")
    print("=" * 70 + "\n")
    
    validator = NovartisDataValidator()
    success, all_study_data = validator.run_full_validation()
    
    if success:
        print(f"\n[SUCCESS] Validation completed successfully!")
        print(f"   Processed {validator.results['studies_processed']} studies")
        print(f"   Ingested {validator.results['total_rows_ingested']:,} total rows")
        return 0
    else:
        print("\n[FAILED] Validation failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
