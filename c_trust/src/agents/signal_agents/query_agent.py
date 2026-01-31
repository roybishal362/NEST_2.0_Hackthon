"""
Query Quality Agent
===================
Specialized agent for analyzing query backlog and data quality friction.

Responsibilities:
- Monitor open query counts and aging
- Analyze query resolution velocity
- Identify data quality friction points
- Track query backlog trends

Key Features:
- Open query count analysis
- Query aging days tracking
- Query resolution rate monitoring
- Backlog trend detection

**Validates: Requirements 2.1**
"""

from typing import Any, Dict, List, Optional
from datetime import datetime

from src.intelligence.base_agent import (
    BaseAgent,
    AgentType,
    RiskSignal,
    FeatureEvidence,
    AgentSignal,
)
from src.core import get_logger

logger = get_logger(__name__)


class QueryQualityAgent(BaseAgent):
    """
    Agent specialized in query backlog and data quality analysis.
    
    Analyzes:
    - Open query count
    - Query aging days (average age of open queries)
    - Query resolution velocity
    - Data entry lag correlation
    
    Risk Assessment:
    - CRITICAL: >200 open queries OR >45 days aging
    - HIGH: >100 open queries OR >30 days aging
    - MEDIUM: >50 open queries OR >14 days aging
    - LOW: ≤50 open queries AND ≤14 days aging
    """
    
    # Required features for analysis
    # Note: Made more lenient - can analyze with partial data
    REQUIRED_FEATURES = [
        "open_query_count",  # Must have at least query count
    ]
    
    # Preferred features that enhance analysis
    PREFERRED_FEATURES = [
        "query_aging_days",
    ]
    
    # Optional features that enhance analysis
    OPTIONAL_FEATURES = [
        "data_entry_lag_days",
    ]
    
    # Risk thresholds
    THRESHOLDS = {
        "open_query_count": {
            "critical": 200,
            "high": 100,
            "medium": 50,
        },
        "query_aging_days": {
            "critical": 45.0,
            "high": 30.0,
            "medium": 14.0,
        },
    }
    
    def __init__(
        self,
        min_confidence: float = 0.6,
        abstention_threshold: float = 0.5
    ):
        """
        Initialize Query Quality Agent.
        
        Args:
            min_confidence: Minimum confidence to emit signal
            abstention_threshold: Threshold below which to abstain
        """
        super().__init__(
            agent_type=AgentType.QUERY_QUALITY,
            min_confidence=min_confidence,
            abstention_threshold=abstention_threshold
        )
        logger.info("QueryQualityAgent initialized")
    
    def analyze(
        self,
        features: Dict[str, Any],
        study_id: str
    ) -> AgentSignal:
        """
        Analyze query quality features and return risk signal.
        
        Args:
            features: Dictionary of engineered features
            study_id: Study identifier for logging
        
        Returns:
            AgentSignal with query quality risk assessment
        """
        logger.debug(f"Analyzing query quality for {study_id}")
        
        # Extract feature values - handle None/missing gracefully
        # Even if features are NULL, we can still analyze with defaults
        open_queries = features.get("open_query_count")
        if open_queries is None:
            open_queries = 0
        
        # If query_aging_days is missing, assume 0 (no aging data available)
        query_aging = features.get("query_aging_days", 0.0)
        if query_aging is None:
            query_aging = 0.0
        
        data_entry_lag = features.get("data_entry_lag_days")
        
        # Check if we have ANY data to analyze
        has_any_data = (
            open_queries is not None or 
            query_aging is not None
        )
        
        if not has_any_data:
            # Truly no data available - abstain
            reason = "No query data available (all features are None)"
            logger.info(f"{study_id}: Query agent abstaining - {reason}")
            return self._create_abstention_signal(reason)
        
        # Collect evidence
        evidence: List[FeatureEvidence] = []
        
        # Open query count analysis
        if open_queries > 0:
            evidence.append(FeatureEvidence(
                feature_name="open_query_count",
                feature_value=open_queries,
                threshold=self.THRESHOLDS["open_query_count"]["medium"],
                severity=self._calculate_severity(
                    open_queries,
                    self.THRESHOLDS["open_query_count"]["medium"],
                    max_value=300
                ),
                description=f"{open_queries} open queries pending resolution"
            ))
        
        # Query aging analysis
        if query_aging > 0:
            evidence.append(FeatureEvidence(
                feature_name="query_aging_days",
                feature_value=query_aging,
                threshold=self.THRESHOLDS["query_aging_days"]["medium"],
                severity=self._calculate_severity(
                    query_aging,
                    self.THRESHOLDS["query_aging_days"]["medium"],
                    max_value=60.0
                ),
                description=f"Average query age: {query_aging:.1f} days"
            ))
        
        # Data entry lag correlation (if available)
        if data_entry_lag is not None:
            if data_entry_lag > 3:
                evidence.append(FeatureEvidence(
                    feature_name="data_entry_lag_days",
                    feature_value=data_entry_lag,
                    threshold=3.0,
                    severity=min(data_entry_lag / 14.0, 1.0),
                    description=f"Data entry lag ({data_entry_lag:.1f} days) may contribute to query backlog"
                ))
        
        # Determine overall risk level
        risk_level = self._assess_overall_risk(open_queries, query_aging)
        
        # Calculate confidence
        confidence = self._calculate_confidence(features)
        
        # Generate recommended actions
        actions = self._generate_recommendations(
            risk_level, open_queries, query_aging, data_entry_lag
        )
        
        logger.info(
            f"{study_id}: Query analysis complete - "
            f"risk={risk_level.value}, confidence={confidence:.2f}, "
            f"open_queries={open_queries}, aging={query_aging:.1f}"
        )
        
        return AgentSignal(
            agent_type=self.agent_type,
            risk_level=risk_level,
            confidence=confidence,
            evidence=evidence,
            recommended_actions=actions,
            features_analyzed=len([f for f in self.REQUIRED_FEATURES + self.OPTIONAL_FEATURES 
                                   if f in features and features[f] is not None])
        )
    
    def _calculate_confidence(self, features: Dict[str, Any]) -> float:
        """
        Calculate confidence based on data availability and quality.
        
        Args:
            features: Available features
        
        Returns:
            Confidence score between 0 and 1
        """
        # Count available features (non-None)
        open_query_available = features.get("open_query_count") is not None
        query_aging_available = features.get("query_aging_days") is not None
        data_entry_lag_available = features.get("data_entry_lag_days") is not None
        
        # Base confidence from having any data
        available_count = sum([open_query_available, query_aging_available, data_entry_lag_available])
        total_features = 3  # open_query, aging, lag
        
        if available_count == 0:
            return 0.0
        
        # Calculate confidence based on data availability
        base_confidence = available_count / total_features
        
        # Boost confidence if we have the most critical features
        if open_query_available and query_aging_available:
            base_confidence = min(base_confidence + 0.2, 1.0)
        
        return base_confidence
    
    def _assess_overall_risk(
        self,
        open_queries: int,
        query_aging: float
    ) -> RiskSignal:
        """
        Assess overall query quality risk level.
        
        Uses worst-case assessment across metrics.
        """
        risk_scores = []
        
        # Open query count risk
        if open_queries >= self.THRESHOLDS["open_query_count"]["critical"]:
            risk_scores.append(4)  # CRITICAL
        elif open_queries >= self.THRESHOLDS["open_query_count"]["high"]:
            risk_scores.append(3)  # HIGH
        elif open_queries >= self.THRESHOLDS["open_query_count"]["medium"]:
            risk_scores.append(2)  # MEDIUM
        else:
            risk_scores.append(1)  # LOW
        
        # Query aging risk
        if query_aging >= self.THRESHOLDS["query_aging_days"]["critical"]:
            risk_scores.append(4)
        elif query_aging >= self.THRESHOLDS["query_aging_days"]["high"]:
            risk_scores.append(3)
        elif query_aging >= self.THRESHOLDS["query_aging_days"]["medium"]:
            risk_scores.append(2)
        else:
            risk_scores.append(1)
        
        # Use maximum risk score (worst case)
        max_risk = max(risk_scores) if risk_scores else 1
        
        risk_map = {
            4: RiskSignal.CRITICAL,
            3: RiskSignal.HIGH,
            2: RiskSignal.MEDIUM,
            1: RiskSignal.LOW,
        }
        
        return risk_map.get(max_risk, RiskSignal.LOW)
    
    def _generate_recommendations(
        self,
        risk_level: RiskSignal,
        open_queries: int,
        query_aging: float,
        data_entry_lag: Optional[float]
    ) -> List[str]:
        """Generate actionable recommendations based on findings."""
        recommendations = []
        
        # Open query recommendations
        if open_queries >= self.THRESHOLDS["open_query_count"]["critical"]:
            recommendations.append(
                f"CRITICAL: {open_queries} open queries - "
                "immediate query resolution sprint required"
            )
        elif open_queries >= self.THRESHOLDS["open_query_count"]["high"]:
            recommendations.append(
                f"HIGH PRIORITY: {open_queries} open queries - "
                "allocate additional resources for query resolution"
            )
        elif open_queries >= self.THRESHOLDS["open_query_count"]["medium"]:
            recommendations.append(
                f"Monitor query backlog ({open_queries} open) - "
                "prioritize oldest queries"
            )
        
        # Query aging recommendations
        if query_aging >= self.THRESHOLDS["query_aging_days"]["critical"]:
            recommendations.append(
                f"CRITICAL: Query aging at {query_aging:.1f} days - "
                "review query workflow and site responsiveness"
            )
        elif query_aging >= self.THRESHOLDS["query_aging_days"]["high"]:
            recommendations.append(
                f"HIGH PRIORITY: Query aging at {query_aging:.1f} days - "
                "escalate to site monitors"
            )
        elif query_aging >= self.THRESHOLDS["query_aging_days"]["medium"]:
            recommendations.append(
                f"Query aging at {query_aging:.1f} days - "
                "follow up with sites on pending queries"
            )
        
        # Data entry lag correlation
        if data_entry_lag is not None and data_entry_lag > 7:
            recommendations.append(
                f"Data entry lag ({data_entry_lag:.1f} days) may be contributing to query backlog - "
                "address root cause"
            )
        
        if not recommendations:
            recommendations.append("Query metrics within acceptable ranges - continue monitoring")
        
        return recommendations


__all__ = ["QueryQualityAgent"]
