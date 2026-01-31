"""
C-TRUST Base Agent Interface - Component 4
========================================
Base interface for all analysis agents.

Philosophy:
- SINGLE RESPONSIBILITY: Each agent analyzes one dimension
- DETERMINISTIC: Agents use only features, no raw data
- ABSTENTION: Agents can abstain if confidence is low
- ISOLATION: Agents don't communicate directly
- TRACEABLE: Every decision links to feature evidence

Agent Design Principles:
1. Input Contract: Receives only engineered features
2. Output Contract: Returns structured signal with confidence
3. Confidence Scoring: 0-1 scale based on data quality
4. Abstention Logic: Can refuse to analyze if data insufficient
5. Evidence Tracking: Cites specific features used

Production Features:
- Type-safe contracts
- Comprehensive validation
- Performance monitoring
- Audit logging
- Agent Registry for orchestration
- Isolation guarantees between agents
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type
import copy
import threading

from src.core import get_logger

logger = get_logger(__name__)


# ========================================
# AGENT ENUMERATIONS
# ========================================

class AgentType(str, Enum):
    """Types of specialized agents"""
    SAFETY = "safety"
    COMPLETENESS = "completeness"
    COMPLIANCE = "compliance"
    OPERATIONS = "operations"
    CODING = "coding"
    TIMELINE = "timeline"
    QUERY_QUALITY = "query_quality"  # Added for MVP
    # New agent types for full 7-agent system
    STABILITY = "stability"
    TEMPORAL_DRIFT = "temporal_drift"
    CROSS_EVIDENCE = "cross_evidence"


class RiskSignal(str, Enum):
    """Risk signals that agents can emit"""
    CRITICAL = "critical"  # Immediate action required
    HIGH = "high"  # Action required soon
    MEDIUM = "medium"  # Monitor closely
    LOW = "low"  # Normal state
    UNKNOWN = "unknown"  # Insufficient data


# ========================================
# AGENT DATA STRUCTURES
# ========================================

@dataclass
class FeatureEvidence:
    """
    Evidence from a single feature.
    
    Attributes:
        feature_name: Name of feature
        feature_value: Actual value
        threshold: Threshold that triggered this evidence
        severity: How severe this signal is (0-1)
        description: Human-readable description
    """
    feature_name: str
    feature_value: Any
    threshold: Optional[float] = None
    severity: float = 0.0
    description: str = ""
    
    def __post_init__(self):
        """Validate severity is in [0, 1]"""
        if not 0 <= self.severity <= 1:
            raise ValueError("Severity must be between 0 and 1")


@dataclass
class AgentSignal:
    """
    Output signal from an agent.
    
    This is the contract for what agents return.
    
    Attributes:
        agent_type: Which agent produced this signal
        risk_level: Assessed risk level
        confidence: Confidence in assessment (0-1)
        evidence: List of feature evidence supporting this signal
        recommended_actions: Suggested actions
        abstained: Whether agent abstained from analysis
        abstention_reason: Why agent abstained (if applicable)
    """
    agent_type: AgentType
    risk_level: RiskSignal
    confidence: float
    evidence: List[FeatureEvidence] = field(default_factory=list)
    recommended_actions: List[str] = field(default_factory=list)
    abstained: bool = False
    abstention_reason: Optional[str] = None
    
    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)
    features_analyzed: int = 0
    
    def __post_init__(self):
        """Validate confidence is in [0, 1]"""
        if not 0 <= self.confidence <= 1:
            raise ValueError("Confidence must be between 0 and 1")
        
        if self.abstained and not self.abstention_reason:
            raise ValueError("Must provide abstention_reason when abstained=True")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "agent_type": self.agent_type.value,
            "risk_level": self.risk_level.value,
            "confidence": self.confidence,
            "evidence": [
                {
                    "feature_name": e.feature_name,
                    "feature_value": e.feature_value,
                    "threshold": e.threshold,
                    "severity": e.severity,
                    "description": e.description
                }
                for e in self.evidence
            ],
            "recommended_actions": self.recommended_actions,
            "abstained": self.abstained,
            "abstention_reason": self.abstention_reason,
            "timestamp": self.timestamp.isoformat(),
            "features_analyzed": self.features_analyzed,
        }


# ========================================
# BASE AGENT INTERFACE
# ========================================

class BaseAgent(ABC):
    """
    Abstract base class for all agents.
    
    All agents must implement:
    - analyze(): Main analysis method
    - _calculate_confidence(): Confidence scoring
    - _should_abstain(): Abstention logic
    """
    
    def __init__(
        self,
        agent_type: AgentType,
        min_confidence: float = 0.6,
        abstention_threshold: float = 0.5
    ):
        """
        Initialize base agent.
        
        Args:
            agent_type: Type of agent
            min_confidence: Minimum confidence to emit non-abstention signal
            abstention_threshold: Threshold below which to abstain
        """
        self.agent_type = agent_type
        self.min_confidence = min_confidence
        self.abstention_threshold = abstention_threshold
        
        # Configuration from YAML (populated by subclasses)
        self.critical_thresholds: Dict[str, float] = {}
        self.feature_weights: Dict[str, float] = {}
        
        logger.info(f"{self.agent_type.value} agent initialized")
    
    @abstractmethod
    def analyze(
        self,
        features: Dict[str, Any],
        study_id: str
    ) -> AgentSignal:
        """
        Analyze features and return risk signal.
        
        Args:
            features: Dictionary of engineered features
            study_id: Study identifier for logging
        
        Returns:
            AgentSignal with risk assessment
        
        This method MUST be implemented by all subclasses.
        """
        pass
    
    @abstractmethod
    def _calculate_confidence(self, features: Dict[str, Any]) -> float:
        """
        Calculate confidence score based on data quality.
        
        Factors to consider:
        - Are required features present?
        - Are feature values missing/null?
        - Is data recent?
        
        Returns:
            Confidence score between 0 and 1
        """
        pass
    
    def _should_abstain(
        self,
        features: Dict[str, Any],
        required_features: List[str]
    ) -> tuple[bool, Optional[str]]:
        """
        Enhanced abstention logic with detailed reasoning and partial data handling.
        
        Args:
            features: Available features
            required_features: Features required for this agent
        
        Returns:
            Tuple of (should_abstain, abstention_reason)
        """
        # Check if required features are present
        missing_features = [f for f in required_features if f not in features]
        
        if missing_features:
            reason = (
                f"Missing required features ({len(missing_features)}/{len(required_features)}): "
                f"{', '.join(missing_features[:3])}"
                f"{'...' if len(missing_features) > 3 else ''}"
            )
            logger.warning(f"{self.agent_type.value} abstaining: {reason}")
            return True, reason
        
        # Check feature data quality (null values)
        null_features = [
            f for f in required_features
            if features.get(f) is None
        ]
        
        if len(null_features) > len(required_features) * 0.5:
            available_count = len(required_features) - len(null_features)
            reason = (
                f"Insufficient data: {len(null_features)}/{len(required_features)} "
                f"required features are null. Available: {available_count}. "
                f"Missing: {', '.join(null_features[:3])}"
                f"{'...' if len(null_features) > 3 else ''}"
            )
            logger.warning(f"{self.agent_type.value} abstaining: {reason}")
            return True, reason
        
        # Calculate confidence with partial data handling
        confidence = self._calculate_confidence_with_partial_data(features, required_features)
        
        if confidence < self.abstention_threshold:
            available_count = len(required_features) - len(null_features)
            reason = (
                f"Low confidence ({confidence:.2f}) below threshold ({self.abstention_threshold}). "
                f"Available features: {available_count}/{len(required_features)}. "
                f"Data quality may be insufficient for reliable analysis."
            )
            logger.info(f"{self.agent_type.value} abstaining: {reason}")
            return True, reason
        
        # Log successful analysis decision
        logger.debug(
            f"{self.agent_type.value} proceeding with analysis: "
            f"confidence={confidence:.2f}, "
            f"available_features={len(required_features) - len(null_features)}/{len(required_features)}"
        )
        
        return False, None
    
    def _calculate_confidence_with_partial_data(
        self,
        features: Dict[str, Any],
        required_features: List[str]
    ) -> float:
        """
        Calculate confidence accounting for missing data and feature variance.
        
        This enhanced confidence calculation:
        1. Accounts for data completeness (how many features available)
        2. Checks feature variance to avoid identical values across studies
        3. Validates data quality (non-zero, non-null values)
        
        Args:
            features: Available features
            required_features: Features required for this agent
        
        Returns:
            Confidence score between 0 and 1
        """
        if not required_features:
            return 0.0
        
        # Get available features (non-null)
        available_features = {
            k: v for k, v in features.items()
            if k in required_features and v is not None
        }
        
        if not available_features:
            return 0.0
        
        # Factor 1: Data completeness (70% weight)
        # How many of the required features are available?
        completeness = len(available_features) / len(required_features)
        
        # Factor 2: Feature variance (30% weight)
        # Avoid identical values that suggest data quality issues
        variance_score = self._calculate_variance_score(available_features)
        
        # Weighted combination
        confidence = (completeness * 0.7) + (variance_score * 0.3)
        
        return min(max(confidence, 0.0), 1.0)
    
    def _calculate_variance_score(self, features: Dict[str, Any]) -> float:
        """
        Calculate variance score to detect identical/low-quality data.
        
        This prevents agents from analyzing data where all values are identical
        (which often indicates extraction or data quality issues).
        
        Args:
            features: Dictionary of feature values
        
        Returns:
            Variance score between 0 and 1 (1 = good variance, 0 = all identical)
        """
        if not features:
            return 0.0
        
        # Extract numeric values only
        numeric_values = []
        for value in features.values():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                numeric_values.append(float(value))
        
        if len(numeric_values) < 2:
            # Not enough numeric features to calculate variance
            # Return moderate score (0.5) to not penalize too much
            return 0.5
        
        # Check if all values are identical
        if len(set(numeric_values)) == 1:
            # All values identical - likely data quality issue
            return 0.0
        
        # Calculate coefficient of variation (normalized variance)
        try:
            mean_val = sum(numeric_values) / len(numeric_values)
            if mean_val == 0:
                # Avoid division by zero
                return 0.5
            
            variance = sum((x - mean_val) ** 2 for x in numeric_values) / len(numeric_values)
            std_dev = variance ** 0.5
            cv = std_dev / abs(mean_val)
            
            # Normalize CV to [0, 1] range
            # CV > 0.5 is considered good variance
            variance_score = min(cv / 0.5, 1.0)
            
            return variance_score
            
        except Exception as e:
            logger.debug(f"Variance calculation error: {e}")
            return 0.5  # Default moderate score on error
    
    def _create_abstention_signal(self, reason: str) -> AgentSignal:
        """Create an abstention signal"""
        return AgentSignal(
            agent_type=self.agent_type,
            risk_level=RiskSignal.UNKNOWN,
            confidence=0.0,
            abstained=True,
            abstention_reason=reason,
        )
    
    def _assess_risk_from_thresholds(
        self,
        feature_value: float,
        thresholds: Dict[str, float]
    ) -> RiskSignal:
        """
        Assess risk level based on threshold comparison.
        
        Args:
            feature_value: Value to assess
            thresholds: Dict with 'critical', 'high', 'medium' keys
        
        Returns:
            Risk signal
        """
        if feature_value >= thresholds.get("critical", float("inf")):
            return RiskSignal.CRITICAL
        elif feature_value >= thresholds.get("high", float("inf")):
            return RiskSignal.HIGH
        elif feature_value >= thresholds.get("medium", float("inf")):
            return RiskSignal.MEDIUM
        else:
            return RiskSignal.LOW
    
    def _calculate_severity(
        self,
        feature_value: float,
        threshold: float,
        max_value: Optional[float] = None
    ) -> float:
        """
        Calculate severity score (0-1) based on how far value exceeds threshold.
        
        Args:
            feature_value: Actual value
            threshold: Threshold value
            max_value: Maximum possible value (for normalization)
        
        Returns:
            Severity score between 0 and 1
        """
        if feature_value <= threshold:
            return 0.0
        
        if max_value:
            # Normalize to [0, 1] range
            excess = feature_value - threshold
            max_excess = max_value - threshold
            return min(excess / max_excess, 1.0)
        else:
            # Simple exponential scaling
            excess_ratio = (feature_value - threshold) / threshold
            return min(excess_ratio, 1.0)


# ========================================
# AGENT REGISTRY AND ORCHESTRATION
# ========================================

class AgentRegistry:
    """
    Central registry for all agents in the system.
    
    Provides:
    - Agent registration and lookup
    - Agent lifecycle management
    - Isolation guarantees (agents get deep copies of data)
    - Orchestration of multi-agent analysis
    
    Thread-safe singleton pattern for production use.
    """
    
    _instance: Optional['AgentRegistry'] = None
    _lock = threading.Lock()
    
    def __new__(cls) -> 'AgentRegistry':
        """Singleton pattern for registry"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize registry (only once due to singleton)"""
        if self._initialized:
            return
        
        self._agents: Dict[str, BaseAgent] = {}
        self._agent_weights: Dict[str, float] = {}
        self._initialized = True
        logger.info("AgentRegistry initialized")
    
    def register(
        self,
        agent: 'BaseAgent',
        weight: float = 1.0
    ) -> None:
        """
        Register an agent with the registry.
        
        Args:
            agent: Agent instance to register
            weight: Weight for consensus voting (default 1.0)
        
        Raises:
            ValueError: If agent with same type already registered
        """
        agent_key = agent.agent_type.value
        
        if agent_key in self._agents:
            logger.warning(f"Replacing existing agent: {agent_key}")
        
        self._agents[agent_key] = agent
        self._agent_weights[agent_key] = weight
        logger.info(f"Registered agent: {agent_key} with weight {weight}")
    
    def unregister(self, agent_type: AgentType) -> bool:
        """
        Unregister an agent from the registry.
        
        Args:
            agent_type: Type of agent to unregister
        
        Returns:
            True if agent was unregistered, False if not found
        """
        agent_key = agent_type.value
        
        if agent_key in self._agents:
            del self._agents[agent_key]
            del self._agent_weights[agent_key]
            logger.info(f"Unregistered agent: {agent_key}")
            return True
        
        return False
    
    def get_agent(self, agent_type: AgentType) -> Optional['BaseAgent']:
        """Get agent by type"""
        return self._agents.get(agent_type.value)
    
    def get_all_agents(self) -> List['BaseAgent']:
        """Get all registered agents"""
        return list(self._agents.values())
    
    def get_agent_weight(self, agent_type: AgentType) -> float:
        """Get weight for an agent"""
        return self._agent_weights.get(agent_type.value, 1.0)
    
    def clear(self) -> None:
        """Clear all registered agents (useful for testing)"""
        self._agents.clear()
        self._agent_weights.clear()
        logger.info("AgentRegistry cleared")
    
    @property
    def agent_count(self) -> int:
        """Number of registered agents"""
        return len(self._agents)


class AgentOrchestrator:
    """
    Orchestrates multi-agent analysis with isolation guarantees.
    
    Key responsibilities:
    - Coordinate agent execution
    - Ensure agent isolation (deep copy of features)
    - Collect and aggregate signals
    - Handle agent failures gracefully
    
    Isolation Guarantee:
    Each agent receives a deep copy of the feature dictionary,
    ensuring that modifications by one agent cannot affect others.
    """
    
    def __init__(self, registry: Optional[AgentRegistry] = None):
        """
        Initialize orchestrator.
        
        Args:
            registry: Agent registry (uses singleton if not provided)
        """
        self.registry = registry or AgentRegistry()
        logger.info("AgentOrchestrator initialized")
    
    def run_all_agents(
        self,
        features: Dict[str, Any],
        study_id: str
    ) -> List[AgentSignal]:
        """
        Run all registered agents with isolation guarantees.
        
        Each agent receives a deep copy of features to ensure
        complete isolation between agents.
        
        Args:
            features: Feature dictionary for analysis
            study_id: Study identifier
        
        Returns:
            List of AgentSignal from all agents
        """
        signals: List[AgentSignal] = []
        agents = self.registry.get_all_agents()
        
        logger.info(f"Running {len(agents)} agents for study {study_id}")
        
        for agent in agents:
            try:
                # ISOLATION: Deep copy features for each agent
                isolated_features = copy.deepcopy(features)
                
                signal = agent.analyze(isolated_features, study_id)
                signals.append(signal)
                
                logger.debug(
                    f"Agent {agent.agent_type.value}: "
                    f"risk={signal.risk_level.value}, "
                    f"confidence={signal.confidence:.2f}, "
                    f"abstained={signal.abstained}"
                )
                
            except Exception as e:
                logger.error(f"Agent {agent.agent_type.value} failed: {e}")
                # Create abstention signal for failed agent
                signals.append(AgentSignal(
                    agent_type=agent.agent_type,
                    risk_level=RiskSignal.UNKNOWN,
                    confidence=0.0,
                    abstained=True,
                    abstention_reason=f"Agent execution failed: {str(e)}"
                ))
        
        logger.info(f"Completed {len(signals)} agent analyses for {study_id}")
        return signals
    
    def run_single_agent(
        self,
        agent_type: AgentType,
        features: Dict[str, Any],
        study_id: str
    ) -> Optional[AgentSignal]:
        """
        Run a single agent with isolation.
        
        Args:
            agent_type: Type of agent to run
            features: Feature dictionary
            study_id: Study identifier
        
        Returns:
            AgentSignal or None if agent not found
        """
        agent = self.registry.get_agent(agent_type)
        
        if agent is None:
            logger.warning(f"Agent not found: {agent_type.value}")
            return None
        
        # ISOLATION: Deep copy features
        isolated_features = copy.deepcopy(features)
        
        try:
            return agent.analyze(isolated_features, study_id)
        except Exception as e:
            logger.error(f"Agent {agent_type.value} failed: {e}")
            return AgentSignal(
                agent_type=agent_type,
                risk_level=RiskSignal.UNKNOWN,
                confidence=0.0,
                abstained=True,
                abstention_reason=f"Agent execution failed: {str(e)}"
            )
    
    def get_non_abstained_signals(
        self,
        signals: List[AgentSignal]
    ) -> List[AgentSignal]:
        """
        Filter out abstained signals.
        
        Args:
            signals: List of all signals
        
        Returns:
            List of signals where agent did not abstain
        """
        return [s for s in signals if not s.abstained]


# ========================================
# EXPORTS
# ========================================

__all__ = [
    "BaseAgent",
    "AgentType",
    "RiskSignal",
    "FeatureEvidence",
    "AgentSignal",
    "AgentRegistry",
    "AgentOrchestrator",
]
