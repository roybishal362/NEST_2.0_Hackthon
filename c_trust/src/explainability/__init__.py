"""
Explainable AI Module for C-TRUST
=================================
Provides template-based explanation generation with Groq API integration,
evidence linking, and confidence level reporting.

Key Components:
- ExplanationEngine: Template-based explanation generation
- GroqExplainer: LLM-powered explanation enhancement using open-source models
- EvidenceLinker: Links explanations to underlying data
- ConfidenceReporter: Reports confidence levels for explanations

**Validates: Requirements 7.1, 7.4**
"""

from .explanation_engine import (
    ExplanationEngine,
    ExplanationResult,
    ExplanationTemplate,
    EvidenceItem,
    ConfidenceLevel,
)
from .groq_explainer import GroqExplainer
from .evidence_linker import EvidenceLinker

__all__ = [
    "ExplanationEngine",
    "ExplanationResult",
    "ExplanationTemplate",
    "EvidenceItem",
    "ConfidenceLevel",
    "GroqExplainer",
    "EvidenceLinker",
]
