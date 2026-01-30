"""
Guardian Dashboard Data Provider
================================
Provides structured data for the Guardian monitoring dashboard.

Responsibilities:
- Compile system health metrics
- Generate staleness heatmap data
- Track agent performance over time
- Aggregate integrity event history

Key Features:
- Real-time health monitoring
- Agent performance timeline
- Staleness visualization data
- Alert history aggregation

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from enum import Enum

from src.core import get_logger
from src.guardian.guardian_agent import (
    GuardianAgent,
    GuardianEvent,
    GuardianEventType,
    GuardianSeverity,
    StalenessIndicator,
)

logger = get_logger(__name__)


class HealthStatus(str, Enum):
    """Overall system health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class AgentPerformanceMetrics:
    """Performance metrics for a single agent"""
    agent_name: str
    avg_processing_time_ms: float
    signals_generated: int
    abstention_count: int
    abstention_rate: float
    avg_confidence: float
    last_active: datetime
    is_healthy: bool = True


@dataclass
class SystemHealthMetrics:
    """Overall system health metrics"""
    status: HealthStatus
    healthy_agents: int
    total_agents: int
    active_studies: int
    stale_entities: int
    critical_events: int
    warning_events: int
    last_updated: datetime = field(default_factory=datetime.now)
    uptime_hours: float = 0.0
    data_freshness_score: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "healthy_agents": self.healthy_agents,
            "total_agents": self.total_agents,
            "active_studies": self.active_studies,
            "stale_entities": self.stale_entities,
            "critical_events": self.critical_events,
            "warning_events": self.warning_events,
            "last_updated": self.last_updated.isoformat(),
            "uptime_hours": self.uptime_hours,
            "data_freshness_score": self.data_freshness_score,
        }


@dataclass 
class StalenessHeatmapEntry:
    """Entry for staleness heatmap visualization"""
    entity_id: str
    entity_type: str  # "study" or "site"
    staleness_score: float
    consecutive_unchanged: int
    data_has_changed: bool
    is_stale: bool
    risk_level: str  # "low", "medium", "high", "critical"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "staleness_score": self.staleness_score,
            "consecutive_unchanged": self.consecutive_unchanged,
            "data_has_changed": self.data_has_changed,
            "is_stale": self.is_stale,
            "risk_level": self.risk_level,
        }


class GuardianDashboardData:
    """
    Provides data for the Guardian monitoring dashboard.
    
    Aggregates metrics from the Guardian Agent and system components
    to provide visualizable dashboard data.
    """
    
    def __init__(
        self,
        guardian: Optional[GuardianAgent] = None,
        total_agents: int = 7
    ):
        """
        Initialize dashboard data provider.
        
        Args:
            guardian: Guardian agent instance (creates new if not provided)
            total_agents: Total number of agents in the system
        """
        self.guardian = guardian or GuardianAgent()
        self.total_agents = total_agents
        self._start_time = datetime.now()
        
        # Agent performance tracking
        self._agent_metrics: Dict[str, AgentPerformanceMetrics] = {}
        self._processing_history: List[Dict[str, Any]] = []
        
        logger.info("GuardianDashboardData initialized")
    
    def get_system_health_metrics(self) -> Dict[str, Any]:
        """
        Get overall system health metrics.
        
        Returns:
            Dictionary with system health information
        """
        # Count events by severity
        all_events = self.guardian.get_events()
        critical_events = len([e for e in all_events if e.severity == GuardianSeverity.CRITICAL])
        warning_events = len([e for e in all_events if e.severity == GuardianSeverity.WARNING])
        
        # Count stale entities
        stale_count = len([
            indicator for indicator in self.guardian._staleness_tracking.values()
            if indicator.is_stale
        ])
        
        # Determine overall health status
        if critical_events > 0:
            status = HealthStatus.CRITICAL
        elif warning_events > 0 or stale_count > 0:
            status = HealthStatus.DEGRADED
        else:
            status = HealthStatus.HEALTHY
        
        # Calculate uptime
        uptime = datetime.now() - self._start_time
        uptime_hours = uptime.total_seconds() / 3600
        
        # Calculate data freshness
        freshness_score = self._calculate_data_freshness()
        
        healthy_agents = len([m for m in self._agent_metrics.values() if m.is_healthy])
        
        metrics = SystemHealthMetrics(
            status=status,
            healthy_agents=healthy_agents if healthy_agents > 0 else self.total_agents,
            total_agents=self.total_agents,
            active_studies=len(self.guardian._staleness_tracking),
            stale_entities=stale_count,
            critical_events=critical_events,
            warning_events=warning_events,
            uptime_hours=round(uptime_hours, 2),
            data_freshness_score=freshness_score,
        )
        
        return metrics.to_dict()
    
    def get_staleness_heatmap(self) -> List[Dict[str, Any]]:
        """
        Get staleness heatmap data for visualization.
        
        Returns:
            List of staleness entries for each monitored entity
        """
        heatmap_data = []
        
        for entity_id, indicator in self.guardian._staleness_tracking.items():
            # Determine risk level based on staleness score
            if indicator.staleness_score >= 0.9:
                risk_level = "critical"
            elif indicator.staleness_score >= 0.6:
                risk_level = "high"
            elif indicator.staleness_score >= 0.3:
                risk_level = "medium"
            else:
                risk_level = "low"
            
            # Determine entity type from ID pattern
            entity_type = "site" if "SITE" in entity_id.upper() else "study"
            
            entry = StalenessHeatmapEntry(
                entity_id=entity_id,
                entity_type=entity_type,
                staleness_score=indicator.staleness_score,
                consecutive_unchanged=indicator.consecutive_unchanged_snapshots,
                data_has_changed=indicator.data_has_changed,
                is_stale=indicator.is_stale,
                risk_level=risk_level,
            )
            heatmap_data.append(entry.to_dict())
        
        # Sort by staleness score (highest first)
        heatmap_data.sort(key=lambda x: x["staleness_score"], reverse=True)
        
        return heatmap_data
    
    def get_agent_performance_timeline(
        self,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Get agent performance timeline data.
        
        Args:
            hours: Number of hours of history to include
        
        Returns:
            List of performance data points over time
        """
        # Filter processing history to requested timeframe
        cutoff = datetime.now() - timedelta(hours=hours)
        
        timeline_data = [
            entry for entry in self._processing_history
            if entry.get("timestamp", datetime.min) >= cutoff
        ]
        
        # If no history, generate sample current state
        if not timeline_data:
            timeline_data = [{
                "timestamp": datetime.now().isoformat(),
                "agents": self._get_current_agent_status(),
            }]
        
        return timeline_data
    
    def get_integrity_event_history(
        self,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get integrity event history.
        
        Args:
            limit: Maximum number of events to return
        
        Returns:
            List of integrity events with details
        """
        events = self.guardian.get_events(limit=limit)
        
        event_list = []
        for event in events:
            event_list.append({
                "event_id": event.event_id,
                "event_type": event.event_type.value,
                "severity": event.severity.value,
                "entity_id": event.entity_id,
                "timestamp": event.timestamp.isoformat(),
                "summary": event.actual_behavior,
                "recommendation": event.recommendation,
            })
        
        return event_list
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """
        Get summary of active alerts.
        
        Returns:
            Dictionary with alert counts and details
        """
        events = self.guardian.get_events()
        
        # Group by severity
        critical = [e for e in events if e.severity == GuardianSeverity.CRITICAL]
        warnings = [e for e in events if e.severity == GuardianSeverity.WARNING]
        info = [e for e in events if e.severity == GuardianSeverity.INFO]
        
        # Group by event type
        by_type = {}
        for event in events:
            type_key = event.event_type.value
            if type_key not in by_type:
                by_type[type_key] = 0
            by_type[type_key] += 1
        
        return {
            "total": len(events),
            "critical": len(critical),
            "warning": len(warnings),
            "info": len(info),
            "by_type": by_type,
            "latest_critical": critical[0].to_dict() if critical else None,
        }
    
    def record_agent_processing(
        self,
        agent_name: str,
        processing_time_ms: float,
        abstained: bool,
        confidence: float
    ) -> None:
        """
        Record agent processing event.
        
        Args:
            agent_name: Name of the agent
            processing_time_ms: Time taken in milliseconds
            abstained: Whether agent abstained
            confidence: Confidence score (0 if abstained)
        """
        if agent_name not in self._agent_metrics:
            self._agent_metrics[agent_name] = AgentPerformanceMetrics(
                agent_name=agent_name,
                avg_processing_time_ms=processing_time_ms,
                signals_generated=0 if abstained else 1,
                abstention_count=1 if abstained else 0,
                abstention_rate=1.0 if abstained else 0.0,
                avg_confidence=confidence,
                last_active=datetime.now(),
            )
        else:
            metrics = self._agent_metrics[agent_name]
            total_calls = metrics.signals_generated + metrics.abstention_count + 1
            
            # Update average processing time
            old_avg = metrics.avg_processing_time_ms
            metrics.avg_processing_time_ms = (old_avg * (total_calls - 1) + processing_time_ms) / total_calls
            
            # Update counts
            if abstained:
                metrics.abstention_count += 1
            else:
                metrics.signals_generated += 1
                # Update average confidence
                valid_signals = metrics.signals_generated
                old_conf = metrics.avg_confidence
                metrics.avg_confidence = (old_conf * (valid_signals - 1) + confidence) / valid_signals
            
            metrics.abstention_rate = metrics.abstention_count / total_calls
            metrics.last_active = datetime.now()
        
        # Record in history
        self._processing_history.append({
            "timestamp": datetime.now(),
            "agent": agent_name,
            "processing_time_ms": processing_time_ms,
            "abstained": abstained,
            "confidence": confidence,
        })
        
        # Trim history if too long
        if len(self._processing_history) > 10000:
            self._processing_history = self._processing_history[-5000:]
    
    def _calculate_data_freshness(self) -> float:
        """Calculate overall data freshness score (0-1)."""
        if not self.guardian._staleness_tracking:
            return 1.0
        
        # Average of (1 - staleness_score) for all entities
        freshness_scores = [
            1.0 - indicator.staleness_score
            for indicator in self.guardian._staleness_tracking.values()
        ]
        
        return sum(freshness_scores) / len(freshness_scores)
    
    def _get_current_agent_status(self) -> List[Dict[str, Any]]:
        """Get current status of all tracked agents."""
        agent_status = []
        
        for name, metrics in self._agent_metrics.items():
            agent_status.append({
                "name": name,
                "processing_time_ms": metrics.avg_processing_time_ms,
                "signals": metrics.signals_generated,
                "abstentions": metrics.abstention_count,
                "abstention_rate": metrics.abstention_rate,
                "confidence": metrics.avg_confidence,
                "is_healthy": metrics.is_healthy,
            })
        
        return agent_status
    
    def get_full_dashboard_data(self) -> Dict[str, Any]:
        """
        Get all dashboard data in a single call.
        
        Returns:
            Complete dashboard data structure
        """
        return {
            "system_health": self.get_system_health_metrics(),
            "staleness_heatmap": self.get_staleness_heatmap(),
            "agent_timeline": self.get_agent_performance_timeline(),
            "event_history": self.get_integrity_event_history(limit=20),
            "alert_summary": self.get_alert_summary(),
            "timestamp": datetime.now().isoformat(),
        }


__all__ = [
    "GuardianDashboardData",
    "SystemHealthMetrics",
    "HealthStatus",
    "AgentPerformanceMetrics",
    "StalenessHeatmapEntry",
]
