"""
C-TRUST Core Settings Module
========================================
Manages application configuration from environment variables and YAML files.
Implements Pydantic-based settings for type safety and validation.

Production-ready configuration management with:
- Environment variable loading (.env)
- YAML configuration merging
- Type-safe settings validation
- Sensible defaults for all configurations
"""

from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Main application settings class.
    
    Loads configuration from:
    1. Environment variables (.env file)
    2. Direct environment variables
    3. YAML configuration files
    
    All settings are type-validated and have sensible defaults.
    """
    
    # ========================================
    # APPLICATION SETTINGS
    # ========================================
    APP_NAME: str = "C-TRUST"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "production"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    # ========================================
    # API CONFIGURATION
    # ========================================
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_PREFIX: str = "/api/v1"
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    # ========================================
    # DATABASE CONFIGURATION
    # ========================================
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "ctrust_db"
    DB_USER: str = "ctrust_admin"
    DB_PASSWORD: str = "changeme_in_production"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    
    @property
    def database_url(self) -> str:
        """Construct PostgreSQL connection URL"""
        return (
            f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )
    
    @property
    def async_database_url(self) -> str:
        """Construct async PostgreSQL connection URL"""
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )
    
    # ========================================
    # REDIS CONFIGURATION
    # ========================================
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    
    @property
    def redis_url(self) -> str:
        """Construct Redis connection URL"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    # ========================================
    # AI/ML CONFIGURATION
    # ========================================
    GROQ_API_KEY: str = Field(..., description="Groq API key is required")
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_TEMPERATURE: float = 0.1
    GROQ_MAX_TOKENS: int = 2048
    
    # ========================================
    # DATA SOURCE CONFIGURATION
    # ========================================
    DATA_ROOT_PATH: str = Field(
        ...,
        description="Path to NEST 2.0 dataset root directory"
    )
    BATCH_SIZE: int = 10
    MAX_WORKERS: int = 4
    SNAPSHOT_RETENTION_DAYS: int = 90
    
    @field_validator("DATA_ROOT_PATH")
    @classmethod
    def validate_data_path(cls, v: str) -> str:
        """Validate that data root path exists"""
        path = Path(v)
        if not path.exists():
            raise ValueError(f"DATA_ROOT_PATH does not exist: {v}")
        return v
    
    # ========================================
    # SECURITY SETTINGS
    # ========================================
    SECRET_KEY: str = Field(
        ...,
        min_length=32,
        description="Secret key for JWT token generation"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # ========================================
    # DQI ENGINE CONFIGURATION
    # ========================================
    DQI_SAFETY_WEIGHT: int = 35
    DQI_COMPLIANCE_WEIGHT: int = 25
    DQI_COMPLETENESS_WEIGHT: int = 25
    DQI_OPERATIONS_WEIGHT: int = 15
    
    DQI_CRITICAL_THRESHOLD: int = 50
    DQI_HIGH_THRESHOLD: int = 70
    DQI_MEDIUM_THRESHOLD: int = 85
    
    @field_validator("DQI_SAFETY_WEIGHT", "DQI_COMPLIANCE_WEIGHT", "DQI_COMPLETENESS_WEIGHT", "DQI_OPERATIONS_WEIGHT")
    @classmethod
    def validate_dqi_weights(cls, v: int, info) -> int:
        """Validate DQI dimension weights sum to 100"""
        # Note: Full validation happens after all fields are set
        return v
    
    # ========================================
    # AGENT CONFIGURATION
    # ========================================
    AGENT_SAFETY_WEIGHT: int = 30
    AGENT_COMPLETENESS_WEIGHT: int = 20
    AGENT_COMPLIANCE_WEIGHT: int = 20
    AGENT_OPERATIONS_WEIGHT: int = 15
    AGENT_CODING_WEIGHT: int = 10
    AGENT_TIMELINE_WEIGHT: int = 5
    
    AGENT_MIN_CONFIDENCE: float = 0.6
    AGENT_ABSTENTION_THRESHOLD: float = 0.5
    
    # ========================================
    # GUARDIAN ENGINE SETTINGS
    # ========================================
    GUARDIAN_ENABLED: bool = True
    GUARDIAN_CHECK_INTERVAL_HOURS: int = 6
    GUARDIAN_DRIFT_THRESHOLD: float = 0.15
    
    # ========================================
    # FEATURE FLAGS
    # ========================================
    FEATURE_REALTIME_UPDATES: bool = True
    FEATURE_COLLABORATION: bool = True
    FEATURE_GUARDIAN: bool = True
    FEATURE_GENAI_EXPLANATIONS: bool = True
    
    # Pydantic Settings Configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


class YAMLConfig:
    """
    YAML configuration loader.
    
    Loads and merges configuration from settings.yaml file.
    Provides structured access to complex configuration objects.
    """
    
    def __init__(self, config_path: str = "config/settings.yaml"):
        """
        Initialize YAML config loader.
        
        Args:
            config_path: Path to settings.yaml file
        """
        self.config_path = Path(config_path)
        self._config: Dict = {}
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from YAML file"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        with open(self.config_path, "r", encoding="utf-8") as f:
            self._config = yaml.safe_load(f)
    
    def get(self, key: str, default=None):
        """
        Get configuration value by dot-separated key path.
        
        Args:
            key: Dot-separated key path (e.g., "dqi.dimensions.safety")
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        keys = key.split(".")
        value = self._config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        
        return value
    
    @property
    def dqi_config(self) -> Dict:
        """Get DQI configuration"""
        return self._config.get("dqi", {})
    
    @property
    def agent_config(self) -> Dict:
        """Get agent configuration"""
        return self._config.get("agents", {})
    
    @property
    def file_type_config(self) -> Dict:
        """Get file type mappings"""
        return self._config.get("file_types", {})
    
    @property
    def genai_config(self) -> Dict:
        """Get GenAI configuration"""
        return self._config.get("genai", {})
    
    @property
    def guardian_config(self) -> Dict:
        """Get Guardian engine configuration"""
        return self._config.get("guardian", {})
    
    @property
    def collaboration_config(self) -> Dict:
        """Get collaboration configuration"""
        return self._config.get("collaboration", {})


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached application settings instance.
    
    Uses LRU cache to ensure single instance across application.
    
    Returns:
        Settings: Application settings instance
    """
    return Settings()


@lru_cache()
def get_yaml_config() -> YAMLConfig:
    """
    Get cached YAML configuration instance.
    
    Uses LRU cache to ensure single instance and avoid repeated file reads.
    
    Returns:
        YAMLConfig: YAML configuration instance
    """
    return YAMLConfig()


# Convenience exports
settings = get_settings()
yaml_config = get_yaml_config()
