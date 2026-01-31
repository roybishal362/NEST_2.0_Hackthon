"""
C-TRUST Core Module
==================

Core infrastructure components for the Clinical AI System including:
- Configuration management
- Database operations
- Logging system
- Utility functions
- Data models
"""

from .config import ConfigManager, config_manager
from .settings import settings, yaml_config, get_settings, get_yaml_config
from .database import DatabaseManager, db_manager, init_database, get_database
from .logger import setup_logging, get_logger, audit_logger
from .models import (
    ClinicalSnapshot,
    AgentSignal,
    ConsensusDecision,
    DQIScore,
    GuardianEvent,
    AIExplanation,
    UserInteraction,
    DashboardAction,
    FeatureVector,
    AuditEvent,
    Severity,
    RiskLevel,
    DQIBand,
    ProcessingStatus
)
from .utils import (
    generate_id,
    generate_snapshot_id,
    calculate_hash,
    safe_divide,
    calculate_percentage,
    normalize_score,
    weighted_average,
    classify_dqi_band,
    format_confidence,
    format_timestamp,
    parse_study_id,
    validate_file_path,
    ensure_directory,
    load_excel_safely,
    load_csv_safely,
    calculate_data_delta,
    merge_dictionaries,
    chunk_list,
    flatten_dict,
    clamp,
    Timer
)
from .performance import (
    ProgressStatus,
    ProgressInfo,
    ProgressTracker,
    RetryConfig,
    RetryResult,
    calculate_backoff_delay,
    retry_with_backoff,
    with_retry,
    QueuedTask,
    TaskResult,
    ResourceConstrainedQueue,
    PerformanceMetrics,
    PerformanceMonitor,
    performance_monitor,
)

__version__ = "1.0.0"
__author__ = "C-TRUST Development Team"

# Initialize core components
def initialize_core_system():
    """Initialize all core system components"""
    try:
        # Setup logging first
        setup_logging()
        logger = get_logger("core.init")
        logger.info("Initializing C-TRUST core system...")
        
        # Initialize database
        init_database()
        logger.info("Database initialized successfully")
        
        # Load configuration
        config = config_manager.get_config()
        logger.info(f"Configuration loaded: {len(config.agent_configs)} agents configured")
        
        # Verify system health
        if db_manager.health_check():
            logger.info("Database health check passed")
        else:
            logger.warning("Database health check failed")
        
        logger.info("C-TRUST core system initialization completed")
        return True
        
    except Exception as e:
        print(f"Failed to initialize core system: {e}")
        return False


__all__ = [
    # Configuration
    'ConfigManager',
    'config_manager',
    'settings',
    'yaml_config',
    'get_settings',
    'get_yaml_config',
    
    # Database
    'DatabaseManager',
    'db_manager',
    'init_database',
    'get_database',
    
    # Logging
    'setup_logging',
    'get_logger',
    'audit_logger',
    
    # Models
    'ClinicalSnapshot',
    'AgentSignal',
    'ConsensusDecision',
    'DQIScore',
    'GuardianEvent',
    'AIExplanation',
    'UserInteraction',
    'DashboardAction',
    'FeatureVector',
    'AuditEvent',
    'Severity',
    'RiskLevel',
    'DQIBand',
    'ProcessingStatus',
    
    # Utilities
    'generate_id',
    'generate_snapshot_id',
    'calculate_hash',
    'safe_divide',
    'calculate_percentage',
    'normalize_score',
    'weighted_average',
    'classify_dqi_band',
    'format_confidence',
    'format_timestamp',
    'parse_study_id',
    'validate_file_path',
    'ensure_directory',
    'load_excel_safely',
    'load_csv_safely',
    'calculate_data_delta',
    'merge_dictionaries',
    'chunk_list',
    'flatten_dict',
    'clamp',
    'Timer',
    
    # Performance monitoring
    'ProgressStatus',
    'ProgressInfo',
    'ProgressTracker',
    'RetryConfig',
    'RetryResult',
    'calculate_backoff_delay',
    'retry_with_backoff',
    'with_retry',
    'QueuedTask',
    'TaskResult',
    'ResourceConstrainedQueue',
    'PerformanceMetrics',
    'PerformanceMonitor',
    'performance_monitor',
    
    # System initialization
    'initialize_core_system'
]