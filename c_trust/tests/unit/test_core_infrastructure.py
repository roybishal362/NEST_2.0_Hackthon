"""
Unit tests for core infrastructure components
"""
import pytest
from datetime import datetime
from pathlib import Path

from src.core import (
    config_manager, 
    generate_id, 
    generate_snapshot_id,
    calculate_hash,
    weighted_average,
    classify_dqi_band,
    Timer
)
from src.core.models import AgentSignal, Severity


class TestConfigManager:
    """Test configuration management"""
    
    def test_config_loading(self):
        """Test configuration loads successfully"""
        config = config_manager.get_config()
        assert config is not None
        assert config.database_url is not None
        assert len(config.agent_configs) > 0
    
    def test_agent_weights(self):
        """Test agent weight retrieval"""
        weight = config_manager.get_agent_weight("safety_compliance")
        assert weight == 3.0
        
        # Test unknown agent
        weight = config_manager.get_agent_weight("unknown_agent")
        assert weight == 1.0
    
    def test_agent_enabled_status(self):
        """Test agent enabled status"""
        enabled = config_manager.is_agent_enabled("safety_compliance")
        assert enabled is True


class TestUtilityFunctions:
    """Test utility functions"""
    
    def test_generate_id(self):
        """Test ID generation"""
        id1 = generate_id()
        id2 = generate_id()
        assert id1 != id2
        assert len(id1) > 0
        
        # Test with prefix
        prefixed_id = generate_id("test")
        assert prefixed_id.startswith("test_")
    
    def test_generate_snapshot_id(self):
        """Test snapshot ID generation"""
        snapshot_id = generate_snapshot_id("STUDY_001")
        assert "STUDY_001" in snapshot_id
        assert "snapshot_" in snapshot_id
    
    def test_calculate_hash(self):
        """Test hash calculation"""
        data1 = {"key": "value"}
        data2 = {"key": "value"}
        data3 = {"key": "different"}
        
        hash1 = calculate_hash(data1)
        hash2 = calculate_hash(data2)
        hash3 = calculate_hash(data3)
        
        assert hash1 == hash2  # Same data should produce same hash
        assert hash1 != hash3  # Different data should produce different hash
    
    def test_weighted_average(self):
        """Test weighted average calculation"""
        values = [80.0, 90.0, 70.0]
        weights = [0.5, 0.3, 0.2]
        
        result = weighted_average(values, weights)
        expected = (80.0 * 0.5 + 90.0 * 0.3 + 70.0 * 0.2) / 1.0
        assert abs(result - expected) < 0.001
    
    def test_classify_dqi_band(self):
        """Test DQI band classification"""
        assert classify_dqi_band(95.0) == "GREEN"
        assert classify_dqi_band(75.0) == "AMBER"
        assert classify_dqi_band(50.0) == "ORANGE"
        assert classify_dqi_band(30.0) == "RED"
    
    def test_timer_context_manager(self):
        """Test Timer context manager"""
        import time
        
        with Timer("Test operation") as timer:
            time.sleep(0.1)  # Sleep for 100ms
        
        assert timer.duration is not None
        assert timer.duration >= 0.1


class TestDataModels:
    """Test Pydantic data models"""
    
    def test_agent_signal_creation(self):
        """Test AgentSignal model creation"""
        signal = AgentSignal(
            agent_name="test_agent",
            entity_id="SITE_001",
            signal_type="TEST_SIGNAL",
            severity=Severity.MEDIUM,
            confidence=0.85,
            evidence=["Test evidence"]
        )
        
        assert signal.agent_name == "test_agent"
        assert signal.entity_id == "SITE_001"
        assert signal.severity == Severity.MEDIUM
        assert signal.confidence == 0.85
        assert len(signal.evidence) == 1
    
    def test_agent_signal_validation(self):
        """Test AgentSignal validation"""
        # Test confidence bounds
        with pytest.raises(ValueError):
            AgentSignal(
                agent_name="test",
                entity_id="test",
                signal_type="test",
                severity=Severity.LOW,
                confidence=1.5  # Invalid: > 1.0
            )
        
        with pytest.raises(ValueError):
            AgentSignal(
                agent_name="test",
                entity_id="test",
                signal_type="test",
                severity=Severity.LOW,
                confidence=-0.1  # Invalid: < 0.0
            )


class TestDatabaseIntegration:
    """Test database integration"""
    
    def test_database_health_check(self):
        """Test database connectivity"""
        from src.core import db_manager
        
        # Database should be healthy after initialization
        assert db_manager.health_check() is True
    
    def test_database_session(self):
        """Test database session creation"""
        from src.core import db_manager
        
        session = db_manager.get_session()
        assert session is not None
        session.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])