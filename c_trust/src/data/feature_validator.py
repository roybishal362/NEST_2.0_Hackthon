"""
Feature Validator for C-TRUST Agent System
==========================================

This module validates that extracted features meet agent requirements.
Each agent requires specific features to operate. The validator checks:
- Which features are available vs missing
- Whether each agent has sufficient data to run (≥50% of required features)
- Overall data quality across all agents

Key Features:
- Validates features against agent requirements
- 50% threshold: agent can run if ≥50% of required features available
- Detailed reporting of available/missing features per agent
- Overall system readiness assessment

Author: C-TRUST Team
Date: 2025
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class AgentValidationResult:
    """
    Validation result for a single agent.
    
    Attributes:
        agent_name: Name of the agent
        required_features: List of features required by this agent
        available_features: List of required features that are available (not None)
        missing_features: List of required features that are missing (None)
        can_run: Whether agent has sufficient data to run (≥50% features available)
        availability_rate: Percentage of required features available (0.0 to 1.0)
    """
    agent_name: str
    required_features: List[str]
    available_features: List[str]
    missing_features: List[str]
    can_run: bool
    availability_rate: float
    
    def __str__(self) -> str:
        """String representation of validation result."""
        status = "✓ CAN RUN" if self.can_run else "✗ CANNOT RUN"
        return (
            f"{self.agent_name}: {status} "
            f"({len(self.available_features)}/{len(self.required_features)} features, "
            f"{self.availability_rate:.0%})"
        )


@dataclass
class ValidationResult:
    """
    Overall validation result for all agents.
    
    Attributes:
        agent_results: Dictionary mapping agent name to AgentValidationResult
        total_agents: Total number of agents
        agents_can_run: Number of agents that can run
        agents_cannot_run: Number of agents that cannot run
        overall_readiness: Overall system readiness (0.0 to 1.0)
    """
    agent_results: Dict[str, AgentValidationResult] = field(default_factory=dict)
    
    @property
    def total_agents(self) -> int:
        """Total number of agents validated."""
        return len(self.agent_results)
    
    @property
    def agents_can_run(self) -> int:
        """Number of agents that can run."""
        return sum(1 for result in self.agent_results.values() if result.can_run)
    
    @property
    def agents_cannot_run(self) -> int:
        """Number of agents that cannot run."""
        return sum(1 for result in self.agent_results.values() if not result.can_run)
    
    @property
    def overall_readiness(self) -> float:
        """Overall system readiness (percentage of agents that can run)."""
        if self.total_agents == 0:
            return 0.0
        return self.agents_can_run / self.total_agents
    
    def add_agent_result(self, result: AgentValidationResult) -> None:
        """Add an agent validation result."""
        self.agent_results[result.agent_name] = result
    
    def get_agent_result(self, agent_name: str) -> Optional[AgentValidationResult]:
        """Get validation result for a specific agent."""
        return self.agent_results.get(agent_name)
    
    def __str__(self) -> str:
        """String representation of overall validation result."""
        lines = [
            "=" * 70,
            "Feature Validation Result",
            "=" * 70,
            f"Overall Readiness: {self.overall_readiness:.0%} "
            f"({self.agents_can_run}/{self.total_agents} agents can run)",
            "",
            "Agent Status:",
            "-" * 70
        ]
        
        for agent_name, result in sorted(self.agent_results.items()):
            lines.append(str(result))
            if result.missing_features:
                lines.append(f"  Missing: {', '.join(result.missing_features)}")
        
        lines.append("=" * 70)
        return "\n".join(lines)


class FeatureValidator:
    """
    Validates extracted features meet agent requirements.
    
    Each agent requires specific features to operate. This validator checks
    whether sufficient features are available for each agent to run.
    
    Validation Rules:
    - Agent can run if ≥50% of required features are available (not None)
    - Features with value None are considered missing
    - Features with value 0 are considered available (zero is valid data)
    
    Example:
        validator = FeatureValidator()
        features = extract_features_from_nest(study_id, nest_data)
        result = validator.validate(features)
        
        if result.overall_readiness >= 0.7:
            print("System ready to run")
        else:
            print(f"Only {result.agents_can_run} agents can run")
    """
    
    def __init__(self):
        """Initialize validator with agent feature requirements."""
        # Define required features per agent (from requirements.md section 1.1)
        self.required_features_by_agent: Dict[str, List[str]] = {
            'completeness': [
                'form_completion_rate',
                'visit_completion_rate',
                'missing_pages_pct'
            ],
            'safety': [
                'sae_dm_open_discrepancies',
                'sae_dm_avg_age_days'
            ],
            'query_quality': [
                'open_query_count',
                'query_aging_days'
            ],
            'coding': [
                'coding_completion_rate',
                'uncoded_terms_count',
                'coding_backlog_days'
            ],
            'temporal_drift': [
                'avg_data_entry_lag_days',
                'visit_date_count'
            ],
            'edc_quality': [
                'verified_forms',
                'total_forms'
            ],
            'stability': [
                'completed_visits',
                'total_planned_visits'
            ]
        }
        
        # Validation threshold: agent can run if ≥50% of features available
        self.availability_threshold = 0.5
        
        logger.info(
            f"FeatureValidator initialized with {len(self.required_features_by_agent)} agents, "
            f"threshold: {self.availability_threshold:.0%}"
        )
    
    def validate(self, features: Dict[str, Any]) -> ValidationResult:
        """
        Validate features and return detailed report.
        
        Args:
            features: Dictionary of extracted features (feature_name -> value)
                     Features with value None are considered missing
        
        Returns:
            ValidationResult with detailed information per agent
        
        Example:
            result = validator.validate(features)
            print(result)  # Prints formatted validation report
            
            for agent_name, agent_result in result.agent_results.items():
                if not agent_result.can_run:
                    print(f"{agent_name} cannot run: {agent_result.missing_features}")
        """
        result = ValidationResult()
        
        # Validate each agent's requirements
        for agent_name, required_features in self.required_features_by_agent.items():
            agent_result = self._validate_agent(agent_name, required_features, features)
            result.add_agent_result(agent_result)
        
        # Log summary
        logger.info(
            f"Validation complete: {result.agents_can_run}/{result.total_agents} agents can run "
            f"(readiness: {result.overall_readiness:.0%})"
        )
        
        # Log details for agents that cannot run
        for agent_name, agent_result in result.agent_results.items():
            if not agent_result.can_run:
                logger.warning(
                    f"{agent_name} cannot run: {len(agent_result.missing_features)} "
                    f"features missing ({agent_result.availability_rate:.0%} available)"
                )
        
        return result
    
    def _validate_agent(
        self,
        agent_name: str,
        required_features: List[str],
        features: Dict[str, Any]
    ) -> AgentValidationResult:
        """
        Validate features for a single agent.
        
        Args:
            agent_name: Name of the agent
            required_features: List of features required by this agent
            features: Dictionary of extracted features
        
        Returns:
            AgentValidationResult for this agent
        """
        # Separate available from missing features
        # Note: 0 is a valid value, only None is considered missing
        available_features = [
            f for f in required_features
            if f in features and features[f] is not None
        ]
        
        missing_features = [
            f for f in required_features
            if f not in features or features[f] is None
        ]
        
        # Calculate availability rate
        availability_rate = (
            len(available_features) / len(required_features)
            if required_features else 0.0
        )
        
        # Agent can run if ≥50% of features available
        can_run = availability_rate >= self.availability_threshold
        
        return AgentValidationResult(
            agent_name=agent_name,
            required_features=required_features,
            available_features=available_features,
            missing_features=missing_features,
            can_run=can_run,
            availability_rate=availability_rate
        )
    
    def get_all_required_features(self) -> List[str]:
        """
        Get list of all features required by any agent.
        
        Returns:
            Sorted list of unique feature names
        
        Example:
            all_features = validator.get_all_required_features()
            print(f"Total features needed: {len(all_features)}")
        """
        all_features = set()
        for features in self.required_features_by_agent.values():
            all_features.update(features)
        return sorted(all_features)
    
    def get_agent_requirements(self, agent_name: str) -> Optional[List[str]]:
        """
        Get required features for a specific agent.
        
        Args:
            agent_name: Name of the agent
        
        Returns:
            List of required feature names, or None if agent not found
        
        Example:
            features = validator.get_agent_requirements('completeness')
            print(f"Completeness agent needs: {features}")
        """
        return self.required_features_by_agent.get(agent_name)
    
    def get_feature_coverage(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get detailed feature coverage statistics.
        
        Args:
            features: Dictionary of extracted features
        
        Returns:
            Dictionary with coverage statistics
        
        Example:
            coverage = validator.get_feature_coverage(features)
            print(f"Overall coverage: {coverage['overall_coverage']:.0%}")
        """
        all_required = self.get_all_required_features()
        available = [f for f in all_required if f in features and features[f] is not None]
        missing = [f for f in all_required if f not in features or features[f] is None]
        
        return {
            'total_required': len(all_required),
            'available': len(available),
            'missing': len(missing),
            'overall_coverage': len(available) / len(all_required) if all_required else 0.0,
            'available_features': available,
            'missing_features': missing
        }
    
    def validate_with_details(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate features and return detailed dictionary (for API responses).
        
        Args:
            features: Dictionary of extracted features
        
        Returns:
            Dictionary with validation results in API-friendly format
        
        Example:
            details = validator.validate_with_details(features)
            return JSONResponse(details)
        """
        result = self.validate(features)
        coverage = self.get_feature_coverage(features)
        
        return {
            'overall_readiness': result.overall_readiness,
            'agents_can_run': result.agents_can_run,
            'agents_cannot_run': result.agents_cannot_run,
            'total_agents': result.total_agents,
            'feature_coverage': coverage,
            'agents': {
                agent_name: {
                    'can_run': agent_result.can_run,
                    'availability_rate': agent_result.availability_rate,
                    'available_features': agent_result.available_features,
                    'missing_features': agent_result.missing_features,
                    'required_features': agent_result.required_features
                }
                for agent_name, agent_result in result.agent_results.items()
            }
        }


# Export
__all__ = ['FeatureValidator', 'ValidationResult', 'AgentValidationResult']
