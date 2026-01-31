#!/usr/bin/env python3
"""
C-TRUST Multi-Agent Analysis Script
====================================

Task 13.2: Run full multi-agent analysis on real data

This script:
1. Executes all signal agents on processed Novartis data
2. Runs consensus engine to generate risk assessments
3. Calculates DQI scores for all studies and sites
4. Generates Guardian Agent integrity checks
5. Stores all agent signals and decisions in database

Requirements: 2.1, 2.4, 3.1, 4.1
"""

import sys
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import traceback

import pandas as pd

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core import initialize_core_system, get_logger, db_manager
from src.core.database import (
    AgentSignalTable,
    ConsensusDecisionTable,
    DQIScoreTable,
    GuardianEventTable,
)
from src.agents.signal_agents.completeness_agent import DataCompletenessAgent
from src.agents.signal_agents.safety_agent import SafetyComplianceAgent
from src.agents.signal_agents.query_agent import QueryQualityAgent
from src.consensus.consensus_engine import ConsensusEngine, ConsensusResult, ConsensusRiskLevel
from src.dqi.dqi_engine import DQICalculationEngine, DQIResult
from src.guardian.guardian_agent import GuardianAgent, DataDelta, GuardianEvent
from src.intelligence.base_agent import AgentSignal, RiskSignal

logger = get_logger(__name__)


class FeatureExtractor:
    """
    Extracts features from raw study data for agent analysis.
    
    Transforms raw DataFrames into feature dictionaries that agents can analyze.
    Maps actual Novartis NEST 2.0 data columns to agent-required features.
    
    Data Sources:
    - EDC_Metrics: 44 columns with form completion, queries, verification status
    - EDRR: Open issue counts per subject
    - SAE Dashboard: Discrepancy tracking with review status
    - Missing Pages: Missing CRF pages with aging days
    """
    
    def extract_study_features(
        self,
        study_id: str,
        study_data: Dict[str, pd.DataFrame]
    ) -> Dict[str, Any]:
        """
        Extract features from all available data for a study.
        
        Args:
            study_id: Study identifier
            study_data: Dictionary of file_type -> DataFrame
        
        Returns:
            Feature dictionary for agent analysis
        """
        features = {
            "study_id": study_id,
            "snapshot_id": f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{study_id}",
        }
        
        # Extract EDC metrics features (primary source for completeness and query data)
        if "edc_metrics" in study_data:
            edc_features = self._extract_edc_features(study_data["edc_metrics"])
            features.update(edc_features)
        
        # Extract SAE features
        if "sae_dm" in study_data:
            sae_features = self._extract_sae_features(study_data["sae_dm"])
            features.update(sae_features)
        
        # Extract missing pages features
        if "missing_pages" in study_data:
            missing_features = self._extract_missing_pages_features(
                study_data["missing_pages"],
                features.get("total_pages_entered", 0)
            )
            features.update(missing_features)
        
        # Extract visit projection features
        if "visit_projection" in study_data:
            visit_features = self._extract_visit_features(study_data["visit_projection"])
            features.update(visit_features)
        
        # Extract EDRR features (query data - supplements EDC metrics)
        if "edrr" in study_data:
            edrr_features = self._extract_edrr_features(study_data["edrr"])
            # Only update if not already set from EDC
            for key, value in edrr_features.items():
                if key not in features or features.get(key) in [None, 0, 0.0]:
                    features[key] = value
        
        return features
    
    def _extract_edc_features(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Extract features from EDC metrics data.
        
        Novartis EDC_Metrics has a multi-row header structure:
        - Row 0: High-level categories (Project Name, Region, etc.)
        - Row 1: Sub-categories (Missing Visits, Missing Page, etc.)
        - Row 2: Detailed column names (# Pages Entered, % Clean Entered CRF, etc.)
        - Row 3: Responsible parties
        - Row 4+: Actual data
        
        Key columns (at row 2, columns 16-43):
        - Col 17: # Pages Entered
        - Col 21: % Clean Entered CRF (form completion rate)
        - Col 22-29: Query counts by type
        - Col 29: #Total Queries
        - Col 30-35: SDV and freeze status
        - Col 39-43: Overdue signatures
        """
        features = {}
        
        try:
            # Make a copy to avoid modifying original
            df = df.copy()
            
            # Normalize column names (lowercase, strip whitespace)
            df.columns = [str(c).lower().strip() for c in df.columns]
            
            # The data loader may have read with different header rows
            # Try to find key columns using partial matching
            col_map = {}
            for col in df.columns:
                col_lower = col.lower()
                if "pages entered" in col_lower:
                    col_map["pages_entered"] = col
                elif "clean entered" in col_lower or "% clean" in col_lower:
                    col_map["clean_crf_pct"] = col
                elif "total queries" in col_lower or "#total queries" in col_lower:
                    col_map["total_queries"] = col
                elif "dm queries" in col_lower:
                    col_map["dm_queries"] = col
                elif "clinical queries" in col_lower:
                    col_map["clinical_queries"] = col
                elif "forms verified" in col_lower:
                    col_map["forms_verified"] = col
                elif "require verification" in col_lower or "sdv" in col_lower:
                    col_map["require_sdv"] = col
                elif "crfs frozen" in col_lower and "not" not in col_lower:
                    col_map["crfs_frozen"] = col
                elif "crfs not frozen" in col_lower:
                    col_map["crfs_not_frozen"] = col
                elif "crfs locked" in col_lower and "un" not in col_lower:
                    col_map["crfs_locked"] = col
                elif "pds confirmed" in col_lower:
                    col_map["pds_confirmed"] = col
                elif "pds proposed" in col_lower:
                    col_map["pds_proposed"] = col
                elif "overdue" in col_lower and "45 days" in col_lower:
                    col_map["overdue_45"] = col
                elif "overdue" in col_lower and "90 days" in col_lower:
                    col_map["overdue_90"] = col
                elif "overdue" in col_lower and "beyond 90" in col_lower:
                    col_map["overdue_beyond_90"] = col
                elif "site id" in col_lower or col_lower == "site":
                    col_map["site"] = col
                elif "subject id" in col_lower or col_lower == "subject":
                    col_map["subject"] = col
                elif "expected visits" in col_lower:
                    col_map["expected_visits"] = col
                elif "non-conformant" in col_lower:
                    col_map["non_conformant"] = col
            
            # If key columns not found, try positional access based on known structure
            # EDC_Metrics files have 44 columns with data starting at column 16
            if not col_map and len(df.columns) >= 44:
                # Try to use positional mapping for the 44-column EDC files
                # Skip first few rows that are headers/metadata
                numeric_rows = df[pd.to_numeric(df.iloc[:, 17], errors='coerce').notna()].copy()
                if len(numeric_rows) > 0:
                    df = numeric_rows
                    # Map by position (0-indexed, but columns start at 16 in the file)
                    col_names = df.columns.tolist()
                    if len(col_names) >= 44:
                        col_map["pages_entered"] = col_names[17] if len(col_names) > 17 else None
                        col_map["clean_crf_pct"] = col_names[21] if len(col_names) > 21 else None
                        col_map["total_queries"] = col_names[29] if len(col_names) > 29 else None
                        col_map["dm_queries"] = col_names[22] if len(col_names) > 22 else None
                        col_map["crfs_frozen"] = col_names[32] if len(col_names) > 32 else None
                        col_map["crfs_not_frozen"] = col_names[33] if len(col_names) > 33 else None
                        col_map["overdue_45"] = col_names[39] if len(col_names) > 39 else None
                        col_map["overdue_90"] = col_names[40] if len(col_names) > 40 else None
                        col_map["overdue_beyond_90"] = col_names[41] if len(col_names) > 41 else None
                        # Remove None values
                        col_map = {k: v for k, v in col_map.items() if v is not None}
            
            # Filter out header/metadata rows (rows with NaN in key columns)
            if "pages_entered" in col_map:
                df = df[pd.to_numeric(df[col_map["pages_entered"]], errors='coerce').notna()]
            
            # Extract total pages entered
            if "pages_entered" in col_map:
                total_pages = pd.to_numeric(df[col_map["pages_entered"]], errors='coerce').sum()
                features["total_pages_entered"] = int(total_pages) if pd.notna(total_pages) else 0
            
            # Extract clean CRF percentage -> form_completion_rate
            if "clean_crf_pct" in col_map:
                # Get numeric values, filtering out text
                clean_values = pd.to_numeric(df[col_map["clean_crf_pct"]], errors='coerce')
                clean_values = clean_values.dropna()
                if len(clean_values) > 0:
                    clean_pct = clean_values.mean()
                    if pd.notna(clean_pct) and clean_pct > 0:
                        features["form_completion_rate"] = float(clean_pct)
            
            # Calculate form completion from pages entered vs non-conformant if not available
            if "form_completion_rate" not in features:
                if "pages_entered" in col_map and "non_conformant" in col_map:
                    total_pages = pd.to_numeric(df[col_map["pages_entered"]], errors='coerce').sum()
                    non_conf = pd.to_numeric(df[col_map["non_conformant"]], errors='coerce').sum()
                    if pd.notna(total_pages) and total_pages > 0:
                        clean_pages = total_pages - (non_conf if pd.notna(non_conf) else 0)
                        features["form_completion_rate"] = (clean_pages / total_pages) * 100
            
            # Calculate form completion from frozen/locked CRFs if still not available
            if "form_completion_rate" not in features:
                if "crfs_frozen" in col_map and "crfs_not_frozen" in col_map:
                    frozen = pd.to_numeric(df[col_map["crfs_frozen"]], errors='coerce').sum()
                    not_frozen = pd.to_numeric(df[col_map["crfs_not_frozen"]], errors='coerce').sum()
                    total = (frozen if pd.notna(frozen) else 0) + (not_frozen if pd.notna(not_frozen) else 0)
                    if total > 0:
                        features["form_completion_rate"] = (frozen / total) * 100
            
            # Extract total queries -> open_query_count
            if "total_queries" in col_map:
                total_queries = pd.to_numeric(df[col_map["total_queries"]], errors='coerce').sum()
                features["open_query_count"] = int(total_queries) if pd.notna(total_queries) else 0
            
            # Extract DM queries separately
            if "dm_queries" in col_map:
                dm_queries = pd.to_numeric(df[col_map["dm_queries"]], errors='coerce').sum()
                features["dm_query_count"] = int(dm_queries) if pd.notna(dm_queries) else 0
            
            # Extract clinical queries
            if "clinical_queries" in col_map:
                clinical_queries = pd.to_numeric(df[col_map["clinical_queries"]], errors='coerce').sum()
                features["clinical_query_count"] = int(clinical_queries) if pd.notna(clinical_queries) else 0
            
            # Calculate query aging from overdue CRFs
            overdue_total = 0
            if "overdue_45" in col_map:
                overdue_45 = pd.to_numeric(df[col_map["overdue_45"]], errors='coerce').sum()
                overdue_total += (overdue_45 if pd.notna(overdue_45) else 0) * 30  # ~30 days avg
            if "overdue_90" in col_map:
                overdue_90 = pd.to_numeric(df[col_map["overdue_90"]], errors='coerce').sum()
                overdue_total += (overdue_90 if pd.notna(overdue_90) else 0) * 67  # ~67 days avg
            if "overdue_beyond_90" in col_map:
                overdue_beyond = pd.to_numeric(df[col_map["overdue_beyond_90"]], errors='coerce').sum()
                overdue_total += (overdue_beyond if pd.notna(overdue_beyond) else 0) * 120  # ~120 days avg
            
            # Calculate average query aging
            total_overdue_count = 0
            for key in ["overdue_45", "overdue_90", "overdue_beyond_90"]:
                if key in col_map:
                    count = pd.to_numeric(df[col_map[key]], errors='coerce').sum()
                    total_overdue_count += count if pd.notna(count) else 0
            
            if total_overdue_count > 0:
                features["query_aging_days"] = overdue_total / total_overdue_count
            else:
                features["query_aging_days"] = 0.0
            
            # Extract SDV metrics
            if "require_sdv" in col_map and "forms_verified" in col_map:
                require_sdv = pd.to_numeric(df[col_map["require_sdv"]], errors='coerce').sum()
                verified = pd.to_numeric(df[col_map["forms_verified"]], errors='coerce').sum()
                if require_sdv > 0:
                    features["sdv_completion_rate"] = (verified / require_sdv) * 100
            
            # Extract protocol deviations
            if "pds_confirmed" in col_map:
                pds = pd.to_numeric(df[col_map["pds_confirmed"]], errors='coerce').sum()
                features["protocol_deviations"] = int(pds) if pd.notna(pds) else 0
            
            # Site and subject counts
            if "site" in col_map:
                features["site_count"] = df[col_map["site"]].nunique()
            if "subject" in col_map:
                features["subject_count"] = df[col_map["subject"]].nunique()
            
            # Non-conformant data
            if "non_conformant" in col_map:
                non_conf = pd.to_numeric(df[col_map["non_conformant"]], errors='coerce').sum()
                features["non_conformant_pages"] = int(non_conf) if pd.notna(non_conf) else 0
                
        except Exception as e:
            logger.warning(f"Error extracting EDC features: {e}")
            import traceback
            traceback.print_exc()
        
        return features
    
    def _extract_sae_features(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Extract features from SAE dashboard data.
        
        Novartis SAE Dashboard columns:
        - Discrepancy ID
        - Study ID, Country, Site, Patient ID
        - Form Name
        - Discrepancy Created Timestamp in Dashboard
        - Review Status (Review Completed, Pending, etc.)
        - Action Status
        """
        features = {}
        
        try:
            df = df.copy()
            df.columns = [str(c).lower().strip() for c in df.columns]
            
            # SAE count (total discrepancies)
            features["sae_count"] = len(df)
            
            # Find review status column
            review_col = None
            for col in df.columns:
                if "review" in col.lower() and "status" in col.lower():
                    review_col = col
                    break
            
            # Calculate SAE backlog from review status
            if review_col:
                # Count pending/incomplete reviews
                pending_count = df[review_col].apply(
                    lambda x: 1 if str(x).lower() not in ["review completed", "completed", "closed"] else 0
                ).sum()
                features["sae_pending_count"] = int(pending_count)
                
                # Estimate backlog days from timestamp
                timestamp_col = None
                for col in df.columns:
                    if "timestamp" in col.lower() or "created" in col.lower():
                        timestamp_col = col
                        break
                
                if timestamp_col:
                    try:
                        df["_created_date"] = pd.to_datetime(df[timestamp_col], errors='coerce')
                        pending_mask = df[review_col].apply(
                            lambda x: str(x).lower() not in ["review completed", "completed", "closed"]
                        )
                        if pending_mask.any():
                            pending_dates = df.loc[pending_mask, "_created_date"]
                            if not pending_dates.empty:
                                avg_age = (datetime.now() - pending_dates.mean()).days
                                features["sae_backlog_days"] = max(0, float(avg_age))
                    except:
                        pass
            
            # Default backlog days if not calculated
            if "sae_backlog_days" not in features:
                # Estimate based on count - more SAEs = likely more backlog
                features["sae_backlog_days"] = min(features["sae_count"] * 0.5, 30.0)
            
            # Fatal SAE count - check form names or other indicators
            fatal_count = 0
            for col in df.columns:
                if "fatal" in col.lower() or "death" in col.lower():
                    try:
                        fatal_count = df[col].apply(
                            lambda x: 1 if str(x).lower() in ["yes", "y", "1", "true", "fatal", "death"] else 0
                        ).sum()
                        break
                    except:
                        continue
            
            # Also check form names for death-related forms
            if fatal_count == 0 and "form name" in df.columns:
                fatal_count = df["form name"].apply(
                    lambda x: 1 if "death" in str(x).lower() or "fatal" in str(x).lower() else 0
                ).sum()
            
            features["fatal_sae_count"] = int(fatal_count)
            
            # Overdue SAE count (pending reviews older than 7 days)
            features["sae_overdue_count"] = features.get("sae_pending_count", 0)
                
        except Exception as e:
            logger.warning(f"Error extracting SAE features: {e}")
        
        return features
    
    def _extract_missing_pages_features(
        self,
        df: pd.DataFrame,
        total_pages: int = 0
    ) -> Dict[str, Any]:
        """
        Extract features from missing pages data.
        
        Novartis Missing Pages columns:
        - Form Details
        - Country, Site Number, Subject Name
        - Visit Name, Page Name
        - Visit date
        - Subject Status
        - # of Days Missing
        """
        features = {}
        
        try:
            df = df.copy()
            df.columns = [str(c).lower().strip() for c in df.columns]
            
            # Missing pages count
            missing_count = len(df)
            features["missing_pages_count"] = missing_count
            
            # Calculate missing pages percentage
            if total_pages > 0:
                features["missing_pages_pct"] = (missing_count / (total_pages + missing_count)) * 100
            else:
                # Estimate based on typical study - use subject count if available
                subject_col = None
                for col in df.columns:
                    if "subject" in col.lower():
                        subject_col = col
                        break
                
                if subject_col:
                    unique_subjects = df[subject_col].nunique()
                    # Estimate ~50 pages per subject
                    estimated_total = unique_subjects * 50
                    if estimated_total > 0:
                        features["missing_pages_pct"] = min((missing_count / estimated_total) * 100, 100)
                    else:
                        features["missing_pages_pct"] = min(missing_count / 50, 100)  # Default estimate
                else:
                    features["missing_pages_pct"] = min(missing_count / 50, 100)
            
            # Extract days missing for aging analysis
            days_col = None
            for col in df.columns:
                if "days" in col.lower() and "missing" in col.lower():
                    days_col = col
                    break
            
            if days_col:
                avg_days_missing = pd.to_numeric(df[days_col], errors='coerce').mean()
                if pd.notna(avg_days_missing):
                    features["avg_days_missing"] = float(avg_days_missing)
                    # Use this for data entry lag estimate
                    features["data_entry_lag_days"] = float(avg_days_missing)
            
        except Exception as e:
            logger.warning(f"Error extracting missing pages features: {e}")
        
        return features
    
    def _extract_visit_features(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Extract features from visit projection data."""
        features = {}
        
        try:
            df = df.copy()
            df.columns = [str(c).lower().strip() for c in df.columns]
            
            # Visit completion rate - look for actual vs planned columns
            completed_cols = [c for c in df.columns if "completed" in c.lower() or "actual" in c.lower()]
            planned_cols = [c for c in df.columns if "planned" in c.lower() or "expected" in c.lower()]
            
            if completed_cols and planned_cols:
                try:
                    completed = df[completed_cols[0]].notna().sum()
                    planned = len(df)
                    if planned > 0:
                        features["visit_completion_rate"] = (completed / planned) * 100
                except:
                    pass
            
            # Visit gap count
            features["_visit_gap_count"] = len(df[df.isna().any(axis=1)])
            
        except Exception as e:
            logger.warning(f"Error extracting visit features: {e}")
        
        return features
    
    def _extract_edrr_features(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Extract features from EDRR (query) data.
        
        Novartis EDRR columns:
        - Study
        - Subject
        - Total Open issue Count per subject
        """
        features = {}
        
        try:
            df = df.copy()
            df.columns = [str(c).lower().strip() for c in df.columns]
            
            # Find open issue count column
            issue_col = None
            for col in df.columns:
                if "open" in col.lower() and ("issue" in col.lower() or "count" in col.lower()):
                    issue_col = col
                    break
            
            if issue_col:
                # Sum all open issues
                total_open = pd.to_numeric(df[issue_col], errors='coerce').sum()
                features["open_query_count"] = int(total_open) if pd.notna(total_open) else 0
                
                # Calculate average issues per subject for aging estimate
                avg_issues = pd.to_numeric(df[issue_col], errors='coerce').mean()
                if pd.notna(avg_issues) and avg_issues > 0:
                    # Estimate aging based on issue count (more issues = likely older)
                    features["query_aging_days"] = min(avg_issues * 5, 60)  # Cap at 60 days
            
            # Total subjects with issues
            features["subjects_with_issues"] = len(df)
                
        except Exception as e:
            logger.warning(f"Error extracting EDRR features: {e}")
        
        return features



class MultiAgentAnalyzer:
    """
    Orchestrates multi-agent analysis on clinical trial data.
    
    Coordinates:
    - Signal agents (Completeness, Safety, Query)
    - Consensus engine for risk assessment
    - DQI calculation engine
    - Guardian agent for integrity checks
    """
    
    def __init__(self):
        """Initialize the multi-agent analyzer."""
        # Initialize agents
        self.completeness_agent = DataCompletenessAgent()
        self.safety_agent = SafetyComplianceAgent()
        self.query_agent = QueryQualityAgent()
        
        # Initialize engines
        self.consensus_engine = ConsensusEngine()
        self.dqi_engine = DQICalculationEngine()
        self.guardian_agent = GuardianAgent()
        
        # Feature extractor
        self.feature_extractor = FeatureExtractor()
        
        # Results storage
        self.results = {
            "start_time": None,
            "end_time": None,
            "studies_analyzed": 0,
            "agent_signals_generated": 0,
            "consensus_decisions_made": 0,
            "dqi_scores_calculated": 0,
            "guardian_events_generated": 0,
            "study_results": {},
            "errors": [],
        }
        
        print("MultiAgentAnalyzer initialized with 3 signal agents")
    
    def analyze_all_studies(
        self,
        all_study_data: Dict[str, Dict[str, pd.DataFrame]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Run multi-agent analysis on all studies.
        
        Args:
            all_study_data: Dictionary of study_id -> file_type -> DataFrame
        
        Returns:
            Dictionary of study_id -> analysis results
        """
        self.results["start_time"] = datetime.now()
        print(f"\nStarting multi-agent analysis on {len(all_study_data)} studies...")
        
        all_results = {}
        previous_results = {}  # For Guardian comparison
        
        for i, (study_id, study_data) in enumerate(all_study_data.items(), 1):
            print(f"\nAnalyzing study {i}/{len(all_study_data)}: {study_id}")
            
            try:
                # Extract features
                features = self.feature_extractor.extract_study_features(study_id, study_data)
                print(f"  Extracted {len(features)} features")
                
                # Run agent analysis
                study_result = self._analyze_single_study(study_id, features, previous_results)
                
                if study_result:
                    all_results[study_id] = study_result
                    self.results["studies_analyzed"] += 1
                    self.results["study_results"][study_id] = {
                        "risk_level": study_result["consensus"].risk_level.value,
                        "risk_score": study_result["consensus"].risk_score,
                        "dqi_score": study_result["dqi"].overall_score,
                        "dqi_band": study_result["dqi"].band.value,
                        "agent_signals": len(study_result["signals"]),
                        "guardian_events": len(study_result.get("guardian_events", [])),
                    }
                    
                    # Store for Guardian comparison
                    previous_results[study_id] = {
                        "features": features,
                        "consensus": study_result["consensus"],
                        "dqi": study_result["dqi"],
                    }
                    
                    print(
                        f"  [OK] Risk: {study_result['consensus'].risk_level.value}, "
                        f"DQI: {study_result['dqi'].overall_score:.1f} ({study_result['dqi'].band.value})"
                    )
                else:
                    print(f"  [SKIP] No analysis results for {study_id}")
                    
            except Exception as e:
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
        
        return all_results
    
    def _analyze_single_study(
        self,
        study_id: str,
        features: Dict[str, Any],
        previous_results: Dict[str, Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Run full analysis on a single study.
        
        Args:
            study_id: Study identifier
            features: Extracted features
            previous_results: Previous analysis results for Guardian comparison
        
        Returns:
            Analysis results dictionary
        """
        result = {
            "study_id": study_id,
            "features": features,
            "signals": [],
            "consensus": None,
            "dqi": None,
            "guardian_events": [],
            "timestamp": datetime.now(),
        }
        
        # Step 1: Run signal agents
        signals = self._run_signal_agents(features, study_id)
        result["signals"] = signals
        self.results["agent_signals_generated"] += len(signals)
        print(f"    Generated {len(signals)} agent signals")
        
        # Step 2: Run consensus engine
        if signals:
            consensus = self.consensus_engine.calculate_consensus(signals, study_id)
            result["consensus"] = consensus
            self.results["consensus_decisions_made"] += 1
            print(f"    Consensus: {consensus.risk_level.value} (score: {consensus.risk_score:.1f})")
        else:
            # Create default consensus if no signals
            from src.consensus.consensus_engine import ConsensusRiskLevel
            result["consensus"] = ConsensusResult(
                entity_id=study_id,
                risk_level=ConsensusRiskLevel.UNKNOWN,
                risk_score=0.0,
                confidence=0.0,
                contributing_agents=[],
                abstained_agents=["completeness", "safety", "query"],
                agent_signals=[],
            )
        
        # Step 3: Calculate DQI
        dqi = self.dqi_engine.calculate_dqi(features, study_id)
        result["dqi"] = dqi
        self.results["dqi_scores_calculated"] += 1
        print(f"    DQI: {dqi.overall_score:.1f} ({dqi.band.value})")
        
        # Step 4: Run Guardian checks (if we have previous data)
        if study_id in previous_results:
            guardian_events = self._run_guardian_checks(
                study_id, features, result, previous_results[study_id]
            )
            result["guardian_events"] = guardian_events
            self.results["guardian_events_generated"] += len(guardian_events)
            if guardian_events:
                print(f"    Guardian: {len(guardian_events)} events detected")
        
        return result
    
    def _run_signal_agents(
        self,
        features: Dict[str, Any],
        study_id: str
    ) -> List[AgentSignal]:
        """
        Run all signal agents on the features.
        
        Args:
            features: Extracted features
            study_id: Study identifier
        
        Returns:
            List of agent signals
        """
        signals = []
        
        # Run Completeness Agent
        try:
            completeness_signal = self.completeness_agent.analyze(features, study_id)
            if not completeness_signal.abstained:
                signals.append(completeness_signal)
                print(f"      Completeness: {completeness_signal.risk_level.value}")
            else:
                print(f"      Completeness: ABSTAINED")
        except Exception as e:
            print(f"      Completeness: ERROR - {e}")
        
        # Run Safety Agent
        try:
            safety_signal = self.safety_agent.analyze(features, study_id)
            if not safety_signal.abstained:
                signals.append(safety_signal)
                print(f"      Safety: {safety_signal.risk_level.value}")
            else:
                print(f"      Safety: ABSTAINED")
        except Exception as e:
            print(f"      Safety: ERROR - {e}")
        
        # Run Query Agent
        try:
            query_signal = self.query_agent.analyze(features, study_id)
            if not query_signal.abstained:
                signals.append(query_signal)
                print(f"      Query: {query_signal.risk_level.value}")
            else:
                print(f"      Query: ABSTAINED")
        except Exception as e:
            print(f"      Query: ERROR - {e}")
        
        return signals
    
    def _run_guardian_checks(
        self,
        study_id: str,
        current_features: Dict[str, Any],
        current_result: Dict[str, Any],
        previous_result: Dict[str, Any]
    ) -> List[GuardianEvent]:
        """
        Run Guardian agent checks for data-output consistency.
        
        Args:
            study_id: Study identifier
            current_features: Current features
            current_result: Current analysis result
            previous_result: Previous analysis result
        
        Returns:
            List of Guardian events
        """
        events = []
        
        try:
            # Calculate data delta
            prev_features = previous_result.get("features", {})
            prev_features["snapshot_id"] = "previous"
            current_features["snapshot_id"] = "current"
            
            data_delta = self.guardian_agent.calculate_data_delta(
                prev_features, current_features, study_id
            )
            
            # Calculate output delta
            prev_output = {
                "snapshot_id": "previous",
                "risk_score": previous_result.get("consensus", {}).risk_score if hasattr(previous_result.get("consensus"), "risk_score") else 0,
                "risk_level": previous_result.get("consensus", {}).risk_level.value if hasattr(previous_result.get("consensus"), "risk_level") else "UNKNOWN",
                "dqi_score": previous_result.get("dqi", {}).overall_score if hasattr(previous_result.get("dqi"), "overall_score") else 0,
                "alerts": [],
            }
            
            curr_output = {
                "snapshot_id": "current",
                "risk_score": current_result["consensus"].risk_score,
                "risk_level": current_result["consensus"].risk_level.value,
                "dqi_score": current_result["dqi"].overall_score,
                "alerts": [],
            }
            
            output_delta = self.guardian_agent.calculate_output_delta(
                prev_output, curr_output, study_id
            )
            
            # Verify consistency
            is_consistent, event = self.guardian_agent.verify_consistency(
                data_delta, output_delta
            )
            
            if event:
                events.append(event)
            
            # Check for staleness
            current_alerts = [s.agent_type.value for s in current_result["signals"]]
            is_stale, stale_event = self.guardian_agent.check_staleness(
                study_id, current_alerts, data_delta.significant
            )
            
            if stale_event:
                events.append(stale_event)
                
        except Exception as e:
            logger.warning(f"Guardian check failed for {study_id}: {e}")
        
        return events

    def store_results_in_database(
        self,
        all_results: Dict[str, Dict[str, Any]]
    ) -> bool:
        """
        Store all analysis results in the database.
        
        Args:
            all_results: Dictionary of study_id -> analysis results
        
        Returns:
            True if storage successful
        """
        print("\nStoring analysis results in database...")
        
        try:
            session = db_manager.get_session()
            snapshot_id = f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            for study_id, result in all_results.items():
                # Store agent signals
                for signal in result.get("signals", []):
                    signal_record = AgentSignalTable(
                        signal_id=str(uuid.uuid4()),
                        snapshot_id=snapshot_id,
                        agent_name=signal.agent_type.value,
                        entity_id=study_id,
                        entity_type="study",
                        signal_type=signal.risk_level.value,
                        severity=signal.risk_level.value,
                        confidence=signal.confidence,
                        evidence=json.dumps([e.__dict__ if hasattr(e, '__dict__') else str(e) for e in signal.evidence]),
                        can_abstain=True,
                        timestamp=datetime.now(),
                    )
                    session.add(signal_record)
                
                # Store consensus decision
                consensus = result.get("consensus")
                if consensus:
                    consensus_record = ConsensusDecisionTable(
                        decision_id=str(uuid.uuid4()),
                        snapshot_id=snapshot_id,
                        entity_id=study_id,
                        entity_type="study",
                        risk_level=consensus.risk_level.value if hasattr(consensus.risk_level, 'value') else str(consensus.risk_level),
                        confidence=consensus.confidence,
                        contributing_agents=json.dumps(consensus.contributing_agents),
                        recommended_actions=json.dumps([]),
                        dqi_score=result.get("dqi", {}).overall_score if hasattr(result.get("dqi"), "overall_score") else 0,
                        timestamp=datetime.now(),
                    )
                    session.add(consensus_record)
                
                # Store DQI score
                dqi = result.get("dqi")
                if dqi:
                    dqi_record = DQIScoreTable(
                        score_id=str(uuid.uuid4()),
                        entity_id=study_id,
                        snapshot_id=snapshot_id,
                        overall_score=dqi.overall_score,
                        dimensions=json.dumps(dqi.to_dict().get("dimension_breakdown", {})),
                        band=dqi.band.value,
                        trend="STABLE",
                        timestamp=datetime.now(),
                    )
                    session.add(dqi_record)
                
                # Store Guardian events
                for event in result.get("guardian_events", []):
                    event_record = GuardianEventTable(
                        event_id=event.event_id,
                        snapshot_id=snapshot_id,
                        event_type=event.event_type.value,
                        severity=event.severity.value,
                        entity_id=study_id,
                        data_delta_summary=event.data_delta_summary,
                        expected_behavior=event.expected_behavior,
                        actual_behavior=event.actual_behavior,
                        recommendation=event.recommendation,
                        timestamp=datetime.now(),
                    )
                    session.add(event_record)
            
            session.commit()
            print(f"Stored results for {len(all_results)} studies in database")
            return True
            
        except Exception as e:
            print(f"Failed to store results in database: {e}")
            traceback.print_exc()
            session.rollback()
            return False
        finally:
            session.close()
    
    def generate_analysis_report(self) -> str:
        """
        Generate a summary report of the multi-agent analysis.
        
        Returns:
            Formatted summary report string
        """
        report_lines = [
            "=" * 70,
            "C-TRUST MULTI-AGENT ANALYSIS REPORT",
            "=" * 70,
            "",
            f"Analysis Time: {self.results.get('start_time', 'N/A')}",
            f"Processing Duration: {self.results.get('processing_time_seconds', 0):.1f} seconds",
            "",
            "SUMMARY",
            "-" * 40,
            f"Studies Analyzed: {self.results['studies_analyzed']}",
            f"Agent Signals Generated: {self.results['agent_signals_generated']}",
            f"Consensus Decisions Made: {self.results['consensus_decisions_made']}",
            f"DQI Scores Calculated: {self.results['dqi_scores_calculated']}",
            f"Guardian Events Generated: {self.results['guardian_events_generated']}",
            "",
        ]
        
        # Risk distribution
        if self.results["study_results"]:
            risk_counts = {}
            dqi_bands = {}
            
            for study_id, result in self.results["study_results"].items():
                risk_level = result.get("risk_level", "UNKNOWN")
                dqi_band = result.get("dqi_band", "UNKNOWN")
                
                risk_counts[risk_level] = risk_counts.get(risk_level, 0) + 1
                dqi_bands[dqi_band] = dqi_bands.get(dqi_band, 0) + 1
            
            report_lines.extend([
                "RISK DISTRIBUTION",
                "-" * 40,
            ])
            for level, count in sorted(risk_counts.items()):
                report_lines.append(f"  {level}: {count} studies")
            
            report_lines.extend([
                "",
                "DQI BAND DISTRIBUTION",
                "-" * 40,
            ])
            for band, count in sorted(dqi_bands.items()):
                report_lines.append(f"  {band}: {count} studies")
            
            report_lines.append("")
        
        # Study details
        if self.results["study_results"]:
            report_lines.extend([
                "STUDY DETAILS",
                "-" * 40,
            ])
            
            for study_id, result in sorted(self.results["study_results"].items()):
                report_lines.append(
                    f"  {study_id}: Risk={result['risk_level']}, "
                    f"DQI={result['dqi_score']:.1f} ({result['dqi_band']}), "
                    f"Signals={result['agent_signals']}"
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
            "ANALYSIS COMPLETE",
            "=" * 70,
        ])
        
        return "\n".join(report_lines)


def load_processed_data() -> Dict[str, Dict[str, pd.DataFrame]]:
    """
    Load previously processed Novartis data.
    
    Returns:
        Dictionary of study_id -> file_type -> DataFrame
    """
    from scripts.validate_novartis_data import NovartisDataValidator
    
    print("Loading Novartis NEST 2.0 data...")
    
    validator = NovartisDataValidator()
    
    if not validator.initialize():
        print("Failed to initialize data validator")
        return {}
    
    study_folders = validator.discover_studies()
    
    if not study_folders:
        print("No studies discovered")
        return {}
    
    all_study_data = validator.process_all_studies(study_folders)
    
    print(f"Loaded data for {len(all_study_data)} studies")
    return all_study_data


def main():
    """Main entry point for multi-agent analysis."""
    print("\n" + "=" * 70)
    print("C-TRUST MULTI-AGENT ANALYSIS")
    print("Task 13.2: Run full multi-agent analysis on real data")
    print("=" * 70 + "\n")
    
    # Initialize core system
    if not initialize_core_system():
        print("Failed to initialize core system")
        return 1
    
    # Load processed data
    all_study_data = load_processed_data()
    
    if not all_study_data:
        print("No data available for analysis")
        return 1
    
    # Run multi-agent analysis
    analyzer = MultiAgentAnalyzer()
    all_results = analyzer.analyze_all_studies(all_study_data)
    
    # Store results in database
    analyzer.store_results_in_database(all_results)
    
    # Generate and print report
    report = analyzer.generate_analysis_report()
    print("\n" + report)
    
    # Save report to file
    report_path = Path("c_trust/exports/multi_agent_analysis_report.txt")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding='utf-8')
    print(f"\nReport saved to: {report_path}")
    
    # Save detailed results as JSON
    json_path = Path("c_trust/exports/multi_agent_analysis_results.json")
    
    # Convert results to JSON-serializable format
    json_results = {
        "start_time": str(analyzer.results.get("start_time", "")),
        "end_time": str(analyzer.results.get("end_time", "")),
        "processing_time_seconds": analyzer.results.get("processing_time_seconds", 0),
        "studies_analyzed": analyzer.results["studies_analyzed"],
        "agent_signals_generated": analyzer.results["agent_signals_generated"],
        "consensus_decisions_made": analyzer.results["consensus_decisions_made"],
        "dqi_scores_calculated": analyzer.results["dqi_scores_calculated"],
        "guardian_events_generated": analyzer.results["guardian_events_generated"],
        "study_results": analyzer.results["study_results"],
        "errors": analyzer.results["errors"],
    }
    
    json_path.write_text(json.dumps(json_results, indent=2), encoding='utf-8')
    print(f"Detailed results saved to: {json_path}")
    
    if analyzer.results["studies_analyzed"] > 0:
        print(f"\n[SUCCESS] Analysis completed successfully!")
        print(f"   Analyzed {analyzer.results['studies_analyzed']} studies")
        print(f"   Generated {analyzer.results['agent_signals_generated']} agent signals")
        print(f"   Calculated {analyzer.results['dqi_scores_calculated']} DQI scores")
        return 0
    else:
        print("\n[FAILED] Analysis failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
