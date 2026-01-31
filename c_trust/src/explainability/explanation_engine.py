"""
C-TRUST Explanation Generation Engine
======================================
Template-based explanation engine with evidence linking and confidence reporting.

Key Features:
- Controlled template-based explanations (prevents hallucination)
- Evidence linking to underlying data
- Confidence level reporting
- Safe explanations (no medical claims)

"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import re

from src.core import get_logger

logger = get_logger(__name__)


class ConfidenceLevel(str, Enum):
    """Confidence levels for explanations"""
    VERY_HIGH = "VERY_HIGH"  # >= 0.9
    HIGH = "HIGH"            # >= 0.75
    MEDIUM = "MEDIUM"        # >= 0.5
    LOW = "LOW"              # >= 0.25
    VERY_LOW = "VERY_LOW"    # < 0.25


class ExplanationType(str, Enum):
    """Types of explanations"""
    RISK_ASSESSMENT = "RISK_ASSESSMENT"
    DQI_SCORE = "DQI_SCORE"
    AGENT_SIGNAL = "AGENT_SIGNAL"
    CONSENSUS_DECISION = "CONSENSUS_DECISION"
    GUARDIAN_ALERT = "GUARDIAN_ALERT"
    RECOMMENDATION = "RECOMMENDATION"


@dataclass
class EvidenceItem:
    """
    Evidence item linking explanation to underlying data.
    
    Attributes:
        evidence_id: Unique identifier for this evidence
        source_type: Type of data source (e.g., "EDC_Metrics", "SAE_Dashboard")
        source_field: Specific field in the source
        value: The actual value from the data
        description: Human-readable description
        timestamp: When this evidence was captured
        relevance_score: How relevant this evidence is (0-1)
    """
    evidence_id: str
    source_type: str
    source_field: str
    value: Any
    description: str
    timestamp: datetime = field(default_factory=datetime.now)
    relevance_score: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "evidence_id": self.evidence_id,
            "source_type": self.source_type,
            "source_field": self.source_field,
            "value": str(self.value),
            "description": self.description,
            "timestamp": self.timestamp.isoformat(),
            "relevance_score": self.relevance_score,
        }


@dataclass
class ExplanationTemplate:
    """
    Template for generating controlled explanations.
    
    Templates use placeholders like {risk_level}, {entity_id}, etc.
    that are filled in with actual values.
    """
    template_id: str
    explanation_type: ExplanationType
    template_text: str
    required_fields: List[str]
    optional_fields: List[str] = field(default_factory=list)
    safety_disclaimer: str = ""
    
    def render(self, context: Dict[str, Any]) -> str:
        """
        Render template with context values.
        
        Args:
            context: Dictionary of values to fill in template
        
        Returns:
            Rendered explanation text
        """
        # Verify required fields
        missing = [f for f in self.required_fields if f not in context]
        if missing:
            raise ValueError(f"Missing required fields: {missing}")
        
        # Render template
        text = self.template_text
        for key, value in context.items():
            placeholder = "{" + key + "}"
            text = text.replace(placeholder, str(value))
        
        # Add safety disclaimer if present
        if self.safety_disclaimer:
            text = f"{text}\n\n{self.safety_disclaimer}"
        
        return text


@dataclass
class ExplanationResult:
    """
    Result of explanation generation.
    
    Attributes:
        explanation_id: Unique identifier
        entity_id: Entity being explained
        explanation_type: Type of explanation
        summary: Brief summary of the explanation
        detailed_explanation: Full explanation text
        evidence: List of evidence items
        confidence: Confidence in the explanation (0-1)
        confidence_level: Categorical confidence level
        confidence_statement: Human-readable confidence statement
        recommendations: List of recommended actions
        template_id: ID of template used (for traceability)
        timestamp: When explanation was generated
        metadata: Additional metadata
    """
    explanation_id: str
    entity_id: str
    explanation_type: ExplanationType
    summary: str
    detailed_explanation: str
    evidence: List[EvidenceItem]
    confidence: float
    confidence_level: ConfidenceLevel
    confidence_statement: str
    recommendations: List[str]
    template_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "explanation_id": self.explanation_id,
            "entity_id": self.entity_id,
            "explanation_type": self.explanation_type.value,
            "summary": self.summary,
            "detailed_explanation": self.detailed_explanation,
            "evidence": [e.to_dict() for e in self.evidence],
            "confidence": self.confidence,
            "confidence_level": self.confidence_level.value,
            "confidence_statement": self.confidence_statement,
            "recommendations": self.recommendations,
            "template_id": self.template_id,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }
    
    def has_medical_claims(self) -> bool:
        """Check if explanation contains medical claims (should always be False)"""
        # Keywords that indicate medical claims
        medical_keywords = [
            "diagnos", "treat", "cure", "prescri", "therap",
            "patient outcome", "clinical decision", "health condition",
            "disease", "symptom", "prognosis", "recommend treatment"
        ]
        
        # Safe phrases that should NOT trigger detection (disclaimers)
        safe_phrases = [
            "does not constitute medical advice",
            "not medical advice",
            "operational data quality",
            "data quality assessment",
            "no medical claims",
        ]
        
        text = f"{self.summary} {self.detailed_explanation}".lower()
        
        # Check if text contains safe disclaimer phrases - if so, don't flag
        for safe in safe_phrases:
            if safe in text:
                # Remove the safe phrase before checking for medical keywords
                text = text.replace(safe, "")
        
        return any(kw in text for kw in medical_keywords)


class ExplanationEngine:
    """
    Template-based explanation generation engine.
    
    Generates controlled, traceable explanations for AI decisions
    using predefined templates. Ensures no hallucination by using
    only template-based text generation.
    
    **Validates: Requirements 7.1, 7.2, 7.4, 7.5**
    """
    
    # Safety disclaimer added to all explanations
    SAFETY_DISCLAIMER = (
        "Note: This is an operational data quality assessment only. "
        "It does not constitute medical advice or clinical interpretation."
    )
    
    def __init__(self):
        """Initialize explanation engine with default templates"""
        self.templates: Dict[str, ExplanationTemplate] = {}
        self._register_default_templates()
        logger.info("ExplanationEngine initialized with default templates")
    
    def _register_default_templates(self):
        """Register default explanation templates"""
        # Risk Assessment Template
        self.register_template(ExplanationTemplate(
            template_id="risk_assessment_standard",
            explanation_type=ExplanationType.RISK_ASSESSMENT,
            template_text=(
                "Risk Assessment for {entity_id}\n\n"
                "Risk Level: {risk_level}\n"
                "Risk Score: {risk_score}/100\n"
                "Confidence: {confidence_pct}%\n\n"
                "Summary: {summary}\n\n"
                "Key Findings:\n{findings}\n\n"
                "Contributing Factors:\n{factors}"
            ),
            required_fields=["entity_id", "risk_level", "risk_score", "confidence_pct", "summary"],
            optional_fields=["findings", "factors"],
            safety_disclaimer=self.SAFETY_DISCLAIMER,
        ))
        
        # DQI Score Template
        self.register_template(ExplanationTemplate(
            template_id="dqi_score_standard",
            explanation_type=ExplanationType.DQI_SCORE,
            template_text=(
                "Data Quality Index for {entity_id}\n\n"
                "Overall Score: {overall_score}/100 ({band})\n"
                "Confidence: {confidence_pct}%\n\n"
                "Dimension Breakdown:\n"
                "- Safety: {safety_score}/100 (weight: 35%)\n"
                "- Compliance: {compliance_score}/100 (weight: 25%)\n"
                "- Completeness: {completeness_score}/100 (weight: 20%)\n"
                "- Operations: {operations_score}/100 (weight: 15%)\n\n"
                "Primary Drivers: {drivers}"
            ),
            required_fields=["entity_id", "overall_score", "band", "confidence_pct"],
            optional_fields=["safety_score", "compliance_score", "completeness_score", 
                           "operations_score", "drivers"],
            safety_disclaimer=self.SAFETY_DISCLAIMER,
        ))
        
        # Agent Signal Template
        self.register_template(ExplanationTemplate(
            template_id="agent_signal_standard",
            explanation_type=ExplanationType.AGENT_SIGNAL,
            template_text=(
                "Agent Signal: {agent_name}\n\n"
                "Entity: {entity_id}\n"
                "Signal Type: {signal_type}\n"
                "Severity: {severity}\n"
                "Confidence: {confidence_pct}%\n\n"
                "Analysis: {analysis}\n\n"
                "Evidence:\n{evidence_list}"
            ),
            required_fields=["agent_name", "entity_id", "signal_type", "severity", "confidence_pct"],
            optional_fields=["analysis", "evidence_list"],
            safety_disclaimer=self.SAFETY_DISCLAIMER,
        ))
        
        # Consensus Decision Template
        self.register_template(ExplanationTemplate(
            template_id="consensus_decision_standard",
            explanation_type=ExplanationType.CONSENSUS_DECISION,
            template_text=(
                "Consensus Decision for {entity_id}\n\n"
                "Final Risk Level: {risk_level}\n"
                "Consensus Confidence: {confidence_pct}%\n"
                "Agent Agreement: {agreement_pct}%\n\n"
                "Contributing Agents: {agents}\n\n"
                "Decision Rationale: {rationale}\n\n"
                "Recommended Actions:\n{actions}"
            ),
            required_fields=["entity_id", "risk_level", "confidence_pct", "agreement_pct"],
            optional_fields=["agents", "rationale", "actions"],
            safety_disclaimer=self.SAFETY_DISCLAIMER,
        ))
        
        # Guardian Alert Template
        self.register_template(ExplanationTemplate(
            template_id="guardian_alert_standard",
            explanation_type=ExplanationType.GUARDIAN_ALERT,
            template_text=(
                "Guardian System Alert\n\n"
                "Alert Type: {alert_type}\n"
                "Severity: {severity}\n"
                "Entity: {entity_id}\n\n"
                "Issue Detected: {issue_description}\n\n"
                "Expected Behavior: {expected}\n"
                "Actual Behavior: {actual}\n\n"
                "Recommendation: {recommendation}"
            ),
            required_fields=["alert_type", "severity", "entity_id", "issue_description"],
            optional_fields=["expected", "actual", "recommendation"],
            safety_disclaimer="",  # Guardian alerts are for administrators only
        ))
        
        # Recommendation Template
        self.register_template(ExplanationTemplate(
            template_id="recommendation_standard",
            explanation_type=ExplanationType.RECOMMENDATION,
            template_text=(
                "Recommendation for {entity_id}\n\n"
                "Priority: {priority}\n"
                "Action Type: {action_type}\n"
                "Target Role: {target_role}\n\n"
                "Description: {description}\n\n"
                "Supporting Evidence:\n{evidence_summary}\n\n"
                "Suggested Timeline: {timeline}"
            ),
            required_fields=["entity_id", "priority", "action_type", "description"],
            optional_fields=["target_role", "evidence_summary", "timeline"],
            safety_disclaimer=self.SAFETY_DISCLAIMER,
        ))
    
    def register_template(self, template: ExplanationTemplate) -> None:
        """Register a new explanation template"""
        self.templates[template.template_id] = template
        logger.debug(f"Registered template: {template.template_id}")
    
    def get_template(self, template_id: str) -> Optional[ExplanationTemplate]:
        """Get template by ID"""
        return self.templates.get(template_id)
    
    def generate_explanation(
        self,
        template_id: str,
        context: Dict[str, Any],
        evidence: List[EvidenceItem],
        confidence: float,
        recommendations: Optional[List[str]] = None,
    ) -> ExplanationResult:
        """
        Generate explanation using template.
        
        Args:
            template_id: ID of template to use
            context: Values to fill in template
            evidence: Evidence items linking to data
            confidence: Confidence score (0-1)
            recommendations: Optional list of recommendations
        
        Returns:
            ExplanationResult with generated explanation
        """
        template = self.templates.get(template_id)
        if not template:
            raise ValueError(f"Unknown template: {template_id}")
        
        # Generate unique explanation ID
        explanation_id = f"EXP_{datetime.now().strftime('%Y%m%d%H%M%S')}_{context.get('entity_id', 'UNKNOWN')}"
        
        # Render template
        detailed_explanation = template.render(context)
        
        # Generate summary (first sentence or line)
        summary = self._generate_summary(detailed_explanation, context)
        
        # Calculate confidence level
        confidence_level = self._calculate_confidence_level(confidence)
        confidence_statement = self._generate_confidence_statement(confidence, confidence_level)
        
        result = ExplanationResult(
            explanation_id=explanation_id,
            entity_id=context.get("entity_id", "UNKNOWN"),
            explanation_type=template.explanation_type,
            summary=summary,
            detailed_explanation=detailed_explanation,
            evidence=evidence,
            confidence=confidence,
            confidence_level=confidence_level,
            confidence_statement=confidence_statement,
            recommendations=recommendations or [],
            template_id=template_id,
            metadata={"context_keys": list(context.keys())},
        )
        
        # Verify no medical claims
        if result.has_medical_claims():
            logger.warning(f"Explanation {explanation_id} may contain medical claims - review required")
        
        logger.info(f"Generated explanation {explanation_id} for {result.entity_id}")
        return result
    
    def _generate_summary(self, detailed: str, context: Dict[str, Any]) -> str:
        """Generate brief summary from detailed explanation"""
        # Extract first meaningful line
        lines = detailed.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line and not line.endswith(':'):
                # Clean up the line
                if len(line) > 150:
                    line = line[:147] + "..."
                return line
        
        # Fallback to entity-based summary
        entity_id = context.get("entity_id", "Entity")
        risk_level = context.get("risk_level", "")
        if risk_level:
            return f"{entity_id}: {risk_level} risk assessment"
        return f"Assessment for {entity_id}"
    
    def _calculate_confidence_level(self, confidence: float) -> ConfidenceLevel:
        """Calculate categorical confidence level"""
        if confidence >= 0.9:
            return ConfidenceLevel.VERY_HIGH
        elif confidence >= 0.75:
            return ConfidenceLevel.HIGH
        elif confidence >= 0.5:
            return ConfidenceLevel.MEDIUM
        elif confidence >= 0.25:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW
    
    def _generate_confidence_statement(
        self, 
        confidence: float, 
        level: ConfidenceLevel
    ) -> str:
        """Generate human-readable confidence statement"""
        statements = {
            ConfidenceLevel.VERY_HIGH: (
                f"This assessment has very high confidence ({confidence:.0%}). "
                "Multiple data sources strongly support this conclusion."
            ),
            ConfidenceLevel.HIGH: (
                f"This assessment has high confidence ({confidence:.0%}). "
                "The available data supports this conclusion."
            ),
            ConfidenceLevel.MEDIUM: (
                f"This assessment has moderate confidence ({confidence:.0%}). "
                "Some data limitations may affect accuracy."
            ),
            ConfidenceLevel.LOW: (
                f"This assessment has low confidence ({confidence:.0%}). "
                "Limited data available - additional review recommended."
            ),
            ConfidenceLevel.VERY_LOW: (
                f"This assessment has very low confidence ({confidence:.0%}). "
                "Insufficient data for reliable assessment - manual review required."
            ),
        }
        return statements.get(level, f"Confidence: {confidence:.0%}")
    
    def explain_risk_assessment(
        self,
        entity_id: str,
        risk_level: str,
        risk_score: float,
        confidence: float,
        findings: List[str],
        factors: List[str],
        evidence: List[EvidenceItem],
        recommendations: Optional[List[str]] = None,
    ) -> ExplanationResult:
        """
        Generate explanation for risk assessment.
        
        Convenience method for risk assessment explanations.
        """
        context = {
            "entity_id": entity_id,
            "risk_level": risk_level,
            "risk_score": f"{risk_score:.1f}",
            "confidence_pct": f"{confidence * 100:.0f}",
            "summary": f"{risk_level} risk detected based on {len(factors)} contributing factors.",
            "findings": "\n".join(f"- {f}" for f in findings) if findings else "No specific findings.",
            "factors": "\n".join(f"- {f}" for f in factors) if factors else "No specific factors identified.",
        }
        
        return self.generate_explanation(
            template_id="risk_assessment_standard",
            context=context,
            evidence=evidence,
            confidence=confidence,
            recommendations=recommendations,
        )
    
    def explain_dqi_score(
        self,
        entity_id: str,
        overall_score: float,
        band: str,
        confidence: float,
        dimension_scores: Dict[str, float],
        drivers: List[str],
        evidence: List[EvidenceItem],
    ) -> ExplanationResult:
        """
        Generate explanation for DQI score.
        
        Convenience method for DQI explanations.
        """
        context = {
            "entity_id": entity_id,
            "overall_score": f"{overall_score:.1f}",
            "band": band,
            "confidence_pct": f"{confidence * 100:.0f}",
            "safety_score": f"{dimension_scores.get('safety', 0):.1f}",
            "compliance_score": f"{dimension_scores.get('compliance', 0):.1f}",
            "completeness_score": f"{dimension_scores.get('completeness', 0):.1f}",
            "operations_score": f"{dimension_scores.get('operations', 0):.1f}",
            "drivers": ", ".join(drivers) if drivers else "No specific drivers identified.",
        }
        
        return self.generate_explanation(
            template_id="dqi_score_standard",
            context=context,
            evidence=evidence,
            confidence=confidence,
        )
    
    def explain_consensus_decision(
        self,
        entity_id: str,
        risk_level: str,
        confidence: float,
        agreement_ratio: float,
        contributing_agents: List[str],
        rationale: str,
        actions: List[str],
        evidence: List[EvidenceItem],
    ) -> ExplanationResult:
        """
        Generate explanation for consensus decision.
        
        Convenience method for consensus explanations.
        """
        context = {
            "entity_id": entity_id,
            "risk_level": risk_level,
            "confidence_pct": f"{confidence * 100:.0f}",
            "agreement_pct": f"{agreement_ratio * 100:.0f}",
            "agents": ", ".join(contributing_agents) if contributing_agents else "No agents contributed.",
            "rationale": rationale or "No specific rationale provided.",
            "actions": "\n".join(f"- {a}" for a in actions) if actions else "No specific actions recommended.",
        }
        
        return self.generate_explanation(
            template_id="consensus_decision_standard",
            context=context,
            evidence=evidence,
            confidence=confidence,
            recommendations=actions,
        )


__all__ = [
    "ExplanationEngine",
    "ExplanationResult",
    "ExplanationTemplate",
    "EvidenceItem",
    "ConfidenceLevel",
    "ExplanationType",
]
