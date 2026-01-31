"""
C-TRUST Governance Module
=========================
Provides configuration management, version control, and governance
capabilities for the Clinical AI System.

Key Components:
- VersionedConfigManager: Configuration management with version control
- ConfigChangeRequest: Human approval workflow for changes
- CalibrationRecommender: Guardian-driven calibration recommendations

"""

from .versioned_config import (
    VersionedConfigManager,
    ConfigVersion,
    ConfigChangeRequest,
    ConfigChangeStatus,
    ConfigChangeType,
    versioned_config_manager,
)

from .calibration_recommender import (
    CalibrationRecommender,
    CalibrationRecommendation,
    CalibrationSource,
    calibration_recommender,
)

__all__ = [
    # Versioned Configuration
    "VersionedConfigManager",
    "ConfigVersion",
    "ConfigChangeRequest",
    "ConfigChangeStatus",
    "ConfigChangeType",
    "versioned_config_manager",
    # Calibration
    "CalibrationRecommender",
    "CalibrationRecommendation",
    "CalibrationSource",
    "calibration_recommender",
]
