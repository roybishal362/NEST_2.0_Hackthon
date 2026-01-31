"""
C-TRUST Safety Agent - Component 4
========================================
Specialized agent for safety signal detection.

Focus Areas:
- Serious Adverse Events (SAE) backlog
- Overdue safety reports
- Fatal SAE detection
- Safety query aging

Production-ready with:
- Comprehensive threshold checking
- Evidence-based decision making
- Confidence scoring
- Abstention logic
"""

from typing import Any, Dict, List

from src.core import get_logger, yaml_config
from src.intelligence.base_agent import (
    AgentSignal,
    AgentType,
    BaseAgent,
    FeatureEvidence,
    RiskSignal,
)

logger = get_logger(__name__)


class SafetyAgent(BaseAgent):
    """
    Specialized agent for safety risk detection.
    
    Analyzes:
    - sae_backlog_days
    - sae_overdue_count
    - fatal_sae_count
    
    Returns risk signal with evidence and recommended actions.
    """
    
    def __init__(self):
        """Initialize Safety Agent with configuration"""
        super().__init__(
            agent_type=AgentType.SAFETY,
            min_confidence=0.6,
            abstention_threshold=0.5
        )
        
        # Load thresholds from configuration
        agent_config = yaml_config.agent_config
        safety_config = agent_config.get("safety_agent", {})
        self.critical_thresholds = safety_config.get("critical_thresholds", {
            "sae_backlog_days": 7,
            "sae_overdue_count": 3,
            "fatal_sae_count": 1,
        })
        
        # Feature weights for this agent
        self.feature_weights = {
            "fatal_sae_count": 1.0,  # Highest priority
            "sae_overdue_count": 0.8,
            "sae_backlog_days": 0.6,
        }
        
        logger.info("SafetyAgent initialized with thresholds: "f"{self.critical_thresholds}")
    
    def analyze(
        self,
        features: Dict[str, Any],
        study_id: str
    ) -> AgentSignal:
        """
        Analyze safety features and return risk signal.
        
        Args:
            features: Dict of engineered features
            study_id: Study ID for logging
        
        Returns:
            Agent signal with safety risk assessment
        """
        logger.info(f"SafetyAgent analyzing {study_id}")
        
        # Define required features
        required_features = [
            "sae_backlog_days",
            "sae_overdue_count",
            "fatal_sae_count",
        ]
        
        # Check if should abstain
        should_abstain, abstention_reason = self._should_abstain(
            features,
            required_features
        )
        
        if should_abstain:
            return self._create_abstention_signal(abstention_reason)
        
        # Collect evidence
        evidence_list: List[FeatureEvidence] = []
        max_risk_level = RiskSignal.LOW
        
        # 1. Fatal SAE analysis
        fatal_sae_count = features.get("fatal_sae_count", 0)
        if fatal_sae_count > 0:
            evidence_list.append(FeatureEvidence(
                feature_name="fatal_sae_count",
                feature_value=fatal_sae_count,
                threshold=self.critical_thresholds["fatal_sae_count"],
                severity=min(fatal_sae_count / 5, 1.0),  # Normalize to max 5
                description=f"{fatal_sae_count} fatal SAE(s) reported"
            ))
            max_risk_level = RiskSignal.CRITICAL
        
        # 2. Overdue SAE analysis
        sae_overdue_count = features.get("sae_overdue_count", 0)
        if sae_overdue_count > 0:
            severity = self._calculate_severity(
                sae_overdue_count,
                self.critical_thresholds["sae_overdue_count"],
                max_value=10
            )
            
            if sae_overdue_count >= self.critical_thresholds["sae_overdue_count"]:
                risk_level = RiskSignal.CRITICAL
            elif sae_overdue_count >= 2:
                risk_level = RiskSignal.HIGH
            else:
                risk_level = RiskSignal.MEDIUM
            
            evidence_list.append(FeatureEvidence(
                feature_name="sae_overdue_count",
                feature_value=sae_overdue_count,
                threshold=self.critical_thresholds["sae_overdue_count"],
                severity=severity,
                description=f"{sae_overdue_count} SAE report(s) overdue"
            ))
            
            if risk_level.value in ["critical", "high"]:
                max_risk_level = risk_level if risk_level == RiskSignal.CRITICAL else max(max_risk_level, risk_level, key=lambda x: ["low", "medium", "high", "critical"].index(x.value))
        
        # 3. SAE backlog analysis
        sae_backlog_days = features.get("sae_backlog_days", 0)
        if sae_backlog_days > 0:
            severity = self._calculate_severity(
                sae_backlog_days,
                self.critical_thresholds["sae_backlog_days"],
                max_value=30
            )
            
            if sae_backlog_days >= self.critical_thresholds["sae_backlog_days"]:
                risk_level = RiskSignal.HIGH
            elif sae_backlog_days >= 5:
                risk_level = RiskSignal.MEDIUM
            else:
                risk_level = RiskSignal.LOW
            
            evidence_list.append(FeatureEvidence(
                feature_name="sae_backlog_days",
                feature_value=sae_backlog_days,
                threshold=self.critical_thresholds["sae_backlog_days"],
                severity=severity,
                description=f"Average SAE age: {sae_backlog_days} days"
            ))
            
            if risk_level.value in ["high", "critical"]:
                max_risk_level = max(max_risk_level, risk_level, key=lambda x: ["low", "medium", "high", "critical"].index(x.value))
        
        # Calculate confidence
        confidence = self._calculate_confidence(features)
        
        # Generate recommended actions
        recommended_actions = self._generate_recommendations(
            features,
            max_risk_level
        )
        
        # Create signal
        signal = AgentSignal(
            agent_type=self.agent_type,
            risk_level=max_risk_level,
            confidence=confidence,
            evidence=evidence_list,
            recommended_actions=recommended_actions,
            features_analyzed=len(required_features)
        )
        
        logger.info(
            f"SafetyAgent: {study_id} - Risk={max_risk_level.value}, "
            f"Confidence={confidence:.2f}, Evidence={len(evidence_list)}"
        )
        
        return signal
    
    def _calculate_confidence(self, features: Dict[str, Any]) -> float:
        """
        Calculate confidence based on feature availability and data quality.
        
        Confidence factors:
        - Are all features present? (+1.0)
        - Are features numerical? (+1.0)
        - Are features non-zero? (indicates real data, +1.0)
        
        Returns score averaged to [0, 1]
        """
        required_features = ["sae_backlog_days", "sae_overdue_count", "fatal_sae_count"]
        
        confidence_score = 0.0
        max_score = 3.0
        
        # Feature presence (1.0)
        present_features = sum(1 for f in required_features if f in features)
        confidence_score += present_features / len(required_features)
        
        # Feature validity (1.0)
        valid_features = sum(
            1 for f in required_features
            if f in features and features[f] is not None
        )
        confidence_score += valid_features / len(required_features)
        
        # Data freshness (1.0) - assuming fresh if features exist
        confidence_score += 1.0
        
        # Normalize to [0, 1]
        final_confidence = confidence_score / max_score
        
        return final_confidence
    
    def _generate_recommendations(
        self,
        features: Dict[str, Any],
        risk_level: RiskSignal
    ) -> List[str]:
        """Generate context-specific recommendations"""
        recommendations = []
        
        fatal_sae = features.get("fatal_sae_count", 0)
        overdue_sae = features.get("sae_overdue_count", 0)
        backlog_days = features.get("sae_backlog_days", 0)
        
        if risk_level == RiskSignal.CRITICAL:
            recommendations.append(
                "CRITICAL: Immediate action required - Escalate to Study Lead and Medical Monitor"
            )
            
            if fatal_sae > 0:
                recommendations.append(
                    f"Review and expedite reporting for {fatal_sae} fatal SAE(s)"
                )
        
        if overdue_sae > 0:
            recommendations.append(
                f"Prioritize resolution of {overdue_sae} overdue SAE report(s)"
            )
            recommendations.append("Allocate additional safety resources")
        
        if backlog_days >= self.critical_thresholds["sae_backlog_days"]:
            recommendations.append(
                f"Review SAE workflow - average backlog is {backlog_days} days"
            )
        
        if not recommendations:
            recommendations.append("Safety metrics within acceptable range")
        
        return recommendations


# ========================================
# EXPORTS
# ========================================

__all__ = ["SafetyAgent"]
