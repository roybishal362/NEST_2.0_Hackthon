"""
C-TRUST Data Quality Index Module
=================================

Data Quality Index calculation engine providing single, explainable
scores for clinical trial data readiness assessment.

DQI Formula (from Requirements 4.1):
    DQI = Safety(35%) + Compliance(25%) + Completeness(20%) + Operations(15%)

DQI Bands (from Requirements 4.4):
    - GREEN:  85-100 (Analysis-ready)
    - AMBER:  65-84  (Minor issues)
    - ORANGE: 40-64  (Attention needed)
    - RED:    <40    (Not submission-ready)
"""

from .dqi_engine import (
    DQICalculationEngine,
    DQIResult,
    DimensionScore,
    DQIDimension,
    DQI_WEIGHTS,
    DQI_BAND_THRESHOLDS,
)

from .change_explanation import (
    DQIChangeExplanationEngine,
    DQIChangeExplanation,
    DimensionChange,
    ChangeDirection,
    ChangeSeverity,
)

__version__ = "1.0.0"

__all__ = [
    # DQI Calculation
    "DQICalculationEngine",
    "DQIResult",
    "DimensionScore",
    "DQIDimension",
    "DQI_WEIGHTS",
    "DQI_BAND_THRESHOLDS",
    # Change Explanation
    "DQIChangeExplanationEngine",
    "DQIChangeExplanation",
    "DimensionChange",
    "ChangeDirection",
    "ChangeSeverity",
]