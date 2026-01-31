"""
C-TRUST Comprehensive Audit Trail System
========================================
Provides immutable logging for all system operations, user actions,
and agent decisions with full traceability.

Key Features:
- Immutable audit event records
- User action tracking and attribution
- System operation logging
- Agent decision logging
- Query and reporting interface

**Validates: Requirements 7.3, 10.3**
"""

import hashlib
import json
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
import logging
from pathlib import Path

from src.core import get_logger

logger = get_logger(__name__)


class AuditEventType(str, Enum):
    """Types of audit events"""
    # System Operations
    SYSTEM_START = "SYSTEM_START"
    SYSTEM_STOP = "SYSTEM_STOP"
    CONFIG_CHANGE = "CONFIG_CHANGE"
    
    # Data Processing
    DATA_INGESTION = "DATA_INGESTION"
    DATA_PROCESSING = "DATA_PROCESSING"
    DATA_VALIDATION = "DATA_VALIDATION"
    DATA_EXPORT = "DATA_EXPORT"
    
    # Agent Operations
    AGENT_ANALYSIS = "AGENT_ANALYSIS"
    AGENT_SIGNAL = "AGENT_SIGNAL"
    AGENT_ABSTENTION = "AGENT_ABSTENTION"
    
    # Consensus Operations
    CONSENSUS_CALCULATION = "CONSENSUS_CALCULATION"
    RISK_ASSESSMENT = "RISK_ASSESSMENT"
    DQI_CALCULATION = "DQI_CALCULATION"
    
    # Guardian Operations
    GUARDIAN_CHECK = "GUARDIAN_CHECK"
    GUARDIAN_ALERT = "GUARDIAN_ALERT"
    
    # User Actions
    USER_LOGIN = "USER_LOGIN"
    USER_LOGOUT = "USER_LOGOUT"
    USER_VIEW = "USER_VIEW"
    USER_DRILL_DOWN = "USER_DRILL_DOWN"
    USER_EXPORT = "USER_EXPORT"
    USER_ACKNOWLEDGE = "USER_ACKNOWLEDGE"
    USER_DISMISS = "USER_DISMISS"
    USER_ESCALATE = "USER_ESCALATE"
    
    # Explanation Operations
    EXPLANATION_GENERATED = "EXPLANATION_GENERATED"
    
    # Error Events
    ERROR_OCCURRED = "ERROR_OCCURRED"
    WARNING_RAISED = "WARNING_RAISED"


@dataclass(frozen=True)
class AuditEvent:
    """
    Immutable audit event record.
    
    The frozen=True makes this dataclass immutable, ensuring
    audit records cannot be modified after creation.
    
    Attributes:
        event_id: Unique identifier for this event
        timestamp: When the event occurred
        event_type: Type of audit event
        component_name: System component that generated the event
        entity_id: Optional entity being operated on
        user_id: Optional user who triggered the event
        session_id: Optional session identifier
        action_taken: Description of the action
        details: Additional event details
        previous_state: State before the action (for changes)
        new_state: State after the action (for changes)
        checksum: Hash for integrity verification
    """
    event_id: str
    timestamp: datetime
    event_type: AuditEventType
    component_name: str
    action_taken: str
    details: Dict[str, Any] = field(default_factory=dict)
    entity_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    previous_state: Optional[Dict[str, Any]] = None
    new_state: Optional[Dict[str, Any]] = None
    checksum: str = ""
    
    def __post_init__(self):
        """Calculate checksum after initialization"""
        if not self.checksum:
            # Use object.__setattr__ since frozen=True
            object.__setattr__(self, 'checksum', self._calculate_checksum())
    
    def _calculate_checksum(self) -> str:
        """Calculate SHA-256 checksum for integrity verification"""
        content = (
            f"{self.event_id}|{self.timestamp.isoformat()}|"
            f"{self.event_type.value}|{self.component_name}|"
            f"{self.entity_id}|{self.user_id}|{self.action_taken}|"
            f"{json.dumps(self.details, sort_keys=True)}"
        )
        return hashlib.sha256(content.encode()).hexdigest()
    
    def verify_integrity(self) -> bool:
        """Verify event integrity using checksum"""
        return self.checksum == self._calculate_checksum()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type.value,
            "component_name": self.component_name,
            "entity_id": self.entity_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "action_taken": self.action_taken,
            "details": self.details,
            "previous_state": self.previous_state,
            "new_state": self.new_state,
            "checksum": self.checksum,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditEvent":
        """Create AuditEvent from dictionary"""
        return cls(
            event_id=data["event_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            event_type=AuditEventType(data["event_type"]),
            component_name=data["component_name"],
            entity_id=data.get("entity_id"),
            user_id=data.get("user_id"),
            session_id=data.get("session_id"),
            action_taken=data["action_taken"],
            details=data.get("details", {}),
            previous_state=data.get("previous_state"),
            new_state=data.get("new_state"),
            checksum=data.get("checksum", ""),
        )


@dataclass
class AuditQuery:
    """Query parameters for audit trail search"""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    event_types: Optional[List[AuditEventType]] = None
    component_names: Optional[List[str]] = None
    entity_ids: Optional[List[str]] = None
    user_ids: Optional[List[str]] = None
    session_ids: Optional[List[str]] = None
    limit: int = 1000
    offset: int = 0
    
    def matches(self, event: AuditEvent) -> bool:
        """Check if an event matches this query"""
        if self.start_time and event.timestamp < self.start_time:
            return False
        if self.end_time and event.timestamp > self.end_time:
            return False
        if self.event_types and event.event_type not in self.event_types:
            return False
        if self.component_names and event.component_name not in self.component_names:
            return False
        if self.entity_ids and event.entity_id not in self.entity_ids:
            return False
        if self.user_ids and event.user_id not in self.user_ids:
            return False
        if self.session_ids and event.session_id not in self.session_ids:
            return False
        return True


@dataclass
class AuditReport:
    """Audit trail report"""
    query: AuditQuery
    events: List[AuditEvent]
    total_count: int
    generated_at: datetime = field(default_factory=datetime.now)
    summary: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "generated_at": self.generated_at.isoformat(),
            "total_count": self.total_count,
            "events_returned": len(self.events),
            "summary": self.summary,
            "events": [e.to_dict() for e in self.events],
        }


class AuditTrailManager:
    """
    Central audit trail management system.
    
    Provides comprehensive, immutable logging for all system operations,
    user actions, and agent decisions.
    
    Features:
    - Thread-safe event logging
    - Immutable event records
    - Integrity verification
    - Query and reporting
    - File-based persistence
    
    **Validates: Requirements 7.3, 10.3**
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        """Singleton pattern for global audit trail"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(
        self,
        storage_path: str = "logs/audit",
        max_memory_events: int = 10000,
    ):
        """
        Initialize audit trail manager.
        
        Args:
            storage_path: Path for audit log files
            max_memory_events: Maximum events to keep in memory
        """
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.max_memory_events = max_memory_events
        self._events: List[AuditEvent] = []
        self._event_counter = 0
        self._write_lock = threading.Lock()
        self._callbacks: List[Callable[[AuditEvent], None]] = []
        
        self._initialized = True
        logger.info(f"AuditTrailManager initialized with storage at {storage_path}")
    
    def log_event(
        self,
        event_type: AuditEventType,
        component_name: str,
        action_taken: str,
        entity_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        previous_state: Optional[Dict[str, Any]] = None,
        new_state: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        """
        Log an audit event.
        
        Args:
            event_type: Type of event
            component_name: Component generating the event
            action_taken: Description of the action
            entity_id: Optional entity being operated on
            user_id: Optional user who triggered the event
            session_id: Optional session identifier
            details: Additional event details
            previous_state: State before the action
            new_state: State after the action
        
        Returns:
            The created AuditEvent
        """
        with self._write_lock:
            self._event_counter += 1
            event_id = f"AUD_{datetime.now().strftime('%Y%m%d%H%M%S')}_{self._event_counter:06d}"
            
            event = AuditEvent(
                event_id=event_id,
                timestamp=datetime.now(),
                event_type=event_type,
                component_name=component_name,
                entity_id=entity_id,
                user_id=user_id,
                session_id=session_id,
                action_taken=action_taken,
                details=details or {},
                previous_state=previous_state,
                new_state=new_state,
            )
            
            # Store in memory
            self._events.append(event)
            
            # Trim if exceeds max
            if len(self._events) > self.max_memory_events:
                self._events = self._events[-self.max_memory_events:]
            
            # Persist to file
            self._persist_event(event)
            
            # Notify callbacks
            for callback in self._callbacks:
                try:
                    callback(event)
                except Exception as e:
                    logger.error(f"Audit callback error: {e}")
            
            logger.debug(f"Audit event logged: {event_id} - {event_type.value}")
            return event
    
    def _persist_event(self, event: AuditEvent) -> None:
        """Persist event to file"""
        try:
            # Daily log files
            date_str = event.timestamp.strftime("%Y%m%d")
            log_file = self.storage_path / f"audit_{date_str}.jsonl"
            
            with open(log_file, "a") as f:
                f.write(json.dumps(event.to_dict()) + "\n")
        except Exception as e:
            logger.error(f"Failed to persist audit event: {e}")
    
    def query_events(self, query: AuditQuery) -> AuditReport:
        """
        Query audit events.
        
        Args:
            query: Query parameters
        
        Returns:
            AuditReport with matching events
        """
        # First check memory
        matching = [e for e in self._events if query.matches(e)]
        
        # If we need more events, check files
        if len(matching) < query.limit and query.start_time:
            file_events = self._load_events_from_files(query)
            matching.extend(file_events)
        
        # Sort by timestamp descending
        matching.sort(key=lambda e: e.timestamp, reverse=True)
        
        # Apply pagination
        total_count = len(matching)
        matching = matching[query.offset:query.offset + query.limit]
        
        # Generate summary
        summary = self._generate_summary(matching)
        
        return AuditReport(
            query=query,
            events=matching,
            total_count=total_count,
            summary=summary,
        )
    
    def _load_events_from_files(self, query: AuditQuery) -> List[AuditEvent]:
        """Load events from log files based on query"""
        events = []
        
        # Determine date range
        start_date = query.start_time.date() if query.start_time else datetime.now().date() - timedelta(days=30)
        end_date = query.end_time.date() if query.end_time else datetime.now().date()
        
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime("%Y%m%d")
            log_file = self.storage_path / f"audit_{date_str}.jsonl"
            
            if log_file.exists():
                try:
                    with open(log_file, "r") as f:
                        for line in f:
                            try:
                                data = json.loads(line.strip())
                                event = AuditEvent.from_dict(data)
                                if query.matches(event):
                                    events.append(event)
                            except Exception as e:
                                logger.warning(f"Failed to parse audit line: {e}")
                except Exception as e:
                    logger.error(f"Failed to read audit file {log_file}: {e}")
            
            current_date += timedelta(days=1)
        
        return events
    
    def _generate_summary(self, events: List[AuditEvent]) -> Dict[str, Any]:
        """Generate summary statistics for events"""
        if not events:
            return {"total": 0}
        
        # Count by type
        type_counts: Dict[str, int] = {}
        for event in events:
            type_counts[event.event_type.value] = type_counts.get(event.event_type.value, 0) + 1
        
        # Count by component
        component_counts: Dict[str, int] = {}
        for event in events:
            component_counts[event.component_name] = component_counts.get(event.component_name, 0) + 1
        
        # Count by user
        user_counts: Dict[str, int] = {}
        for event in events:
            if event.user_id:
                user_counts[event.user_id] = user_counts.get(event.user_id, 0) + 1
        
        return {
            "total": len(events),
            "by_type": type_counts,
            "by_component": component_counts,
            "by_user": user_counts,
            "time_range": {
                "earliest": min(e.timestamp for e in events).isoformat(),
                "latest": max(e.timestamp for e in events).isoformat(),
            },
        }
    
    def get_user_actions(
        self,
        user_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[AuditEvent]:
        """
        Get all actions by a specific user.
        
        Args:
            user_id: User identifier
            start_time: Optional start time filter
            end_time: Optional end time filter
        
        Returns:
            List of audit events for the user
        """
        query = AuditQuery(
            user_ids=[user_id],
            start_time=start_time,
            end_time=end_time,
        )
        report = self.query_events(query)
        return report.events
    
    def get_entity_history(
        self,
        entity_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[AuditEvent]:
        """
        Get all events related to a specific entity.
        
        Args:
            entity_id: Entity identifier
            start_time: Optional start time filter
            end_time: Optional end time filter
        
        Returns:
            List of audit events for the entity
        """
        query = AuditQuery(
            entity_ids=[entity_id],
            start_time=start_time,
            end_time=end_time,
        )
        report = self.query_events(query)
        return report.events
    
    def verify_integrity(self, events: Optional[List[AuditEvent]] = None) -> Tuple[bool, List[str]]:
        """
        Verify integrity of audit events.
        
        Args:
            events: Optional list of events to verify. If None, verifies all in memory.
        
        Returns:
            Tuple of (all_valid, list of invalid event IDs)
        """
        events = events or self._events
        invalid_ids = []
        
        for event in events:
            if not event.verify_integrity():
                invalid_ids.append(event.event_id)
        
        return len(invalid_ids) == 0, invalid_ids
    
    def register_callback(self, callback: Callable[[AuditEvent], None]) -> None:
        """Register callback for new audit events"""
        self._callbacks.append(callback)
    
    def unregister_callback(self, callback: Callable[[AuditEvent], None]) -> None:
        """Unregister callback"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    # Convenience methods for common operations
    
    def log_user_action(
        self,
        user_id: str,
        action: str,
        entity_id: Optional[str] = None,
        session_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        """Log a user action"""
        event_type_map = {
            "VIEW": AuditEventType.USER_VIEW,
            "DRILL_DOWN": AuditEventType.USER_DRILL_DOWN,
            "EXPORT": AuditEventType.USER_EXPORT,
            "ACKNOWLEDGE": AuditEventType.USER_ACKNOWLEDGE,
            "DISMISS": AuditEventType.USER_DISMISS,
            "ESCALATE": AuditEventType.USER_ESCALATE,
            "LOGIN": AuditEventType.USER_LOGIN,
            "LOGOUT": AuditEventType.USER_LOGOUT,
        }
        
        event_type = event_type_map.get(action.upper(), AuditEventType.USER_VIEW)
        
        return self.log_event(
            event_type=event_type,
            component_name="user_interface",
            action_taken=action,
            entity_id=entity_id,
            user_id=user_id,
            session_id=session_id,
            details=details,
        )
    
    def log_agent_decision(
        self,
        agent_name: str,
        entity_id: str,
        decision: str,
        confidence: float,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        """Log an agent decision"""
        return self.log_event(
            event_type=AuditEventType.AGENT_SIGNAL,
            component_name=f"agent.{agent_name}",
            action_taken=decision,
            entity_id=entity_id,
            details={
                "confidence": confidence,
                **(details or {}),
            },
        )
    
    def log_data_processing(
        self,
        operation: str,
        entity_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        """Log a data processing operation"""
        return self.log_event(
            event_type=AuditEventType.DATA_PROCESSING,
            component_name="data_pipeline",
            action_taken=operation,
            entity_id=entity_id,
            details=details,
        )
    
    def log_config_change(
        self,
        user_id: str,
        config_key: str,
        previous_value: Any,
        new_value: Any,
    ) -> AuditEvent:
        """Log a configuration change"""
        return self.log_event(
            event_type=AuditEventType.CONFIG_CHANGE,
            component_name="config_manager",
            action_taken=f"Changed {config_key}",
            user_id=user_id,
            previous_state={"value": previous_value},
            new_state={"value": new_value},
            details={"config_key": config_key},
        )
    
    def log_error(
        self,
        component_name: str,
        error_message: str,
        entity_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        """Log an error event"""
        return self.log_event(
            event_type=AuditEventType.ERROR_OCCURRED,
            component_name=component_name,
            action_taken=error_message,
            entity_id=entity_id,
            details=details,
        )
    
    def get_recent_events(self, count: int = 100) -> List[AuditEvent]:
        """Get most recent events"""
        return sorted(self._events, key=lambda e: e.timestamp, reverse=True)[:count]
    
    def clear_memory_cache(self) -> None:
        """Clear in-memory event cache (events remain in files)"""
        with self._write_lock:
            self._events.clear()
            logger.info("Audit trail memory cache cleared")


# Global audit trail instance
audit_trail = AuditTrailManager()


__all__ = [
    "AuditTrailManager",
    "AuditEvent",
    "AuditEventType",
    "AuditQuery",
    "AuditReport",
    "audit_trail",
]
