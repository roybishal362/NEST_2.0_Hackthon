"""
C-TRUST Data Models
========================================
Production-ready Pydantic models for clinical trial data structures.

Models defined:
- Study: Top-level study information
- Site: Clinical site data
- Subject: Patient/subject data  
- EDCMetrics: Electronic Data Capture metrics
- VisitProjection: Visit schedule and projections
- MissingPages: Missing CRF pages tracking
- SAEDashboard: Serious Adverse Event data
- CodingReport: Medical/drug coding status
- EDRR: Edit Data Review Report
- DataSnapshot: Versioned data snapshot

All models include:
- Type validation via Pydantic
- Optional fields with sensible defaults
- Computed properties for derived metrics
- JSON serialization support
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, computed_field


# ========================================
# ENUMERATIONS
# ========================================

class StudyPhase(str, Enum):
    """Clinical trial phase"""
    PHASE_1 = "Phase 1"
    PHASE_2 = "Phase 2"
    PHASE_3 = "Phase 3"
    PHASE_4 = "Phase 4"
    UNKNOWN = "Unknown"


class StudyStatus(str, Enum):
    """Study operational status"""
    ONGOING = "Ongoing"
    ENROLLMENT_COMPLETE = "Enrollment Complete"
    ON_HOLD = "On Hold"
    COMPLETED = "Completed"
    TERMINATED = "Terminated"


class RiskLevel(str, Enum):
    """Risk severity classification"""
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    UNKNOWN = "Unknown"


class FileType(str, Enum):
    """NEST 2.0 file type classifications"""
    EDC_METRICS = "edc_metrics"
    VISIT_PROJECTION = "visit_projection"
    MISSING_PAGES = "missing_pages"
    MISSING_LAB = "missing_lab"
    SAE_DM = "sae_dm"
    SAE_SAFETY = "sae_safety"
    INACTIVATED = "inactivated"
    EDRR = "edrr"
    MEDDRA = "meddra"
    WHODD = "whodd"


# ========================================
# BASE MODELS
# ========================================

class BaseDataModel(BaseModel):
    """
    Base model for all data structures.
    
    Provides:
    - JSON serialization configuration
    - Created/updated timestamps
    - Common validation rules
    """
    
    model_config = ConfigDict(
        # Allow arbitrary types for complex objects
        arbitrary_types_allowed=True,
        # Validate assignments after model creation
        validate_assignment=True,
        # Use enum values in JSON
        use_enum_values=True,
        # Populate by field name (not alias)
        populate_by_name=True,
    )
    
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ========================================
# STUDY-LEVEL MODELS
# ========================================

class Study(BaseDataModel):
    """
    Top-level study information.
    
    Represents a clinical trial with its core attributes and metrics.
    """
    
    study_id: str = Field(..., description="Unique study identifier (e.g., STUDY_01)")
    study_name: Optional[str] = Field(None, description="Study name/title")
    protocol_number: Optional[str] = Field(None, description="Protocol number")
    
    # Study characteristics
    phase: StudyPhase = Field(StudyPhase.UNKNOWN, description="Clinical trial phase")
    status: StudyStatus = Field(StudyStatus.ONGOING, description="Current study status")
    indication: Optional[str] = Field(None, description="Therapeutic indication")
    
    # Enrollment metrics
    target_enrollment: Optional[int] = Field(None, description="Target subject count", ge=0)
    actual_enrollment: Optional[int] = Field(None, description="Actual enrolled subjects", ge=0)
    active_sites: Optional[int] = Field(None, description="Number of active sites", ge=0)
    
    # Timeline
    first_patient_in: Optional[datetime] = Field(None, description="First patient enrolled date")
    last_patient_in: Optional[datetime] = Field(None, description="Last patient enrolled date")
    database_lock_target: Optional[datetime] = Field(None, description="Target database lock date")
    
    # Data quality
    dqi_score: Optional[float] = Field(None, description="Data Quality Index score", ge=0, le=100)
    risk_level: RiskLevel = Field(RiskLevel.UNKNOWN, description="Overall risk classification")
    
    # File tracking
    available_files: Dict[FileType, bool] = Field(default_factory=dict)
    last_data_refresh: Optional[datetime] = Field(None, description="Last data snapshot timestamp")
    
    @computed_field
    @property
    def enrollment_percentage(self) -> Optional[float]:
        """Calculate enrollment completion percentage"""
        if self.target_enrollment and self.actual_enrollment:
            return round((self.actual_enrollment / self.target_enrollment) * 100, 2)
        return None
    
    @computed_field
    @property
    def is_enrollment_complete(self) -> bool:
        """Check if enrollment is complete"""
        if self.enrollment_percentage:
            return self.enrollment_percentage >= 100.0
        return False


class Site(BaseDataModel):
    """
    Clinical site information.
    
    Represents a site participating in a clinical trial.
    """
    
    site_id: str = Field(..., description="Unique site identifier")
    study_id: str = Field(..., description="Parent study identifier")
    site_number: Optional[str] = Field(None, description="Site number")
    
    # Site details
    country: Optional[str] = Field(None, description="Site country")
    region: Optional[str] = Field(None, description="Geographic region")
    status: Optional[str] = Field(None, description="Site status (active, closed, etc.)")
    
    # Enrollment
    target_subjects: Optional[int] = Field(None, ge=0)
    enrolled_subjects: Optional[int] = Field(None, ge=0)
    
    # Data quality metrics
    dqi_score: Optional[float] = Field(None, ge=0, le=100)
    risk_level: RiskLevel = Field(RiskLevel.UNKNOWN)
    
    # Issue tracking
    open_queries: Optional[int] = Field(None, ge=0)
    overdue_queries: Optional[int] = Field(None, ge=0)
    missing_pages: Optional[int] = Field(None, ge=0)


class Subject(BaseDataModel):
    """
    Subject/Patient information (anonymized).
    
    Represents an anonymized clinical trial participant.
    """
    
    subject_id: str = Field(..., description="Anonymized subject identifier")
    study_id: str = Field(..., description="Parent study identifier")
    site_id: str = Field(..., description="Parent site identifier")
    
    # Subject status
    enrollment_date: Optional[datetime] = None
    status: Optional[str] = Field(None, description="Subject status (active, completed, withdrawn)")
    
    # Visit tracking
    completed_visits: Optional[int] = Field(None, ge=0)
    expected_visits: Optional[int] = Field(None, ge=0)
    next_visit_date: Optional[datetime] = None
    
    # Data quality
    has_missing_data: bool = False
    has_safety_events: bool = False
    has_protocol_deviations: bool = False


# ========================================
# FILE-SPECIFIC MODELS
# ========================================

class EDCMetrics(BaseDataModel):
    """
    Electronic Data Capture metrics from CPID_EDC_Metrics files.
    
    Contains operational metrics for electronic data capture system.
    """
    
    study_id: str
    snapshot_date: datetime
    
    # Form metrics
    total_forms: Optional[int] = Field(None, ge=0)
    completed_forms: Optional[int] = Field(None, ge=0)
    pending_forms: Optional[int] = Field(None, ge=0)
    
    # Query metrics
    total_queries: Optional[int] = Field(None, ge=0)
    open_queries: Optional[int] = Field(None, ge=0)
    closed_queries: Optional[int] = Field(None, ge=0)
    overdue_queries: Optional[int] = Field(None, ge=0)
    
    # Data entry metrics
    avg_data_entry_lag_days: Optional[float] = Field(None, ge=0)
    forms_entered_last_30_days: Optional[int] = Field(None, ge=0)
    
    # Quality metrics
    edit_check_pass_rate: Optional[float] = Field(None, ge=0, le=100)
    first_pass_rate: Optional[float] = Field(None, ge=0, le=100)
    
    @computed_field
    @property
    def query_closure_rate(self) -> Optional[float]:
        """Calculate percentage of closed queries"""
        if self.total_queries and self.closed_queries is not None:
            return round((self.closed_queries / self.total_queries) * 100, 2)
        return None


class VisitProjection(BaseDataModel):
    """
    Visit projection and tracking data.
    
    Tracks patient visit schedules, completions, and projections.
    """
    
    study_id: str
    snapshot_date: datetime
    
    # Visit summary
    total_planned_visits: Optional[int] = Field(None, ge=0)
    completed_visits: Optional[int] = Field(None, ge=0)
    upcoming_visits: Optional[int] = Field(None, ge=0)
    overdue_visits: Optional[int] = Field(None, ge=0)
    
    # Timing metrics
    avg_visit_delay_days: Optional[float] = Field(None, ge=0)
    max_visit_delay_days: Optional[int] = Field(None, ge=0)
    
    # Projections
    projected_completion_date: Optional[datetime] = None
    on_track_for_timeline: bool = True
    
    @computed_field
    @property
    def visit_completion_rate(self) -> Optional[float]:
        """Calculate visit completion percentage"""
        if self.total_planned_visits and self.completed_visits is not None:
            return round((self.completed_visits / self.total_planned_visits) * 100, 2)
        return None


class MissingPages(BaseDataModel):
    """
    Missing CRF pages tracking.
    
    Identifies incomplete case report forms.
    """
    
    study_id: str
    snapshot_date: datetime
    
    # Page metrics
    total_expected_pages: Optional[int] = Field(None, ge=0)
    missing_pages_count: Optional[int] = Field(None, ge=0)
    
    # Breakdown by type
    missing_by_site: Dict[str, int] = Field(default_factory=dict)
    missing_by_form_type: Dict[str, int] = Field(default_factory=dict)
    
    # Criticality
    critical_missing_pages: Optional[int] = Field(None, ge=0)
    
    @computed_field
    @property
    def missing_pages_percentage(self) -> Optional[float]:
        """Calculate percentage of missing pages"""
        if self.total_expected_pages and self.missing_pages_count is not None:
            return round((self.missing_pages_count / self.total_expected_pages) * 100, 2)
        return None


class SAEDashboard(BaseDataModel):
    """
    Serious Adverse Event (SAE) dashboard data.
    
    Critical safety monitoring metrics.
    """
    
    study_id: str
    snapshot_date: datetime
    source: str = Field(..., description="Source file (DM or Safety)")
    
    # SAE counts
    total_saes: Optional[int] = Field(None, ge=0)
    open_saes: Optional[int] = Field(None, ge=0)
    closed_saes: Optional[int] = Field(None, ge=0)
    
    # Severity breakdown
    fatal_saes: Optional[int] = Field(None, ge=0)
    life_threatening_saes: Optional[int] = Field(None, ge=0)
    hospitalization_saes: Optional[int] = Field(None, ge=0)
    
    # Timing
    avg_reporting_delay_days: Optional[float] = Field(None, ge=0)
    overdue_saes: Optional[int] = Field(None, ge=0)
    max_sae_age_days: Optional[int] = Field(None, ge=0)
    
    # Reconciliation
    unreconciled_saes: Optional[int] = Field(None, ge=0)


class CodingReport(BaseDataModel):
    """
    Medical/Drug coding status.
    
    Tracks MedDRA and WHODD coding completeness.
    """
    
    study_id: str
    snapshot_date: datetime
    coding_dictionary: str = Field(..., description="MedDRA or WHODD")
    
    # Coding metrics
    total_terms: Optional[int] = Field(None, ge=0)
    coded_terms: Optional[int] = Field(None, ge=0)
    uncoded_terms: Optional[int] = Field(None, ge=0)
    
    # Auto-coding
    auto_coded_terms: Optional[int] = Field(None, ge=0)
    manually_coded_terms: Optional[int] = Field(None, ge=0)
    
    @computed_field
    @property
    def coding_completion_rate(self) -> Optional[float]:
        """Calculate coding completion percentage"""
        if self.total_terms and self.coded_terms is not None:
            return round((self.coded_terms / self.total_terms) * 100, 2)
        return None


class EDRR(BaseDataModel):
    """
    Edit Data Review Report.
    
    Tracks edit checks and data review findings.
    """
    
    study_id: str
    snapshot_date: datetime
    
    # Edit check metrics
    total_edit_checks: Optional[int] = Field(None, ge=0)
    failed_edit_checks: Optional[int] = Field(None, ge=0)
    
    # Query generation
    queries_generated: Optional[int] = Field(None, ge=0)
    queries_resolved: Optional[int] = Field(None, ge=0)
    
    # Review status
    forms_under_review: Optional[int] = Field(None, ge=0)
    forms_approved: Optional[int] = Field(None, ge=0)


# ========================================
# SNAPSHOT & VERSIONING
# ========================================

class DataSnapshot(BaseDataModel):
    """
    Versioned snapshot of study data.
    
    Enables temporal analysis and drift detection.
    """
    
    snapshot_id: str = Field(..., description="Unique snapshot identifier")
    study_id: str
    snapshot_date: datetime
    
    # Snapshot metadata
    snapshot_version: int = Field(..., ge=1)
    is_baseline: bool = False
    is_latest: bool = True
    
    # Data references
    edc_metrics_id: Optional[str] = None
    visit_projection_id: Optional[str] = None
    missing_pages_id: Optional[str] = None
    sae_dashboard_id: Optional[str] = None
    
    # Computed metrics (stored with snapshot)
    dqi_score: Optional[float] = Field(None, ge=0, le=100)
    risk_level: RiskLevel = Field(RiskLevel.UNKNOWN)
    
    # Audit trail
    created_by: Optional[str] = None
    data_hash: Optional[str] = Field(None, description="Hash for integrity checking")


# ========================================
# EXPORT ALL MODELS
# ========================================

__all__ = [
    # Enums
    "StudyPhase",
    "StudyStatus",
    "RiskLevel",
    "FileType",
    # Core models
    "Study",
    "Site",
    "Subject",
    # File-specific models
    "EDCMetrics",
    "VisitProjection",
    "MissingPages",
    "SAEDashboard",
    "CodingReport",
    "EDRR",
    # Versioning
    "DataSnapshot",
]
