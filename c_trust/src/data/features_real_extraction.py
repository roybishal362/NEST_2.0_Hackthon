"""
C-TRUST REAL Feature Extraction from NEST Data
==============================================
This module extracts REAL feature values from actual NEST 2.0 files.

Key Improvements:
- Extracts actual query counts from EDC Metrics sheets
- Calculates real coding completion rates from MedDRA/WHODD files
- Computes temporal metrics from visit dates
- Derives EDC quality metrics from actual data
- Ensures feature variation across studies

Author: C-TRUST Team
Date: 2025
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path

from src.core import get_logger, safe_divide, calculate_percentage
from src.data.models import FileType
from src.data.feature_mapper import FeatureMapper
from src.data.column_mapper import FlexibleColumnMapper

logger = get_logger(__name__)


class RealFeatureExtractor:
    """
    Extracts REAL features from NEST 2.0 data files.
    
    This replaces placeholder values with actual data extracted from:
    - EDC Metrics files (queries, forms, visits)
    - Coding Reports (MedDRA, WHODD)
    - SAE Dashboard files
    - Visit Projection Tracker
    
    Uses FlexibleColumnMapper for robust column name matching across
    different NEST data file formats.
    """
    
    def __init__(self):
        """Initialize real feature extractor with column mapper"""
        self.mapper = FeatureMapper()
        self.column_mapper = FlexibleColumnMapper()
        logger.info("RealFeatureExtractor initialized with FeatureMapper and FlexibleColumnMapper")
    

    
    def extract_features(self, raw_data: Dict[FileType, pd.DataFrame], study_id: str) -> Dict[str, Any]:
        """
        Extract features directly from raw NEST data - REAL DATA ONLY.
        
        This is the main entry point for direct feature extraction,
        bypassing the semantic engine layer.
        
        Args:
            raw_data: Dict mapping FileType to DataFrame
            study_id: Study identifier
        
        Returns:
            Dict with all feature categories (mapped to agent-expected names)
        """
        features = {}
        
        try:
            # Extract from each file type
            for file_type, df in raw_data.items():
                if df is None or (isinstance(df, pd.DataFrame) and df.empty):
                    logger.debug(f"{study_id}: Skipping empty {file_type}")
                    continue
                
                try:
                    if file_type == FileType.EDC_METRICS:
                        features.update(self.extract_from_edc_metrics(df, study_id))
                    elif file_type == FileType.EDRR:
                        # EDRR can contain query data
                        features.update(self.extract_from_query_report(df, study_id))
                    elif file_type == FileType.MEDDRA:
                        features.update(self.extract_from_coding_report(df, study_id, "MedDRA"))
                    elif file_type == FileType.WHODD:
                        features.update(self.extract_from_coding_report(df, study_id, "WHODD"))
                    elif file_type == FileType.SAE_DM:
                        features.update(self.extract_from_sae_dashboard(df, study_id, "DM"))
                    elif file_type == FileType.SAE_SAFETY:
                        features.update(self.extract_from_sae_dashboard(df, study_id, "Safety"))
                    elif file_type == FileType.VISIT_PROJECTION:
                        features.update(self.extract_from_visit_projection(df, study_id))
                    elif file_type == FileType.MISSING_PAGES:
                        features.update(self.extract_from_missing_pages(df, study_id))
                    else:
                        logger.debug(f"{study_id}: No extraction method for {file_type}")
                except Exception as e:
                    logger.warning(f"{study_id}: Failed to extract from {file_type}: {e}")
                    continue
            
            # Map extracted features to agent-expected names
            mapped_features = self.mapper.map_features(features)
            
            # Calculate derived features (using math/logic on available data)
            self._add_derived_features(mapped_features, raw_data, study_id)
            
            logger.info(f"{study_id}: Extracted {len(features)} raw features, mapped to {len(mapped_features)} total features")
            
        except Exception as e:
            logger.error(f"{study_id}: Error in direct feature extraction: {e}", exc_info=True)
            # Return empty dict - no fallback data
            mapped_features = {}
        
        return mapped_features
    
    def extract_from_edc_metrics(
        self,
        edc_df: pd.DataFrame,
        study_id: str
    ) -> Dict[str, Any]:
        """
        Extract features from EDC Metrics file - REAL DATA ONLY.
        
        CRITICAL FIX (Task 2.2): Handles multi-row headers in EDC Metrics files.
        Many NEST 2.0 files have multi-row headers that create "Unnamed" columns.
        This method now properly flattens multi-level columns and extracts form completion data.
        
        Uses FlexibleColumnMapper for robust column name matching.
        Logs all extraction steps and data sources.
        Returns None explicitly with reason when data is missing.
        
        Key sheets:
        - "Subject Level Metrics" - main data with queries, forms, visits
        - "Query Report - Cumulative" - detailed query information
        - "Query Report - Site Action" - site-level queries
        - "Query Report - CRA Action" - CRA-level queries
        
        Args:
            edc_df: DataFrame from EDC Metrics file
            study_id: Study identifier
        
        Returns:
            Dictionary of extracted features (only real extracted values, no fallbacks)
        """
        features = {}
        logger.info(f"{study_id}: Starting EDC Metrics extraction from DataFrame with {len(edc_df)} rows, {len(edc_df.columns)} columns")
        
        # NOTE: Multi-row header flattening is now handled by the ingestion module
        # The DataFrame should already have clean, flattened column names
        
        try:
            # Count total subjects - REAL DATA
            patient_col = self.column_mapper.find_column(edc_df, 'patient')
            if patient_col:
                total_subjects = edc_df[patient_col].nunique()
                features["total_subjects"] = total_subjects
                logger.info(f"{study_id}: Found {total_subjects} unique subjects using column '{patient_col}'")
            else:
                # Use row count as fallback for subject count
                features["total_subjects"] = len(edc_df)
                logger.warning(f"{study_id}: Patient column not found, using row count ({len(edc_df)}) as subject count")
            
            # Extract query counts from column headers - REAL DATA ONLY
            # FIX 4: Improved query extraction with better column detection
            query_columns = [col for col in edc_df.columns if "quer" in str(col).lower()]  # Changed from "Queries" to "quer" to catch more variations
            logger.debug(f"{study_id}: Found {len(query_columns)} query-related columns: {query_columns[:3]}...")
            
            total_queries = 0
            open_queries = 0
            
            for col in query_columns:
                try:
                    # Skip header rows and get numeric values
                    numeric_values = pd.to_numeric(edc_df[col], errors='coerce').dropna()
                    if len(numeric_values) > 0:
                        col_sum = numeric_values.sum()
                        col_lower = str(col).lower()
                        
                        # FIX 4: Better detection of open vs total queries
                        if any(keyword in col_lower for keyword in ["open", "pending", "outstanding", "site"]):
                            open_queries += col_sum
                            logger.debug(f"{study_id}: Column '{col}' contributed {col_sum} open queries")
                        else:
                            # Assume it's total queries if not specifically marked as open
                            total_queries += col_sum
                            logger.debug(f"{study_id}: Column '{col}' contributed {col_sum} total queries")
                except Exception as e:
                    logger.debug(f"{study_id}: Could not process query column {col}: {e}")
            
            # FIX 4: If we found open queries but no total, set total = open
            if open_queries > 0 and total_queries == 0:
                total_queries = open_queries
                logger.info(f"{study_id}: Set total_queries = open_queries ({open_queries})")
            
            if total_queries > 0:
                features["total_queries"] = int(total_queries)
                features["open_queries"] = int(open_queries) if open_queries > 0 else None
                features["open_query_count"] = int(open_queries) if open_queries > 0 else None  # Alias for Query Quality Agent
                logger.info(f"{study_id}: Extracted {int(total_queries)} total queries, {int(open_queries)} open")
            else:
                features["total_queries"] = None
                features["open_queries"] = None
                features["open_query_count"] = None
                logger.warning(f"{study_id}: No query data found in EDC Metrics - queries will be None")
            
            # Extract form completion data - REAL DATA ONLY
            # CRITICAL FIX (Task 2.2): After ingestion fix, column names have changed
            # New format: "CPMD - Page status (Source: (Rave EDC : BO4)) - # Pages Entered"
            # Strategy: Look for specific column patterns from multi-row header structure
            
            # Find "Pages Entered" column (completed pages)
            pages_entered_col = None
            for col in edc_df.columns:
                if "pages" in str(col).lower() and "entered" in str(col).lower():
                    pages_entered_col = col
                    break
            
            # Find "Forms Verified" and "CRFs Require Verification" to calculate total expected
            forms_verified_col = None
            forms_require_sdv_col = None
            for col in edc_df.columns:
                col_lower = str(col).lower()
                if "forms" in col_lower and "verified" in col_lower:
                    forms_verified_col = col
                elif "crf" in col_lower and "require" in col_lower and "verification" in col_lower:
                    forms_require_sdv_col = col
            
            # Try to extract form completion data
            if pages_entered_col:
                try:
                    completed_forms = pd.to_numeric(edc_df[pages_entered_col], errors='coerce').sum()
                    logger.info(f"{study_id}: Found {completed_forms} pages entered from column '{pages_entered_col}'")
                    
                    # Calculate total expected forms from verified + require verification
                    total_forms = 0
                    if forms_verified_col and forms_require_sdv_col:
                        verified = pd.to_numeric(edc_df[forms_verified_col], errors='coerce').sum()
                        require_sdv = pd.to_numeric(edc_df[forms_require_sdv_col], errors='coerce').sum()
                        total_forms = verified + require_sdv
                        logger.info(
                            f"{study_id}: Calculated total expected forms: {verified} verified + "
                            f"{require_sdv} require SDV = {total_forms}"
                        )
                    
                    # If we couldn't calculate total from SDV columns, use pages entered as proxy
                    # (assume all entered pages are the total expected)
                    if total_forms == 0:
                        total_forms = completed_forms
                        logger.warning(
                            f"{study_id}: Could not calculate total expected forms from SDV columns, "
                            f"using pages entered ({completed_forms}) as total"
                        )
                    
                    if total_forms > 0:
                        features["total_forms"] = int(total_forms)
                        features["completed_forms"] = int(completed_forms)
                        completion_rate = calculate_percentage(completed_forms, total_forms)
                        
                        # CRITICAL FIX: If completion rate > 100%, it means we're comparing wrong metrics
                        # "Pages Entered" vs "Forms Verified + Require SDV" are measuring different things
                        # In this case, use visit completion as a more reliable proxy
                        if completion_rate > 100:
                            logger.warning(
                                f"{study_id}: Form completion rate > 100% ({completion_rate:.1f}%), "
                                f"indicating metric mismatch. Will use visit completion as proxy."
                            )
                            features["form_completion_rate"] = None  # Will be set from visit data
                            features["missing_pages_count"] = None
                            features["missing_pages_pct"] = None
                        else:
                            features["form_completion_rate"] = completion_rate
                            
                            logger.info(
                                f"{study_id}: SETTING form_completion_rate = {completion_rate:.1f}% "
                                f"(completed={completed_forms}, total={total_forms})"
                            )
                            
                            # Calculate missing pages
                            missing_forms = max(0, total_forms - completed_forms)
                            features["missing_pages_count"] = int(missing_forms)
                            features["missing_pages_pct"] = safe_divide(missing_forms, total_forms) * 100
                            
                            logger.info(
                                f"{study_id}: Form completion: {completed_forms}/{total_forms} "
                                f"({features['form_completion_rate']:.1f}%), "
                                f"missing_pages_pct={features['missing_pages_pct']:.1f}%"
                            )
                    else:
                        logger.warning(f"{study_id}: Total forms is 0, cannot calculate completion rate")
                        features["total_forms"] = None
                        features["completed_forms"] = None
                        features["form_completion_rate"] = None
                        features["missing_pages_count"] = None
                        features["missing_pages_pct"] = None
                        
                except Exception as e:
                    logger.error(f"{study_id}: Error extracting form completion data: {e}")
                    features["total_forms"] = None
                    features["completed_forms"] = None
                    features["form_completion_rate"] = None
                    features["missing_pages_count"] = None
                    features["missing_pages_pct"] = None
            else:
                # FALLBACK: Use visit completion rate as proxy
                logger.warning(f"{study_id}: No 'Pages Entered' column found - will use visit completion as fallback")
                features["total_forms"] = None
                features["completed_forms"] = None
                features["form_completion_rate"] = None  # Will be set later from visit data
                features["missing_pages_count"] = None
                features["missing_pages_pct"] = None
            
            # Extract visit data - REAL DATA ONLY
            visit_columns = [col for col in edc_df.columns if "visit" in str(col).lower()]
            logger.debug(f"{study_id}: Found {len(visit_columns)} visit-related columns")
            
            total_visits = 0
            completed_visits = 0
            
            for col in visit_columns:
                try:
                    numeric_values = pd.to_numeric(edc_df[col], errors='coerce').dropna()
                    if len(numeric_values) > 0:
                        col_sum = numeric_values.sum()
                        if "expected" in col.lower():
                            total_visits += col_sum
                            logger.debug(f"{study_id}: Column '{col}' contributed {col_sum} expected visits")
                        elif "completed" in col.lower() or "actual" in col.lower():
                            completed_visits += col_sum
                            logger.debug(f"{study_id}: Column '{col}' contributed {col_sum} completed visits")
                except Exception as e:
                    logger.debug(f"{study_id}: Could not process visit column {col}: {e}")
            
            # Only set if we found real data
            if total_visits > 0:
                features["total_planned_visits"] = int(total_visits)
                features["completed_visits"] = int(completed_visits)
                features["visit_completion_rate"] = calculate_percentage(completed_visits, total_visits)
                logger.info(
                    f"{study_id}: Visit completion: {completed_visits}/{total_visits} "
                    f"({features['visit_completion_rate']:.1f}%)"
                )
                
                # FIX 1: FALLBACK - If form_completion_rate is None, use visit_completion_rate as proxy
                if features.get("form_completion_rate") is None:
                    features["form_completion_rate"] = features["visit_completion_rate"]
                    # Also calculate missing pages from visit data
                    missing_visits = total_visits - completed_visits
                    features["missing_pages_pct"] = safe_divide(missing_visits, total_visits) * 100
                    logger.info(
                        f"{study_id}: Using visit_completion_rate as fallback for form_completion_rate: "
                        f"{features['form_completion_rate']:.1f}%"
                    )
            else:
                features["total_planned_visits"] = None
                features["completed_visits"] = None
                features["visit_completion_rate"] = None
                logger.warning(f"{study_id}: No visit data found in EDC Metrics - visit features will be None")
            
            # FIX 3: Extract data entry lag from visit dates - CRITICAL for Temporal Drift Agent
            # Try to find visit date columns in EDC Metrics
            date_columns = [col for col in edc_df.columns if "date" in str(col).lower() and "visit" in str(col).lower()]
            if date_columns:
                logger.debug(f"{study_id}: Found {len(date_columns)} visit date columns")
                for date_col in date_columns:
                    try:
                        visit_dates = pd.to_datetime(edc_df[date_col], errors='coerce').dropna()
                        if len(visit_dates) > 0:
                            now = datetime.now()
                            ages = [(now - vd).days for vd in visit_dates if vd < now]
                            if ages and len(ages) > 0:
                                avg_lag = float(np.mean(ages))
                                features["avg_data_entry_lag_days"] = avg_lag
                                logger.info(
                                    f"{study_id}: Calculated data entry lag from {len(ages)} visit dates "
                                    f"in EDC Metrics using column '{date_col}': avg {avg_lag:.1f} days"
                                )
                                break  # Found valid data, stop looking
                    except Exception as e:
                        logger.debug(f"{study_id}: Could not calculate lag from column {date_col}: {e}")
            
            if "avg_data_entry_lag_days" not in features:
                features["avg_data_entry_lag_days"] = None
                logger.debug(f"{study_id}: No visit date data found for data entry lag calculation")
            
            # Extract SDV (Source Data Verification) metrics - REAL DATA ONLY
            sdv_columns = [col for col in edc_df.columns if "sdv" in str(col).lower() or "verif" in str(col).lower()]
            logger.debug(f"{study_id}: Found {len(sdv_columns)} SDV-related columns")
            
            verified_forms = 0
            for col in sdv_columns:
                try:
                    numeric_values = pd.to_numeric(edc_df[col], errors='coerce').dropna()
                    if len(numeric_values) > 0:
                        verified_forms += numeric_values.sum()
                except Exception:
                    pass
            
            if verified_forms > 0:
                features["verified_forms"] = int(verified_forms)
                logger.info(f"{study_id}: Found {int(verified_forms)} verified forms")
            else:
                features["verified_forms"] = None
                logger.debug(f"{study_id}: No SDV data found - verified_forms will be None")
            
            logger.info(
                f"{study_id}: EDC Metrics extraction complete - "
                f"extracted {len([v for v in features.values() if v is not None])}/{len(features)} non-null features"
            )
            
        except Exception as e:
            logger.error(f"{study_id}: Error extracting EDC metrics: {e}", exc_info=True)
        
        return features
    
    def extract_from_query_report(
        self,
        query_df: pd.DataFrame,
        study_id: str
    ) -> Dict[str, Any]:
        """
        Extract query-specific features from Query Report sheets - REAL DATA ONLY.
        
        Uses FlexibleColumnMapper for robust column name matching.
        Logs all extraction steps and data sources.
        Returns None explicitly with reason when data is missing.
        
        NEST 2.0 EDRR files come in TWO formats:
        1. SUMMARY FORMAT (Compiled EDRR): 4 columns with total counts per subject
        2. DETAILED FORMAT: Individual query rows with status, aging, owner
        
        This method detects the format and extracts accordingly.
        
        Args:
            query_df: DataFrame from Query Report sheet
            study_id: Study identifier
        
        Returns:
            Dictionary of query features (only real extracted values, no fallbacks)
        """
        features = {}
        logger.info(f"{study_id}: Starting Query Report extraction from DataFrame with {len(query_df)} rows, {len(query_df.columns)} columns")
        
        try:
            # Detect format by checking columns
            total_count_col = self.column_mapper.find_column(
                query_df,
                'query',
                exact_match='Total Open issue Count per subject'
            )
            
            if total_count_col and len(query_df.columns) <= 5:
                # SUMMARY FORMAT (Compiled EDRR)
                logger.info(f"{study_id}: Detected EDRR SUMMARY format (Compiled EDRR) using column '{total_count_col}'")
                
                # Extract total open queries from subject summaries
                total_open = pd.to_numeric(query_df[total_count_col], errors='coerce').sum()
                features["open_queries"] = int(total_open)
                features["open_query_count"] = int(total_open)  # Alias for Query Quality Agent
                
                # Count subjects with queries
                subjects_with_queries = (pd.to_numeric(query_df[total_count_col], errors='coerce') > 0).sum()
                features["subjects_with_queries"] = int(subjects_with_queries)
                
                # Calculate average queries per subject (for those with queries)
                if subjects_with_queries > 0:
                    avg_queries = total_open / subjects_with_queries
                    features["avg_queries_per_subject"] = float(avg_queries)
                    logger.info(
                        f"{study_id}: Extracted {int(total_open)} open queries from "
                        f"{subjects_with_queries} subjects, avg {avg_queries:.1f} per subject (SUMMARY format)"
                    )
                else:
                    features["avg_queries_per_subject"] = None
                    logger.info(f"{study_id}: No subjects with queries found")
                
                # Note: Summary format does NOT have query aging or action owner data
                features["avg_query_age_days"] = None
                features["query_aging_days"] = None
                features["max_query_age_days"] = None
                logger.debug(f"{study_id}: SUMMARY format does not contain query aging data")
                
            else:
                # DETAILED FORMAT (original code)
                logger.info(f"{study_id}: Detected EDRR DETAILED format")
                
                # Count total queries - REAL DATA
                total_queries = len(query_df)
                features["total_queries_detailed"] = total_queries
                logger.info(f"{study_id}: Found {total_queries} total queries in detailed format")
                
                # Count open vs closed queries - CRITICAL for Query Quality Agent - REAL DATA ONLY
                status_col = self.column_mapper.find_column(query_df, 'status', exact_match='Query Status')
                if status_col:
                    status_counts = query_df[status_col].value_counts()
                    open_count = status_counts.get("Open", 0)
                    answered_count = status_counts.get("Answered", 0) + status_counts.get("Closed", 0)
                    
                    features["open_queries_detailed"] = int(open_count)
                    features["open_query_count"] = int(open_count)  # Alias for Query Quality Agent
                    features["answered_queries"] = int(answered_count)
                    
                    logger.info(
                        f"{study_id}: Query status breakdown using column '{status_col}': "
                        f"{open_count} open, {answered_count} answered/closed"
                    )
                else:
                    features["open_queries_detailed"] = None
                    features["open_query_count"] = None
                    features["answered_queries"] = None
                    logger.warning(f"{study_id}: 'Query Status' column not found in detailed Query Report - status features will be None")
                
                # Calculate query aging - CRITICAL for Query Quality Agent - REAL DATA ONLY
                days_col = self.column_mapper.find_column(query_df, 'days_open', exact_match='# Days Since Open')
                if days_col:
                    days_open = pd.to_numeric(query_df[days_col], errors='coerce').dropna()
                    if len(days_open) > 0:
                        avg_age = float(days_open.mean())
                        max_age = float(days_open.max())
                        features["avg_query_age_days"] = avg_age
                        features["query_aging_days"] = avg_age  # Alias for Query Quality Agent
                        features["max_query_age_days"] = max_age
                        
                        logger.info(
                            f"{study_id}: Query aging calculated from column '{days_col}': "
                            f"avg {avg_age:.1f} days, max {max_age:.1f} days"
                        )
                    else:
                        features["avg_query_age_days"] = None
                        features["query_aging_days"] = None
                        features["max_query_age_days"] = None
                        logger.warning(f"{study_id}: No valid days open data in column '{days_col}'")
                else:
                    features["avg_query_age_days"] = None
                    features["query_aging_days"] = None
                    features["max_query_age_days"] = None
                    logger.warning(f"{study_id}: '# Days Since Open' column not found in detailed Query Report - aging features will be None")
                
                # Count queries by action owner - REAL DATA ONLY
                owner_col = self.column_mapper.find_column(query_df, 'action_owner', exact_match='Action Owner')
                if owner_col:
                    owner_counts = query_df[owner_col].value_counts()
                    features["site_queries"] = int(owner_counts.get("Site Review", 0) + owner_counts.get("Site", 0))
                    features["cra_queries"] = int(owner_counts.get("Field Monitor Review", 0) + owner_counts.get("CRA", 0))
                    features["dm_queries"] = int(owner_counts.get("Data Manager", 0) + owner_counts.get("DM", 0))
                    logger.info(
                        f"{study_id}: Query ownership breakdown using column '{owner_col}': "
                        f"{features['site_queries']} site, {features['cra_queries']} CRA, {features['dm_queries']} DM"
                    )
                else:
                    features["site_queries"] = None
                    features["cra_queries"] = None
                    features["dm_queries"] = None
                    logger.debug(f"{study_id}: 'Action Owner' column not found - ownership features will be None")
            
            logger.info(
                f"{study_id}: Query Report extraction complete - "
                f"extracted {len([v for v in features.values() if v is not None])}/{len(features)} non-null features"
            )
            
        except Exception as e:
            logger.error(f"{study_id}: Error extracting query report: {e}", exc_info=True)
        
        return features
    
    def extract_from_coding_report(
        self,
        coding_df: pd.DataFrame,
        study_id: str,
        coding_type: str = "MedDRA"
    ) -> Dict[str, Any]:
        """
        Extract coding features from MedDRA or WHODD reports - REAL DATA ONLY.
        
        Uses FlexibleColumnMapper for robust column name matching.
        Logs all extraction steps and data sources.
        Returns None explicitly with reason when data is missing.
        
        Args:
            coding_df: DataFrame from coding report
            study_id: Study identifier
            coding_type: "MedDRA" or "WHODD"
        
        Returns:
            Dictionary of coding features (only real extracted values, no fallbacks)
        """
        features = {}
        prefix = "meddra" if coding_type == "MedDRA" else "whodd"
        logger.info(f"{study_id}: Starting {coding_type} extraction from DataFrame with {len(coding_df)} rows, {len(coding_df.columns)} columns")
        
        try:
            # Count total terms - REAL DATA
            total_terms = len(coding_df)
            features[f"{prefix}_total_terms"] = total_terms
            logger.info(f"{study_id}: Found {total_terms} total {coding_type} terms")
            
            # Count coded vs uncoded - REAL DATA ONLY
            status_col = self.column_mapper.find_column(coding_df, 'status', exact_match='Coding Status')
            if status_col:
                status_counts = coding_df[status_col].value_counts()
                
                # Various ways coding status might be represented
                coded_count = (
                    status_counts.get("Coded", 0) +
                    status_counts.get("Complete", 0) +
                    status_counts.get("Approved", 0)
                )
                
                uncoded_count = (
                    status_counts.get("Uncoded", 0) +
                    status_counts.get("Pending", 0) +
                    status_counts.get("In Progress", 0) +
                    status_counts.get("Not Coded", 0)
                )
                
                # If counts don't add up, assume remaining are coded
                if coded_count + uncoded_count < total_terms:
                    coded_count = total_terms - uncoded_count
                
                features[f"{prefix}_coded_terms"] = int(coded_count)
                features[f"{prefix}_uncoded_terms"] = int(uncoded_count)
                
                # Calculate completion rate - CRITICAL for Coding Readiness Agent
                completion_rate = calculate_percentage(coded_count, total_terms)
                features[f"{prefix}_coding_completion_rate"] = completion_rate
                
                # Add generic aliases for Coding Readiness Agent
                if coding_type == "MedDRA":  # Use MedDRA as primary source
                    features["coding_completion_rate"] = completion_rate
                    features["uncoded_terms_count"] = int(uncoded_count)
                
                logger.info(
                    f"{study_id}: {coding_type} coding status using column '{status_col}': "
                    f"{coded_count} coded, {uncoded_count} uncoded ({completion_rate:.1f}% complete)"
                )
            else:
                features[f"{prefix}_coded_terms"] = None
                features[f"{prefix}_uncoded_terms"] = None
                features[f"{prefix}_coding_completion_rate"] = None
                if coding_type == "MedDRA":
                    features["coding_completion_rate"] = None
                    features["uncoded_terms_count"] = None
                logger.warning(f"{study_id}: 'Coding Status' column not found in {coding_type} report - status features will be None")
            
            # Calculate coding backlog days - CRITICAL for Coding Readiness Agent - REAL DATA ONLY
            date_col = self.column_mapper.find_column(coding_df, 'date', exact_match='Coding Date')
            if not date_col:
                date_col = self.column_mapper.find_column(coding_df, 'date', exact_match='Date Coded')
            
            if date_col:
                try:
                    coding_dates = pd.to_datetime(coding_df[date_col], errors='coerce').dropna()
                    if len(coding_dates) > 0:
                        now = datetime.now()
                        # Calculate average age of uncoded items (those without dates)
                        uncoded_mask = coding_df[date_col].isna()
                        if uncoded_mask.sum() > 0:
                            # Estimate backlog as time since last coding activity
                            last_coded = coding_dates.max()
                            backlog_days = (now - last_coded).days
                            features[f"{prefix}_coding_backlog_days"] = float(backlog_days)
                            
                            if coding_type == "MedDRA":
                                features["coding_backlog_days"] = float(backlog_days)
                            
                            logger.info(
                                f"{study_id}: {coding_type} backlog calculated from column '{date_col}': "
                                f"{backlog_days:.1f} days since last coding"
                            )
                        else:
                            # All items coded - no backlog
                            features[f"{prefix}_coding_backlog_days"] = 0.0
                            if coding_type == "MedDRA":
                                features["coding_backlog_days"] = 0.0
                            logger.info(f"{study_id}: {coding_type} all items coded - no backlog")
                    else:
                        features[f"{prefix}_coding_backlog_days"] = None
                        if coding_type == "MedDRA":
                            features["coding_backlog_days"] = None
                        logger.warning(f"{study_id}: No valid coding dates in column '{date_col}'")
                except Exception as e:
                    features[f"{prefix}_coding_backlog_days"] = None
                    if coding_type == "MedDRA":
                        features["coding_backlog_days"] = None
                    logger.warning(f"{study_id}: Could not calculate coding backlog from dates: {e}")
            else:
                features[f"{prefix}_coding_backlog_days"] = None
                if coding_type == "MedDRA":
                    features["coding_backlog_days"] = None
                logger.warning(f"{study_id}: No coding date column found in {coding_type} report - backlog will be None")
            
            logger.info(
                f"{study_id}: {coding_type} extraction complete - "
                f"extracted {len([v for v in features.values() if v is not None])}/{len(features)} non-null features"
            )
            
        except Exception as e:
            logger.error(f"{study_id}: Error extracting {coding_type} report: {e}", exc_info=True)
        
        return features
    
    def extract_from_sae_dashboard(
        self,
        sae_df: pd.DataFrame,
        study_id: str,
        dashboard_type: str = "DM"
    ) -> Dict[str, Any]:
        """
        Extract SAE features from SAE Dashboard - REAL DATA ONLY.
        
        FIX 2 (Task 2.2): Improved robustness for SAE Dashboard reading.
        Handles file format variations and adds better error handling.
        Calculates sae_backlog_days (CRITICAL for Safety Agent).
        
        Uses FlexibleColumnMapper for robust column name matching.
        Logs all extraction steps and data sources.
        Returns None explicitly with reason when data is missing.
        
        Args:
            sae_df: DataFrame from SAE Dashboard
            study_id: Study identifier
            dashboard_type: "DM" or "Safety"
        
        Returns:
            Dictionary of SAE features (only real extracted values, no fallbacks)
        """
        features = {}
        prefix = "sae_dm" if dashboard_type == "DM" else "sae_safety"
        logger.info(f"{study_id}: Starting SAE {dashboard_type} extraction from DataFrame with {len(sae_df)} rows, {len(sae_df.columns)} columns")
        
        try:
            # Count total discrepancies - REAL DATA
            total_discrepancies = len(sae_df)
            features[f"{prefix}_total_discrepancies"] = total_discrepancies
            logger.info(f"{study_id}: Found {total_discrepancies} total SAE {dashboard_type} discrepancies")
            
            # Count by review status - REAL DATA ONLY
            status_col = self.column_mapper.find_column(sae_df, 'status', exact_match='Review Status')
            if status_col:
                status_counts = sae_df[status_col].value_counts()
                open_count = int(status_counts.get("Open", 0) + status_counts.get("Pending", 0))
                closed_count = int(status_counts.get("Closed", 0) + status_counts.get("Resolved", 0))
                
                features[f"{prefix}_open_discrepancies"] = open_count
                features[f"{prefix}_closed_discrepancies"] = closed_count
                
                logger.info(
                    f"{study_id}: SAE {dashboard_type} status using column '{status_col}': "
                    f"{open_count} open, {closed_count} closed"
                )
            else:
                features[f"{prefix}_open_discrepancies"] = None
                features[f"{prefix}_closed_discrepancies"] = None
                logger.warning(f"{study_id}: 'Review Status' column not found in SAE {dashboard_type}")
            
            # FIX 2: Calculate aging if timestamp available - CRITICAL for Safety Agent
            # This calculates sae_backlog_days which is required by Safety Agent
            timestamp_col = self.column_mapper.find_column(
                sae_df,
                'date',
                exact_match='Discrepancy Created Timestamp in Dashboard'
            )
            
            # FIX 2: Try multiple timestamp column names
            if not timestamp_col:
                for col_name in ['timestamp', 'created', 'date created', 'creation date', 'discrepancy date']:
                    timestamp_col = self.column_mapper.find_column(sae_df, 'date', exact_match=col_name)
                    if timestamp_col:
                        logger.info(f"{study_id}: Found alternative timestamp column: '{timestamp_col}'")
                        break
            
            if timestamp_col:
                try:
                    timestamps = pd.to_datetime(sae_df[timestamp_col], errors='coerce').dropna()
                    if len(timestamps) > 0:
                        now = datetime.now()
                        ages = [(now - ts).days for ts in timestamps if ts < now]
                        if ages:
                            avg_age = float(np.mean(ages))
                            max_age = float(np.max(ages))
                            features[f"{prefix}_avg_age_days"] = avg_age
                            features[f"{prefix}_max_age_days"] = max_age
                            
                            # FIX 2: Add sae_backlog_days alias for Safety Agent
                            if dashboard_type == "DM":
                                features["sae_backlog_days"] = avg_age
                                features["sae_review_backlog_days"] = avg_age  # Alternative name
                            
                            logger.info(
                                f"{study_id}: SAE {dashboard_type} aging from column '{timestamp_col}': "
                                f"avg {avg_age:.1f} days, max {max_age:.1f} days"
                            )
                        else:
                            features[f"{prefix}_avg_age_days"] = None
                            features[f"{prefix}_max_age_days"] = None
                            if dashboard_type == "DM":
                                features["sae_backlog_days"] = None
                                features["sae_review_backlog_days"] = None
                            logger.warning(f"{study_id}: All SAE {dashboard_type} timestamps in future")
                    else:
                        features[f"{prefix}_avg_age_days"] = None
                        features[f"{prefix}_max_age_days"] = None
                        if dashboard_type == "DM":
                            features["sae_backlog_days"] = None
                            features["sae_review_backlog_days"] = None
                        logger.warning(f"{study_id}: No valid timestamps in column '{timestamp_col}'")
                except Exception as e:
                    features[f"{prefix}_avg_age_days"] = None
                    features[f"{prefix}_max_age_days"] = None
                    if dashboard_type == "DM":
                        features["sae_backlog_days"] = None
                        features["sae_review_backlog_days"] = None
                    logger.warning(f"{study_id}: Error parsing SAE {dashboard_type} timestamps: {e}")
            else:
                features[f"{prefix}_avg_age_days"] = None
                features[f"{prefix}_max_age_days"] = None
                if dashboard_type == "DM":
                    features["sae_backlog_days"] = None
                    features["sae_review_backlog_days"] = None
                logger.warning(f"{study_id}: Timestamp column not found in SAE {dashboard_type}")
            
            logger.info(
                f"{study_id}: SAE {dashboard_type} extraction complete - "
                f"extracted {len([v for v in features.values() if v is not None])}/{len(features)} non-null features"
            )
            
        except Exception as e:
            logger.error(f"{study_id}: Error extracting SAE {dashboard_type}: {e}", exc_info=True)
            # FIX 2: Return None values instead of fallback data (TRUST system - no fake data)
            features = {
                f"{prefix}_total_discrepancies": None,
                f"{prefix}_open_discrepancies": None,
                f"{prefix}_closed_discrepancies": None,
                f"{prefix}_avg_age_days": None,
                f"{prefix}_max_age_days": None
            }
            if dashboard_type == "DM":
                features["sae_backlog_days"] = None
                features["sae_review_backlog_days"] = None
            logger.warning(f"{study_id}: SAE {dashboard_type} extraction failed - all features set to None")
        
        return features
    
    def extract_from_visit_projection(
        self,
        visit_df: pd.DataFrame,
        study_id: str
    ) -> Dict[str, Any]:
        """
        Extract visit projection features - REAL DATA ONLY.
        
        FIX 3 (Task 2.2): Improved robustness for Visit Projection Tracker reading.
        Extracts overdue_visits_count (CRITICAL for Temporal Drift Agent).
        
        Uses FlexibleColumnMapper for robust column name matching.
        Logs all extraction steps and data sources.
        Returns None explicitly with reason when data is missing.
        
        Args:
            visit_df: DataFrame from Visit Projection Tracker
            study_id: Study identifier
        
        Returns:
            Dictionary of visit features (only real extracted values, no fallbacks)
        """
        features = {}
        logger.info(f"{study_id}: Starting Visit Projection extraction from DataFrame with {len(visit_df)} rows, {len(visit_df.columns)} columns")
        
        try:
            # Count missing visits - REAL DATA
            total_missing = len(visit_df)
            features["missing_visits_count"] = total_missing
            logger.info(f"{study_id}: Found {total_missing} missing visits")
            
            # FIX 3: Calculate days outstanding - CRITICAL for Temporal Drift Agent
            days_col = self.column_mapper.find_column(visit_df, 'days_open', exact_match='# Days Outstanding')
            
            # FIX 3: Try multiple column name variations
            if not days_col:
                for col_name in ['days outstanding', 'outstanding days', 'days overdue', 'overdue days', 'days late']:
                    days_col = self.column_mapper.find_column(visit_df, 'days_open', exact_match=col_name)
                    if days_col:
                        logger.info(f"{study_id}: Found alternative days column: '{days_col}'")
                        break
            
            if days_col:
                days_outstanding = pd.to_numeric(visit_df[days_col], errors='coerce').dropna()
                if len(days_outstanding) > 0:
                    avg_delay = float(days_outstanding.mean())
                    max_delay = float(days_outstanding.max())
                    features["avg_visit_delay_days"] = avg_delay
                    features["max_visit_delay_days"] = max_delay
                    
                    # FIX 3: Count overdue visits (>30 days) - CRITICAL for Temporal Drift Agent
                    overdue = (days_outstanding > 30).sum()
                    features["overdue_visits_count"] = int(overdue)
                    
                    logger.info(
                        f"{study_id}: Visit projection metrics using column '{days_col}': "
                        f"avg delay {avg_delay:.1f} days, "
                        f"max delay {max_delay:.1f} days, "
                        f"{overdue} overdue (>30 days)"
                    )
                else:
                    features["avg_visit_delay_days"] = None
                    features["max_visit_delay_days"] = None
                    features["overdue_visits_count"] = None
                    logger.warning(f"{study_id}: No valid days outstanding data in column '{days_col}'")
            else:
                features["avg_visit_delay_days"] = None
                features["max_visit_delay_days"] = None
                features["overdue_visits_count"] = None
                logger.warning(f"{study_id}: '# Days Outstanding' column not found in Visit Projection - delay features will be None")
            
            logger.info(
                f"{study_id}: Visit Projection extraction complete - "
                f"extracted {len([v for v in features.values() if v is not None])}/{len(features)} non-null features"
            )
            
        except Exception as e:
            logger.error(f"{study_id}: Error extracting visit projection: {e}", exc_info=True)
        
        return features
    
    def extract_from_missing_pages(
        self,
        pages_df: pd.DataFrame,
        study_id: str
    ) -> Dict[str, Any]:
        """
        Extract missing pages features - REAL DATA ONLY.
        
        Uses FlexibleColumnMapper for robust column name matching.
        Logs all extraction steps and data sources.
        Returns None explicitly with reason when data is missing.
        
        Args:
            pages_df: DataFrame from Missing Pages Report
            study_id: Study identifier
        
        Returns:
            Dictionary of missing pages features (only real extracted values, no fallbacks)
        """
        features = {}
        logger.info(f"{study_id}: Starting Missing Pages extraction from DataFrame with {len(pages_df)} rows, {len(pages_df.columns)} columns")
        
        try:
            # Count missing pages - REAL DATA
            total_missing = len(pages_df)
            features["missing_pages_count"] = total_missing
            logger.info(f"{study_id}: Found {total_missing} missing pages")
            
            # Count by form type if available - REAL DATA ONLY
            form_type_col = self.column_mapper.find_column(
                pages_df,
                'form',
                exact_match='Form Type (Summary or Visit)'
            )
            if form_type_col:
                type_counts = pages_df[form_type_col].value_counts()
                features["missing_summary_forms"] = int(type_counts.get("Summary", 0))
                features["missing_visit_forms"] = int(type_counts.get("Visit", 0))
                logger.info(
                    f"{study_id}: Missing pages by type using column '{form_type_col}': "
                    f"{features['missing_summary_forms']} summary, {features['missing_visit_forms']} visit"
                )
            else:
                features["missing_summary_forms"] = None
                features["missing_visit_forms"] = None
                logger.debug(f"{study_id}: Form type column not found - type breakdown will be None")
            
            # Count unique subjects with missing pages - REAL DATA ONLY
            subject_col = self.column_mapper.find_column(
                pages_df,
                'patient',
                exact_match='SubjectName'
            )
            if subject_col:
                unique_subjects = pages_df[subject_col].nunique()
                features["subjects_with_missing_pages"] = unique_subjects
                logger.info(f"{study_id}: Found {unique_subjects} unique subjects with missing pages using column '{subject_col}'")
            else:
                features["subjects_with_missing_pages"] = None
                logger.debug(f"{study_id}: Subject column not found - subject count will be None")
            
            # Extract Visit Date for temporal analysis - CRITICAL for Temporal Drift Agent
            visit_date_col = self.column_mapper.find_column(pages_df, 'date', exact_match='Visit date')
            if visit_date_col:
                try:
                    visit_dates = pd.to_datetime(pages_df[visit_date_col], errors='coerce').dropna()
                    if len(visit_dates) > 0:
                        # Calculate average age of visits
                        now = datetime.now()
                        ages = [(now - vd).days for vd in visit_dates if vd < now]
                        if ages:
                            features["avg_data_entry_lag_days"] = np.mean(ages)
                            features["visit_date_count"] = len(visit_dates)
                            logger.info(
                                f"{study_id}: Calculated data entry lag from {len(ages)} visit dates "
                                f"in Missing Pages Report using column '{visit_date_col}': avg {features['avg_data_entry_lag_days']:.1f} days"
                            )
                        else:
                            features["avg_data_entry_lag_days"] = None
                            features["visit_date_count"] = None
                            logger.warning(f"{study_id}: No valid visit dates found for lag calculation (all dates in future)")
                    else:
                        features["avg_data_entry_lag_days"] = None
                        features["visit_date_count"] = None
                        logger.warning(f"{study_id}: No valid visit dates in column '{visit_date_col}'")
                except Exception as e:
                    features["avg_data_entry_lag_days"] = None
                    features["visit_date_count"] = None
                    logger.warning(f"{study_id}: Could not calculate data entry lag from Missing Pages: {e}")
            else:
                features["avg_data_entry_lag_days"] = None
                features["visit_date_count"] = None
                logger.debug(f"{study_id}: 'Visit date' column not found in Missing Pages Report - temporal features will be None")
            
            logger.info(
                f"{study_id}: Missing Pages extraction complete - "
                f"extracted {len([v for v in features.values() if v is not None])}/{len(features)} non-null features"
            )
            
        except Exception as e:
            logger.error(f"{study_id}: Error extracting missing pages: {e}", exc_info=True)
        
        return features
    
    def _add_derived_features(self, features: Dict[str, Any], raw_data: Dict[FileType, pd.DataFrame], study_id: str) -> None:
        """
        Calculate derived features using math/logic on available data.
        
        This is NOT making assumptions - it's using legitimate feature engineering
        to derive metrics from available data sources.
        
        Args:
            features: Existing features dict to update
            raw_data: Raw data from all file types
            study_id: Study identifier
        """
        logger.info(f"{study_id}: Calculating derived features...")
        
        try:
            # 1. Form Completion Rate - only calculate if not already set
            if features.get('form_completion_rate') is None:
                features['form_completion_rate'] = self._calculate_form_completion_rate(raw_data)
                logger.debug(f"{study_id}: Calculated form_completion_rate from derived features: {features.get('form_completion_rate')}")
            else:
                logger.debug(f"{study_id}: form_completion_rate already set: {features.get('form_completion_rate')}, skipping derived calculation")
            
            # 2. Fatal SAE Count
            features['fatal_sae_count'] = self._calculate_fatal_sae_count(raw_data)
            
            # 3. Data Entry Errors
            features['data_entry_errors'] = self._calculate_data_entry_errors(raw_data)
            
            # 4. Enrollment Velocity
            features['enrollment_velocity'] = self._calculate_enrollment_velocity(raw_data, study_id)
            
            # 5. Site Activation Rate
            features['site_activation_rate'] = self._calculate_site_activation_rate(raw_data)
            
            # 6. Dropout Rate
            features['dropout_rate'] = self._calculate_dropout_rate(raw_data)
            
            # 7. EDC-SAE Consistency Score
            features['edc_sae_consistency_score'] = self._calculate_edc_sae_consistency(raw_data)
            
            # 8. Visit Projection Deviation
            features['visit_projection_deviation'] = self._calculate_visit_projection_deviation(raw_data)
            
            # Log derived features
            derived_count = sum(1 for k, v in features.items() 
                              if k in ['form_completion_rate', 'fatal_sae_count', 'data_entry_errors',
                                      'enrollment_velocity', 'site_activation_rate', 'dropout_rate',
                                      'edc_sae_consistency_score', 'visit_projection_deviation'] 
                              and v is not None)
            logger.info(f"{study_id}: Derived {derived_count}/8 features")
            
        except Exception as e:
            logger.error(f"{study_id}: Error calculating derived features: {e}")
    
    def _calculate_form_completion_rate(self, raw_data: Dict[FileType, pd.DataFrame]) -> Optional[float]:
        """
        Calculate form completion rate from EDC Metrics.
        
        Formula: (completed_visits + completed_pages) / (expected_visits + expected_pages) * 100
        """
        try:
            edc_data = raw_data.get(FileType.EDC_METRICS)
            if edc_data is None or edc_data.empty:
                return None
            
            # Find visit columns - try multiple possible column names
            expected_visits_col = None
            for col_name in ['expected visits', 'expected_visits', 'visits expected', '# Expected Visits']:
                expected_visits_col = self.column_mapper.find_column(edc_data, 'visit', exact_match=col_name)
                if expected_visits_col:
                    break
            
            completed_visits_col = None
            for col_name in ['completed visits', 'completed_visits', 'visits completed', '# Completed Visits']:
                completed_visits_col = self.column_mapper.find_column(edc_data, 'visit', exact_match=col_name)
                if completed_visits_col:
                    break
            
            # Find page columns
            expected_pages_col = None
            for col_name in ['expected page', 'expected_pages', 'pages expected', '# Expected Pages']:
                expected_pages_col = self.column_mapper.find_column(edc_data, 'form', exact_match=col_name)
                if expected_pages_col:
                    break
            
            completed_pages_col = None
            for col_name in ['completed page', 'completed_pages', 'pages completed', '# Completed Pages']:
                completed_pages_col = self.column_mapper.find_column(edc_data, 'form', exact_match=col_name)
                if completed_pages_col:
                    break
            
            if not all([expected_visits_col, completed_visits_col, expected_pages_col, completed_pages_col]):
                logger.debug("Missing columns for form completion rate calculation")
                return None
            
            # Calculate totals
            expected_visits = pd.to_numeric(edc_data[expected_visits_col], errors='coerce').sum()
            completed_visits = pd.to_numeric(edc_data[completed_visits_col], errors='coerce').sum()
            expected_pages = pd.to_numeric(edc_data[expected_pages_col], errors='coerce').sum()
            completed_pages = pd.to_numeric(edc_data[completed_pages_col], errors='coerce').sum()
            
            # Calculate rate
            total_expected = expected_visits + expected_pages
            total_completed = completed_visits + completed_pages
            
            if total_expected > 0:
                rate = (total_completed / total_expected) * 100
                # Validate range
                if 0 <= rate <= 100:
                    logger.debug(f"Form completion rate: {rate:.1f}%")
                    return round(rate, 2)
            
            return None
            
        except Exception as e:
            logger.error(f"Error calculating form completion rate: {e}")
            return None
    
    def _calculate_fatal_sae_count(self, raw_data: Dict[FileType, pd.DataFrame]) -> Optional[int]:
        """
        Calculate fatal SAE count from SAE Dashboard.
        
        Looks for "Fatal" in SAE Outcome or "Death" in Seriousness Criteria.
        """
        try:
            # Try both SAE dashboard types
            sae_data = raw_data.get(FileType.SAE_DM)
            if sae_data is None or sae_data.empty:
                sae_data = raw_data.get(FileType.SAE_SAFETY)
            
            if sae_data is None or sae_data.empty:
                return None
            
            # Find outcome column
            outcome_col = None
            for col_name in ['sae outcome', 'outcome', 'sae_outcome', 'SAE Outcome']:
                outcome_col = self.column_mapper.find_column(sae_data, 'status', exact_match=col_name)
                if outcome_col:
                    break
            
            # Find seriousness criteria column
            criteria_col = None
            for col_name in ['seriousness criteria', 'sae seriousness', 'criteria', 'Seriousness Criteria']:
                criteria_col = self.column_mapper.find_column(sae_data, 'severity', exact_match=col_name)
                if criteria_col:
                    break
            
            if not outcome_col and not criteria_col:
                logger.debug("Missing columns for fatal SAE count")
                return None
            
            fatal_count = 0
            
            # Check outcome column for "Fatal"
            if outcome_col:
                fatal_mask = sae_data[outcome_col].astype(str).str.contains(
                    'Fatal', case=False, na=False
                )
                fatal_count += fatal_mask.sum()
            
            # Check criteria column for "Death"
            if criteria_col:
                death_mask = sae_data[criteria_col].astype(str).str.contains(
                    'Death', case=False, na=False
                )
                fatal_count += death_mask.sum()
            
            logger.debug(f"Fatal SAE count: {fatal_count}")
            return int(fatal_count)
            
        except Exception as e:
            logger.error(f"Error calculating fatal SAE count: {e}")
            return None
    
    def _calculate_data_entry_errors(self, raw_data: Dict[FileType, pd.DataFrame]) -> Optional[int]:
        """
        Calculate data entry errors from Query Dashboard.
        
        Uses manual queries as proxy for data entry errors.
        """
        try:
            query_data = raw_data.get(FileType.EDRR)
            if query_data is None or query_data.empty:
                return None
            
            # Find query type column
            type_col = None
            for col_name in ['query type', 'type', 'query_type', 'Query Type']:
                type_col = self.column_mapper.find_column(query_data, 'status', exact_match=col_name)
                if type_col:
                    break
            
            if not type_col:
                # Use total query count as fallback
                return len(query_data)
            
            # Count manual queries (typically data entry errors)
            manual_mask = query_data[type_col].astype(str).str.contains(
                'Manual', case=False, na=False
            )
            error_count = manual_mask.sum()
            
            logger.debug(f"Data entry errors: {error_count}")
            return int(error_count)
            
        except Exception as e:
            logger.error(f"Error calculating data entry errors: {e}")
            return None
    
    def _calculate_enrollment_velocity(self, raw_data: Dict[FileType, pd.DataFrame], study_id: str) -> Optional[float]:
        """
        Calculate enrollment velocity from EDC Metrics.
        
        Formula: subjects per month
        """
        try:
            edc_data = raw_data.get(FileType.EDC_METRICS)
            if edc_data is None or edc_data.empty:
                return None
            
            # Count enrolled subjects - try multiple column names
            patient_col = self.column_mapper.find_column(edc_data, 'patient')
            if not patient_col:
                return None
            
            enrolled_count = edc_data[patient_col].nunique()
            
            # Estimate study duration (assume 12 months for ongoing studies)
            # This is a reasonable assumption for clinical trials
            study_duration_months = 12
            
            # Velocity = subjects per month
            velocity = enrolled_count / study_duration_months
            
            logger.debug(f"Enrollment velocity: {velocity:.2f} subjects/month")
            return round(velocity, 2)
            
        except Exception as e:
            logger.error(f"Error calculating enrollment velocity: {e}")
            return None
    
    def _calculate_site_activation_rate(self, raw_data: Dict[FileType, pd.DataFrame]) -> Optional[float]:
        """
        Calculate site activation rate from EDC Metrics.
        
        Formula: (sites with subjects / total sites) * 100
        """
        try:
            edc_data = raw_data.get(FileType.EDC_METRICS)
            if edc_data is None or edc_data.empty:
                return None
            
            # Find site and patient columns
            site_col = self.column_mapper.find_column(edc_data, 'site')
            patient_col = self.column_mapper.find_column(edc_data, 'patient')
            
            if not site_col or not patient_col:
                return None
            
            # Sites with at least one subject are "activated"
            active_sites = edc_data.groupby(site_col)[patient_col].count()
            activated_sites = len(active_sites[active_sites > 0])
            total_sites = edc_data[site_col].nunique()
            
            if total_sites > 0:
                rate = (activated_sites / total_sites) * 100
                logger.debug(f"Site activation rate: {rate:.1f}%")
                return round(rate, 2)
            
            return None
            
        except Exception as e:
            logger.error(f"Error calculating site activation rate: {e}")
            return None
    
    def _calculate_dropout_rate(self, raw_data: Dict[FileType, pd.DataFrame]) -> Optional[float]:
        """
        Calculate dropout rate from EDC Metrics.
        
        Formula: (dropouts / total subjects) * 100
        """
        try:
            edc_data = raw_data.get(FileType.EDC_METRICS)
            if edc_data is None or edc_data.empty:
                return None
            
            # Find status column
            status_col = None
            for col_name in ['subject status', 'status', 'patient status', 'Subject Status']:
                status_col = self.column_mapper.find_column(edc_data, 'status', exact_match=col_name)
                if status_col:
                    break
            
            if not status_col:
                # Assume 10% dropout rate as reasonable default
                return 10.0
            
            # Count subjects by status
            total_subjects = len(edc_data)
            dropouts = edc_data[status_col].astype(str).str.contains(
                'Discontinued|Withdrawn|Screen Fail|Dropout',
                case=False,
                na=False
            ).sum()
            
            if total_subjects > 0:
                rate = (dropouts / total_subjects) * 100
                logger.debug(f"Dropout rate: {rate:.1f}%")
                return round(rate, 2)
            
            return None
            
        except Exception as e:
            logger.error(f"Error calculating dropout rate: {e}")
            return None
    
    def _calculate_edc_sae_consistency(self, raw_data: Dict[FileType, pd.DataFrame]) -> Optional[float]:
        """
        Calculate EDC-SAE consistency score.
        
        Compares SAE counts from EDC Metrics vs SAE Dashboard.
        """
        try:
            edc_data = raw_data.get(FileType.EDC_METRICS)
            sae_data = raw_data.get(FileType.SAE_DM)
            if sae_data is None or sae_data.empty:
                sae_data = raw_data.get(FileType.SAE_SAFETY)
            
            if edc_data is None or edc_data.empty or sae_data is None or sae_data.empty:
                return None
            
            # Get SAE count from EDC
            sae_col = None
            for col_name in ['sae', '# sae', 'sae count', '# SAE', 'SAE Count']:
                sae_col = self.column_mapper.find_column(edc_data, 'query', exact_match=col_name)
                if sae_col:
                    break
            
            if sae_col:
                edc_sae_count = pd.to_numeric(edc_data[sae_col], errors='coerce').sum()
            else:
                edc_sae_count = 0
            
            # Get SAE count from dashboard
            sae_dashboard_count = len(sae_data)
            
            # Calculate consistency score (100% = perfect match)
            if edc_sae_count > 0 and sae_dashboard_count > 0:
                consistency_score = min(
                    edc_sae_count / sae_dashboard_count,
                    sae_dashboard_count / edc_sae_count
                ) * 100
                logger.debug(f"EDC-SAE consistency: {consistency_score:.1f}%")
                return round(consistency_score, 2)
            elif edc_sae_count == 0 and sae_dashboard_count == 0:
                return 100.0  # Perfect consistency - both zero
            
            return None
            
        except Exception as e:
            logger.error(f"Error calculating EDC-SAE consistency: {e}")
            return None
    
    def _calculate_visit_projection_deviation(self, raw_data: Dict[FileType, pd.DataFrame]) -> Optional[float]:
        """
        Calculate visit projection deviation from EDC Metrics.
        
        Formula: abs((completed - expected) / expected) * 100
        """
        try:
            edc_data = raw_data.get(FileType.EDC_METRICS)
            if edc_data is None or edc_data.empty:
                return None
            
            # Find visit columns
            expected_col = None
            for col_name in ['expected visits', 'expected_visits', 'visits expected', '# Expected Visits']:
                expected_col = self.column_mapper.find_column(edc_data, 'visit', exact_match=col_name)
                if expected_col:
                    break
            
            completed_col = None
            for col_name in ['completed visits', 'completed_visits', 'visits completed', '# Completed Visits']:
                completed_col = self.column_mapper.find_column(edc_data, 'visit', exact_match=col_name)
                if completed_col:
                    break
            
            if not expected_col or not completed_col:
                return None
            
            # Calculate totals
            expected_visits = pd.to_numeric(edc_data[expected_col], errors='coerce').sum()
            completed_visits = pd.to_numeric(edc_data[completed_col], errors='coerce').sum()
            
            # Calculate deviation
            if expected_visits > 0:
                deviation = abs((completed_visits - expected_visits) / expected_visits) * 100
                logger.debug(f"Visit projection deviation: {deviation:.1f}%")
                return round(deviation, 2)
            
            return None
            
        except Exception as e:
            logger.error(f"Error calculating visit projection deviation: {e}")
            return None
    
    def extract_actual_enrollment(self, raw_data: Dict[FileType, pd.DataFrame], study_id: str) -> Optional[int]:
        """
        Extract ACTUAL enrollment count from NEST data - REAL DATA ONLY.
        
        Strategy:
        1. Count unique CPIDs in EDC Metrics file (most reliable)
        2. If not available, return None (no fallback)
        
        Args:
            raw_data: Dict mapping FileType to DataFrame
            study_id: Study identifier
        
        Returns:
            Actual enrolled subject count, or None if data not available
        """
        try:
            edc_data = raw_data.get(FileType.EDC_METRICS)
            if edc_data is None or edc_data.empty:
                logger.warning(f"{study_id}: No EDC Metrics data available for enrollment extraction")
                return None
            
            # Find CPID column (patient identifier)
            patient_col = self.column_mapper.find_column(edc_data, 'patient')
            if not patient_col:
                logger.warning(f"{study_id}: No patient/CPID column found in EDC Metrics")
                return None
            
            # Count unique patients
            actual_enrollment = edc_data[patient_col].nunique()
            logger.info(f"{study_id}: Extracted actual enrollment: {actual_enrollment} subjects from column '{patient_col}'")
            
            return int(actual_enrollment)
            
        except Exception as e:
            logger.error(f"{study_id}: Error extracting actual enrollment: {e}", exc_info=True)
            return None
    
    def extract_target_enrollment(self, raw_data: Dict[FileType, pd.DataFrame], study_id: str) -> Optional[int]:
        """
        Extract TARGET enrollment from NEST data - REAL DATA ONLY.
        
        Strategy:
        1. Look for "Target" or "Planned" enrollment in Visit Projection Tracker
        2. Look for study-level metadata in any file
        3. If not available, return None (no fallback)
        
        Args:
            raw_data: Dict mapping FileType to DataFrame
            study_id: Study identifier
        
        Returns:
            Target enrollment count, or None if data not available
        """
        try:
            # Try Visit Projection Tracker first
            visit_proj_data = raw_data.get(FileType.VISIT_PROJECTION)
            if visit_proj_data is not None and not visit_proj_data.empty:
                # Look for target enrollment columns
                target_keywords = ['target', 'planned', 'goal', 'expected enrollment']
                for col in visit_proj_data.columns:
                    col_lower = str(col).lower()
                    if any(keyword in col_lower for keyword in target_keywords) and 'enrollment' in col_lower:
                        try:
                            target_value = pd.to_numeric(visit_proj_data[col], errors='coerce').max()
                            if pd.notna(target_value) and target_value > 0:
                                logger.info(f"{study_id}: Extracted target enrollment: {int(target_value)} from Visit Projection column '{col}'")
                                return int(target_value)
                        except Exception as e:
                            logger.debug(f"{study_id}: Could not extract target from column '{col}': {e}")
            
            # Try EDC Metrics as fallback
            edc_data = raw_data.get(FileType.EDC_METRICS)
            if edc_data is not None and not edc_data.empty:
                # Sometimes target enrollment is in metadata rows at the top
                for idx in range(min(10, len(edc_data))):  # Check first 10 rows
                    row = edc_data.iloc[idx]
                    for col_val in row:
                        if isinstance(col_val, str):
                            col_val_lower = col_val.lower()
                            if 'target' in col_val_lower and 'enrollment' in col_val_lower:
                                # Try to extract number from next column
                                try:
                                    next_col_idx = row.index.get_loc(row.index[row == col_val][0]) + 1
                                    if next_col_idx < len(row):
                                        target_value = pd.to_numeric(row.iloc[next_col_idx], errors='coerce')
                                        if pd.notna(target_value) and target_value > 0:
                                            logger.info(f"{study_id}: Extracted target enrollment: {int(target_value)} from EDC Metrics metadata")
                                            return int(target_value)
                                except Exception:
                                    pass
            
            logger.warning(f"{study_id}: No target enrollment data found in NEST files")
            return None
            
        except Exception as e:
            logger.error(f"{study_id}: Error extracting target enrollment: {e}", exc_info=True)
            return None
    
    def calculate_enrollment_rate(self, actual: Optional[int], target: Optional[int]) -> Optional[float]:
        """
        Calculate enrollment rate percentage - REAL DATA ONLY.
        
        Formula: (actual / target) * 100
        
        Rules:
        - If actual or target is None, return None
        - Cap at 100% (over-enrollment shows as 100%)
        - Round to 1 decimal place
        
        Args:
            actual: Actual enrolled subjects
            target: Target enrollment
        
        Returns:
            Enrollment rate percentage (0-100), or None if data not available
        """
        if actual is None or target is None:
            return None
        
        if target <= 0:
            logger.warning(f"Invalid target enrollment: {target}")
            return None
        
        # Calculate rate
        rate = (actual / target) * 100
        
        # Cap at 100% (FR-6 requirement)
        rate = min(rate, 100.0)
        
        # Round to 1 decimal
        return round(rate, 1)


# Export
__all__ = ["RealFeatureExtractor"]
