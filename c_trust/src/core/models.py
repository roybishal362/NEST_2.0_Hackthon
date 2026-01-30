"""
Core data models for the Clinical AI System (C-TRUST)
"""
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from dataclasses import dataclass


class Severity(str, Enum):
    """Risk severity levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RiskLevel(str, Enum):
    """Risk assessment levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class DQIBand(str, Enum):
    """Data Quality Index bands"""
    GREEN = "GREEN"    # 85-100
    AMBER = "AMBER"    # 65-84
    ORANGE = "ORANGE"  # 40-64
    RED = "RED"        # <40


class ProcessingStatus(str, Enum):
    """Data processing status"""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class ClinicalSnapshot:
    """Represents a time-bound collection of clinical trial data"""
    snapshot_id: str
    timestamp: datetime
    study_id: str
    data_sources: Dict[str, Any]
    processing_status: ProcessingStatus


class AgentSignal(BaseModel):
    """Signal output from an individual agent"""
    agent_name: str
    entity_id: str
    signal_type: str
    severity: Severity
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: List[str] = Field(default_factory=list)
    can_abstain: bool = True
    timestamp: datetime = Field(default_factory=datetime.now)


class ConsensusDecision(BaseModel):
    """Final decision from consensus engine"""
    entity_id: str
    entity_type: str  # "SITE" | "SUBJECT"
    risk_level: RiskLevel
    confidence: float = Field(ge=0.0, le=1.0)
    contributing_agents: List[str]
    recommended_actions: List[str] = Field(default_factory=list)
    dqi_score: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class DQIScore(BaseModel):
    """Data Quality Index score and breakdown"""
    entity_id: str
    overall_score: float = Field(ge=0.0, le=100.0)
    dimensions: Dict[str, float] = Field(default_factory=dict)
    band: DQIBand
    trend: str  # "IMPROVING" | "STABLE" | "DECLINING"
    snapshot_id: str
    timestamp: datetime = Field(default_factory=datetime.now)


class GuardianEvent(BaseModel):
    """Guardian Agent integrity monitoring event"""
    event_id: str
    event_type: str
    severity: str
    entity_id: str
    data_delta_summary: str
    expected_behavior: str
    actual_behavior: str
    recommendation: str
    snapshot_id: str
    timestamp: datetime = Field(default_factory=datetime.now)


class AIExplanation(BaseModel):
    """AI-generated explanation for decisions"""
    entity_id: str
    risk_summary: str
    evidence: List[str]
    recommendations: List[str]
    confidence_statement: str
    timestamp: datetime = Field(default_factory=datetime.now)


class UserInteraction(BaseModel):
    """User interaction with the system"""
    user_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    action_type: str  # "VIEW" | "DRILL_DOWN" | "EXPORT"
    entity_context: str
    session_id: str


class DashboardAction(BaseModel):
    """User action from dashboard"""
    user_id: str
    role: str
    action: str  # "ACKNOWLEDGE" | "DISMISS" | "ESCALATE"
    entity_id: str
    comment: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class FeatureVector(BaseModel):
    """Feature vector for agent analysis"""
    entity_id: str
    features: Dict[str, float]
    feature_metadata: Dict[str, Any] = Field(default_factory=dict)
    snapshot_id: str
    timestamp: datetime = Field(default_factory=datetime.now)


class AuditEvent(BaseModel):
    """Audit trail event"""
    event_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    event_type: str
    entity_id: Optional[str] = None
    user_id: Optional[str] = None
    component_name: str
    action_taken: str
    details: Dict[str, Any] = Field(default_factory=dict)