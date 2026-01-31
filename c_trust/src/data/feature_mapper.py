"""
Feature Name Mapper
===================
Maps extracted feature names to agent-expected names.

CRITICAL: This is a TRUST system - NO FALLBACK DATA OR ESTIMATES.
- Only maps features that REQUIRE mapping (simple renames)
- Only calculates features using PERFECT formulas from REAL data
- If data is missing, features are not set (agents will abstain if needed)
- No default values, no estimates, no fake data

This module provides minimal, targeted mapping between:
- Features extracted from NEST files (actual column names)
- Features expected by agents (standardized names)

Author: C-TRUST Team
Date: 2026-01-26
"""

from typing import Dict, Any
from src.core import get_logger, safe_divide

logger = get_logger(__name__)


class FeatureMapper:
    """
    Maps extracted features to agent-expected feature names.
        
    Handles:
    - Simple renames (e.g., open_queries_detailed → open_query_count)
    - Perfect formula calculations (e.g., missing_pages_pct from REAL counts)
    - NO estimates, NO defaults, NO fake data
    """
    
    # Simple 1:1 renames
    RENAME_MAP = {
        # Query features
        "open_queries_detailed": "open_query_count",
        "total_queries_detailed": "total_query_count",
        
        # Coding features
        "meddra_coding_completion_rate": "coding_completion_rate",
        "meddra_uncoded_terms": "uncoded_term_count",
        
        # Visit features
        "missing_visits_count": "overdue_visits_count",
    }
    
    def map_features(self, extracted_features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map extracted features to agent-expected names - REAL DATA ONLY.
        
        CRITICAL: NO FALLBACKS OR FAKE DATA
        - Only maps features that exist in extracted_features
        - Only calculates features using PERFECT formulas from REAL data
        - If data is missing, features are not set (agents will abstain)
        
        Args:
            extracted_features: Features extracted from NEST files
        
        Returns:
            Dictionary with mapped feature names and calculated features (REAL DATA ONLY)
        """
        mapped = {}
        
        # Step 1: Apply simple renames
        for old_name, new_name in self.RENAME_MAP.items():
            if old_name in extracted_features:
                mapped[new_name] = extracted_features[old_name]
                logger.debug(f"Mapped {old_name} → {new_name}")
        
        # Step 2: Handle special cases where one feature maps to multiple names
        # avg_query_age_days is used by multiple agents with different names
        if "avg_query_age_days" in extracted_features:
            mapped["query_aging_days"] = extracted_features["avg_query_age_days"]
            logger.debug("Mapped avg_query_age_days → query_aging_days")
        
        # Step 3: Calculate derived features using PERFECT formulas (REAL DATA ONLY)
        calculated = self._calculate_derived_features(extracted_features)
        mapped.update(calculated)
        
        # Step 4: Keep all original features (for debugging and future use)
        for key, value in extracted_features.items():
            if key not in mapped:
                mapped[key] = value
        
        logger.info(
            f"Mapped {len(extracted_features)} extracted features to {len(mapped)} total features "
            f"(NO FALLBACKS - agents will abstain if features missing)"
        )
        
        return mapped
    
    def _calculate_derived_features(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate features using PERFECT formulas from REAL data - NO ESTIMATES.
        
        CRITICAL: Only calculates features where we have ALL required inputs as REAL data.
        If any input is missing, the feature is NOT calculated (agent will abstain).
        
        Args:
            features: Extracted features (REAL data only)
        
        Returns:
            Dictionary of calculated features (PERFECT formulas only, NO estimates)
        """
        calculated = {}
        
        # Calculate missing_pages_pct - ONLY if we have BOTH real values
        if "missing_pages_count" in features and "total_forms" in features:
            missing = features["missing_pages_count"]
            total = features["total_forms"]
            
            # Only calculate if both are valid numbers
            if isinstance(missing, (int, float)) and isinstance(total, (int, float)) and total > 0:
                calculated["missing_pages_pct"] = safe_divide(missing, total) * 100
                logger.debug(f"Calculated missing_pages_pct: {calculated['missing_pages_pct']:.1f}% (from REAL data)")
            else:
                logger.debug("Cannot calculate missing_pages_pct: invalid input values")
        else:
            logger.debug("Cannot calculate missing_pages_pct: missing required features (missing_pages_count or total_forms)")
        
        # Map SAE backlog days - ONLY if we have REAL data from SAE Dashboard
        if "sae_dm_avg_age_days" in features:
            calculated["sae_backlog_days"] = features["sae_dm_avg_age_days"]
            logger.debug(f"Mapped sae_dm_avg_age_days → sae_backlog_days: {calculated['sae_backlog_days']:.1f} days")
        elif "sae_safety_avg_age_days" in features:
            calculated["sae_backlog_days"] = features["sae_safety_avg_age_days"]
            logger.debug(f"Mapped sae_safety_avg_age_days → sae_backlog_days: {calculated['sae_backlog_days']:.1f} days")
        else:
            logger.debug("Cannot map sae_backlog_days: no SAE dashboard data available")
        
        return calculated


# Export
__all__ = ["FeatureMapper"]
