"""
Export API Endpoint
===================
Provides data export functionality in CSV and Excel formats.

Phase 4, Task 16: Implement Export API Endpoint

Features:
- CSV export with all study data
- Excel export with formatted workbook (optional)
- Includes DQI scores, agent signals, dimension scores
- Automatic file cleanup (delete old exports)
- Error handling and logging
"""

import csv
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import pandas as pd

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from src.core import get_logger

logger = get_logger(__name__)

# Create router
router = APIRouter(prefix="/export", tags=["export"])

# Export directory
EXPORT_DIR = Path("c_trust/exports")
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

# File expiration (24 hours)
EXPORT_EXPIRATION_HOURS = 24


# ========================================
# REQUEST/RESPONSE MODELS
# ========================================

class ExportRequest(BaseModel):
    """Export request model"""
    format: str = Field(..., description="Export format: 'csv' or 'excel'")
    study_ids: Optional[List[str]] = Field(None, description="List of study IDs to export (None = all)")
    include_agent_signals: bool = Field(True, description="Include agent signal details")
    include_temporal_metrics: bool = Field(True, description="Include temporal drift metrics")
    user_id: Optional[str] = Field(None, description="User ID for audit trail")
    filters: Optional[Dict[str, Any]] = Field(None, description="Additional filters")


class ExportResponse(BaseModel):
    """Export response model"""
    filename: str = Field(..., description="Generated filename")
    download_url: str = Field(..., description="Download URL")
    expires_at: str = Field(..., description="Expiration timestamp (ISO format)")
    row_count: int = Field(..., description="Number of rows exported")
    format: str = Field(..., description="Export format")
    metadata: Dict[str, Any] = Field(..., description="Export metadata")


# ========================================
# EXPORT FUNCTIONS
# ========================================

def get_export_data(study_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Get study data for export from data cache.
    
    Args:
        study_ids: Optional list of study IDs to filter
    
    Returns:
        List of study data dictionaries
    """
    import json
    from pathlib import Path
    
    logger.info(f"Retrieving export data for studies: {study_ids or 'all'}")
    
    # Load data from cache
    cache_file = Path("c_trust/data_cache.json")
    if not cache_file.exists():
        logger.warning("Data cache not found, returning empty export data")
        return []
    
    try:
        with open(cache_file, "r") as f:
            cache_data = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load data cache: {e}", exc_info=True)
        return []
    
    # Filter by study_ids if provided
    if study_ids:
        cache_data = {k: v for k, v in cache_data.items() if k in study_ids}
    
    # Convert cache data to export format
    export_data = []
    
    for study_id, study_data in cache_data.items():
        # Extract dimension scores
        dimension_scores = {}
        for dim in study_data.get("dimension_scores", []):
            dim_name = dim.get("dimension", "unknown")
            dimension_scores[f"dimension_{dim_name}_score"] = dim.get("raw_score", 0)
        
        # Extract features
        features = study_data.get("features", {})
        
        # Build export row
        row = {
            'study_id': study_id,
            'study_name': study_id,  # Use study_id as name for now
            'dqi_score': study_data.get("overall_score"),
            'dqi_band': _get_dqi_band(study_data.get("overall_score")),
            'risk_level': study_data.get("risk_level"),
            
            # Enrollment data
            'enrollment_actual': features.get("total_subjects"),
            'enrollment_target': features.get("target_enrollment"),
            'enrollment_rate': features.get("enrollment_rate"),
            'enrollment_velocity': features.get("enrollment_velocity"),
            
            # Temporal metrics
            'visit_schedule_adherence': features.get("visit_completion_rate"),
            'data_entry_lag_days': features.get("avg_data_entry_lag_days"),
            
            # Safety metrics
            'sae_backlog_days': features.get("sae_backlog_days"),
            'fatal_sae_count': features.get("fatal_sae_count"),
            'sae_overdue_count': features.get("sae_overdue_count"),
            
            # Completeness metrics
            'missing_pages_pct': features.get("missing_pages_pct"),
            'visit_completion_rate': features.get("visit_completion_rate"),
            'form_completion_rate': features.get("form_completion_rate"),
            
            # Query metrics
            'open_query_count': features.get("open_query_count"),
            'query_aging_days': features.get("query_aging_days"),
            'subjects_with_queries': features.get("subjects_with_queries"),
            
            # Coding metrics
            'uncoded_terms_count': features.get("uncoded_terms_count"),
            'coding_completion_rate': features.get("coding_completion_rate"),
            'coding_backlog_days': features.get("coding_backlog_days"),
        }
        
        # Add dimension scores
        row.update(dimension_scores)
        
        export_data.append(row)
    
    logger.info(f"Retrieved {len(export_data)} studies for export")
    return export_data


def _get_dqi_band(dqi_score: Optional[float]) -> str:
    """
    Get DQI band classification from score.
    
    Args:
        dqi_score: DQI score (0-100)
    
    Returns:
        Band classification: GREEN, AMBER, ORANGE, or RED
    """
    if dqi_score is None:
        return "UNKNOWN"
    
    if dqi_score >= 85:
        return "GREEN"
    elif dqi_score >= 75:
        return "AMBER"
    elif dqi_score >= 65:
        return "ORANGE"
    else:
        return "RED"


def generate_csv_export(
    data: List[Dict[str, Any]],
    filename: str,
    include_agent_signals: bool = True,
    include_temporal_metrics: bool = True
) -> Path:
    """
    Generate CSV export file.
    
    Args:
        data: List of study data dictionaries
        filename: Output filename
        include_agent_signals: Include agent signal columns
        include_temporal_metrics: Include temporal metrics columns
    
    Returns:
        Path to generated CSV file
    """
    output_path = EXPORT_DIR / filename
    
    logger.info(f"Generating CSV export: {filename}")
    
    if not data:
        # Create empty CSV with headers
        headers = get_export_columns(include_agent_signals, include_temporal_metrics)
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
        return output_path
    
    # Convert to DataFrame for easier manipulation
    df = pd.DataFrame(data)
    
    # Select columns based on options
    columns = get_export_columns(include_agent_signals, include_temporal_metrics)
    
    # Filter to available columns
    available_columns = [col for col in columns if col in df.columns]
    df = df[available_columns]
    
    # Write to CSV
    df.to_csv(output_path, index=False, encoding='utf-8')
    
    logger.info(f"CSV export complete: {len(df)} rows, {len(df.columns)} columns")
    
    return output_path


def generate_excel_export(
    data: List[Dict[str, Any]],
    filename: str,
    include_agent_signals: bool = True,
    include_temporal_metrics: bool = True
) -> Path:
    """
    Generate Excel export file with formatting.
    
    Args:
        data: List of study data dictionaries
        filename: Output filename
        include_agent_signals: Include agent signal columns
        include_temporal_metrics: Include temporal metrics columns
    
    Returns:
        Path to generated Excel file
    """
    output_path = EXPORT_DIR / filename
    
    logger.info(f"Generating Excel export: {filename}")
    
    if not data:
        # Create empty Excel with headers
        headers = get_export_columns(include_agent_signals, include_temporal_metrics)
        df = pd.DataFrame(columns=headers)
        df.to_excel(output_path, index=False, engine='openpyxl')
        return output_path
    
    # Convert to DataFrame
    df = pd.DataFrame(data)
    
    # Select columns
    columns = get_export_columns(include_agent_signals, include_temporal_metrics)
    available_columns = [col for col in columns if col in df.columns]
    df = df[available_columns]
    
    # Write to Excel with formatting
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Study Data', index=False)
        
        # Auto-adjust column widths
        worksheet = writer.sheets['Study Data']
        for idx, col in enumerate(df.columns, 1):
            max_length = max(
                df[col].astype(str).apply(len).max(),
                len(str(col))
            )
            worksheet.column_dimensions[chr(64 + idx)].width = min(max_length + 2, 50)
    
    logger.info(f"Excel export complete: {len(df)} rows, {len(df.columns)} columns")
    
    return output_path


def get_export_columns(
    include_agent_signals: bool = True,
    include_temporal_metrics: bool = True
) -> List[str]:
    """
    Get list of columns to include in export.
    
    Args:
        include_agent_signals: Include agent signal columns
        include_temporal_metrics: Include temporal metrics columns
    
    Returns:
        List of column names
    """
    # Core columns (always included)
    columns = [
        'study_id',
        'study_name',
        'dqi_score',
        'dqi_band',
        'risk_level',  # Added risk_level
        'consensus_risk_level',
        'consensus_risk_score',
        'consensus_confidence',
        'enrollment_actual',
        'enrollment_target',
        'enrollment_rate',
    ]
    
    # Agent signal columns
    if include_agent_signals:
        agent_columns = [
            'safety_risk',
            'safety_confidence',
            'completeness_risk',
            'completeness_confidence',
            'coding_risk',
            'coding_confidence',
            'query_quality_risk',
            'query_quality_confidence',
            'edc_quality_risk',
            'edc_quality_confidence',
            'temporal_drift_risk',
            'temporal_drift_confidence',
            'stability_risk',
            'stability_confidence',
        ]
        columns.extend(agent_columns)
    
    # Temporal metrics columns
    if include_temporal_metrics:
        temporal_columns = [
            'enrollment_velocity',
            'visit_schedule_adherence',
            'data_entry_lag_days',
        ]
        columns.extend(temporal_columns)
    
    # Dimension scores
    dimension_columns = [
        'dimension_safety_score',
        'dimension_completeness_score',
        'dimension_accuracy_score',
        'dimension_timeliness_score',
        'dimension_consistency_score',
        'dimension_compliance_score',
    ]
    columns.extend(dimension_columns)
    
    return columns


def cleanup_old_exports():
    """
    Delete export files older than EXPORT_EXPIRATION_HOURS.
    
    This function is called as a background task after each export.
    """
    try:
        cutoff_time = datetime.now() - timedelta(hours=EXPORT_EXPIRATION_HOURS)
        
        deleted_count = 0
        for file_path in EXPORT_DIR.glob("*"):
            if file_path.is_file():
                file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_mtime < cutoff_time:
                    file_path.unlink()
                    deleted_count += 1
                    logger.debug(f"Deleted old export: {file_path.name}")
        
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old export files")
    
    except Exception as e:
        logger.error(f"Error cleaning up old exports: {e}", exc_info=True)


# ========================================
# API ENDPOINTS
# ========================================

@router.post("/csv", response_model=ExportResponse)
async def export_csv(
    request: ExportRequest,
    background_tasks: BackgroundTasks
) -> ExportResponse:
    """
    Export study data to CSV format.
    
    Args:
        request: Export request parameters
        background_tasks: FastAPI background tasks
    
    Returns:
        Export response with download URL
    """
    try:
        logger.info(f"CSV export requested by user: {request.user_id or 'anonymous'}")
        
        # Get data
        data = get_export_data(request.study_ids)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"c_trust_export_{timestamp}.csv"
        
        # Generate CSV
        output_path = generate_csv_export(
            data,
            filename,
            request.include_agent_signals,
            request.include_temporal_metrics
        )
        
        # Calculate expiration
        expires_at = datetime.now() + timedelta(hours=EXPORT_EXPIRATION_HOURS)
        
        # Schedule cleanup
        background_tasks.add_task(cleanup_old_exports)
        
        # Build response
        response = ExportResponse(
            filename=filename,
            download_url=f"/api/export/download/{filename}",
            expires_at=expires_at.isoformat(),
            row_count=len(data),
            format="csv",
            metadata={
                "generation_timestamp": datetime.now().isoformat(),
                "user_id": request.user_id or "anonymous",
                "applied_filters": request.filters or {},
            }
        )
        
        logger.info(f"CSV export complete: {filename} ({len(data)} rows)")
        
        return response
    
    except Exception as e:
        logger.error(f"CSV export failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.post("/excel", response_model=ExportResponse)
async def export_excel(
    request: ExportRequest,
    background_tasks: BackgroundTasks
) -> ExportResponse:
    """
    Export study data to Excel format.
    
    Args:
        request: Export request parameters
        background_tasks: FastAPI background tasks
    
    Returns:
        Export response with download URL
    """
    try:
        logger.info(f"Excel export requested by user: {request.user_id or 'anonymous'}")
        
        # Get data
        data = get_export_data(request.study_ids)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"c_trust_export_{timestamp}.xlsx"
        
        # Generate Excel
        output_path = generate_excel_export(
            data,
            filename,
            request.include_agent_signals,
            request.include_temporal_metrics
        )
        
        # Calculate expiration
        expires_at = datetime.now() + timedelta(hours=EXPORT_EXPIRATION_HOURS)
        
        # Schedule cleanup
        background_tasks.add_task(cleanup_old_exports)
        
        # Build response
        response = ExportResponse(
            filename=filename,
            download_url=f"/api/export/download/{filename}",
            expires_at=expires_at.isoformat(),
            row_count=len(data),
            format="excel",
            metadata={
                "generation_timestamp": datetime.now().isoformat(),
                "user_id": request.user_id or "anonymous",
                "applied_filters": request.filters or {},
            }
        )
        
        logger.info(f"Excel export complete: {filename} ({len(data)} rows)")
        
        return response
    
    except Exception as e:
        logger.error(f"Excel export failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/download/{filename}")
async def download_export(filename: str):
    """
    Download an export file.
    
    Args:
        filename: Name of the export file
    
    Returns:
        File response for download
    """
    from fastapi.responses import FileResponse
    
    try:
        file_path = EXPORT_DIR / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Export file not found")
        
        # Check if file is expired
        file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
        cutoff_time = datetime.now() - timedelta(hours=EXPORT_EXPIRATION_HOURS)
        
        if file_mtime < cutoff_time:
            file_path.unlink()  # Delete expired file
            raise HTTPException(status_code=410, detail="Export file has expired")
        
        logger.info(f"Downloading export: {filename}")
        
        return FileResponse(
            path=str(file_path),
            filename=filename,
            media_type='application/octet-stream'
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Download failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")
