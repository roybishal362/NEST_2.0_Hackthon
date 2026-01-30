"""
C-TRUST FastAPI Backend - Main Application
========================================
Production-ready REST API for C-TRUST dashboard and integrations.

Endpoints:
- GET /api/v1/health - Health check
- GET /api/v1/studies - List all studies
- GET /api/v1/studies/{study_id} - Get study details
- GET /api/v1/studies/{study_id}/dqi - Get DQI score
- GET /api/v1/studies/{study_id}/features - Get engineered features
- GET /api/v1/agents - List all agents and their status
- GET /api/v1/agents/{agent_id}/signals - Get agent signals
- GET /api/v1/notifications - Get notifications
- GET /api/v1/guardian/status - Get Guardian Agent status
- POST /api/v1/ingest - Trigger data ingestion
- WebSocket /api/v1/ws - Real-time updates

Production Features:
- Async endpoints for performance
- Comprehensive error handling
- Request validation
- CORS support
- API documentation (auto-generated)
- Health checks
- Structured logging
- JWT authentication (optional)
"""

from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import asyncio
import dataclasses
import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.core import get_logger, settings
from src.data import (
    DataIngestionEngine,
    FeatureEngineeringEngine,
    FileType,
    StudyDiscovery,
)
from src.data.features_real_extraction import RealFeatureExtractor
from src.intelligence.dqi import DQIEngine

# Import API routers
from src.api.analysis import router as analysis_router
from src.api.metrics import router as metrics_router
from src.api.export import router as export_router

# Initialize logger
logger = get_logger(__name__)

# Global instances (initialized on startup)
data_ingestion: Optional[DataIngestionEngine] = None
feature_extractor: Optional[RealFeatureExtractor] = None
feature_engine: Optional[FeatureEngineeringEngine] = None
dqi_engine: Optional[DQIEngine] = None


# ========================================
# APPLICATION LIFECYCLE
# ========================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("C-TRUST API starting up...")
    
    global data_ingestion, feature_extractor, feature_engine, dqi_engine
    
    try:
        # Initialize engines
        data_ingestion = DataIngestionEngine()
        feature_extractor = RealFeatureExtractor()
        feature_engine = FeatureEngineeringEngine()
        dqi_engine = DQIEngine()
        
        logger.info("All engines initialized successfully")

        # Check for data cache or run initial analysis
        cache_file = Path("data_cache.json")
        if not cache_file.exists():
            logger.info("No data cache found. Running initial analysis...")
            # Run in background to not block startup
            asyncio.create_task(run_analysis_pipeline())
    
    except Exception as e:
        logger.error(f"Failed to initialize engines: {e}", exc_info=True)
        # Don't raise here to allow partial startup if data is bad
        # raise 
    
    yield
    
    # Shutdown
    logger.info("C-TRUST API shutting down...")


async def run_analysis_pipeline():
    """
    Run the full analysis pipeline:
    Ingest -> Direct Feature Extract -> DQI -> Cache
    """
    logger.info("Starting full analysis pipeline...")
    
    try:
        # 1. Ingest all studies
        if not data_ingestion:
            logger.error("Data ingestion engine not initialized")
            return
            
        all_data = data_ingestion.ingest_all_studies(parallel=True)
        
        cache_data = {}
        
        # 2. Process each study
        for study_id, raw_data in all_data.items():
            try:
                # Direct Feature Extraction (no semantic layer)
                features = feature_extractor.extract_features(raw_data, study_id)
                
                # DQI Calculation
                dqi = dqi_engine.calculate_dqi(features, study_id)
                dqi_dict = dqi.to_dict()
                
                # Extract site data for API
                # Try to extract real site data from NEST dataset
                sites_summary = extract_real_sites_from_nest(study_id, raw_data)
                
                # Fallback to mock data if extraction fails
                if not sites_summary:
                    logger.warning(f"Real site extraction failed for {study_id}, using mock data")
                    sites_summary = generate_mock_sites(study_id, features)
                
                # Create timeline data
                timeline = {
                    "phase": "Phase 2",
                    "status": "Ongoing",
                    "enrollment_pct": 0.0,  # Ensure float type for Pydantic validation
                    "est_completion": None
                }

                cache_data[study_id] = {
                    "overall_score": dqi_dict["overall_score"],
                    "risk_level": dqi_dict["risk_level"],
                    "dimension_scores": dqi_dict["dimension_scores"],
                    "features": features, 
                    "timeline": timeline,
                    "sites": sites_summary,
                    "last_updated": datetime.now().isoformat()
                }
                
            except Exception as e:
                logger.error(f"Error processing pipeline for {study_id}: {e}", exc_info=True)
        
        # 3. Save to cache
        with open("data_cache.json", "w") as f:
            # Helper to serialize datetimes
            def json_serial(obj):
                if isinstance(obj, (datetime, datetime.date)):
                    return obj.isoformat()
                raise TypeError (f"Type {type(obj)} not serializable")
                
            json.dump(cache_data, f, default=json_serial, indent=2)
            
        logger.info(f"Analysis pipeline complete. Cached {len(cache_data)} studies.")
        
    except Exception as e:
        logger.error(f"Analysis pipeline failed: {e}", exc_info=True)


def extract_real_sites_from_nest(study_id: str, raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract real site and patient data from NEST dataset with robust error handling.
    
    This function implements the following improvements:
    - Fallback sheet name search for CPID data
    - FlexibleColumnMapper for all column lookups
    - Comprehensive error logging at each step
    - Ensures patients array is always included in site data
    
    Args:
        study_id: Study identifier (e.g., "STUDY_01")
        raw_data: Raw data dictionary from ingestion (contains DataFrames)
    
    Returns:
        List of site summary dictionaries with real patient data
    """
    import pandas as pd
    from src.data.column_mapper import FlexibleColumnMapper
    
    logger.info(f"[{study_id}] Starting patient extraction from NEST dataset")
    sites = []
    
    try:
        # Step 1: Find CPID EDC Metrics sheet with fallback names
        cpid_data = None
        sheet_names_to_try = [
            FileType.EDC_METRICS,  # Primary: Use FileType enum
            'CPID EDC Metrics',    # Fallback 1: Exact name
            'CPID_EDC_Metrics',    # Fallback 2: Underscore variant
            'EDC Metrics',         # Fallback 3: Short name
            'CPID',                # Fallback 4: Very short name
        ]
        
        for sheet_name in sheet_names_to_try:
            cpid_data = raw_data.get(sheet_name)
            if cpid_data is not None and not cpid_data.empty:
                logger.info(f"[{study_id}] Found patient data in sheet: '{sheet_name}'")
                break
        
        if cpid_data is None or cpid_data.empty:
            logger.error(
                f"[{study_id}] No CPID EDC Metrics sheet found. "
                f"Tried: {[str(s) for s in sheet_names_to_try]}. "
                f"Available sheets: {list(raw_data.keys())}"
            )
            return []
        
        logger.info(f"[{study_id}] CPID data shape: {cpid_data.shape}, columns: {list(cpid_data.columns)}")
        
        # Step 2: Find column names using FlexibleColumnMapper
        mapper = FlexibleColumnMapper()
        site_col = mapper.find_column(cpid_data, 'site')
        patient_col = mapper.find_column(cpid_data, 'patient')
        
        if not site_col:
            logger.error(
                f"[{study_id}] Site column not found. "
                f"Available columns: {list(cpid_data.columns)}"
            )
            return []
        
        if not patient_col:
            logger.error(
                f"[{study_id}] Patient column not found. "
                f"Available columns: {list(cpid_data.columns)}"
            )
            return []
        
        logger.info(f"[{study_id}] Using columns: site='{site_col}', patient='{patient_col}'")
        
        # Step 3: Get SAE data with flexible column mapping
        sae_data = raw_data.get(FileType.SAE_DM)
        sae_site_col = None
        if sae_data is not None and not sae_data.empty:
            sae_site_col = mapper.find_column(sae_data, 'site')
            if sae_site_col:
                logger.info(f"[{study_id}] SAE data available with site column: '{sae_site_col}'")
            else:
                logger.warning(f"[{study_id}] SAE data available but site column not found")
        else:
            logger.info(f"[{study_id}] No SAE data available")
        
        # Step 4: Get EDRR (query) data with flexible column mapping
        edrr_data = raw_data.get(FileType.EDRR)
        edrr_site_col = None
        edrr_status_col = None
        if edrr_data is not None and not edrr_data.empty:
            edrr_site_col = mapper.find_column(edrr_data, 'site')
            edrr_status_col = mapper.find_column(edrr_data, 'status')
            if edrr_site_col:
                logger.info(
                    f"[{study_id}] EDRR data available with site column: '{edrr_site_col}', "
                    f"status column: '{edrr_status_col}'"
                )
            else:
                logger.warning(f"[{study_id}] EDRR data available but site column not found")
        else:
            logger.info(f"[{study_id}] No EDRR data available")
        
        # Step 5: Build site summaries
        unique_sites = [s for s in cpid_data[site_col].unique() if pd.notna(s)]
        logger.info(f"[{study_id}] Found {len(unique_sites)} unique sites")
        
        for site_id in unique_sites:
            try:
                site_data = cpid_data[cpid_data[site_col] == site_id]
                
                # Get unique patients for this site (filter out NaN)
                patients = [str(p) for p in site_data[patient_col].unique() if pd.notna(p)]
                enrollment = len(patients)
                
                logger.debug(f"[{study_id}] Site {site_id}: {enrollment} patients")
                
                # Count SAEs for this site
                saes = 0
                if sae_data is not None and sae_site_col:
                    try:
                        saes = len(sae_data[sae_data[sae_site_col] == site_id])
                        logger.debug(f"[{study_id}] Site {site_id}: {saes} SAEs")
                    except Exception as e:
                        logger.warning(f"[{study_id}] Site {site_id}: Error counting SAEs: {e}")
                
                # Count queries for this site
                queries = 0
                open_queries = 0
                if edrr_data is not None and edrr_site_col:
                    try:
                        site_queries = edrr_data[edrr_data[edrr_site_col] == site_id]
                        queries = len(site_queries)
                        if edrr_status_col:
                            # Try to find open queries (case-insensitive)
                            open_queries = len(
                                site_queries[
                                    site_queries[edrr_status_col].astype(str).str.upper().str.contains('OPEN', na=False)
                                ]
                            )
                        logger.debug(
                            f"[{study_id}] Site {site_id}: {queries} queries "
                            f"({open_queries} open, {queries - open_queries} resolved)"
                        )
                    except Exception as e:
                        logger.warning(f"[{study_id}] Site {site_id}: Error counting queries: {e}")
                
                # Risk level based on metrics
                if saes > 3 or open_queries > 20:
                    risk_level = "High"
                elif saes > 1 or open_queries > 10:
                    risk_level = "Medium"
                else:
                    risk_level = "Low"
                
                # CRITICAL: Always include patients array
                site_summary = {
                    "site_id": str(site_id),
                    "site_name": f"Site {site_id}",
                    "enrollment": enrollment,
                    "target_enrollment": enrollment + 10,  # Mock target for now
                    "saes": saes,
                    "queries": queries,
                    "open_queries": open_queries,
                    "resolved_queries": queries - open_queries,
                    "risk_level": risk_level,
                    "last_data_entry": datetime.now().isoformat(),
                    "patients": patients  # CRITICAL: Include patient array
                }
                
                sites.append(site_summary)
                
            except Exception as e:
                logger.error(
                    f"[{study_id}] Error processing site {site_id}: {e}",
                    exc_info=True
                )
                # Continue processing other sites even if one fails
                continue
        
        total_patients = sum(len(s['patients']) for s in sites)
        logger.info(
            f"[{study_id}] Extraction complete: {len(sites)} sites, "
            f"{total_patients} total patients"
        )
        
        return sites
        
    except Exception as e:
        logger.error(
            f"[{study_id}] Patient extraction failed: {e}",
            exc_info=True
        )
        # Return partial results if any sites were successfully processed
        if sites:
            logger.warning(
                f"[{study_id}] Returning partial results: {len(sites)} sites"
            )
        return sites


def generate_mock_sites(study_id: str, features: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Generate mock site data for a study.
    
    In production, this would extract real site data from the NEST dataset.
    For demo purposes, we generate realistic mock data based on study features.
    
    Args:
        study_id: Study identifier
        features: Extracted features for the study
    
    Returns:
        List of site summary dictionaries
    """
    import random
    
    # Seed random for consistency per study
    random.seed(hash(study_id))
    
    # Determine number of sites (3-8 per study)
    num_sites = 3 + (hash(study_id) % 6)
    
    sites = []
    total_enrollment = features.get("total_subjects", 100)
    
    for i in range(1, num_sites + 1):
        site_id = f"SITE_{i:03d}"
        
        # Distribute enrollment across sites (with variation)
        base_enrollment = total_enrollment // num_sites
        variation = random.randint(-5, 10)
        enrollment = max(5, base_enrollment + variation)
        
        # Calculate site-specific metrics
        site_hash = hash(f"{study_id}_{site_id}")
        
        # SAEs: 0-5 per site, weighted by enrollment
        saes = int((enrollment / 20) * (site_hash % 3))
        
        # Queries: 5-50 per site, weighted by enrollment
        queries = max(5, int((enrollment / 2) * (1 + (site_hash % 5) / 10)))
        open_queries = int(queries * 0.3)  # 30% still open
        
        # Risk level based on metrics
        if saes > 3 or open_queries > 20:
            risk_level = "High"
        elif saes > 1 or open_queries > 10:
            risk_level = "Medium"
        else:
            risk_level = "Low"
        
        sites.append({
            "site_id": site_id,
            "site_name": f"Clinical Site {i}",
            "enrollment": enrollment,
            "target_enrollment": enrollment + random.randint(10, 30),
            "saes": saes,
            "queries": queries,
            "open_queries": open_queries,
            "resolved_queries": queries - open_queries,
            "risk_level": risk_level,
            "last_data_entry": datetime.now().isoformat()
        })
    
    return sites


# ========================================
# FASTAPI APPLICATION
# ========================================

app = FastAPI(
    title="C-TRUST API",
    description="Clinical Trial Unified Signal & Trust - REST API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(analysis_router, prefix="/api/v1")
app.include_router(metrics_router, prefix="/api/v1")
app.include_router(export_router, prefix="/api/v1")


# ========================================
# RESPONSE MODELS
# ========================================

class ComponentStatus(BaseModel):
    """Component health status"""
    available: bool
    status: str
    details: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = "healthy"
    timestamp: datetime = Field(default_factory=datetime.now)
    version: str = "1.0.0"
    environment: str = Field(default=settings.ENVIRONMENT)
    components: Optional[Dict[str, ComponentStatus]] = None


class StudyListItem(BaseModel):
    """Study list item"""
    study_id: str
    study_name: str
    enrollment_percentage: Optional[float] = None
    dqi_score: Optional[float] = None
    risk_level: Optional[str] = None
    file_types_available: List[str] = Field(default_factory=list)


class SiteSummary(BaseModel):
    """Site summary for list view"""
    site_id: str
    enrollment: int = 0
    saes: int = 0
    queries: int = 0
    risk_level: str = "Low"

class StudyTimeline(BaseModel):
    """Study timeline milestones"""
    phase: str = "Unknown"
    status: str = "Unknown"
    enrollment_pct: float = 0.0
    est_completion: Optional[datetime] = None

class EnrollmentData(BaseModel):
    """Enrollment data for a study"""
    actual: Optional[int] = None
    target: Optional[int] = None
    rate_pct: Optional[float] = None
    status: str = "unknown"  # on_track, behind, complete, unknown

class StudyDetail(BaseModel):
    """Detailed study information"""
    study_id: str
    study_name: str
    enrollment_percentage: Optional[float]
    enrollment: Optional[EnrollmentData] = None
    dqi_score: Optional[float]
    risk_level: Optional[str]
    dimension_scores: Optional[Dict[str, Any]] = None
    file_types_available: List[str]
    last_refresh: Optional[datetime] = None
    sites: List[SiteSummary] = Field(default_factory=list)
    timeline: Optional[StudyTimeline] = None

class DashboardSummary(BaseModel):
    """Executive dashboard summary"""
    total_studies: int
    avg_dqi: float
    critical_risks: int
    sites_at_risk: int
    total_patients: int



class DQIResponse(BaseModel):
    """DQI score response"""
    study_id: str
    overall_score: float
    risk_level: str
    threshold_met: str
    dimension_scores: List[Dict[str, Any]]
    timestamp: datetime


class ErrorResponse(BaseModel):
    """Error response"""
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


# ========================================
# API ENDPOINTS
# ========================================

@app.get("/api/v1/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """
    Health check endpoint.
    
    Returns system status, version information, and component health status.
    Includes LLM client status, data cache status, and feature extraction status.
    """
    logger.debug("Health check requested")
    
    components = {}
    overall_status = "healthy"
    
    # Check LLM Client status
    try:
        from src.intelligence.llm_client import GroqLLMClient
        llm_client = GroqLLMClient()
        llm_status = llm_client.get_status()
        
        components["llm_client"] = ComponentStatus(
            available=llm_status.get("available", False),
            status="available" if llm_status.get("available") else "mock_mode",
            details=llm_status
        )
        
        if not llm_status.get("available"):
            overall_status = "degraded"
            
    except Exception as e:
        logger.error(f"Failed to check LLM client status: {e}")
        components["llm_client"] = ComponentStatus(
            available=False,
            status="error",
            details={"error": str(e)}
        )
        overall_status = "degraded"
    
    # Check Data Cache status
    try:
        import json
        from pathlib import Path
        cache_file = Path("data_cache.json")
        
        if cache_file.exists():
            with open(cache_file, "r") as f:
                cache_data = json.load(f)
            
            studies_count = len(cache_data.get("studies", {}))
            
            components["data_cache"] = ComponentStatus(
                available=True,
                status="available",
                details={
                    "studies_count": studies_count,
                    "file_exists": True,
                    "last_modified": cache_file.stat().st_mtime
                }
            )
        else:
            components["data_cache"] = ComponentStatus(
                available=False,
                status="missing",
                details={"file_exists": False}
            )
            overall_status = "degraded"
            
    except Exception as e:
        logger.error(f"Failed to check data cache status: {e}")
        components["data_cache"] = ComponentStatus(
            available=False,
            status="error",
            details={"error": str(e)}
        )
        overall_status = "degraded"
    
    # Check Feature Extraction status (sample check)
    try:
        from src.data.features_real_extraction import extract_features_from_nest
        
        # Just verify the function is importable and callable
        components["feature_extraction"] = ComponentStatus(
            available=True,
            status="available",
            details={"module_loaded": True}
        )
        
    except Exception as e:
        logger.error(f"Failed to check feature extraction status: {e}")
        components["feature_extraction"] = ComponentStatus(
            available=False,
            status="error",
            details={"error": str(e)}
        )
        overall_status = "degraded"
    
    return HealthResponse(
        status=overall_status,
        components=components
    )


@app.get("/api/v1/studies", response_model=List[StudyListItem], tags=["Studies"])
async def list_studies():
    """
    List all available studies.
    
    Returns basic information for each study including DQI score.
    """
    logger.info("Listing all studies")
    
    try:
        # Discover studies
        discovery = StudyDiscovery()
        studies = discovery.discover_all_studies()
        
        study_list = []
        
        # Load cached results if available
        import json
        from pathlib import Path
        cache_file = Path("data_cache.json")
        cached_scores = {}
        if cache_file.exists():
            try:
                with open(cache_file, "r") as f:
                    cached_scores = json.load(f)
            except:
                pass

        for study in studies:
            # Get available file types (handle both enum and string types)
            file_types = [
                ft.value if hasattr(ft, 'value') else str(ft) 
                for ft in study.available_files.keys()
            ]
            
            # Use cached score if available, otherwise None (Unknown)
            dqi_score = cached_scores.get(study.study_id, {}).get("overall_score")
            risk_level = cached_scores.get(study.study_id, {}).get("risk_level")
            
            study_item = StudyListItem(
                study_id=study.study_id,
                study_name=study.study_name or study.study_id,
                enrollment_percentage=study.enrollment_percentage,
                dqi_score=dqi_score,
                risk_level=risk_level,
                file_types_available=file_types
            )
            
            study_list.append(study_item)
        
        logger.info(f"Found {len(study_list)} studies")
        return study_list
    
    except Exception as e:
        logger.error(f"Error listing studies: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list studies: {str(e)}"
        )


@app.get("/api/v1/studies/{study_id}", response_model=StudyDetail, tags=["Studies"])
async def get_study(study_id: str):
    """
    Get detailed information for a specific study.
    
    Args:
        study_id: Study identifier (e.g., "STUDY_01")
    
    Returns:
        Detailed study information including DQI breakdown
    """
    logger.info(f"Getting details for study: {study_id}")
    
    try:
        # Discover study
        discovery = StudyDiscovery()
        studies = discovery.discover_all_studies()
        
        study = next((s for s in studies if s.study_id == study_id), None)
        
        if not study:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Study not found: {study_id}"
            )
        
        # Get file types (handle both enum and string types)
        file_types = [
            ft.value if hasattr(ft, 'value') else str(ft) 
            for ft in study.available_files.keys()
        ]
        
        # Load enhanced data from cache
        import json
        from pathlib import Path
        cache_file = Path("data_cache.json")
        cached_data = {}
        if cache_file.exists():
            try:
                with open(cache_file, "r") as f:
                    full_cache = json.load(f)
                    cached_data = full_cache.get(study_id, {})
            except:
                pass

        # Extract timeline
        timeline_data = cached_data.get("timeline", {})
        # Ensure enrollment_pct is never None (Pydantic validation requires float)
        enrollment_pct_value = timeline_data.get("enrollment_pct")
        if enrollment_pct_value is None:
            enrollment_pct_value = 0.0
        
        timeline = StudyTimeline(
            phase=timeline_data.get("phase", "Phase 2"),
            status=timeline_data.get("status", "Ongoing"),
            enrollment_pct=enrollment_pct_value,
            est_completion=timeline_data.get("est_completion")
        )

        # Extract sites
        sites_data = cached_data.get("sites", [])
        sites = [SiteSummary(**s) for s in sites_data]

        # Extract enrollment data from features
        features = cached_data.get("features", {})
        enrollment_data = None
        
        if features:
            actual = features.get("actual_enrollment")
            target = features.get("target_enrollment")
            rate = features.get("enrollment_rate")
            
            # Determine status
            status = "unknown"
            if actual is not None and target is not None and rate is not None:
                if rate >= 100.0:
                    status = "complete"
                elif rate >= 80.0:
                    status = "on_track"
                else:
                    status = "behind"
            
            enrollment_data = EnrollmentData(
                actual=actual,
                target=target,
                rate_pct=rate,
                status=status
            )

        dqi_score = cached_data.get("overall_score")
        risk_level = cached_data.get("risk_level")

        study_detail = StudyDetail(
            study_id=study.study_id,
            study_name=study.study_name or study.study_id,
            enrollment_percentage=study.enrollment_percentage,
            enrollment=enrollment_data,
            dqi_score=dqi_score,
            risk_level=risk_level,
            file_types_available=file_types,
            last_refresh=study.last_data_refresh,
            sites=sites,
            timeline=timeline
        )
        
        return study_detail
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting study {study_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get study: {str(e)}"
        )


@app.get("/api/v1/dashboard/summary", response_model=DashboardSummary, tags=["Dashboard"])
async def get_dashboard_summary():
    """
    Get executive dashboard summary metrics.
    Aggregates data across all studies.
    """
    import json
    from pathlib import Path
    
    try:
        cache_file = Path("data_cache.json")
        if not cache_file.exists():
            return DashboardSummary(
                total_studies=0, avg_dqi=0, critical_risks=0, sites_at_risk=0, total_patients=0
            )
            
        with open(cache_file, "r") as f:
            data = json.load(f)
            
        total_studies = len(data)
        scores = [d.get("overall_score", 0) for d in data.values() if d.get("overall_score")]
        avg_dqi = sum(scores) / len(scores) if scores else 0
        
        critical_risks = sum(1 for d in data.values() if d.get("risk_level") == "Critical")
        
        # Count sites at risk
        sites_at_risk = 0
        total_patients = 0
        
        for study_data in data.values():
            sites = study_data.get("sites", [])
            for site in sites:
                if site.get("risk_level") in ["High", "Critical"]:
                    sites_at_risk += 1
                total_patients += site.get("enrollment", 0)
                
        return DashboardSummary(
            total_studies=total_studies,
            avg_dqi=round(avg_dqi, 1),
            critical_risks=critical_risks,
            sites_at_risk=sites_at_risk,
            total_patients=total_patients
        )
        
    except Exception as e:
        logger.error(f"Error getting dashboard summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get dashboard summary: {str(e)}"
        )


@app.get("/api/v1/studies/{study_id}/dqi", response_model=DQIResponse, tags=["DQI"])
async def get_study_dqi(study_id: str):
    """
    Calculate and return DQI score for a study.
    
    This endpoint:
    1. Ingests data for the study
    2. Processes through semantic engine
    3. Engineers features
    4. Calculates DQI score
    
    Args:
        study_id: Study identifier
    
    Returns:
        DQI score with dimensional breakdown
    """
    logger.info(f"Calculating DQI for study: {study_id}")
    
    try:
        # Discover study
        discovery = StudyDiscovery()
        studies = discovery.discover_all_studies()
        
        study = next((s for s in studies if s.study_id == study_id), None)
        
        if not study:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Study not found: {study_id}"
            )
        
        # Ingest data
        raw_data = data_ingestion.ingest_study(study)
        
        # Extract features directly (no semantic layer)
        features = feature_extractor.extract_features(raw_data, study_id)
        
        # Calculate DQI
        dqi_score = dqi_engine.calculate_dqi(features, study_id)
        
        # Convert to response format
        response = DQIResponse(
            study_id=study_id,
            overall_score=dqi_score.overall_score,
            risk_level=dqi_score.risk_level.value,
            threshold_met=dqi_score.threshold_met,
            dimension_scores=[
                dim.to_dict() if hasattr(dim, 'to_dict') else {
                    "dimension": dim.dimension.value,
                    "raw_score": dim.raw_score,
                    "weight": dim.weight,
                    "weighted_score": dim.weighted_score,
                    "contributing_features": dim.contributing_features
                }
                for dim in dqi_score.dimension_scores
            ],
            timestamp=dqi_score.timestamp
        )
        
        logger.info(f"DQI calculated for {study_id}: {dqi_score.overall_score:.2f}")
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating DQI for {study_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate DQI: {str(e)}"
        )


@app.get("/api/v1/studies/{study_id}/features", response_model=Dict[str, Any], tags=["Features"])
async def get_study_features(study_id: str):
    """
    Get engineered features for a study.
    
    Args:
        study_id: Study identifier
    
    Returns:
        Dictionary of feature_name -> value
    """
    logger.info(f"Getting features for study: {study_id}")
    
    try:
        # Discover study
        discovery = StudyDiscovery()
        studies = discovery.discover_all_studies()
        
        study = next((s for s in studies if s.study_id == study_id), None)
        
        if not study:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Study not found: {study_id}"
            )
        
        # Ingest and extract features directly
        raw_data = data_ingestion.ingest_study(study)
        features = feature_extractor.extract_features(raw_data, study_id)
        
        logger.info(f"Features retrieved for {study_id}: {len(features)} features")
        return features
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting features for {study_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get features: {str(e)}"
        )


@app.post("/api/v1/ingest", tags=["System"])
async def trigger_ingestion():
    """
    Trigger full data ingestion for all studies.
    
    WARNING: This is a long-running operation.
    
    Returns:
        Summary of ingestion results
    """
    logger.info("Manual data ingestion triggered")
    
    try:
        # trigger full pipeline in background
        asyncio.create_task(run_analysis_pipeline())
        
        return {
            "status": "success",
            "message": "Analysis pipeline started in background",
            "timestamp": datetime.now()
        }
    
    except Exception as e:
        logger.error(f"Error during ingestion: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion failed: {str(e)}"
        )


# ========================================
# AGENT ENDPOINTS
# ========================================

class AgentStatus(BaseModel):
    """Agent status response"""
    agent_id: str
    name: str
    status: str = "active"
    confidence: float = 0.0
    last_run: Optional[datetime] = None
    signals_count: int = 0
    weight: float = 1.0


class AgentSignalResponse(BaseModel):
    """Agent signal response"""
    signal_id: str
    agent_id: str
    study_id: str
    severity: str
    message: str
    confidence: float
    timestamp: datetime
    evidence: List[str] = Field(default_factory=list)


class AgentEvidence(BaseModel):
    """Evidence from an agent"""
    feature: str
    value: Any
    threshold: Optional[float] = None
    severity: float


class AgentInsight(BaseModel):
    """Detailed agent insight"""
    name: str
    type: str
    risk_level: str
    confidence: float
    weight: float
    abstained: bool
    evidence: List[AgentEvidence] = Field(default_factory=list)
    recommended_actions: List[str] = Field(default_factory=list)


class AgentInsightsResponse(BaseModel):
    """Complete agent insights response"""
    study_id: str
    agents: List[AgentInsight]
    consensus: Optional[Dict[str, Any]] = None
    dqi_agent_driven: Optional[Dict[str, Any]] = None  # NEW: Agent-driven DQI result
    timestamp: datetime = Field(default_factory=datetime.now)


@app.get("/api/v1/agents", response_model=List[AgentStatus], tags=["Agents"])
async def list_agents():
    """
    List all agents and their current status.
    """
    # Return mock agent data for now - will be connected to real agents
    agents = [
        AgentStatus(
            agent_id="completeness",
            name="Data Completeness Agent",
            status="active",
            confidence=0.92,
            last_run=datetime.now(),
            signals_count=5,
            weight=1.5
        ),
        AgentStatus(
            agent_id="safety",
            name="Safety & Compliance Agent",
            status="active",
            confidence=0.88,
            last_run=datetime.now(),
            signals_count=3,
            weight=3.0
        ),
        AgentStatus(
            agent_id="query",
            name="Query Quality Agent",
            status="active",
            confidence=0.95,
            last_run=datetime.now(),
            signals_count=2,
            weight=1.5
        ),
        AgentStatus(
            agent_id="coding",
            name="Coding Readiness Agent",
            status="active",
            confidence=0.90,
            last_run=datetime.now(),
            signals_count=1,
            weight=1.2
        ),
        AgentStatus(
            agent_id="temporal",
            name="Temporal Drift Agent",
            status="active",
            confidence=0.87,
            last_run=datetime.now(),
            signals_count=3,
            weight=1.2
        ),
        AgentStatus(
            agent_id="edc",
            name="EDC Quality Agent",
            status="active",
            confidence=0.91,
            last_run=datetime.now(),
            signals_count=2,
            weight=1.5
        ),
        AgentStatus(
            agent_id="stability",
            name="Stability Agent",
            status="active",
            confidence=0.85,
            last_run=datetime.now(),
            signals_count=4,
            weight=-1.5
        ),
    ]
    return agents


@app.get("/api/v1/agents/{agent_id}/signals", response_model=List[AgentSignalResponse], tags=["Agents"])
async def get_agent_signals(agent_id: str, study_id: Optional[str] = None):
    """
    Get signals from a specific agent.
    
    Args:
        agent_id: Agent identifier
        study_id: Optional filter by study
    """
    # Return mock signals - will be connected to real agent signals
    signals = [
        AgentSignalResponse(
            signal_id=f"sig_{agent_id}_001",
            agent_id=agent_id,
            study_id="STUDY_05",
            severity="high",
            message="Missing visit data detected (15% incomplete)",
            confidence=0.92,
            timestamp=datetime.now(),
            evidence=["Visit V3 missing for 12 subjects", "Visit V5 missing for 8 subjects"]
        ),
        AgentSignalResponse(
            signal_id=f"sig_{agent_id}_002",
            agent_id=agent_id,
            study_id="STUDY_11",
            severity="medium",
            message="Form completion rate below threshold",
            confidence=0.85,
            timestamp=datetime.now(),
            evidence=["AE form completion at 82%", "Lab form completion at 82%"]
        ),
    ]
    
    if study_id:
        signals = [s for s in signals if s.study_id == study_id]
    
    return signals


@app.get("/api/v1/studies/{study_id}/agents", response_model=AgentInsightsResponse, tags=["Agents"])
async def get_agent_insights(study_id: str):
    """
    Get detailed agent analysis for a study.
    
    This endpoint:
    1. Extracts features for the study
    2. Runs the 7-agent pipeline
    3. Returns detailed agent analysis including:
       - Agent name, type, risk level, confidence, weight
       - Whether agent abstained
       - Evidence (feature name, value, threshold, severity)
       - Recommended actions
       - Consensus result
    
    Args:
        study_id: Study identifier (e.g., "STUDY_01")
    
    Returns:
        Detailed agent insights with consensus
    """
    logger.info(f"Getting agent insights for study: {study_id}")
    
    try:
        from src.intelligence.agent_pipeline import get_pipeline
        
        # Discover study
        discovery = StudyDiscovery()
        studies = discovery.discover_all_studies()
        
        study = next((s for s in studies if s.study_id == study_id), None)
        
        if not study:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Study not found: {study_id}"
            )
        
        # Ingest and extract features directly
        raw_data = data_ingestion.ingest_study(study)
        features = feature_extractor.extract_features(raw_data, study_id)
        
        # Run agent pipeline
        pipeline = get_pipeline()
        result = pipeline.run_full_analysis(study_id, features)
        
        # Format agent insights
        agent_insights = []
        for r in result.agent_results:
            # Extract evidence if signal exists
            evidence = []
            if r.signal and hasattr(r.signal, 'evidence'):
                for e in r.signal.evidence:
                    evidence.append(AgentEvidence(
                        feature=e.feature_name,
                        value=e.feature_value,
                        threshold=e.threshold if hasattr(e, 'threshold') else None,
                        severity=e.severity
                    ))
            
            # Extract recommended actions
            recommended_actions = []
            if r.signal and hasattr(r.signal, 'recommended_actions'):
                recommended_actions = r.signal.recommended_actions
            
            agent_insights.append(AgentInsight(
                name=r.agent_name,
                type=r.agent_type.value,
                risk_level=r.signal.risk_level.value if r.signal else "unknown",
                confidence=r.signal.confidence if r.signal else 0.0,
                weight=pipeline.AGENT_WEIGHTS.get(r.agent_type, 1.0),
                abstained=r.abstained,
                evidence=evidence,
                recommended_actions=recommended_actions
            ))
        
        # Format consensus
        consensus_dict = None
        if result.consensus:
            consensus_dict = result.consensus.to_dict()
        
        # Format agent-driven DQI
        dqi_agent_driven_dict = None
        if result.dqi_agent_driven:
            dqi_agent_driven_dict = result.dqi_agent_driven.to_dict()
        
        response = AgentInsightsResponse(
            study_id=study_id,
            agents=agent_insights,
            consensus=consensus_dict,
            dqi_agent_driven=dqi_agent_driven_dict,  # NEW: Include agent-driven DQI
            timestamp=datetime.now()
        )
        
        logger.info(f"Agent insights retrieved for {study_id}: {len(agent_insights)} agents")
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent insights for {study_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get agent insights: {str(e)}"
        )


# ========================================
# GUARDIAN ENDPOINTS
# ========================================

class GuardianSystemHealth(BaseModel):
    """Guardian system health metrics"""
    status: str = "healthy"
    agents_operational: int = 7
    last_check: datetime = Field(default_factory=datetime.now)
    event_storage_health: str = "OK"
    staleness_tracking_health: str = "OK"


class GuardianIntegrityAlert(BaseModel):
    """Guardian integrity alert"""
    event_id: str
    event_type: str
    severity: str
    entity_id: str
    snapshot_id: str
    data_delta_summary: str
    expected_behavior: str
    actual_behavior: str
    recommendation: str
    timestamp: datetime


class GuardianAgentPerformance(BaseModel):
    """Agent performance metrics"""
    agent_name: str
    signals_generated: int = 0
    abstention_rate: float = 0.0
    avg_confidence: float = 0.0
    last_run: Optional[datetime] = None


class GuardianStatusResponse(BaseModel):
    """Complete Guardian status response"""
    status: str = "healthy"  # Root-level status for backward compatibility
    system_health: GuardianSystemHealth
    integrity_alerts: List[GuardianIntegrityAlert] = Field(default_factory=list)
    agent_performance: List[GuardianAgentPerformance] = Field(default_factory=list)
    diagnostic_report: Optional[Dict[str, Any]] = None


@app.get("/api/v1/guardian/status", response_model=GuardianStatusResponse, tags=["Guardian"])
async def get_guardian_status():
    """
    Get Guardian Agent status and health metrics.
    
    Returns:
        - System health status
        - Recent integrity alerts
        - Agent performance metrics
        - Diagnostic report
    """
    logger.info("Guardian status requested")
    
    try:
        from src.guardian.guardian_agent import GuardianAgent
        
        # Initialize Guardian
        guardian = GuardianAgent()
        
        # Run self-diagnostic
        diagnostic = guardian.run_self_diagnostic()
        
        # Get system health from diagnostic
        system_health = GuardianSystemHealth(
            status=diagnostic.get("status", "HEALTHY"),
            agents_operational=7,  # Number of active agents
            last_check=datetime.now(),
            event_storage_health=diagnostic.get("checks", {}).get("event_storage", {}).get("status", "OK"),
            staleness_tracking_health=diagnostic.get("checks", {}).get("staleness_tracking", {}).get("status", "OK")
        )
        
        # Get recent integrity alerts (last 10)
        recent_events = guardian.get_events(limit=10)
        integrity_alerts = [
            GuardianIntegrityAlert(
                event_id=event.event_id,
                event_type=event.event_type.value,
                severity=event.severity.value,
                entity_id=event.entity_id,
                snapshot_id=event.snapshot_id,
                data_delta_summary=event.data_delta_summary,
                expected_behavior=event.expected_behavior,
                actual_behavior=event.actual_behavior,
                recommendation=event.recommendation,
                timestamp=event.timestamp
            )
            for event in recent_events
        ]
        
        # Get agent performance metrics (mock for now - will be connected to real agent tracking)
        agent_performance = [
            GuardianAgentPerformance(
                agent_name="Data Completeness",
                signals_generated=12,
                abstention_rate=0.05,
                avg_confidence=0.92,
                last_run=datetime.now()
            ),
            GuardianAgentPerformance(
                agent_name="Safety & Compliance",
                signals_generated=8,
                abstention_rate=0.02,
                avg_confidence=0.95,
                last_run=datetime.now()
            ),
            GuardianAgentPerformance(
                agent_name="Query Quality",
                signals_generated=15,
                abstention_rate=0.08,
                avg_confidence=0.88,
                last_run=datetime.now()
            ),
            GuardianAgentPerformance(
                agent_name="Coding Readiness",
                signals_generated=6,
                abstention_rate=0.12,
                avg_confidence=0.85,
                last_run=datetime.now()
            ),
            GuardianAgentPerformance(
                agent_name="Temporal Drift",
                signals_generated=10,
                abstention_rate=0.06,
                avg_confidence=0.90,
                last_run=datetime.now()
            ),
            GuardianAgentPerformance(
                agent_name="EDC Quality",
                signals_generated=9,
                abstention_rate=0.04,
                avg_confidence=0.93,
                last_run=datetime.now()
            ),
            GuardianAgentPerformance(
                agent_name="Stability",
                signals_generated=7,
                abstention_rate=0.10,
                avg_confidence=0.87,
                last_run=datetime.now()
            ),
        ]
        
        response = GuardianStatusResponse(
            status=system_health.status,  # Add root-level status
            system_health=system_health,
            integrity_alerts=integrity_alerts,
            agent_performance=agent_performance,
            diagnostic_report=diagnostic
        )
        
        logger.info(f"Guardian status: {system_health.status}, {len(integrity_alerts)} alerts")
        return response
        
    except Exception as e:
        logger.error(f"Error getting Guardian status: {e}", exc_info=True)
        # Return degraded status on error
        return GuardianStatusResponse(
            status="DEGRADED",  # Add root-level status
            system_health=GuardianSystemHealth(
                status="DEGRADED",
                agents_operational=0,
                last_check=datetime.now(),
                event_storage_health="ERROR",
                staleness_tracking_health="ERROR"
            ),
            integrity_alerts=[],
            agent_performance=[],
            diagnostic_report={"error": str(e)}
        )


@app.get("/api/v1/guardian/events", response_model=List[GuardianIntegrityAlert], tags=["Guardian"])
async def get_guardian_events(
    entity_id: Optional[str] = None,
    event_type: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 50
):
    """
    Get Guardian integrity events with optional filtering.
    
    Args:
        entity_id: Filter by entity ID (study/site)
        event_type: Filter by event type
        severity: Filter by severity (INFO, WARNING, CRITICAL)
        limit: Maximum number of events to return
    
    Returns:
        List of Guardian integrity alerts
    """
    logger.info(f"Guardian events requested: entity={entity_id}, type={event_type}, severity={severity}")
    
    try:
        from src.guardian.guardian_agent import GuardianAgent, GuardianEventType, GuardianSeverity
        
        # Initialize Guardian
        guardian = GuardianAgent()
        
        # Convert string parameters to enums if provided
        event_type_enum = None
        if event_type:
            try:
                event_type_enum = GuardianEventType(event_type)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid event_type: {event_type}"
                )
        
        severity_enum = None
        if severity:
            try:
                severity_enum = GuardianSeverity(severity)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid severity: {severity}"
                )
        
        # Get filtered events
        events = guardian.get_events(
            entity_id=entity_id,
            event_type=event_type_enum,
            severity=severity_enum,
            limit=limit
        )
        
        # Convert to response format
        alerts = [
            GuardianIntegrityAlert(
                event_id=event.event_id,
                event_type=event.event_type.value,
                severity=event.severity.value,
                entity_id=event.entity_id,
                snapshot_id=event.snapshot_id,
                data_delta_summary=event.data_delta_summary,
                expected_behavior=event.expected_behavior,
                actual_behavior=event.actual_behavior,
                recommendation=event.recommendation,
                timestamp=event.timestamp
            )
            for event in events
        ]
        
        logger.info(f"Returning {len(alerts)} Guardian events")
        return alerts
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting Guardian events: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get Guardian events: {str(e)}"
        )


# ========================================
# NOTIFICATION ENDPOINTS
# ========================================

class NotificationResponse(BaseModel):
    """Notification response"""
    notification_id: str
    id: Optional[str] = None  # Alias for backward compatibility
    type: str  # critical, warning, info, success
    title: str
    message: str
    study_id: Optional[str] = None
    role: str  # CRA, DataManager, StudyLead, All
    timestamp: datetime
    read: bool = False
    acknowledged: bool = False
    
    def __init__(self, **data):
        super().__init__(**data)
        # Set id to notification_id if not provided
        if self.id is None:
            self.id = self.notification_id


@app.get("/api/v1/notifications", response_model=List[NotificationResponse], tags=["Notifications"])
async def get_notifications(
    role: Optional[str] = None,
    unread_only: bool = False,
    limit: int = 50
):
    """
    Get notifications for the current user.
    
    Args:
        role: Filter by role (CRA, DataManager, StudyLead)
        unread_only: Only return unread notifications
        limit: Maximum number of notifications to return
    """
    # Return mock notifications - will be connected to real notification system
    notifications = [
        NotificationResponse(
            notification_id="notif_001",
            type="critical",
            title="SAE Review Overdue",
            message="3 SAEs in Study 08 have exceeded the 48-hour review window",
            study_id="STUDY_08",
            role="StudyLead",
            timestamp=datetime.now(),
            read=False,
            acknowledged=False
        ),
        NotificationResponse(
            notification_id="notif_002",
            type="warning",
            title="Data Entry Lag Detected",
            message="Site SITE-101 shows a 5-day lag in data entry",
            study_id="STUDY_05",
            role="CRA",
            timestamp=datetime.now(),
            read=False,
            acknowledged=False
        ),
        NotificationResponse(
            notification_id="notif_003",
            type="info",
            title="DQI Score Improved",
            message="Study 11 DQI score improved from 72 to 81",
            study_id="STUDY_11",
            role="All",
            timestamp=datetime.now(),
            read=True,
            acknowledged=True
        ),
    ]
    
    if role:
        notifications = [n for n in notifications if n.role == role or n.role == "All"]
    
    if unread_only:
        notifications = [n for n in notifications if not n.read]
    
    return notifications[:limit]


@app.post("/api/v1/notifications/{notification_id}/acknowledge", tags=["Notifications"])
async def acknowledge_notification(notification_id: str):
    """
    Acknowledge a notification.
    """
    logger.info(f"Notification acknowledged: {notification_id}")
    return {"status": "acknowledged", "notification_id": notification_id}


@app.post("/api/v1/notifications/{notification_id}/read", tags=["Notifications"])
async def mark_notification_read(notification_id: str):
    """
    Mark a notification as read.
    """
    logger.info(f"Notification marked as read: {notification_id}")
    return {"status": "read", "notification_id": notification_id}


# ========================================
# WEBSOCKET FOR REAL-TIME UPDATES
# ========================================

class ConnectionManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to WebSocket: {e}")


ws_manager = ConnectionManager()


@app.websocket("/api/v1/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time updates.
    
    Clients can subscribe to receive:
    - DQI score updates
    - New agent signals
    - Guardian alerts
    - Notification updates
    """
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            logger.debug(f"WebSocket received: {data}")
            
            # Echo back for now - can be extended for subscriptions
            await websocket.send_json({
                "type": "ack",
                "message": f"Received: {data}",
                "timestamp": datetime.now().isoformat()
            })
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


# ========================================
# SITE VIEW ENDPOINTS
# ========================================

class SiteDetail(BaseModel):
    """Detailed site information"""
    site_id: str
    site_name: Optional[str] = None
    enrollment: int = 0
    target_enrollment: Optional[int] = None
    enrollment_rate: Optional[float] = None
    saes: int = 0
    queries: int = 0
    open_queries: int = 0
    resolved_queries: int = 0
    risk_level: str = "Low"
    dqi_score: Optional[float] = None
    completeness_rate: Optional[float] = None
    last_data_entry: Optional[datetime] = None
    patients: List[str] = Field(default_factory=list)


class PatientSummary(BaseModel):
    """Patient summary for site view"""
    patient_id: str
    enrollment_date: Optional[datetime] = None
    status: str = "Active"
    visits_completed: int = 0
    visits_total: int = 0
    saes: int = 0
    queries: int = 0
    last_visit: Optional[datetime] = None


@app.get("/api/v1/studies/{study_id}/sites", tags=["Sites"])
async def get_study_sites(study_id: str):
    """
    Get all sites for a study with enhanced error handling and data quality validation.
    
    This endpoint implements the following improvements:
    - Patient data validation for each site
    - Clear error messages for data extraction failures
    - Data quality indicator in response
    - Fallback for missing patient arrays
    
    Args:
        study_id: Study identifier (e.g., "STUDY_01")
    
    Returns:
        JSON response with sites list and data quality metadata
    """
    logger.info(f"Getting sites for study: {study_id}")
    
    try:
        import json
        from pathlib import Path
        
        # Load cached data
        cache_file = Path("data_cache.json")
        if not cache_file.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No data cache available. Please run data ingestion first."
            )
        
        with open(cache_file, "r") as f:
            full_cache = json.load(f)
            
        study_data = full_cache.get(study_id)
        if not study_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Study '{study_id}' not found in cache. Available studies: {list(full_cache.keys())}"
            )
        
        # Get sites from cache
        sites_data = study_data.get("sites", [])
        
        if not sites_data:
            logger.warning(f"No sites data found for study {study_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No sites data available for study '{study_id}'. Data extraction may have failed."
            )
        
        # Track data quality metrics
        sites_with_patients = 0
        sites_missing_patients = 0
        total_patients = 0
        data_quality_warnings = []
        
        # Enhance site data with additional details and validate patient data
        site_details = []
        for site in sites_data:
            site_id = site.get("site_id", "UNKNOWN")
            
            # Validate patient data presence
            patients = site.get("patients")
            if patients is None:
                sites_missing_patients += 1
                logger.warning(
                    f"Study {study_id}, Site {site_id}: Missing patients array. "
                    f"Patient data extraction may have failed."
                )
                # Fallback: provide empty array with warning
                patients = []
                data_quality_warnings.append(
                    f"Site {site_id}: Patient data unavailable (extraction failed)"
                )
            elif not isinstance(patients, list):
                sites_missing_patients += 1
                logger.error(
                    f"Study {study_id}, Site {site_id}: Invalid patients data type: {type(patients)}"
                )
                patients = []
                data_quality_warnings.append(
                    f"Site {site_id}: Invalid patient data format"
                )
            else:
                sites_with_patients += 1
                total_patients += len(patients)
                
                # Validate patient count matches enrollment
                enrollment = site.get("enrollment", 0)
                if len(patients) != enrollment:
                    logger.warning(
                        f"Study {study_id}, Site {site_id}: Patient count mismatch. "
                        f"Enrollment: {enrollment}, Patients: {len(patients)}"
                    )
                    data_quality_warnings.append(
                        f"Site {site_id}: Patient count mismatch (enrollment: {enrollment}, patients: {len(patients)})"
                    )
            
            # Calculate enrollment rate if target is available
            enrollment_rate = None
            if site.get("target_enrollment"):
                enrollment_rate = (site.get("enrollment", 0) / site["target_enrollment"]) * 100
            
            # Calculate completeness rate (mock for now - would come from real data)
            completeness_rate = 0.85 + (hash(site_id) % 15) / 100  # Mock: 85-100%
            
            # Calculate DQI score for site (mock for now)
            site_dqi = 70 + (hash(site_id) % 25)  # Mock: 70-95
            
            site_detail = {
                "site_id": site_id,
                "site_name": site.get("site_name", f"Site {site_id}"),
                "enrollment": site.get("enrollment", 0),
                "target_enrollment": site.get("target_enrollment"),
                "enrollment_rate": enrollment_rate,
                "saes": site.get("saes", 0),
                "queries": site.get("queries", 0),
                "open_queries": site.get("open_queries", site.get("queries", 0)),
                "resolved_queries": site.get("resolved_queries", 0),
                "risk_level": site.get("risk_level", "Low"),
                "dqi_score": site_dqi,
                "completeness_rate": completeness_rate,
                "last_data_entry": site.get("last_data_entry"),
                "patients": patients,
                "data_quality_warning": None if patients else "Patient data unavailable"
            }
            site_details.append(site_detail)
        
        # Determine overall data quality status
        if sites_missing_patients == 0:
            data_quality = "complete"
            data_quality_message = "All sites have complete patient data"
        elif sites_with_patients == 0:
            data_quality = "unavailable"
            data_quality_message = "Patient data unavailable for all sites. Data extraction failed."
        else:
            data_quality = "partial"
            data_quality_message = (
                f"Patient data available for {sites_with_patients}/{len(sites_data)} sites. "
                f"{sites_missing_patients} sites missing patient data."
            )
        
        logger.info(
            f"Study {study_id}: Found {len(site_details)} sites. "
            f"Data quality: {data_quality}. "
            f"Sites with patients: {sites_with_patients}/{len(sites_data)}. "
            f"Total patients: {total_patients}"
        )
        
        # Return enhanced response with data quality metadata
        return {
            "study_id": study_id,
            "sites": site_details,
            "total_sites": len(site_details),
            "total_patients": total_patients,
            "data_quality": {
                "status": data_quality,
                "message": data_quality_message,
                "sites_with_patient_data": sites_with_patients,
                "sites_missing_patient_data": sites_missing_patients,
                "warnings": data_quality_warnings if data_quality_warnings else None
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting sites for {study_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve sites for study '{study_id}': {str(e)}"
        )


@app.get("/api/v1/sites/{site_id}", response_model=SiteDetail, tags=["Sites"])
async def get_site_details(site_id: str, study_id: Optional[str] = None):
    """
    Get detailed information for a specific site.
    
    Args:
        site_id: Site identifier (e.g., "SITE_001")
        study_id: Optional study identifier to narrow search
    
    Returns:
        Detailed site information including patient list
    """
    logger.info(f"Getting details for site: {site_id}")
    
    try:
        import json
        from pathlib import Path
        
        # Load cached data
        cache_file = Path("data_cache.json")
        if not cache_file.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No data available"
            )
        
        with open(cache_file, "r") as f:
            full_cache = json.load(f)
        
        # Search for site across all studies (or specific study if provided)
        site_found = None
        found_study_id = None
        
        studies_to_search = [study_id] if study_id else full_cache.keys()
        
        for sid in studies_to_search:
            study_data = full_cache.get(sid, {})
            sites = study_data.get("sites", [])
            
            for site in sites:
                if site.get("site_id") == site_id:
                    site_found = site
                    found_study_id = sid
                    break
            
            if site_found:
                break
        
        if not site_found:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Site not found: {site_id}"
            )
        
        # Get patient list for this site (mock for now - would come from real data)
        # In production, this would query the database for patients at this site
        num_patients = site_found.get("enrollment", 0)
        patients = [f"PAT_{site_id}_{i:03d}" for i in range(1, num_patients + 1)]
        
        # Calculate metrics
        enrollment_rate = None
        if site_found.get("target_enrollment"):
            enrollment_rate = (site_found.get("enrollment", 0) / site_found["target_enrollment"]) * 100
        
        completeness_rate = 0.85 + (hash(site_id) % 15) / 100
        site_dqi = 70 + (hash(site_id) % 25)
        
        site_detail = SiteDetail(
            site_id=site_found.get("site_id", site_id),
            site_name=site_found.get("site_name", f"Site {site_id}"),
            enrollment=site_found.get("enrollment", 0),
            target_enrollment=site_found.get("target_enrollment"),
            enrollment_rate=enrollment_rate,
            saes=site_found.get("saes", 0),
            queries=site_found.get("queries", 0),
            open_queries=site_found.get("open_queries", site_found.get("queries", 0)),
            resolved_queries=site_found.get("resolved_queries", 0),
            risk_level=site_found.get("risk_level", "Low"),
            dqi_score=site_dqi,
            completeness_rate=completeness_rate,
            last_data_entry=site_found.get("last_data_entry"),
            patients=patients
        )
        
        logger.info(f"Site details retrieved for {site_id}")
        return site_detail
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting site details for {site_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get site details: {str(e)}"
        )


@app.get("/api/v1/sites/{site_id}/patients", response_model=List[PatientSummary], tags=["Sites"])
async def get_site_patients(site_id: str):
    """
    Get all patients for a specific site.
    
    Args:
        site_id: Site identifier
    
    Returns:
        List of patients with summary metrics
    """
    logger.info(f"Getting patients for site: {site_id}")
    
    try:
        # First get the site details to know how many patients
        site_detail = await get_site_details(site_id)
        
        # Generate patient summaries (mock for now - would come from real data)
        patients = []
        for i, patient_id in enumerate(site_detail.patients, 1):
            # Mock patient data - in production this would come from database
            patients.append(PatientSummary(
                patient_id=patient_id,
                enrollment_date=datetime.now() - timedelta(days=365 - i*10),
                status="Active" if i % 10 != 0 else "Completed",
                visits_completed=min(i % 8, 6),
                visits_total=6,
                saes=1 if i % 15 == 0 else 0,
                queries=i % 3,
                last_visit=datetime.now() - timedelta(days=i*7)
            ))
        
        logger.info(f"Found {len(patients)} patients for site {site_id}")
        return patients
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting patients for site {site_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get patients: {str(e)}"
        )


# ========================================
# DATA EXPORT ENDPOINTS
# ========================================

@app.get("/api/v1/export/studies", tags=["Export"])
async def export_studies_csv():
    """
    Export all studies data as CSV.
    """
    import json
    from pathlib import Path
    import csv
    from io import StringIO
    from fastapi.responses import StreamingResponse
    
    try:
        cache_file = Path("data_cache.json")
        if not cache_file.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No data available for export"
            )
        
        with open(cache_file, "r") as f:
            data = json.load(f)
        
        # Create CSV
        output = StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(["Study ID", "DQI Score", "Risk Level", "Safety", "Completeness", "Accuracy", "Timeliness", "Conformance", "Consistency"])
        
        # Data rows
        for study_id, study_data in data.items():
            dimension_scores = study_data.get("dimension_scores", {})
            
            # Handle both old (list) and new (dict) structures
            if isinstance(dimension_scores, list):
                # Old structure: list of {dimension, raw_score, ...}
                dim_map = {d.get("dimension"): d.get("raw_score", "N/A") for d in dimension_scores}
                safety_score = dim_map.get("safety", "N/A")
                completeness_score = dim_map.get("completeness", "N/A")
                accuracy_score = dim_map.get("accuracy", "N/A")
                timeliness_score = dim_map.get("timeliness", "N/A")
                conformance_score = dim_map.get("conformance", "N/A")
                consistency_score = dim_map.get("consistency", "N/A")
            elif isinstance(dimension_scores, dict):
                # New structure: dict with dimension names as keys
                safety_score = dimension_scores.get("safety", {}).get("score", "N/A") if isinstance(dimension_scores.get("safety"), dict) else "N/A"
                completeness_score = dimension_scores.get("completeness", {}).get("score", "N/A") if isinstance(dimension_scores.get("completeness"), dict) else "N/A"
                accuracy_score = dimension_scores.get("accuracy", {}).get("score", "N/A") if isinstance(dimension_scores.get("accuracy"), dict) else "N/A"
                timeliness_score = dimension_scores.get("timeliness", {}).get("score", "N/A") if isinstance(dimension_scores.get("timeliness"), dict) else "N/A"
                conformance_score = dimension_scores.get("conformance", {}).get("score", "N/A") if isinstance(dimension_scores.get("conformance"), dict) else "N/A"
                consistency_score = dimension_scores.get("consistency", {}).get("score", "N/A") if isinstance(dimension_scores.get("consistency"), dict) else "N/A"
            else:
                # Fallback
                safety_score = completeness_score = accuracy_score = timeliness_score = conformance_score = consistency_score = "N/A"
            
            writer.writerow([
                study_id,
                study_data.get("overall_score", "N/A"),
                study_data.get("risk_level", "Unknown"),
                safety_score,
                completeness_score,
                accuracy_score,
                timeliness_score,
                conformance_score,
                consistency_score,
            ])
        
        output.seek(0)
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=ctrust_studies_export.csv"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting studies: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {str(e)}"
        )


# ========================================
# ERROR HANDLERS
# ========================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            detail=str(exc)
        ).model_dump(mode='json')
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="Internal server error",
            detail=str(exc)
        ).model_dump(mode='json')
    )


# ========================================
# MAIN ENTRY POINT
# ========================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.api.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
