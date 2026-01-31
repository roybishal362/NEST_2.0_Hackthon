"""
Analysis API Endpoints
======================
Full analysis pipeline API with cache integration.

Endpoints:
- POST /api/v1/analysis/{study_id} - Run full analysis
- GET /api/v1/analysis/{study_id} - Get cached analysis
- POST /api/v1/analysis/refresh - Trigger full refresh
- GET /api/v1/analysis/status - Get system status
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from src.core import get_logger
from src.core.cache import get_cache
from src.intelligence.agent_pipeline import get_pipeline, PipelineResult
from src.data import DataIngestionEngine, FeatureEngineeringEngine, StudyDiscovery

logger = get_logger(__name__)

# Create router
router = APIRouter(prefix="/analysis", tags=["Analysis"])


# ========================================
# RESPONSE MODELS
# ========================================

class AgentSignalResponse(BaseModel):
    """Single agent signal response"""
    agent_name: str
    agent_type: str
    risk_level: Optional[str] = None
    confidence: Optional[float] = None
    processing_time_ms: float
    abstained: bool = False
    error: Optional[str] = None


class ConsensusResponse(BaseModel):
    """Consensus decision response"""
    risk_level: str
    confidence: float
    risk_score: float
    recommended_action: str
    explanation: str


class DQIResponse(BaseModel):
    """DQI score response"""
    overall_score: float
    risk_level: str
    threshold_met: str
    dimension_scores: Dict[str, float]


class AnalysisResponse(BaseModel):
    """Full analysis response"""
    study_id: str
    timestamp: datetime
    cached: bool = False
    cache_age_seconds: Optional[float] = None
    agent_signals: List[AgentSignalResponse]
    consensus: Optional[ConsensusResponse] = None
    dqi_score: Optional[DQIResponse] = None
    processing_time_ms: float
    agents_succeeded: int
    agents_failed: int
    agents_abstained: int


class RefreshResponse(BaseModel):
    """Refresh trigger response"""
    status: str
    message: str
    studies_queued: int = 0


class SystemStatusResponse(BaseModel):
    """System status response"""
    status: str
    pipeline: Dict[str, Any]
    cache: Dict[str, Any]
    scheduler: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)


# ========================================
# HELPER FUNCTIONS
# ========================================

def _run_analysis_for_study(study_id: str) -> PipelineResult:
    """Run full analysis pipeline for a study."""
    pipeline = get_pipeline()
    
    # Get features for study
    try:
        ingestion = DataIngestionEngine()
        feature_engine = FeatureEngineeringEngine()
        
        # Ingest data
        ingestion.ingest_study(study_id)
        tables = ingestion.get_study_data(study_id)
        
        # Engineer features
        features = feature_engine.engineer_features(tables)
        
    except Exception as e:
        logger.error(f"Data preparation failed: {e}")
        # Use minimal features
        features = {"study_id": study_id}
    
    # Run pipeline
    return pipeline.run_full_analysis(study_id, features)


def _convert_result_to_response(
    result: PipelineResult,
    cached: bool = False,
    cache_age: float = 0
) -> AnalysisResponse:
    """Convert PipelineResult to API response."""
    
    # Convert agent signals
    agent_signals = []
    for ar in result.agent_results:
        signal_resp = AgentSignalResponse(
            agent_name=ar.agent_name,
            agent_type=ar.agent_type.value if ar.agent_type else "unknown",
            risk_level=ar.signal.risk_level.value if ar.signal else None,
            confidence=ar.signal.confidence if ar.signal else None,
            processing_time_ms=ar.processing_time_ms,
            abstained=ar.abstained,
            error=ar.error,
        )
        agent_signals.append(signal_resp)
    
    # Convert consensus
    consensus_resp = None
    if result.consensus:
        consensus_resp = ConsensusResponse(
            risk_level=result.consensus.risk_level.value,
            confidence=result.consensus.confidence,
            risk_score=result.consensus.risk_score,
            recommended_action=result.consensus.recommended_action.value,
            explanation=result.consensus.explanation,
        )
    
    # Convert DQI
    dqi_resp = None
    if result.dqi_score:
        dimension_dict = {}
        for ds in result.dqi_score.dimension_scores:
            dimension_dict[ds.dimension.value] = ds.raw_score
        
        dqi_resp = DQIResponse(
            overall_score=result.dqi_score.overall_score,
            risk_level=result.dqi_score.risk_level.value,
            threshold_met=result.dqi_score.threshold_met,
            dimension_scores=dimension_dict,
        )
    
    return AnalysisResponse(
        study_id=result.study_id,
        timestamp=result.timestamp,
        cached=cached,
        cache_age_seconds=cache_age if cached else None,
        agent_signals=agent_signals,
        consensus=consensus_resp,
        dqi_score=dqi_resp,
        processing_time_ms=result.total_processing_time_ms,
        agents_succeeded=result.agents_succeeded,
        agents_failed=result.agents_failed,
        agents_abstained=result.agents_abstained,
    )


# ========================================
# ENDPOINTS
# ========================================

@router.get("/{study_id}", response_model=AnalysisResponse)
async def get_analysis(study_id: str):
    """
    Get analysis for a study (cache-first).
    
    Returns cached analysis if available, otherwise runs full analysis.
    """
    cache = get_cache()
    cache_key = f"analysis_{study_id}"
    
    # Try cache first
    cached_data = cache.get(cache_key)
    
    if cached_data:
        # Cache hit - return immediately
        logger.info(f"Cache hit for {study_id}")
        
        cache_age = (datetime.now() - datetime.fromisoformat(cached_data["timestamp"])).total_seconds()
        
        # Reconstruct response from cached data
        return AnalysisResponse(
            study_id=study_id,
            timestamp=datetime.fromisoformat(cached_data["timestamp"]),
            cached=True,
            cache_age_seconds=cache_age,
            agent_signals=cached_data.get("agent_signals", []),
            consensus=cached_data.get("consensus"),
            dqi_score=cached_data.get("dqi_score"),
            processing_time_ms=cached_data.get("processing_time_ms", 0),
            agents_succeeded=cached_data.get("agents_succeeded", 0),
            agents_failed=cached_data.get("agents_failed", 0),
            agents_abstained=cached_data.get("agents_abstained", 0),
        )
    
    # Cache miss - run full analysis
    logger.info(f"Cache miss for {study_id}, running analysis...")
    
    try:
        result = _run_analysis_for_study(study_id)
        response = _convert_result_to_response(result)
        
        # Cache the result
        cache.set(cache_key, response.dict(), ttl=1800)  # 30 min TTL
        
        return response
        
    except Exception as e:
        logger.error(f"Analysis failed for {study_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{study_id}", response_model=AnalysisResponse)
async def run_analysis(study_id: str, force_refresh: bool = False):
    """
    Run analysis for a study.
    
    Args:
        study_id: Study identifier
        force_refresh: Force recompute even if cached
    """
    cache = get_cache()
    cache_key = f"analysis_{study_id}"
    
    if force_refresh:
        cache.invalidate(cache_key)
    
    try:
        result = _run_analysis_for_study(study_id)
        response = _convert_result_to_response(result)
        
        # Cache the result
        cache.set(cache_key, response.dict(), ttl=1800)
        
        return response
        
    except Exception as e:
        logger.error(f"Analysis failed for {study_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refresh", response_model=RefreshResponse)
async def trigger_refresh(background_tasks: BackgroundTasks):
    """
    Trigger background refresh for all studies.
    
    This invalidates cache and queues analysis for all studies.
    """
    try:
        discovery = StudyDiscovery()
        studies = discovery.discover_studies()
        
        cache = get_cache()
        
        # Invalidate all study caches
        for study_id in studies:
            cache.invalidate(f"analysis_{study_id}")
        
        # Queue background refresh
        for study_id in studies:
            background_tasks.add_task(_run_analysis_for_study, study_id)
        
        return RefreshResponse(
            status="queued",
            message=f"Refresh queued for {len(studies)} studies",
            studies_queued=len(studies),
        )
        
    except Exception as e:
        logger.error(f"Refresh failed: {e}")
        return RefreshResponse(
            status="error",
            message=str(e),
            studies_queued=0,
        )


@router.get("/status/system", response_model=SystemStatusResponse)
async def get_system_status():
    """
    Get system status including pipeline and cache stats.
    """
    pipeline = get_pipeline()
    cache = get_cache()
    
    # Try to get scheduler status
    scheduler_status = None
    try:
        from src.core.scheduler import get_scheduler
        scheduler = get_scheduler()
        scheduler_status = scheduler.get_status()
    except Exception:
        pass
    
    return SystemStatusResponse(
        status="healthy",
        pipeline=pipeline.get_pipeline_stats(),
        cache=cache.get_stats(),
        scheduler=scheduler_status,
    )


__all__ = ["router"]
