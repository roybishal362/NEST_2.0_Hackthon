"""
Pytest configuration and shared fixtures for C-TRUST tests
"""
import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

from src.core import initialize_core_system, config_manager, db_manager
from src.core.models import ClinicalSnapshot, AgentSignal, Severity


@pytest.fixture(scope="session")
def test_config():
    """Test configuration fixture"""
    return {
        "database_url": "sqlite:///:memory:",
        "log_level": "DEBUG",
        "batch_size": 10,
        "max_concurrent_jobs": 2
    }


@pytest.fixture(scope="session")
def temp_data_dir():
    """Create temporary directory for test data"""
    temp_dir = tempfile.mkdtemp(prefix="ctrust_test_")
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_snapshot():
    """Sample clinical snapshot for testing"""
    return ClinicalSnapshot(
        snapshot_id="test_snapshot_001",
        timestamp=datetime.now(),
        study_id="STUDY_001",
        data_sources={
            "EDC_Metrics": {"status": "loaded", "records": 100},
            "SAE_Dashboard": {"status": "loaded", "records": 5}
        },
        processing_status="COMPLETED"
    )


@pytest.fixture
def sample_agent_signal():
    """Sample agent signal for testing"""
    return AgentSignal(
        agent_name="data_completeness",
        entity_id="SITE_001",
        signal_type="MISSING_DATA",
        severity=Severity.MEDIUM,
        confidence=0.85,
        evidence=["Missing 15% of visit data", "Last update 3 days ago"],
        can_abstain=True
    )


@pytest.fixture
def mock_clinical_data():
    """Mock clinical trial data for testing"""
    return {
        "studies": [
            {
                "study_id": "STUDY_001",
                "sites": ["SITE_001", "SITE_002"],
                "subjects": 50,
                "visits": 200
            }
        ],
        "sites": [
            {
                "site_id": "SITE_001",
                "study_id": "STUDY_001",
                "subjects": 25,
                "completion_rate": 0.85
            }
        ]
    }


@pytest.fixture(autouse=True)
def setup_test_environment(test_config):
    """Setup test environment for each test"""
    # Override configuration for testing
    original_config = config_manager._config
    
    # Create test configuration
    test_system_config = config_manager._config.copy()
    test_system_config.database_url = test_config["database_url"]
    test_system_config.log_level = test_config["log_level"]
    
    config_manager._config = test_system_config
    
    # Initialize test database
    db_manager._initialize_engine()
    db_manager.create_tables()
    
    yield
    
    # Cleanup
    config_manager._config = original_config


@pytest.fixture
def property_test_settings():
    """Settings for property-based tests"""
    return {
        "max_examples": 100,
        "deadline": 10000,  # 10 seconds
        "suppress_health_check": []
    }