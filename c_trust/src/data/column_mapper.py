"""
Flexible Column Mapper for NEST 2.0 Data
=========================================

This module provides flexible column name mapping to handle variations in NEST data files.
Column names vary across studies (e.g., 'Visit' vs 'Visit Name' vs 'VISIT'), so this mapper
uses both exact matching and fuzzy matching to find the correct columns.

Key Features:
- Semantic name mappings for all required columns
- Exact match with case-insensitive comparison
- Fuzzy matching with 80% similarity threshold
- Comprehensive logging of column mappings

Author: C-TRUST Team
Date: 2025
"""

import pandas as pd
from typing import Optional, List, Dict
from difflib import SequenceMatcher
import logging

logger = logging.getLogger(__name__)


class FlexibleColumnMapper:
    """
    Maps semantic column names to actual NEST column names using fuzzy matching.
    
    This handles the reality that NEST 2.0 files have inconsistent column naming:
    - Different capitalization (Visit vs VISIT vs visit)
    - Different separators (Visit_Name vs Visit Name vs VisitName)
    - Additional descriptive text (Visit vs Visit Name vs Visit Name (Source: EDC))
    
    Example:
        mapper = FlexibleColumnMapper()
        visit_col = mapper.find_column(df, 'visit')
        if visit_col:
            visits = df[visit_col]
    """
    
    def __init__(self):
        """Initialize column mapper with semantic name mappings."""
        # Define semantic mappings for all required columns
        # Each semantic name maps to a list of possible actual column names
        self.mappings: Dict[str, List[str]] = {
            'visit': [
                'Visit',
                'Visit Name',
                'VISIT',
                'VisitName',
                'visit_name',
                'Visit Name (Source: EDC)',
                'Visit Date',
                'Visits Completed',
                'Expected Visits',
                'Actual Visits'
            ],
            'form': [
                'Form',
                'Form Name',
                'FORM',
                'FormName',
                'form_name',
                'Form Type',
                'Form Type (Summary or Visit)',
                'Forms Entered',
                'Completed Forms',
                'Total Forms'
            ],
            'site': [
                'Site',
                'Site ID',
                'SITE',
                'SiteID',
                'site_id',
                'Site Number',
                'Site Name'
            ],
            'patient': [
                'CPID',
                'Patient ID',
                'PatientID',
                'patient_id',
                'Subject ID',
                'SubjectID',
                'subject_id',
                'SubjectName',
                'Subject Name'
            ],
            'status': [
                'Status',
                'STATUS',
                'Query Status',
                'Form Status',
                'Review Status',
                'Coding Status',
                'Completion Status'
            ],
            'date': [
                'Date',
                'DATE',
                'Visit Date',
                'Entry Date',
                'Created Date',
                'Coding Date',
                'Date Coded',
                'Discrepancy Created Timestamp in Dashboard'
            ],
            'severity': [
                'Severity',
                'SEVERITY',
                'SAE Severity',
                'Grade',
                'Severity Grade'
            ],
            'completion': [
                'Completion',
                'Complete',
                'Completion Status',
                'Status',
                'Completion Rate'
            ],
            'query': [
                'Query',
                'Queries',
                'Open Queries',
                'Total Open issue Count per subject',
                'Query Status',
                'Query Count'
            ],
            'days_open': [
                '# Days Since Open',
                'Days Since Open',
                'Days Open',
                'Age Days',
                '# Days Outstanding'
            ],
            'action_owner': [
                'Action Owner',
                'Owner',
                'Assigned To',
                'Responsible Party'
            ]
        }
        
        logger.info("FlexibleColumnMapper initialized with %d semantic mappings", len(self.mappings))
    
    def find_column(
        self,
        df: pd.DataFrame,
        semantic_name: str,
        exact_match: Optional[str] = None
    ) -> Optional[str]:
        """
        Find actual column name using exact match then fuzzy matching.
        
        This method tries multiple strategies to find the correct column:
        1. Try exact match (if provided)
        2. Try exact match from semantic mappings (case-insensitive)
        3. Try fuzzy match with 80% similarity threshold
        
        Args:
            df: DataFrame to search
            semantic_name: Semantic name (e.g., 'visit', 'form', 'patient')
            exact_match: Optional exact column name to try first
        
        Returns:
            Actual column name if found, None otherwise
        
        Example:
            # Find visit column (may be "Visit", "Visit Name", "VISIT", etc.)
            visit_col = mapper.find_column(df, 'visit')
            if visit_col:
                print(f"Found visit column: {visit_col}")
        """
        if df is None or df.empty:
            logger.debug("Cannot find column in None or empty DataFrame")
            return None
        
        # Get possible column names for this semantic name
        possible_names = self.mappings.get(semantic_name, [])
        
        if not possible_names and not exact_match:
            logger.warning(f"No mappings defined for semantic name: {semantic_name}")
            return None
        
        # Strategy 1: Try exact match first (if provided)
        if exact_match:
            for col in df.columns:
                if str(col).strip().lower() == exact_match.strip().lower():
                    logger.debug(f"Found exact match for '{semantic_name}': {col}")
                    return col
        
        # Strategy 2: Try exact match from semantic mappings (case-insensitive)
        for col in df.columns:
            col_normalized = str(col).strip().lower()
            for possible_name in possible_names:
                if col_normalized == possible_name.strip().lower():
                    logger.debug(f"Found semantic match for '{semantic_name}': {col}")
                    return col
        
        # Strategy 3: Try fuzzy match with 80% threshold
        best_match = None
        best_ratio = 0.0
        threshold = 0.80
        
        for col in df.columns:
            col_normalized = str(col).strip().lower()
            
            # Try fuzzy matching against all possible names
            for possible_name in possible_names:
                possible_normalized = possible_name.strip().lower()
                
                # Calculate similarity ratio
                ratio = SequenceMatcher(None, col_normalized, possible_normalized).ratio()
                
                if ratio > best_ratio and ratio >= threshold:
                    best_ratio = ratio
                    best_match = col
        
        if best_match:
            logger.debug(
                f"Found fuzzy match for '{semantic_name}': {best_match} "
                f"(similarity: {best_ratio:.2%})"
            )
            return best_match
        
        # No match found
        logger.debug(
            f"No column found for semantic name '{semantic_name}' in DataFrame with columns: "
            f"{list(df.columns)[:5]}{'...' if len(df.columns) > 5 else ''}"
        )
        return None
    
    def find_columns(
        self,
        df: pd.DataFrame,
        semantic_names: List[str]
    ) -> Dict[str, Optional[str]]:
        """
        Find multiple columns at once.
        
        Args:
            df: DataFrame to search
            semantic_names: List of semantic names to find
        
        Returns:
            Dictionary mapping semantic names to actual column names (or None if not found)
        
        Example:
            columns = mapper.find_columns(df, ['visit', 'form', 'patient'])
            if columns['visit']:
                visits = df[columns['visit']]
        """
        results = {}
        for semantic_name in semantic_names:
            results[semantic_name] = self.find_column(df, semantic_name)
        
        found_count = sum(1 for v in results.values() if v is not None)
        logger.debug(
            f"Found {found_count}/{len(semantic_names)} columns: "
            f"{[k for k, v in results.items() if v is not None]}"
        )
        
        return results
    
    def add_mapping(self, semantic_name: str, possible_names: List[str]) -> None:
        """
        Add or update a semantic mapping.
        
        This allows extending the mapper with new column name variations discovered
        in the data.
        
        Args:
            semantic_name: Semantic name (e.g., 'custom_field')
            possible_names: List of possible actual column names
        
        Example:
            mapper.add_mapping('custom_field', ['Custom Field', 'CUSTOM', 'custom'])
        """
        if semantic_name in self.mappings:
            # Extend existing mapping
            existing = set(self.mappings[semantic_name])
            new_names = [n for n in possible_names if n not in existing]
            self.mappings[semantic_name].extend(new_names)
            logger.info(
                f"Extended mapping for '{semantic_name}' with {len(new_names)} new names"
            )
        else:
            # Create new mapping
            self.mappings[semantic_name] = possible_names
            logger.info(
                f"Created new mapping for '{semantic_name}' with {len(possible_names)} names"
            )
    
    def get_mapping_info(self, semantic_name: str) -> Dict[str, any]:
        """
        Get information about a semantic mapping.
        
        Args:
            semantic_name: Semantic name to query
        
        Returns:
            Dictionary with mapping information
        
        Example:
            info = mapper.get_mapping_info('visit')
            print(f"Visit column has {info['count']} possible names")
        """
        possible_names = self.mappings.get(semantic_name, [])
        return {
            'semantic_name': semantic_name,
            'possible_names': possible_names,
            'count': len(possible_names),
            'exists': semantic_name in self.mappings
        }
    
    def get_all_mappings(self) -> Dict[str, List[str]]:
        """
        Get all semantic mappings.
        
        Returns:
            Dictionary of all semantic name to possible names mappings
        """
        return self.mappings.copy()


# Export
__all__ = ['FlexibleColumnMapper']
