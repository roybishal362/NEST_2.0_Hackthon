"""
Configuration management for C-TRUST system
"""
import os
import yaml
from typing import Dict, Any, List, Union
from pathlib import Path
from pydantic import BaseModel


class AgentConfig(BaseModel):
    """Configuration for individual agents"""
    name: str
    weight: float
    enabled: bool = True
    abstention_threshold: float = 0.3


class DQIConfig(BaseModel):
    """Data Quality Index configuration"""
    weights: Dict[str, float] = {
        "safety": 0.35,
        "compliance": 0.25,
        "completeness": 0.20,
        "operations": 0.15
    }
    bands: Dict[str, Dict[str, float]] = {
        "GREEN": {"min": 85, "max": 100},
        "AMBER": {"min": 65, "max": 84},
        "ORANGE": {"min": 40, "max": 64},
        "RED": {"min": 0, "max": 39}
    }


class DataSourcesConfig(BaseModel):
    """Configuration for data sources and file patterns"""
    supported_types: List[str] = []
    file_patterns: Dict[str, Union[str, List[str]]] = {}


class SystemConfig(BaseModel):
    """Main system configuration"""
    # Database
    database_url: str = "sqlite:///c_trust.db"
    
    # Processing
    batch_size: int = 1000
    max_concurrent_jobs: int = 4
    processing_timeout_minutes: int = 30
    
    # Agents
    agent_configs: Dict[str, AgentConfig] = {
        "data_completeness": AgentConfig(name="Data Completeness", weight=1.5),
        "safety_compliance": AgentConfig(name="Safety & Compliance", weight=3.0),
        "query_quality": AgentConfig(name="Query Quality", weight=1.5),
        "coding_readiness": AgentConfig(name="Coding Readiness", weight=1.2),
        "stability": AgentConfig(name="Stability", weight=-1.5),
        "temporal_drift": AgentConfig(name="Temporal Drift", weight=1.2),
        "cross_evidence": AgentConfig(name="Cross Evidence", weight=1.0)
    }
    
    # DQI
    dqi_config: DQIConfig = DQIConfig()
    
    # Guardian
    guardian_enabled: bool = True
    guardian_sensitivity: float = 0.1
    
    # Dashboard
    dashboard_port: int = 8501
    dashboard_host: str = "localhost"
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/c_trust.log"

    # Data Sources
    data_sources: DataSourcesConfig = DataSourcesConfig()


class ConfigManager:
    """Manages system configuration with versioning"""
    
    def __init__(self, config_path: str = "config/system_config.yaml"):
        self.config_path = Path(config_path)
        self.config_version = "1.0.0"
        self._config: SystemConfig = SystemConfig()
        self.load_config()
    
    def load_config(self) -> SystemConfig:
        """Load configuration from file"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    config_data = yaml.safe_load(f)
                
                # Handle nested YAML structure
                if config_data:
                    # Flatten nested structure for compatibility
                    flattened_config = {}
                    
                    # Database configuration
                    if 'database' in config_data:
                        flattened_config['database_url'] = config_data['database'].get('url', 'sqlite:///c_trust.db')
                    
                    # Processing configuration
                    if 'processing' in config_data:
                        proc = config_data['processing']
                        flattened_config['batch_size'] = proc.get('batch_size', 1000)
                        flattened_config['max_concurrent_jobs'] = proc.get('max_concurrent_jobs', 4)
                        flattened_config['processing_timeout_minutes'] = proc.get('timeout_minutes', 30)
                    
                    # Agent configurations
                    if 'agents' in config_data:
                        agent_configs = {}
                        for agent_name, agent_data in config_data['agents'].items():
                            agent_configs[agent_name] = AgentConfig(
                                name=agent_data.get('name', agent_name),
                                weight=agent_data.get('weight', 1.0),
                                enabled=agent_data.get('enabled', True),
                                abstention_threshold=agent_data.get('abstention_threshold', 0.3)
                            )
                        flattened_config['agent_configs'] = agent_configs
                    
                    # DQI configuration
                    if 'dqi' in config_data:
                        dqi_data = config_data['dqi']
                        dqi_config = DQIConfig()
                        if 'weights' in dqi_data:
                            dqi_config.weights = dqi_data['weights']
                        if 'bands' in dqi_data:
                            dqi_config.bands = dqi_data['bands']
                        flattened_config['dqi_config'] = dqi_config
                    
                    # Guardian configuration
                    if 'guardian' in config_data:
                        guard = config_data['guardian']
                        flattened_config['guardian_enabled'] = guard.get('enabled', True)
                        flattened_config['guardian_sensitivity'] = guard.get('sensitivity', 0.1)
                    
                    # Dashboard configuration
                    if 'dashboard' in config_data:
                        dash = config_data['dashboard']
                        flattened_config['dashboard_port'] = dash.get('port', 8501)
                        flattened_config['dashboard_host'] = dash.get('host', 'localhost')
                    
                    # Logging configuration
                    if 'logging' in config_data:
                        log = config_data['logging']
                        flattened_config['log_level'] = log.get('level', 'INFO')
                        flattened_config['log_file'] = log.get('file', 'logs/c_trust.log')

                    # Data Sources configuration
                    if 'data_sources' in config_data:
                        ds = config_data['data_sources']
                        data_sources_config = DataSourcesConfig(
                            supported_types=ds.get('supported_types', []),
                            file_patterns=ds.get('file_patterns', {})
                        )
                        flattened_config['data_sources'] = data_sources_config
                    
                    self._config = SystemConfig(**flattened_config)
                else:
                    self._config = SystemConfig()
                    
            except Exception as e:
                print(f"Error loading config: {e}. Using defaults.")
                self._config = SystemConfig()
        else:
            # Create default config file
            self._config = SystemConfig()
            self.save_config()
        
        return self._config
    
    def save_config(self) -> None:
        """Save current configuration to file"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        config_dict = self._config.dict()
        config_dict["_version"] = self.config_version
        
        with open(self.config_path, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False, indent=2)
    
    def get_config(self) -> SystemConfig:
        """Get current configuration"""
        return self._config
    
    def update_config(self, updates: Dict[str, Any]) -> None:
        """Update configuration with new values"""
        # Create new config with updates
        config_dict = self._config.dict()
        config_dict.update(updates)
        
        # Validate and save
        self._config = SystemConfig(**config_dict)
        self.save_config()
    
    def get_agent_weight(self, agent_name: str) -> float:
        """Get weight for specific agent"""
        if agent_name in self._config.agent_configs:
            return self._config.agent_configs[agent_name].weight
        return 1.0
    
    def is_agent_enabled(self, agent_name: str) -> bool:
        """Check if agent is enabled"""
        if agent_name in self._config.agent_configs:
            return self._config.agent_configs[agent_name].enabled
        return True


# Global config manager instance
config_manager = ConfigManager()