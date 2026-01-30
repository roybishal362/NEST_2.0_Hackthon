"""
C-TRUST Groq API Integration for Enhanced Explanations
=======================================================
Uses Groq API with open-source models (llama-3.3-70b-versatile or mixtral-8x7b-32768)
for enhanced explanation generation while maintaining safety constraints.

Key Features:
- Integration with Groq API using open-source models
- Controlled prompts to prevent hallucination
- Safety guardrails to prevent medical claims
- Fallback to template-based explanations on failure

**Validates: Requirements 7.1, 7.4**
"""

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
import json

from src.core import get_logger

logger = get_logger(__name__)


@dataclass
class GroqConfig:
    """Configuration for Groq API"""
    api_key: str
    model: str = "llama-3.3-70b-versatile"
    temperature: float = 0.1  # Low temperature for consistent outputs
    max_tokens: int = 2048
    timeout: int = 30


class GroqExplainer:
    """
    Groq API integration for enhanced explanations.
    
    Uses open-source LLMs via Groq API to enhance template-based
    explanations while maintaining strict safety constraints.
    
    Safety Features:
    - Controlled system prompts
    - Output validation
    - Medical claim detection
    - Fallback to templates on failure
    
    **Validates: Requirements 7.1, 7.4**
    """
    
    # System prompt for safe explanation generation
    SYSTEM_PROMPT = """You are a clinical trial data quality analyst assistant. Your role is to help explain data quality metrics and operational insights.

CRITICAL RULES:
1. NEVER make medical claims or clinical interpretations
2. NEVER suggest diagnoses, treatments, or patient outcomes
3. ONLY discuss data quality, completeness, and operational metrics
4. Be factual and cite specific data points when available
5. Use professional but accessible language
6. If uncertain, acknowledge limitations

You are explaining operational data quality metrics, NOT providing medical advice."""

    # Forbidden phrases that indicate medical claims
    FORBIDDEN_PHRASES = [
        "diagnos", "treat", "cure", "prescri", "medic", "therap",
        "patient outcome", "clinical decision", "medical advice",
        "health condition", "disease", "symptom", "prognosis",
        "recommend treatment", "clinical interpretation"
    ]
    
    def __init__(self, config: Optional[GroqConfig] = None):
        """
        Initialize Groq explainer.
        
        Args:
            config: Optional Groq configuration. If not provided,
                   reads from environment variables.
        """
        if config:
            self.config = config
        else:
            self.config = GroqConfig(
                api_key=os.getenv("GROQ_API_KEY", ""),
                model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
                temperature=float(os.getenv("GROQ_TEMPERATURE", "0.1")),
                max_tokens=int(os.getenv("GROQ_MAX_TOKENS", "2048")),
            )
        
        self._client = None
        self._initialized = False
        
        if self.config.api_key:
            self._initialize_client()
        else:
            logger.warning("Groq API key not configured - LLM enhancement disabled")
    
    def _initialize_client(self):
        """Initialize Groq client"""
        try:
            from groq import Groq
            self._client = Groq(api_key=self.config.api_key)
            self._initialized = True
            logger.info(f"Groq client initialized with model: {self.config.model}")
        except ImportError:
            logger.warning("Groq package not installed - run: pip install groq")
            self._initialized = False
        except Exception as e:
            logger.error(f"Failed to initialize Groq client: {e}")
            self._initialized = False
    
    @property
    def is_available(self) -> bool:
        """Check if Groq API is available"""
        return self._initialized and self._client is not None
    
    def enhance_explanation(
        self,
        base_explanation: str,
        context: Dict[str, Any],
        max_length: int = 500,
    ) -> str:
        """
        Enhance a template-based explanation using LLM.
        
        Args:
            base_explanation: Template-generated explanation
            context: Additional context for enhancement
            max_length: Maximum length of enhanced explanation
        
        Returns:
            Enhanced explanation or original if enhancement fails
        """
        if not self.is_available:
            logger.debug("Groq not available, returning base explanation")
            return base_explanation
        
        try:
            prompt = self._build_enhancement_prompt(base_explanation, context)
            
            response = self._client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.config.temperature,
                max_tokens=min(self.config.max_tokens, max_length * 2),
            )
            
            enhanced = response.choices[0].message.content.strip()
            
            # Validate output
            if self._validate_output(enhanced):
                logger.debug("Successfully enhanced explanation")
                return enhanced
            else:
                logger.warning("Enhanced explanation failed validation, using base")
                return base_explanation
                
        except Exception as e:
            logger.error(f"Groq enhancement failed: {e}")
            return base_explanation
    
    def generate_summary(
        self,
        data_points: Dict[str, Any],
        entity_id: str,
        summary_type: str = "risk",
    ) -> str:
        """
        Generate a summary of data points.
        
        Args:
            data_points: Dictionary of data points to summarize
            entity_id: Entity being summarized
            summary_type: Type of summary (risk, dqi, agent)
        
        Returns:
            Generated summary or fallback text
        """
        if not self.is_available:
            return self._fallback_summary(data_points, entity_id, summary_type)
        
        try:
            prompt = self._build_summary_prompt(data_points, entity_id, summary_type)
            
            response = self._client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.config.temperature,
                max_tokens=512,
            )
            
            summary = response.choices[0].message.content.strip()
            
            if self._validate_output(summary):
                return summary
            else:
                return self._fallback_summary(data_points, entity_id, summary_type)
                
        except Exception as e:
            logger.error(f"Groq summary generation failed: {e}")
            return self._fallback_summary(data_points, entity_id, summary_type)
    
    def explain_trend(
        self,
        current_value: float,
        previous_value: float,
        metric_name: str,
        entity_id: str,
    ) -> str:
        """
        Generate explanation for a metric trend.
        
        Args:
            current_value: Current metric value
            previous_value: Previous metric value
            metric_name: Name of the metric
            entity_id: Entity being analyzed
        
        Returns:
            Trend explanation
        """
        change = current_value - previous_value
        change_pct = (change / previous_value * 100) if previous_value != 0 else 0
        
        if not self.is_available:
            return self._fallback_trend_explanation(
                current_value, previous_value, change_pct, metric_name, entity_id
            )
        
        try:
            prompt = f"""Explain this data quality metric trend for {entity_id}:

Metric: {metric_name}
Previous Value: {previous_value:.2f}
Current Value: {current_value:.2f}
Change: {change:+.2f} ({change_pct:+.1f}%)

Provide a brief (2-3 sentences) operational explanation of what this change means for data quality. Do NOT make any medical interpretations."""

            response = self._client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.config.temperature,
                max_tokens=256,
            )
            
            explanation = response.choices[0].message.content.strip()
            
            if self._validate_output(explanation):
                return explanation
            else:
                return self._fallback_trend_explanation(
                    current_value, previous_value, change_pct, metric_name, entity_id
                )
                
        except Exception as e:
            logger.error(f"Groq trend explanation failed: {e}")
            return self._fallback_trend_explanation(
                current_value, previous_value, change_pct, metric_name, entity_id
            )
    
    def _build_enhancement_prompt(
        self, 
        base_explanation: str, 
        context: Dict[str, Any]
    ) -> str:
        """Build prompt for explanation enhancement"""
        context_str = "\n".join(f"- {k}: {v}" for k, v in context.items() if v)
        
        return f"""Enhance this data quality explanation while keeping it factual and operational:

ORIGINAL EXPLANATION:
{base_explanation}

ADDITIONAL CONTEXT:
{context_str}

INSTRUCTIONS:
1. Make the explanation clearer and more actionable
2. Keep all factual data points
3. Do NOT add medical interpretations
4. Keep it concise (under 300 words)
5. Focus on data quality and operational metrics only

Enhanced explanation:"""
    
    def _build_summary_prompt(
        self,
        data_points: Dict[str, Any],
        entity_id: str,
        summary_type: str,
    ) -> str:
        """Build prompt for summary generation"""
        data_str = "\n".join(f"- {k}: {v}" for k, v in data_points.items())
        
        type_instructions = {
            "risk": "Summarize the risk level and key contributing factors.",
            "dqi": "Summarize the data quality score and main areas of concern.",
            "agent": "Summarize the agent's findings and confidence level.",
        }
        
        instruction = type_instructions.get(summary_type, "Provide a brief summary.")
        
        return f"""Generate a brief summary (2-3 sentences) for {entity_id}:

DATA POINTS:
{data_str}

TASK: {instruction}

Remember: Focus ONLY on data quality metrics. Do NOT make medical interpretations.

Summary:"""
    
    def _validate_output(self, text: str) -> bool:
        """
        Validate LLM output for safety.
        
        Returns False if output contains forbidden phrases.
        """
        text_lower = text.lower()
        
        for phrase in self.FORBIDDEN_PHRASES:
            if phrase in text_lower:
                logger.warning(f"Output contains forbidden phrase: {phrase}")
                return False
        
        # Check for reasonable length
        if len(text) < 10 or len(text) > 5000:
            logger.warning(f"Output length out of bounds: {len(text)}")
            return False
        
        return True
    
    def _fallback_summary(
        self,
        data_points: Dict[str, Any],
        entity_id: str,
        summary_type: str,
    ) -> str:
        """Generate fallback summary without LLM"""
        if summary_type == "risk":
            risk_level = data_points.get("risk_level", "UNKNOWN")
            score = data_points.get("risk_score", 0)
            return f"{entity_id} has {risk_level} risk (score: {score:.1f}/100)."
        
        elif summary_type == "dqi":
            score = data_points.get("overall_score", 0)
            band = data_points.get("band", "UNKNOWN")
            return f"{entity_id} DQI score: {score:.1f}/100 ({band})."
        
        elif summary_type == "agent":
            agent = data_points.get("agent_name", "Agent")
            severity = data_points.get("severity", "UNKNOWN")
            return f"{agent} detected {severity} severity issue for {entity_id}."
        
        return f"Summary for {entity_id}."
    
    def _fallback_trend_explanation(
        self,
        current: float,
        previous: float,
        change_pct: float,
        metric: str,
        entity_id: str,
    ) -> str:
        """Generate fallback trend explanation without LLM"""
        if change_pct > 5:
            direction = "improved"
        elif change_pct < -5:
            direction = "declined"
        else:
            direction = "remained stable"
        
        return (
            f"The {metric} for {entity_id} has {direction} "
            f"from {previous:.1f} to {current:.1f} ({change_pct:+.1f}%)."
        )


__all__ = ["GroqExplainer", "GroqConfig"]
