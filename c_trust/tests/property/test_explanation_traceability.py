"""
Property-Based Tests for Explanation Traceability and Safety
============================================================
Tests Property 10: Explanation Traceability and Safety

**Property 10: Explanation Traceability and Safety**
*For any* AI-generated explanation or risk assessment, the system should provide 
structured explanations with clear links to underlying data, use only controlled 
templates to prevent hallucination, and never make medical claims.

**Validates: Requirements 7.1, 7.2, 7.5**

This test uses Hypothesis to generate various explanation scenarios and verify
that the explanation engine maintains traceability and safety constraints.
"""

from datetime import datetime
from typing import Any, Dict, List

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck, assume

from src.explainability import (
    ExplanationEngine,
    ExplanationResult,
    ExplanationTemplate,
    EvidenceItem,
    ConfidenceLevel,
    EvidenceLinker,
)
from src.explainability.explanation_engine import ExplanationType


# ========================================
# TEST STRATEGIES
# ========================================

@st.composite
def entity_id_strategy(draw):
    """Generate valid entity IDs"""
    prefix = draw(st.sampled_from(["STUDY", "SITE", "SUBJECT"]))
    number = draw(st.integers(min_value=1, max_value=999))
    return f"{prefix}_{number:03d}"


@st.composite
def risk_level_strategy(draw):
    """Generate valid risk levels"""
    return draw(st.sampled_from(["LOW", "MEDIUM", "HIGH", "CRITICAL"]))


@st.composite
def confidence_strategy(draw):
    """Generate valid confidence values"""
    return draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False))


@st.composite
def risk_score_strategy(draw):
    """Generate valid risk scores"""
    return draw(st.floats(min_value=0.0, max_value=100.0, allow_nan=False))


@st.composite
def evidence_item_strategy(draw):
    """Generate valid evidence items"""
    source_types = ["EDC_Metrics", "SAE_Dashboard", "Query_Metrics", "Compliance_Data"]
    fields = ["missing_pages_pct", "sae_backlog_days", "open_query_count", "visit_completion_rate"]
    
    return EvidenceItem(
        evidence_id=f"EVD_{draw(st.integers(min_value=1000, max_value=9999))}",
        source_type=draw(st.sampled_from(source_types)),
        source_field=draw(st.sampled_from(fields)),
        value=draw(st.floats(min_value=0, max_value=100, allow_nan=False)),
        description=draw(st.text(min_size=5, max_size=100, alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'Z')))),
        relevance_score=draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False)),
    )


@st.composite
def findings_strategy(draw):
    """Generate list of findings"""
    count = draw(st.integers(min_value=0, max_value=5))
    findings = []
    for _ in range(count):
        finding = draw(st.text(min_size=10, max_size=100, alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'Z'))))
        findings.append(finding)
    return findings


@st.composite
def factors_strategy(draw):
    """Generate list of contributing factors"""
    count = draw(st.integers(min_value=0, max_value=5))
    factors = []
    for _ in range(count):
        factor = draw(st.text(min_size=10, max_size=100, alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'Z'))))
        factors.append(factor)
    return factors


@st.composite
def risk_assessment_context_strategy(draw):
    """Generate complete risk assessment context"""
    return {
        "entity_id": draw(entity_id_strategy()),
        "risk_level": draw(risk_level_strategy()),
        "risk_score": draw(risk_score_strategy()),
        "confidence": draw(confidence_strategy()),
        "findings": draw(findings_strategy()),
        "factors": draw(factors_strategy()),
        "evidence": draw(st.lists(evidence_item_strategy(), min_size=1, max_size=5)),
    }


# ========================================
# PROPERTY TESTS
# ========================================

class TestExplanationTraceabilityProperty:
    """
    Property-based tests for explanation traceability and safety.
    
    Feature: clinical-ai-system, Property 10: Explanation Traceability and Safety
    """
    
    @given(context=risk_assessment_context_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_explanation_links_to_evidence(self, context: Dict[str, Any]):
        """
        Feature: clinical-ai-system, Property 10: Explanation Traceability and Safety
        Validates: Requirements 7.1
        
        Property: For any explanation, it should contain links to underlying evidence.
        """
        engine = ExplanationEngine()
        
        result = engine.explain_risk_assessment(
            entity_id=context["entity_id"],
            risk_level=context["risk_level"],
            risk_score=context["risk_score"],
            confidence=context["confidence"],
            findings=context["findings"],
            factors=context["factors"],
            evidence=context["evidence"],
        )
        
        # Verify evidence is linked
        assert result.evidence is not None, "Explanation should have evidence"
        assert len(result.evidence) == len(context["evidence"]), \
            "All provided evidence should be linked"
        
        # Verify each evidence item has required fields
        for evidence in result.evidence:
            assert evidence.evidence_id is not None, "Evidence should have ID"
            assert evidence.source_type is not None, "Evidence should have source type"
            assert evidence.source_field is not None, "Evidence should have source field"
    
    @given(context=risk_assessment_context_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_explanation_uses_template(self, context: Dict[str, Any]):
        """
        Feature: clinical-ai-system, Property 10: Explanation Traceability and Safety
        Validates: Requirements 7.2
        
        Property: For any explanation, it should be generated from a controlled template.
        """
        engine = ExplanationEngine()
        
        result = engine.explain_risk_assessment(
            entity_id=context["entity_id"],
            risk_level=context["risk_level"],
            risk_score=context["risk_score"],
            confidence=context["confidence"],
            findings=context["findings"],
            factors=context["factors"],
            evidence=context["evidence"],
        )
        
        # Verify template ID is recorded
        assert result.template_id is not None, "Explanation should have template ID"
        assert result.template_id != "", "Template ID should not be empty"
        
        # Verify template exists in engine
        template = engine.get_template(result.template_id)
        assert template is not None, f"Template {result.template_id} should exist"
    
    @given(context=risk_assessment_context_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_explanation_has_no_medical_claims(self, context: Dict[str, Any]):
        """
        Feature: clinical-ai-system, Property 10: Explanation Traceability and Safety
        Validates: Requirements 7.5
        
        Property: For any explanation, it should never contain medical claims.
        """
        engine = ExplanationEngine()
        
        result = engine.explain_risk_assessment(
            entity_id=context["entity_id"],
            risk_level=context["risk_level"],
            risk_score=context["risk_score"],
            confidence=context["confidence"],
            findings=context["findings"],
            factors=context["factors"],
            evidence=context["evidence"],
        )
        
        # Verify no medical claims
        assert not result.has_medical_claims(), \
            "Explanation should not contain medical claims"
    
    @given(context=risk_assessment_context_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_explanation_has_confidence_statement(self, context: Dict[str, Any]):
        """
        Feature: clinical-ai-system, Property 10: Explanation Traceability and Safety
        Validates: Requirements 7.4
        
        Property: For any explanation, it should include confidence level reporting.
        """
        engine = ExplanationEngine()
        
        result = engine.explain_risk_assessment(
            entity_id=context["entity_id"],
            risk_level=context["risk_level"],
            risk_score=context["risk_score"],
            confidence=context["confidence"],
            findings=context["findings"],
            factors=context["factors"],
            evidence=context["evidence"],
        )
        
        # Verify confidence is reported
        assert result.confidence is not None, "Explanation should have confidence"
        assert 0.0 <= result.confidence <= 1.0, "Confidence should be in [0, 1]"
        assert result.confidence_level is not None, "Explanation should have confidence level"
        assert result.confidence_statement is not None, "Explanation should have confidence statement"
        assert len(result.confidence_statement) > 0, "Confidence statement should not be empty"
    
    @given(confidence=confidence_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_confidence_level_classification(self, confidence: float):
        """
        Feature: clinical-ai-system, Property 10: Explanation Traceability and Safety
        Validates: Requirements 7.4
        
        Property: For any confidence value, it should be correctly classified into a level.
        """
        engine = ExplanationEngine()
        level = engine._calculate_confidence_level(confidence)
        
        # Verify correct classification
        if confidence >= 0.9:
            assert level == ConfidenceLevel.VERY_HIGH
        elif confidence >= 0.75:
            assert level == ConfidenceLevel.HIGH
        elif confidence >= 0.5:
            assert level == ConfidenceLevel.MEDIUM
        elif confidence >= 0.25:
            assert level == ConfidenceLevel.LOW
        else:
            assert level == ConfidenceLevel.VERY_LOW
    
    @given(context=risk_assessment_context_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_explanation_is_serializable(self, context: Dict[str, Any]):
        """
        Feature: clinical-ai-system, Property 10: Explanation Traceability and Safety
        Validates: Requirements 7.1
        
        Property: For any explanation, it should be serializable to dictionary.
        """
        engine = ExplanationEngine()
        
        result = engine.explain_risk_assessment(
            entity_id=context["entity_id"],
            risk_level=context["risk_level"],
            risk_score=context["risk_score"],
            confidence=context["confidence"],
            findings=context["findings"],
            factors=context["factors"],
            evidence=context["evidence"],
        )
        
        # Verify serialization works
        result_dict = result.to_dict()
        assert isinstance(result_dict, dict), "Result should serialize to dict"
        
        # Verify required fields are present
        required_fields = [
            "explanation_id", "entity_id", "explanation_type",
            "summary", "detailed_explanation", "evidence",
            "confidence", "confidence_level", "confidence_statement",
            "template_id", "timestamp"
        ]
        for field in required_fields:
            assert field in result_dict, f"Serialized result should have {field}"
    
    @given(context=risk_assessment_context_strategy())
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_explanation_contains_entity_id(self, context: Dict[str, Any]):
        """
        Feature: clinical-ai-system, Property 10: Explanation Traceability and Safety
        Validates: Requirements 7.1
        
        Property: For any explanation, the entity ID should be traceable in the output.
        """
        engine = ExplanationEngine()
        
        result = engine.explain_risk_assessment(
            entity_id=context["entity_id"],
            risk_level=context["risk_level"],
            risk_score=context["risk_score"],
            confidence=context["confidence"],
            findings=context["findings"],
            factors=context["factors"],
            evidence=context["evidence"],
        )
        
        # Verify entity ID is in result
        assert result.entity_id == context["entity_id"], \
            "Explanation should contain correct entity ID"
        
        # Verify entity ID appears in detailed explanation
        assert context["entity_id"] in result.detailed_explanation, \
            "Entity ID should appear in detailed explanation"
    
    @given(
        entity_id=entity_id_strategy(),
        risk_level=risk_level_strategy(),
        risk_score=risk_score_strategy(),
        confidence=confidence_strategy(),
    )
    @settings(max_examples=100, deadline=10000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_explanation_summary_is_concise(
        self, 
        entity_id: str, 
        risk_level: str, 
        risk_score: float, 
        confidence: float
    ):
        """
        Feature: clinical-ai-system, Property 10: Explanation Traceability and Safety
        Validates: Requirements 7.1
        
        Property: For any explanation, the summary should be concise (under 200 chars).
        """
        engine = ExplanationEngine()
        
        result = engine.explain_risk_assessment(
            entity_id=entity_id,
            risk_level=risk_level,
            risk_score=risk_score,
            confidence=confidence,
            findings=["Finding 1"],
            factors=["Factor 1"],
            evidence=[],
        )
        
        # Verify summary is concise
        assert len(result.summary) <= 200, \
            f"Summary should be under 200 chars, got {len(result.summary)}"
        assert len(result.summary) > 0, "Summary should not be empty"


# ========================================
# UNIT TESTS
# ========================================

class TestExplanationEngineUnit:
    """Unit tests for explanation engine"""
    
    def test_default_templates_registered(self):
        """Test that default templates are registered"""
        engine = ExplanationEngine()
        
        expected_templates = [
            "risk_assessment_standard",
            "dqi_score_standard",
            "agent_signal_standard",
            "consensus_decision_standard",
            "guardian_alert_standard",
            "recommendation_standard",
        ]
        
        for template_id in expected_templates:
            template = engine.get_template(template_id)
            assert template is not None, f"Template {template_id} should be registered"
    
    def test_template_rendering(self):
        """Test template rendering with context"""
        engine = ExplanationEngine()
        template = engine.get_template("risk_assessment_standard")
        
        context = {
            "entity_id": "SITE_001",
            "risk_level": "HIGH",
            "risk_score": "75.5",
            "confidence_pct": "85",
            "summary": "High risk detected",
            "findings": "- Finding 1\n- Finding 2",
            "factors": "- Factor 1",
        }
        
        rendered = template.render(context)
        
        assert "SITE_001" in rendered
        assert "HIGH" in rendered
        assert "75.5" in rendered
        assert "85%" in rendered
    
    def test_safety_disclaimer_added(self):
        """Test that safety disclaimer is added to explanations"""
        engine = ExplanationEngine()
        
        result = engine.explain_risk_assessment(
            entity_id="SITE_001",
            risk_level="HIGH",
            risk_score=75.0,
            confidence=0.85,
            findings=["Finding 1"],
            factors=["Factor 1"],
            evidence=[],
        )
        
        # Check for safety disclaimer
        assert "does not constitute medical advice" in result.detailed_explanation.lower() or \
               "operational data quality" in result.detailed_explanation.lower(), \
               "Safety disclaimer should be present"
    
    def test_medical_claim_detection(self):
        """Test that medical claims are detected"""
        result = ExplanationResult(
            explanation_id="TEST_001",
            entity_id="SITE_001",
            explanation_type=ExplanationType.RISK_ASSESSMENT,
            summary="This is a diagnosis of the patient condition",
            detailed_explanation="The treatment should be prescribed immediately",
            evidence=[],
            confidence=0.9,
            confidence_level=ConfidenceLevel.VERY_HIGH,
            confidence_statement="High confidence",
            recommendations=[],
            template_id="test",
        )
        
        assert result.has_medical_claims(), \
            "Should detect medical claims in explanation"
    
    def test_no_medical_claims_in_normal_explanation(self):
        """Test that normal explanations don't trigger medical claim detection"""
        result = ExplanationResult(
            explanation_id="TEST_001",
            entity_id="SITE_001",
            explanation_type=ExplanationType.RISK_ASSESSMENT,
            summary="Data quality assessment shows high risk",
            detailed_explanation="The data completeness rate is below threshold",
            evidence=[],
            confidence=0.9,
            confidence_level=ConfidenceLevel.VERY_HIGH,
            confidence_statement="High confidence",
            recommendations=[],
            template_id="test",
        )
        
        assert not result.has_medical_claims(), \
            "Normal explanations should not trigger medical claim detection"


class TestEvidenceLinkerUnit:
    """Unit tests for evidence linker"""
    
    def test_evidence_extraction(self):
        """Test evidence extraction from data sources"""
        from src.explainability.evidence_linker import DataSource
        
        linker = EvidenceLinker()
        
        source = DataSource(
            source_id="SRC_001",
            source_type="EDC_Metrics",
            data={
                "missing_pages_pct": 15.5,
                "visit_completion_rate": 85.0,
            },
        )
        
        evidence = linker.extract_evidence([source], "SITE_001")
        
        assert len(evidence) > 0, "Should extract evidence from source"
        assert all(e.source_type == "EDC_Metrics" for e in evidence)
    
    def test_evidence_chain_creation(self):
        """Test evidence chain creation"""
        linker = EvidenceLinker()
        
        evidence_items = [
            EvidenceItem(
                evidence_id="EVD_001",
                source_type="EDC_Metrics",
                source_field="missing_pages_pct",
                value=15.5,
                description="Missing Pages: 15.5%",
                relevance_score=0.8,
            ),
        ]
        
        chain = linker.create_evidence_chain(
            explanation_id="EXP_001",
            entity_id="SITE_001",
            evidence_items=evidence_items,
        )
        
        assert chain.chain_id is not None
        assert chain.explanation_id == "EXP_001"
        assert chain.entity_id == "SITE_001"
        assert len(chain.evidence_items) == 1
    
    def test_relevance_filtering(self):
        """Test evidence filtering by relevance"""
        linker = EvidenceLinker()
        
        evidence_items = [
            EvidenceItem(
                evidence_id="EVD_001",
                source_type="EDC_Metrics",
                source_field="field1",
                value=10,
                description="Low relevance",
                relevance_score=0.2,
            ),
            EvidenceItem(
                evidence_id="EVD_002",
                source_type="EDC_Metrics",
                source_field="field2",
                value=20,
                description="High relevance",
                relevance_score=0.9,
            ),
        ]
        
        filtered = linker.filter_by_relevance(evidence_items, min_relevance=0.5)
        
        assert len(filtered) == 1
        assert filtered[0].evidence_id == "EVD_002"
