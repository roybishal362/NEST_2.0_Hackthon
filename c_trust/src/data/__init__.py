"""C-TRUST Data Module
========================================
Complete data processing pipeline for clinical trial data.

Exports:
- Data models (Pydantic)
- Data ingestion engine
- Feature engineering
"""

from src.data.features import (
    FeatureCalculator,
    FeatureCategory,
    FeatureDefinition,
    FeatureEngineeringEngine,
    FeatureLevel,
    FeatureRegistry,
)
from src.data.ingestion import (
    DataIngestionEngine,
    ExcelFileReader,
    FileTypeDetector,
    StudyDiscovery,
    DataValidator,
    BatchProcessor,
)
from src.data.models import (
    CodingReport,
    DataSnapshot,
    EDCMetrics,
    EDRR,
    FileType,
    MissingPages,
    RiskLevel,
    SAEDashboard,
    Site,
    Study,
    StudyPhase,
    StudyStatus,
    Subject,
    VisitProjection,
)

__all__ = [
    # Models
    "Study",
    "Site",
    "Subject",
    "EDCMetrics",
    "VisitProjection",
    "MissingPages",
    "SAEDashboard",
    "CodingReport",
    "EDRR",
    "DataSnapshot",
    "FileType",
    "RiskLevel",
    "StudyPhase",
    "StudyStatus",
    # Ingestion
    "DataIngestionEngine",
    "ExcelFileReader",
    "StudyDiscovery",
    "FileTypeDetector",
    "DataValidator",
    "BatchProcessor",
    # Features
    "FeatureEngineeringEngine",
    "FeatureCalculator",
    "FeatureRegistry",
    "FeatureDefinition",
    "FeatureCategory",
    "FeatureLevel",
]
