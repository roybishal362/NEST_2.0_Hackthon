"""
C-TRUST Agent Pipeline Orchestrator
====================================
Central orchestration layer for all 7 AI agents.

This is the CRITICAL missing piece that:
1. Instantiates all 7 specialized agents
2. Runs them in parallel on study features
3. Collects signals for consensus voting
4. Integrates with DQI and Guardian for final scoring

Architecture:
    Features → AgentPipeline → 7 Agents (parallel)
                    ↓
              ConsensusEngine
                    ↓
              DQIEngine + Guardian
                    ↓
              AnalysisResult

Usage:
    pipeline = AgentPipeline()
    result = pipeline.run_full_analysis(study_id, features)
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import time

from src.core import get_logger

# Import all 7 agents
from src.agents.signal_agents import (
    DataCompletenessAgent,
    SafetyComplianceAgent,
    QueryQualityAgent,
    CodingReadinessAgent,
    TemporalDriftAgent,
    EDCQualityAgent,
    StabilityAgent,
    CrossEvidenceAgent,
)

# Import consensus and DQI engines
from src.intelligence.consensus import ConsensusEngine, ConsensusDecision
from src.intelligence.dqi import DQIEngine, DQIScore
from src.intelligence.dqi_engine_agent_driven import calculate_dqi_from_agents, DQIResult
from src.intelligence.base_agent import AgentSignal, AgentType

# Import Guardian
from src.guardian.guardian_agent import GuardianAgent

logger = get_logger(__name__)


# ========================================
# DATA STRUCTURES
# ========================================

@dataclass
class AgentResult:
    """Result from a single agent."""
    agent_type: AgentType
    agent_name: str
    signal: Optional[AgentSignal]
    processing_time_ms: float
    error: Optional[str] = None
    abstained: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_type": self.agent_type.value,
            "agent_name": self.agent_name,
            "signal": self.signal.to_dict() if self.signal else None,
            "processing_time_ms": self.processing_time_ms,
            "error": self.error,
            "abstained": self.abstained,
        }


@dataclass
class PipelineResult:
    """Complete result from pipeline execution."""
    study_id: str
    agent_results: List[AgentResult]
    consensus: Optional[ConsensusDecision]
    dqi_score: Optional[DQIScore]
    dqi_agent_driven: Optional[DQIResult]  # NEW: Agent-driven DQI result
    total_processing_time_ms: float
    agents_succeeded: int
    agents_failed: int
    agents_abstained: int
    timestamp: datetime = field(default_factory=datetime.now)
    guardian_events: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "study_id": self.study_id,
            "agent_results": [r.to_dict() for r in self.agent_results],
            "consensus": self.consensus.to_dict() if self.consensus else None,
            "dqi_score": self.dqi_score.to_dict() if self.dqi_score else None,
            "dqi_agent_driven": self.dqi_agent_driven.to_dict() if self.dqi_agent_driven else None,
            "total_processing_time_ms": self.total_processing_time_ms,
            "agents_succeeded": self.agents_succeeded,
            "agents_failed": self.agents_failed,
            "agents_abstained": self.agents_abstained,
            "timestamp": self.timestamp.isoformat(),
            "guardian_events": self.guardian_events,
        }


# ========================================
# AGENT PIPELINE
# ========================================

class AgentPipeline:
    """
    Central orchestrator for all 7 C-TRUST agents.
    
    Responsibilities:
    - Manage agent lifecycle
    - Execute agents in parallel for performance
    - Collect and validate agent signals
    - Pass to consensus engine for final decision
    - Integrate with Guardian for system integrity
    """
    
    # Agent weights for consensus (higher = more influence)
    AGENT_WEIGHTS = {
        AgentType.SAFETY: 3.0,           # Highest priority - patient safety
        AgentType.COMPLETENESS: 1.5,
        AgentType.QUERY_QUALITY: 1.5,
        AgentType.CODING: 1.2,           # NEW: Coding Readiness
        AgentType.TIMELINE: 1.2,         # NEW: Temporal Drift
        AgentType.OPERATIONS: 1.5,       # NEW: EDC Quality
        AgentType.STABILITY: -1.5,       # NEW: Negative = improvement signal
        AgentType.CROSS_EVIDENCE: 1.5,
        AgentType.COMPLIANCE: 1.5,
    }
    
    def __init__(
        self,
        max_workers: int = 4,
        enable_guardian: bool = True
    ):
        """
        Initialize the agent pipeline.
        
        Args:
            max_workers: Max parallel agent executions
            enable_guardian: Whether to run Guardian validation
        """
        self.max_workers = max_workers
        self.enable_guardian = enable_guardian
        
        # Initialize all 7 agents
        self.agents = {
            "Data Completeness": DataCompletenessAgent(),
            "Safety & Compliance": SafetyComplianceAgent(),
            "Query Quality": QueryQualityAgent(),
            "Coding Readiness": CodingReadinessAgent(),
            "Temporal Drift": TemporalDriftAgent(),
            "EDC Quality": EDCQualityAgent(),
            "Stability": StabilityAgent(),
            "Cross-Evidence": CrossEvidenceAgent(),
        }
        
        # Initialize engines
        self.consensus_engine = ConsensusEngine(custom_weights=self.AGENT_WEIGHTS)
        self.dqi_engine = DQIEngine()
        self.guardian = GuardianAgent() if enable_guardian else None
        
        # Tracking
        self._execution_count = 0
        self._total_time = 0.0
        
        logger.info(f"AgentPipeline initialized with {len(self.agents)} agents")
    
    def run_full_analysis(
        self,
        study_id: str,
        features: Dict[str, Any],
        parallel: bool = True
    ) -> PipelineResult:
        """
        Run complete analysis pipeline for a study.
        
        Flow:
        1. Run all 7 agents on features
        2. Collect signals
        3. Calculate consensus
        4. Calculate DQI
        5. Guardian validation
        
        Args:
            study_id: Study identifier
            features: Engineered features dictionary
            parallel: Run agents in parallel (faster)
        
        Returns:
            PipelineResult with full analysis
        """
        start_time = time.time()
        logger.info(f"Starting full analysis for {study_id}")
        
        # Step 1: Run all agents
        if parallel:
            agent_results = self._run_agents_parallel(features, study_id)
        else:
            agent_results = self._run_agents_sequential(features, study_id)
        
        # Step 2: Collect valid signals for consensus
        signals = []
        succeeded = 0
        failed = 0
        abstained = 0
        
        for result in agent_results:
            if result.error:
                failed += 1
                logger.warning(f"Agent {result.agent_name} failed: {result.error}")
            elif result.abstained:
                abstained += 1
            else:
                succeeded += 1
                if result.signal:
                    signals.append(result.signal)
        
        # Step 3: Calculate consensus
        consensus = None
        if signals:
            try:
                consensus = self.consensus_engine.calculate_consensus(
                    signals=signals,
                    study_id=study_id
                )
                logger.info(f"Consensus: {consensus.risk_level.value} ({consensus.confidence:.2f})")
            except Exception as e:
                logger.error(f"Consensus calculation failed: {e}")
        
        # Step 4: Calculate DQI (both old and new methods)
        dqi_score = None
        dqi_agent_driven = None
        
        # Old DQI calculation (for backward compatibility)
        try:
            dqi_score = self.dqi_engine.calculate_dqi(
                features=features,
                study_id=study_id
            )
            logger.info(f"DQI Score (legacy): {dqi_score.overall_score:.1f}")
        except Exception as e:
            logger.error(f"DQI calculation failed: {e}")
        
        # NEW: Agent-driven DQI calculation
        if signals and consensus:
            try:
                dqi_agent_driven = calculate_dqi_from_agents(
                    agent_signals=signals,
                    consensus=consensus,
                    study_id=study_id
                )
                logger.info(
                    f"DQI Score (agent-driven): {dqi_agent_driven.score:.1f} "
                    f"({dqi_agent_driven.band.value}, confidence={dqi_agent_driven.confidence:.2f})"
                )
            except Exception as e:
                logger.error(f"Agent-driven DQI calculation failed: {e}")
        
        # Step 5: Guardian validation
        guardian_events = []
        if self.guardian and consensus and dqi_score:
            try:
                # Create data snapshot for Guardian
                data_snapshot = {
                    "study_id": study_id,
                    "dqi_score": dqi_score.overall_score,
                    "risk_level": consensus.risk_level.value,
                    "agent_signals": [s.to_dict() for s in signals],
                    "timestamp": datetime.now().isoformat(),
                }
                
                # Validate cross-agent consistency
                validation = self.guardian.validate_cross_agent_signals([
                    {"agent_type": s.agent_type.value, "risk_level": s.risk_level.value, 
                     "confidence": s.confidence, "abstained": False}
                    for s in signals
                ])
                
                if not validation.get("valid"):
                    for issue in validation.get("issues", []):
                        guardian_events.append(issue)
                
            except Exception as e:
                logger.error(f"Guardian validation failed: {e}")
        
        # Calculate total time
        total_time = (time.time() - start_time) * 1000
        self._execution_count += 1
        self._total_time += total_time
        
        result = PipelineResult(
            study_id=study_id,
            agent_results=agent_results,
            consensus=consensus,
            dqi_score=dqi_score,
            dqi_agent_driven=dqi_agent_driven,  # NEW: Include agent-driven DQI
            total_processing_time_ms=total_time,
            agents_succeeded=succeeded,
            agents_failed=failed,
            agents_abstained=abstained,
            guardian_events=guardian_events,
        )
        
        logger.info(
            f"Pipeline complete: {succeeded}/{len(self.agents)} agents, "
            f"{total_time:.1f}ms"
        )
        
        return result
    
    def _run_agents_parallel(
        self,
        features: Dict[str, Any],
        study_id: str
    ) -> List[AgentResult]:
        """Run all agents in parallel using ThreadPoolExecutor."""
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}
            
            for name, agent in self.agents.items():
                future = executor.submit(self._run_single_agent, name, agent, features, study_id)
                futures[future] = name
            
            for future in futures:
                try:
                    result = future.result(timeout=30)  # 30s timeout
                    results.append(result)
                except Exception as e:
                    name = futures[future]
                    results.append(AgentResult(
                        agent_type=AgentType.SAFETY,  # Default
                        agent_name=name,
                        signal=None,
                        processing_time_ms=0,
                        error=str(e),
                    ))
        
        return results
    
    def _run_agents_sequential(
        self,
        features: Dict[str, Any],
        study_id: str
    ) -> List[AgentResult]:
        """Run all agents sequentially (for debugging)."""
        results = []
        
        for name, agent in self.agents.items():
            result = self._run_single_agent(name, agent, features, study_id)
            results.append(result)
        
        return results
    
    def _run_single_agent(
        self,
        name: str,
        agent: Any,
        features: Dict[str, Any],
        study_id: str
    ) -> AgentResult:
        """Run a single agent and capture result."""
        start_time = time.time()
        
        # Get agent type from agent
        agent_type = agent.agent_type if hasattr(agent, 'agent_type') else AgentType.SAFETY
        
        try:
            signal = agent.analyze(features, study_id)
            processing_time = (time.time() - start_time) * 1000
            
            # Check if agent abstained
            abstained = signal is None or (hasattr(signal, 'abstained') and signal.abstained)
            
            return AgentResult(
                agent_type=agent_type,
                agent_name=name,
                signal=signal if not abstained else None,
                processing_time_ms=processing_time,
                abstained=abstained,
            )
            
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            logger.error(f"Agent {name} error: {e}")
            
            return AgentResult(
                agent_type=agent_type,
                agent_name=name,
                signal=None,
                processing_time_ms=processing_time,
                error=str(e),
            )
    
    def get_agent_status(self) -> List[Dict[str, Any]]:
        """Get status of all agents."""
        status = []
        for name, agent in self.agents.items():
            status.append({
                "name": name,
                "type": agent.AGENT_TYPE.value if hasattr(agent, 'AGENT_TYPE') else "unknown",
                "weight": self.AGENT_WEIGHTS.get(
                    agent.AGENT_TYPE if hasattr(agent, 'AGENT_TYPE') else AgentType.SAFETY, 
                    1.0
                ),
                "status": "active",
            })
        return status
    
    def get_pipeline_stats(self) -> Dict[str, Any]:
        """Get pipeline execution statistics."""
        return {
            "total_executions": self._execution_count,
            "total_time_ms": self._total_time,
            "avg_time_ms": self._total_time / max(self._execution_count, 1),
            "agent_count": len(self.agents),
            "guardian_enabled": self.enable_guardian,
        }


# ========================================
# SINGLETON INSTANCE
# ========================================

_pipeline_instance: Optional[AgentPipeline] = None


def get_pipeline() -> AgentPipeline:
    """Get or create singleton pipeline instance."""
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = AgentPipeline()
    return _pipeline_instance


def reset_pipeline() -> None:
    """Reset pipeline instance (for testing)."""
    global _pipeline_instance
    _pipeline_instance = None


# ========================================
# EXPORTS
# ========================================

__all__ = [
    "AgentPipeline",
    "AgentResult",
    "PipelineResult",
    "get_pipeline",
    "reset_pipeline",
]
