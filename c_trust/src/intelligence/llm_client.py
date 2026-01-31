"""
Groq LLM Client for C-TRUST
===========================
Integration with Groq API for natural language explanations and insights.

Responsibilities:
- Generate human-readable explanations for agent signals
- Create contextual recommendations
- Summarize study status in natural language
- Provide fallback when API unavailable

Key Features:
- Async-capable API client
- Prompt template management
- Response caching
- Graceful fallback handling

**Validates: Requirements for Explainable AI**
"""

import os
import json
from typing import Any, Dict, List, Optional
from datetime import datetime

from src.core import get_logger

logger = get_logger(__name__)

# Try to import Groq client
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    logger.warning("Groq package not installed. Using mock mode.")


class GroqLLMClient:
    """
    Groq API client for generating natural language explanations.
    
    Provides:
    - Agent signal explanations
    - Study status summaries
    - Contextual recommendations
    - Fallback responses when API unavailable
    """
    
    # Model configuration
    DEFAULT_MODEL = "llama-3.1-8b-instant"
    FALLBACK_MODEL = "mixtral-8x7b-32768"
    MAX_TOKENS = 1000
    TEMPERATURE = 0.3  # Lower for more consistent outputs
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        mock_mode: bool = False
    ):
        """
        Initialize Groq client with enhanced validation and error handling.
        
        Args:
            api_key: Groq API key (falls back to GROQ_API_KEY env var)
            model: Model to use (defaults to llama-3.1-8b-instant)
            mock_mode: Force mock mode even if API key available
        """
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        self.model = model or self.DEFAULT_MODEL
        self.mock_mode = mock_mode
        self.client = None
        self.initialization_error = None
        
        # Validate API key on startup
        if not self.api_key:
            self.initialization_error = "GROQ_API_KEY not found in environment"
            logger.error(self.initialization_error)
            self.mock_mode = True
        elif not GROQ_AVAILABLE:
            self.initialization_error = "Groq package not installed"
            logger.error(self.initialization_error)
            self.mock_mode = True
        else:
            try:
                self.client = Groq(api_key=self.api_key)
                self._test_connection()
                logger.info(f"LLM client initialized successfully with model: {self.model}")
            except Exception as e:
                self.initialization_error = f"Failed to initialize Groq client: {str(e)}"
                logger.error(self.initialization_error, exc_info=True)
                self.mock_mode = True
                self.client = None
        
        if self.mock_mode:
            logger.warning(f"LLM client in MOCK MODE. Reason: {self.initialization_error}")
        
        # Response cache
        self._cache: Dict[str, Dict[str, Any]] = {}
    
    def _test_connection(self):
        """
        Test API connection with minimal request.
        
        Raises:
            Exception: If connection test fails
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5,
                timeout=10
            )
            logger.info("API connection test successful")
        except Exception as e:
            logger.error(f"API connection test failed: {e}")
            raise
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get LLM client status for health checks.
        
        Returns:
            Dictionary with status information including:
            - available: Whether real API is available
            - mock_mode: Whether running in mock mode
            - error: Initialization error if any
            - api_key_configured: Whether API key is set
            - groq_package_available: Whether Groq package is installed
        """
        return {
            'available': not self.mock_mode and self.client is not None,
            'mock_mode': self.mock_mode,
            'error': self.initialization_error,
            'api_key_configured': bool(self.api_key),
            'groq_package_available': GROQ_AVAILABLE,
            'model': self.model
        }
    
    def generate_explanation(
        self,
        signal: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate natural language explanation for an agent signal.
        
        Args:
            signal: Agent signal dictionary with risk_level, evidence, etc.
            context: Optional additional context (study info, etc.)
        
        Returns:
            Human-readable explanation
        """
        if self.mock_mode:
            return self._mock_explanation(signal)
        
        try:
            from src.intelligence.prompts import AGENT_EXPLANATION_PROMPT
            
            prompt = AGENT_EXPLANATION_PROMPT.format(
                agent_type=signal.get("agent_type", "Unknown"),
                risk_level=signal.get("risk_level", "Unknown"),
                confidence=signal.get("confidence", 0),
                evidence=json.dumps(signal.get("evidence", []), indent=2),
                recommendations=json.dumps(signal.get("recommended_actions", []), indent=2),
            )
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert clinical trial data analyst explaining AI-generated insights to study managers."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.MAX_TOKENS,
                temperature=self.TEMPERATURE,
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            return self._mock_explanation(signal)
    
    def generate_recommendations(
        self,
        signals: List[Dict[str, Any]],
        study_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate contextual recommendations from multiple agent signals.
        
        Args:
            signals: List of agent signal dictionaries
            study_context: Optional study context
        
        Returns:
            Dictionary with:
            - recommendations: List of prioritized recommendations
            - source: 'ai' or 'template' (clearly indicates data source)
            - warning: Warning message if using fallback (optional)
            - error: Error message if API failed (optional)
            - troubleshooting: List of troubleshooting hints (optional)
            - timestamp: When recommendations were generated
        """
        timestamp = datetime.utcnow().isoformat()
        
        # Mock mode - return template-based recommendations with clear warning
        if self.mock_mode:
            logger.warning(
                f"Generating template-based recommendations (mock mode). "
                f"Reason: {self.initialization_error}"
            )
            return {
                'recommendations': self._mock_recommendations(signals),
                'source': 'template',
                'warning': (
                    f"⚠️ AI recommendations unavailable. Using template-based suggestions. "
                    f"Reason: {self.initialization_error}"
                ),
                'troubleshooting': self._get_troubleshooting_hints(),
                'timestamp': timestamp,
                'mock_mode': True
            }
        
        # Try to generate AI-powered recommendations
        try:
            from src.intelligence.prompts import RECOMMENDATION_PROMPT
            
            # Summarize signals for prompt
            signal_summary = []
            for signal in signals:
                if not signal.get("abstained"):
                    signal_summary.append({
                        "agent": signal.get("agent_type"),
                        "risk": signal.get("risk_level"),
                        "actions": signal.get("recommended_actions", [])[:2],
                    })
            
            prompt = RECOMMENDATION_PROMPT.format(
                signal_summary=json.dumps(signal_summary, indent=2),
                study_context=json.dumps(study_context or {}, indent=2),
            )
            
            logger.info(f"Generating AI recommendations using model: {self.model}")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a clinical trial operations expert providing actionable recommendations."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.MAX_TOKENS,
                temperature=self.TEMPERATURE,
            )
            
            # Parse recommendations from response
            content = response.choices[0].message.content.strip()
            recommendations = [line.strip() for line in content.split("\n") if line.strip() and line.strip()[0].isdigit()]
            
            logger.info(f"Successfully generated {len(recommendations)} AI recommendations")
            
            return {
                'recommendations': recommendations if recommendations else [content],
                'source': 'ai',
                'model': self.model,
                'timestamp': timestamp,
                'mock_mode': False
            }
            
        except Exception as e:
            # API call failed - fall back to template with detailed error info
            error_msg = str(e)
            logger.error(f"LLM API call failed: {error_msg}", exc_info=True)
            
            return {
                'recommendations': self._mock_recommendations(signals),
                'source': 'template',
                'error': error_msg,
                'warning': (
                    f"⚠️ AI recommendations failed. Using template-based suggestions. "
                    f"Error: {error_msg}"
                ),
                'troubleshooting': self._get_troubleshooting_hints(),
                'timestamp': timestamp,
                'mock_mode': False,
                'fallback': True
            }
    
    def summarize_study_status(
        self,
        study_data: Dict[str, Any]
    ) -> str:
        """
        Generate natural language summary of study status.
        
        Args:
            study_data: Study data including DQI, agent signals, etc.
        
        Returns:
            Human-readable study summary
        """
        if self.mock_mode:
            return self._mock_study_summary(study_data)
        
        try:
            from src.intelligence.prompts import STUDY_SUMMARY_PROMPT
            
            prompt = STUDY_SUMMARY_PROMPT.format(
                study_id=study_data.get("study_id", "Unknown"),
                dqi_score=study_data.get("dqi_score", 0),
                risk_level=study_data.get("risk_level", "Unknown"),
                dimension_scores=json.dumps(study_data.get("dimension_scores", {}), indent=2),
                agent_count=study_data.get("agent_signals_count", 0),
            )
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are summarizing clinical trial status for stakeholders. Be concise and factual."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.2,
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            return self._mock_study_summary(study_data)
    
    def _get_troubleshooting_hints(self) -> List[str]:
        """
        Provide troubleshooting hints based on error type.
        
        Returns:
            List of actionable troubleshooting steps
        """
        hints = []
        
        if not self.api_key:
            hints.extend([
                "Set GROQ_API_KEY environment variable",
                "Verify .env file is in project root",
                "Restart application after setting environment variable"
            ])
        elif not GROQ_AVAILABLE:
            hints.append("Install groq package: pip install groq")
        elif self.initialization_error and "authentication" in str(self.initialization_error).lower():
            hints.extend([
                "Verify API key is valid",
                "Check API key hasn't expired",
                "Ensure API key has correct permissions"
            ])
        elif self.initialization_error and "connection" in str(self.initialization_error).lower():
            hints.extend([
                "Check network connectivity",
                "Verify firewall settings allow Groq API access",
                "Try again in a few moments"
            ])
        else:
            hints.append("Check application logs for detailed error information")
        
        return hints
    
    def _mock_explanation(self, signal: Dict[str, Any]) -> str:
        """Generate mock explanation when API unavailable."""
        agent_type = signal.get("agent_type", "Unknown Agent")
        risk_level = signal.get("risk_level", "unknown")
        confidence = signal.get("confidence", 0)
        
        risk_descriptions = {
            "critical": "requires immediate attention",
            "high": "should be addressed promptly",
            "medium": "warrants monitoring",
            "low": "is within acceptable parameters",
        }
        
        risk_desc = risk_descriptions.get(risk_level.lower(), "has been analyzed")
        
        explanation = f"The {agent_type.replace('_', ' ').title()} has determined that this study {risk_desc}. "
        explanation += f"This assessment has a confidence level of {confidence*100:.0f}%. "
        
        evidence = signal.get("evidence", [])
        if evidence:
            explanation += f"Key findings include: "
            findings = [e.get("description", "") for e in evidence[:3] if e.get("description")]
            explanation += "; ".join(findings) + "."
        
        actions = signal.get("recommended_actions", [])
        if actions:
            explanation += f" Recommended action: {actions[0]}"
        
        return explanation
    
    def _mock_recommendations(self, signals: List[Dict[str, Any]]) -> List[str]:
        """Generate mock recommendations when API unavailable."""
        recommendations = []
        
        # Collect and prioritize recommendations from signals
        all_actions = []
        for signal in signals:
            if not signal.get("abstained"):
                risk = signal.get("risk_level", "low")
                priority = {"critical": 1, "high": 2, "medium": 3, "low": 4}.get(risk.lower(), 5)
                for action in signal.get("recommended_actions", []):
                    all_actions.append((priority, action))
        
        # Sort by priority and take top 5
        all_actions.sort(key=lambda x: x[0])
        recommendations = [f"{i+1}. {action}" for i, (_, action) in enumerate(all_actions[:5])]
        
        if not recommendations:
            recommendations = ["1. Continue monitoring - all metrics within acceptable ranges"]
        
        return recommendations
    
    def _mock_study_summary(self, study_data: Dict[str, Any]) -> str:
        """Generate mock study summary when API unavailable."""
        study_id = study_data.get("study_id", "Unknown")
        dqi_score = study_data.get("dqi_score", 0)
        risk_level = study_data.get("risk_level", "Unknown")
        
        if dqi_score >= 80:
            status = "performing well"
        elif dqi_score >= 60:
            status = "performing adequately with some areas for improvement"
        elif dqi_score >= 40:
            status = "experiencing moderate challenges"
        else:
            status = "facing significant challenges requiring immediate attention"
        
        summary = f"Study {study_id} is currently {status} with a Data Quality Index of {dqi_score:.1f}%. "
        summary += f"The overall risk assessment is {risk_level}. "
        
        dimension_scores = study_data.get("dimension_scores", {})
        if dimension_scores:
            lowest = min(dimension_scores.items(), key=lambda x: x[1])
            summary += f"The {lowest[0]} dimension requires the most attention at {lowest[1]:.1f}%."
        
        return summary
    
    @property
    def is_available(self) -> bool:
        """Check if real Groq API is available."""
        return not self.mock_mode and self.client is not None


__all__ = ["GroqLLMClient"]
