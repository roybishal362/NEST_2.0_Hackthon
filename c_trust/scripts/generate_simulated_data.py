"""
Simulated Data Generator for C-TRUST
====================================
Generates simulated clinical trial data with known quality issues
to validate that the DQI system correctly identifies low-quality data.

Phase 3, Task 11: Create Simulated Data Generator

Usage:
    python scripts/generate_simulated_data.py
    python scripts/generate_simulated_data.py --study SIM-001
    python scripts/generate_simulated_data.py --all
"""

import argparse
import yaml
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from typing import Dict, Any, List
import random


class SimulatedDataGenerator:
    """Generates simulated clinical trial data with known quality issues"""
    
    def __init__(self, profiles_path: str = "c_trust/config/simulated_profiles.yaml"):
        """
        Initialize the generator with study profiles.
        
        Args:
            profiles_path: Path to YAML file containing study profiles
        """
        self.profiles_path = Path(profiles_path)
        self.profiles = self._load_profiles()
        self.output_dir = Path("c_trust/data/simulated")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_profiles(self) -> Dict[str, Any]:
        """Load study profiles from YAML file"""
        with open(self.profiles_path, 'r') as f:
            data = yaml.safe_load(f)
        
        # Remove metadata
        profiles = {k: v for k, v in data.items() if k != 'metadata'}
        return profiles
    
    def generate_all_studies(self):
        """Generate all simulated studies"""
        print(f"\n{'='*80}")
        print("SIMULATED DATA GENERATION")
        print(f"{'='*80}\n")
        
        for study_id in self.profiles.keys():
            print(f"Generating {study_id}...")
            self.generate_study(study_id)
            print(f"✓ {study_id} complete\n")
        
        print(f"{'='*80}")
        print(f"Generated {len(self.profiles)} simulated studies")
        print(f"Output directory: {self.output_dir}")
        print(f"{'='*80}\n")
    
    def generate_study(self, study_id: str):
        """
        Generate a complete simulated study.
        
        Args:
            study_id: Study identifier (e.g., "SIM-001")
        """
        if study_id not in self.profiles:
            raise ValueError(f"Unknown study: {study_id}")
        
        profile = self.profiles[study_id]
        issues = profile['issues']
        enrollment = profile['enrollment']
        
        # Create study directory
        study_dir = self.output_dir / study_id
        study_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate each data file with correct naming patterns
        self.generate_edc_metrics(study_dir, study_id, issues, enrollment)
        self.generate_sae_dashboard(study_dir, study_id, issues, enrollment)
        self.generate_visit_projection_tracker(study_dir, study_id, issues, enrollment)
        self.generate_coding_reports_meddra(study_dir, study_id, issues)  # MedDRA
        self.generate_coding_reports_whodd(study_dir, study_id, issues)   # WHODD
        self.generate_edrr(study_dir, study_id, issues, enrollment)
        self.generate_missing_lab_ranges(study_dir, study_id, issues)
    
    def generate_edc_metrics(self, study_dir: Path, study_id: str, 
                            issues: Dict, enrollment: Dict):
        """
        Generate EDC Metrics file (CPID EDC Metrics).
        
        Contains:
        - Patient IDs (CPIDs)
        - Visit completion data
        - Data entry timestamps
        - Missing pages/visits
        """
        actual_enrollment = enrollment['actual']
        completeness = issues['completeness']
        temporal = issues['temporal_drift']
        
        # Generate patient IDs
        patients = [f"{study_id}-{i:04d}" for i in range(1, actual_enrollment + 1)]
        
        # Generate visit data
        visits = ['Screening', 'Baseline', 'Week 4', 'Week 8', 'Week 12', 'Week 16']
        
        rows = []
        for patient in patients:
            for visit in visits:
                # Determine if visit is missing based on missing_visits_pct
                is_missing = random.random() < (completeness[0]['missing_visits_pct'] / 100)
                
                if not is_missing:
                    # Calculate pages
                    expected_pages = 10
                    missing_pages_pct = completeness[1]['missing_pages_pct']
                    actual_pages = int(expected_pages * (1 - missing_pages_pct / 100))
                    
                    # Data entry lag
                    lag_days = temporal[2]['data_entry_lag_days']
                    entry_date = datetime.now() - timedelta(days=random.randint(0, lag_days * 2))
                    
                    rows.append({
                        'CPID': patient,
                        'Visit': visit,
                        'Expected_Pages': expected_pages,
                        'Actual_Pages': actual_pages,
                        'Missing_Pages': expected_pages - actual_pages,
                        'Data_Entry_Date': entry_date.strftime('%Y-%m-%d'),
                        'Status': 'Complete' if actual_pages == expected_pages else 'Incomplete'
                    })
        
        df = pd.DataFrame(rows)
        output_path = study_dir / f"{study_id}_CPID_EDC_Metrics_URSV2.0.xlsx"
        df.to_excel(output_path, sheet_name='CPID EDC Metrics', index=False)
    
    def generate_sae_dashboard(self, study_dir: Path, study_id: str, 
                               issues: Dict, enrollment: Dict):
        """
        Generate SAE Dashboard file.
        
        Contains:
        - Serious Adverse Events
        - Fatal SAEs
        - Review backlog
        """
        safety = issues['safety']
        actual_enrollment = enrollment['actual']
        
        fatal_sae_count = safety[0]['fatal_sae_count']
        sae_review_backlog_days = safety[1]['sae_review_backlog_days']
        
        # Generate SAEs
        rows = []
        sae_id = 1
        
        # Generate fatal SAEs
        for _ in range(fatal_sae_count):
            patient = random.choice([f"{study_id}-{i:04d}" for i in range(1, actual_enrollment + 1)])
            report_date = datetime.now() - timedelta(days=random.randint(30, 180))
            review_date = report_date + timedelta(days=sae_review_backlog_days)
            
            rows.append({
                'SAE_ID': f"SAE-{sae_id:04d}",
                'CPID': patient,
                'Event_Term': random.choice(['Cardiac Arrest', 'Respiratory Failure', 'Septic Shock']),
                'Severity': 'Fatal',
                'Report_Date': report_date.strftime('%Y-%m-%d'),
                'Review_Date': review_date.strftime('%Y-%m-%d') if review_date <= datetime.now() else None,
                'Days_to_Review': (review_date - report_date).days if review_date <= datetime.now() else None,
                'Status': 'Reviewed' if review_date <= datetime.now() else 'Pending'
            })
            sae_id += 1
        
        # Generate non-fatal SAEs
        non_fatal_count = random.randint(10, 30)
        for _ in range(non_fatal_count):
            patient = random.choice([f"{study_id}-{i:04d}" for i in range(1, actual_enrollment + 1)])
            report_date = datetime.now() - timedelta(days=random.randint(10, 120))
            review_days = random.randint(5, sae_review_backlog_days)
            review_date = report_date + timedelta(days=review_days)
            
            rows.append({
                'SAE_ID': f"SAE-{sae_id:04d}",
                'CPID': patient,
                'Event_Term': random.choice(['Pneumonia', 'Myocardial Infarction', 'Stroke', 'Hospitalization']),
                'Severity': random.choice(['Serious', 'Life-threatening']),
                'Report_Date': report_date.strftime('%Y-%m-%d'),
                'Review_Date': review_date.strftime('%Y-%m-%d') if review_date <= datetime.now() else None,
                'Days_to_Review': (review_date - report_date).days if review_date <= datetime.now() else None,
                'Status': 'Reviewed' if review_date <= datetime.now() else 'Pending'
            })
            sae_id += 1
        
        df = pd.DataFrame(rows)
        output_path = study_dir / f"{study_id}_SAE_Dashboard.xlsx"
        df.to_excel(output_path, sheet_name='SAE DM', index=False)
    
    def generate_visit_projection_tracker(self, study_dir: Path, study_id: str, 
                                          issues: Dict, enrollment: Dict):
        """
        Generate Visit Projection Tracker file.
        
        Contains:
        - Target enrollment
        - Visit schedule adherence
        - Enrollment velocity
        """
        target_enrollment = enrollment['target']
        actual_enrollment = enrollment['actual']
        temporal = issues['temporal_drift']
        
        # Generate visit projection data
        visits = ['Screening', 'Baseline', 'Week 4', 'Week 8', 'Week 12', 'Week 16']
        
        rows = []
        for visit in visits:
            # Calculate expected vs actual based on visit_schedule_adherence
            adherence = temporal[1]['visit_schedule_adherence'] / 100
            expected_visits = int(actual_enrollment * 0.9)  # 90% should complete each visit
            actual_visits = int(expected_visits * adherence)
            
            rows.append({
                'Visit': visit,
                'Expected_Visits': expected_visits,
                'Actual_Visits': actual_visits,
                'Adherence_Pct': round((actual_visits / expected_visits) * 100, 1) if expected_visits > 0 else 0,
                'Behind_Schedule': expected_visits - actual_visits
            })
        
        # Add enrollment summary row
        rows.insert(0, {
            'Visit': 'Enrollment Summary',
            'Expected_Visits': target_enrollment,
            'Actual_Visits': actual_enrollment,
            'Adherence_Pct': round((actual_enrollment / target_enrollment) * 100, 1),
            'Behind_Schedule': target_enrollment - actual_enrollment
        })
        
        df = pd.DataFrame(rows)
        output_path = study_dir / f"{study_id}_Visit_Projection_Tracker.xlsx"
        
        # Add target enrollment in metadata (first row)
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Write metadata
            metadata_df = pd.DataFrame([
                ['Target Enrollment', target_enrollment],
                ['Actual Enrollment', actual_enrollment],
                ['Enrollment Rate', f"{enrollment['rate_pct']}%"]
            ])
            metadata_df.to_excel(writer, sheet_name='Visit Projection Tracker', 
                                index=False, header=False, startrow=0)
            
            # Write visit data
            df.to_excel(writer, sheet_name='Visit Projection Tracker', 
                       index=False, startrow=4)
    
    def generate_coding_reports_meddra(self, study_dir: Path, study_id: str, issues: Dict):
        """
        Generate MedDRA Coding Reports file.
        
        Contains:
        - Adverse event coding
        - Uncoded AE terms
        - MedDRA coding quality
        """
        coding = issues['coding']
        
        uncoded_terms_pct = coding[0]['uncoded_terms_pct']
        coding_backlog_days = coding[1]['coding_backlog_days']
        meddra_quality = coding[2]['meddra_coding_quality']
        
        # Generate MedDRA coding data
        total_ae_terms = 150
        uncoded_count = int(total_ae_terms * uncoded_terms_pct / 100)
        coded_count = total_ae_terms - uncoded_count
        
        rows = []
        
        # Generate coded AE terms
        ae_terms = [
            'Headache', 'Nausea', 'Fatigue', 'Dizziness', 'Vomiting', 
            'Diarrhea', 'Rash', 'Fever', 'Cough', 'Dyspnea',
            'Chest Pain', 'Abdominal Pain', 'Back Pain', 'Arthralgia', 'Myalgia'
        ]
        
        for i in range(1, coded_count + 1):
            submission_date = datetime.now() - timedelta(days=random.randint(10, 180))
            coding_days = random.randint(1, coding_backlog_days // 2)
            coding_date = submission_date + timedelta(days=coding_days)
            
            # Quality score
            quality_score = random.randint(int(meddra_quality * 0.8), 100)
            
            verbatim = random.choice(ae_terms)
            
            rows.append({
                'Term_ID': f"AE-{i:04d}",
                'Verbatim_Term': verbatim,
                'MedDRA_Code': f"10{random.randint(100000, 999999)}",
                'MedDRA_PT': f"{verbatim}",
                'MedDRA_SOC': random.choice(['Nervous system disorders', 'Gastrointestinal disorders', 
                                            'General disorders', 'Respiratory disorders']),
                'Submission_Date': submission_date.strftime('%Y-%m-%d'),
                'Coding_Date': coding_date.strftime('%Y-%m-%d'),
                'Days_to_Code': coding_days,
                'Coder': f"Coder{random.randint(1, 5)}",
                'Status': 'Coded'
            })
        
        # Generate uncoded AE terms
        for i in range(coded_count + 1, total_ae_terms + 1):
            submission_date = datetime.now() - timedelta(days=random.randint(1, coding_backlog_days * 2))
            days_pending = (datetime.now() - submission_date).days
            
            verbatim = random.choice(ae_terms)
            
            rows.append({
                'Term_ID': f"AE-{i:04d}",
                'Verbatim_Term': verbatim,
                'MedDRA_Code': None,
                'MedDRA_PT': None,
                'MedDRA_SOC': None,
                'Submission_Date': submission_date.strftime('%Y-%m-%d'),
                'Coding_Date': None,
                'Days_to_Code': days_pending,
                'Coder': None,
                'Status': 'Pending'
            })
        
        df = pd.DataFrame(rows)
        output_path = study_dir / f"{study_id}_GlobalCodingReport_MedDRA.xlsx"
        df.to_excel(output_path, sheet_name='MedDRA Coding', index=False)
    
    def generate_coding_reports_whodd(self, study_dir: Path, study_id: str, issues: Dict):
        """
        Generate WHODD (WHODrug) Coding Reports file.
        
        Contains:
        - Concomitant medication coding
        - Uncoded medication terms
        - WHODrug coding quality
        """
        coding = issues['coding']
        
        uncoded_terms_pct = coding[0]['uncoded_terms_pct']
        coding_backlog_days = coding[1]['coding_backlog_days']
        whodd_quality = coding[2]['meddra_coding_quality']  # Use same quality metric
        
        # Generate WHODrug coding data
        total_med_terms = 100
        uncoded_count = int(total_med_terms * uncoded_terms_pct / 100)
        coded_count = total_med_terms - uncoded_count
        
        rows = []
        
        # Generate coded medication terms
        med_terms = [
            'Aspirin', 'Ibuprofen', 'Acetaminophen', 'Metformin', 'Lisinopril',
            'Atorvastatin', 'Omeprazole', 'Levothyroxine', 'Amlodipine', 'Metoprolol',
            'Losartan', 'Gabapentin', 'Sertraline', 'Simvastatin', 'Prednisone'
        ]
        
        for i in range(1, coded_count + 1):
            submission_date = datetime.now() - timedelta(days=random.randint(10, 180))
            coding_days = random.randint(1, coding_backlog_days // 2)
            coding_date = submission_date + timedelta(days=coding_days)
            
            verbatim = random.choice(med_terms)
            
            rows.append({
                'Term_ID': f"MED-{i:04d}",
                'Verbatim_Term': verbatim,
                'WHODrug_Code': f"C{random.randint(100000, 999999)}",
                'Drug_Name': verbatim,
                'ATC_Code': f"{random.choice(['A', 'B', 'C', 'N'])}{random.randint(10, 99)}",
                'Submission_Date': submission_date.strftime('%Y-%m-%d'),
                'Coding_Date': coding_date.strftime('%Y-%m-%d'),
                'Days_to_Code': coding_days,
                'Coder': f"Coder{random.randint(1, 5)}",
                'Status': 'Coded'
            })
        
        # Generate uncoded medication terms
        for i in range(coded_count + 1, total_med_terms + 1):
            submission_date = datetime.now() - timedelta(days=random.randint(1, coding_backlog_days * 2))
            days_pending = (datetime.now() - submission_date).days
            
            verbatim = random.choice(med_terms)
            
            rows.append({
                'Term_ID': f"MED-{i:04d}",
                'Verbatim_Term': verbatim,
                'WHODrug_Code': None,
                'Drug_Name': None,
                'ATC_Code': None,
                'Submission_Date': submission_date.strftime('%Y-%m-%d'),
                'Coding_Date': None,
                'Days_to_Code': days_pending,
                'Coder': None,
                'Status': 'Pending'
            })
        
        df = pd.DataFrame(rows)
        output_path = study_dir / f"{study_id}_GlobalCodingReport_WHODD.xlsx"
        df.to_excel(output_path, sheet_name='WHODrug Coding', index=False)
    
    def generate_edrr(self, study_dir: Path, study_id: str, 
                     issues: Dict, enrollment: Dict):
        """
        Generate EDRR (Edit Check and Query) file.
        
        Contains:
        - Open queries
        - Query aging
        - Query resolution rate
        """
        query_quality = issues['query_quality']
        actual_enrollment = enrollment['actual']
        
        open_queries_count = query_quality[0]['open_queries_count']
        query_aging_days = query_quality[1]['query_aging_days']
        resolution_rate = query_quality[2]['query_resolution_rate'] / 100
        
        # Calculate total queries
        total_queries = int(open_queries_count / (1 - resolution_rate))
        resolved_queries = total_queries - open_queries_count
        
        rows = []
        query_id = 1
        
        # Generate resolved queries
        for _ in range(resolved_queries):
            patient = random.choice([f"{study_id}-{i:04d}" for i in range(1, actual_enrollment + 1)])
            open_date = datetime.now() - timedelta(days=random.randint(30, 180))
            resolution_days = random.randint(1, query_aging_days // 2)
            close_date = open_date + timedelta(days=resolution_days)
            
            rows.append({
                'Query_ID': f"QRY-{query_id:04d}",
                'CPID': patient,
                'Query_Type': random.choice(['Missing Data', 'Data Discrepancy', 'Protocol Deviation', 'Clarification']),
                'Open_Date': open_date.strftime('%Y-%m-%d'),
                'Close_Date': close_date.strftime('%Y-%m-%d'),
                'Days_Open': resolution_days,
                'Status': 'Resolved'
            })
            query_id += 1
        
        # Generate open queries
        for _ in range(open_queries_count):
            patient = random.choice([f"{study_id}-{i:04d}" for i in range(1, actual_enrollment + 1)])
            open_date = datetime.now() - timedelta(days=random.randint(1, query_aging_days * 2))
            days_open = (datetime.now() - open_date).days
            
            rows.append({
                'Query_ID': f"QRY-{query_id:04d}",
                'CPID': patient,
                'Query_Type': random.choice(['Missing Data', 'Data Discrepancy', 'Protocol Deviation', 'Clarification']),
                'Open_Date': open_date.strftime('%Y-%m-%d'),
                'Close_Date': None,
                'Days_Open': days_open,
                'Status': 'Open'
            })
            query_id += 1
        
        df = pd.DataFrame(rows)
        output_path = study_dir / f"{study_id}_EDRR.xlsx"
        df.to_excel(output_path, sheet_name='EDRR', index=False)
    
    def generate_missing_lab_ranges(self, study_dir: Path, study_id: str, issues: Dict):
        """
        Generate Missing Lab Ranges file.
        
        Contains:
        - Lab test data
        - Missing reference ranges
        - EDC quality metrics
        """
        edc_quality = issues['edc_quality']
        
        conformance_rate = edc_quality[0]['edc_conformance_rate'] / 100
        error_count = edc_quality[1]['data_entry_errors_count']
        
        # Generate lab data
        lab_tests = ['Hemoglobin', 'WBC', 'Platelets', 'Creatinine', 'ALT', 'AST', 'Glucose']
        
        rows = []
        for test in lab_tests:
            # Determine if reference range is missing
            has_range = random.random() < conformance_rate
            
            rows.append({
                'Lab_Test': test,
                'Reference_Range_Lower': random.uniform(50, 100) if has_range else None,
                'Reference_Range_Upper': random.uniform(150, 200) if has_range else None,
                'Unit': 'mg/dL',
                'Has_Reference_Range': 'Yes' if has_range else 'No',
                'Data_Entry_Errors': random.randint(0, error_count // len(lab_tests))
            })
        
        df = pd.DataFrame(rows)
        output_path = study_dir / f"{study_id}_Missing_Lab_Ranges.xlsx"
        df.to_excel(output_path, sheet_name='Missing Lab Ranges', index=False)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Generate simulated clinical trial data')
    parser.add_argument('--study', type=str, help='Generate specific study (e.g., SIM-001)')
    parser.add_argument('--all', action='store_true', help='Generate all studies')
    parser.add_argument('--profiles', type=str, default='c_trust/config/simulated_profiles.yaml',
                       help='Path to profiles YAML file')
    
    args = parser.parse_args()
    
    generator = SimulatedDataGenerator(profiles_path=args.profiles)
    
    if args.all or not args.study:
        generator.generate_all_studies()
    else:
        print(f"\nGenerating {args.study}...")
        generator.generate_study(args.study)
        print(f"✓ {args.study} complete\n")


if __name__ == "__main__":
    main()
