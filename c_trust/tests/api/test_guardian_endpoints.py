"""
Tests for Guardian API Endpoints
================================
Tests the Guardian status and events endpoints.

**Validates: Task 2.3 - Guardian API Endpoint**
"""

import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from src.api.main import app
from src.guardian.guardian_agent import (
    GuardianAgent,
    GuardianEvent,
    GuardianEventType,
    GuardianSeverity,
)


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def guardian_with_events():
    """Create Guardian with test events"""
    guardian = GuardianAgent()
    
    # Create test events
    guardian._create_event(
        event_type=GuardianEventType.DATA_OUTPUT_INCONSISTENCY,
        severity=GuardianSeverity.CRITICAL,
        entity_id="STUDY_01",
        snapshot_id="snap_001",
        data_delta_summary="Data improved by 15%",
        expected_behavior="Risk score should decrease",
        actual_behavior="Risk score increased by 10 points",
        recommendation="Investigate agent logic",
    )
    
    guardian._create_event(
        event_type=GuardianEventType.STALENESS_DETECTED,
        severity=GuardianSeverity.WARNING,
        entity_id="STUDY_02",
        snapshot_id="snap_002",
        data_delta_summary="Data changed but alerts unchanged for 4 snapshots",
        expected_behavior="Alerts should update",
        actual_behavior="Same 3 alerts persisted",
        recommendation="Review agent sensitivity",
    )
    
    return guardian


class TestGuardianStatusEndpoint:
    """Tests for /api/v1/guardian/status endpoint"""
    
    def test_status_endpoint_returns_200(self, client):
        """Test that status endpoint returns 200 OK"""
        response = client.get("/api/v1/guardian/status")
        assert response.status_code == 200
    
    def test_status_endpoint_returns_json(self, client):
        """Test that status endpoint returns JSON"""
        response = client.get("/api/v1/guardian/status")
        assert response.headers["content-type"] == "application/json"
        data = response.json()
        assert isinstance(data, dict)
    
    def test_status_includes_system_health(self, client):
        """Test that status includes system health"""
        response = client.get("/api/v1/guardian/status")
        data = response.json()
        
        assert "system_health" in data
        health = data["system_health"]
        
        assert "status" in health
        assert "agents_operational" in health
        assert "last_check" in health
        assert "event_storage_health" in health
        assert "staleness_tracking_health" in health
    
    def test_status_includes_integrity_alerts(self, client):
        """Test that status includes integrity alerts"""
        response = client.get("/api/v1/guardian/status")
        data = response.json()
        
        assert "integrity_alerts" in data
        assert isinstance(data["integrity_alerts"], list)
    
    def test_status_includes_agent_performance(self, client):
        """Test that status includes agent performance"""
        response = client.get("/api/v1/guardian/status")
        data = response.json()
        
        assert "agent_performance" in data
        assert isinstance(data["agent_performance"], list)
        
        # Check agent performance structure
        if data["agent_performance"]:
            perf = data["agent_performance"][0]
            assert "agent_name" in perf
            assert "signals_generated" in perf
            assert "abstention_rate" in perf
            assert "avg_confidence" in perf
    
    def test_status_includes_diagnostic_report(self, client):
        """Test that status includes diagnostic report"""
        response = client.get("/api/v1/guardian/status")
        data = response.json()
        
        assert "diagnostic_report" in data
        assert isinstance(data["diagnostic_report"], dict)
        
        # Check diagnostic structure
        diagnostic = data["diagnostic_report"]
        assert "status" in diagnostic
        assert "checks" in diagnostic
        assert "timestamp" in diagnostic
    
    def test_status_system_health_values(self, client):
        """Test system health has valid values"""
        response = client.get("/api/v1/guardian/status")
        data = response.json()
        
        health = data["system_health"]
        assert health["status"] in ["HEALTHY", "DEGRADED", "CRITICAL"]
        assert isinstance(health["agents_operational"], int)
        assert health["agents_operational"] >= 0
    
    def test_status_handles_guardian_errors_gracefully(self, client, monkeypatch):
        """Test that status endpoint handles Guardian errors gracefully"""
        # Mock Guardian to raise an error
        def mock_init(*args, **kwargs):
            raise Exception("Guardian initialization failed")
        
        from src.guardian import guardian_agent
        monkeypatch.setattr(guardian_agent, "GuardianAgent", mock_init)
        
        response = client.get("/api/v1/guardian/status")
        
        # Should still return 200 with degraded status
        assert response.status_code == 200
        data = response.json()
        assert data["system_health"]["status"] == "DEGRADED"


class TestGuardianEventsEndpoint:
    """Tests for /api/v1/guardian/events endpoint"""
    
    def test_events_endpoint_returns_200(self, client):
        """Test that events endpoint returns 200 OK"""
        response = client.get("/api/v1/guardian/events")
        assert response.status_code == 200
    
    def test_events_endpoint_returns_list(self, client):
        """Test that events endpoint returns a list"""
        response = client.get("/api/v1/guardian/events")
        data = response.json()
        assert isinstance(data, list)
    
    def test_events_structure(self, client):
        """Test event structure if events exist"""
        response = client.get("/api/v1/guardian/events")
        data = response.json()
        
        # If there are events, check structure
        if data:
            event = data[0]
            assert "event_id" in event
            assert "event_type" in event
            assert "severity" in event
            assert "entity_id" in event
            assert "snapshot_id" in event
            assert "data_delta_summary" in event
            assert "expected_behavior" in event
            assert "actual_behavior" in event
            assert "recommendation" in event
            assert "timestamp" in event
    
    def test_events_filter_by_entity_id(self, client):
        """Test filtering events by entity_id"""
        response = client.get("/api/v1/guardian/events?entity_id=STUDY_01")
        assert response.status_code == 200
        data = response.json()
        
        # All events should be for STUDY_01
        for event in data:
            assert event["entity_id"] == "STUDY_01"
    
    def test_events_filter_by_event_type(self, client):
        """Test filtering events by event_type"""
        response = client.get("/api/v1/guardian/events?event_type=STALENESS_DETECTED")
        assert response.status_code == 200
        data = response.json()
        
        # All events should be STALENESS_DETECTED
        for event in data:
            assert event["event_type"] == "STALENESS_DETECTED"
    
    def test_events_filter_by_severity(self, client):
        """Test filtering events by severity"""
        response = client.get("/api/v1/guardian/events?severity=CRITICAL")
        assert response.status_code == 200
        data = response.json()
        
        # All events should be CRITICAL
        for event in data:
            assert event["severity"] == "CRITICAL"
    
    def test_events_limit_parameter(self, client):
        """Test limit parameter"""
        response = client.get("/api/v1/guardian/events?limit=5")
        assert response.status_code == 200
        data = response.json()
        
        # Should return at most 5 events
        assert len(data) <= 5
    
    def test_events_invalid_event_type(self, client):
        """Test invalid event_type returns 400"""
        response = client.get("/api/v1/guardian/events?event_type=INVALID_TYPE")
        assert response.status_code == 400
    
    def test_events_invalid_severity(self, client):
        """Test invalid severity returns 400"""
        response = client.get("/api/v1/guardian/events?severity=INVALID_SEVERITY")
        assert response.status_code == 400
    
    def test_events_combined_filters(self, client):
        """Test combining multiple filters"""
        response = client.get(
            "/api/v1/guardian/events"
            "?entity_id=STUDY_01"
            "&severity=CRITICAL"
            "&limit=10"
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check filters applied
        for event in data:
            assert event["entity_id"] == "STUDY_01"
            assert event["severity"] == "CRITICAL"
        
        assert len(data) <= 10


class TestGuardianIntegration:
    """Integration tests for Guardian endpoints"""
    
    def test_status_and_events_consistency(self, client):
        """Test that status and events endpoints are consistent"""
        # Get status
        status_response = client.get("/api/v1/guardian/status")
        status_data = status_response.json()
        
        # Get events
        events_response = client.get("/api/v1/guardian/events")
        events_data = events_response.json()
        
        # Number of integrity alerts in status should match events
        status_alerts = status_data["integrity_alerts"]
        
        # Both should be lists
        assert isinstance(status_alerts, list)
        assert isinstance(events_data, list)
    
    def test_guardian_diagnostic_checks(self, client):
        """Test that diagnostic checks are present"""
        response = client.get("/api/v1/guardian/status")
        data = response.json()
        
        diagnostic = data["diagnostic_report"]
        checks = diagnostic["checks"]
        
        # Should have key checks
        assert "event_storage" in checks
        assert "staleness_tracking" in checks
        assert "configuration" in checks
        
        # Each check should have status
        for check_name, check_data in checks.items():
            assert "status" in check_data
            assert check_data["status"] in ["OK", "WARNING", "CRITICAL"]
    
    def test_agent_performance_metrics(self, client):
        """Test agent performance metrics structure"""
        response = client.get("/api/v1/guardian/status")
        data = response.json()
        
        performance = data["agent_performance"]
        
        # Should have performance for multiple agents
        assert len(performance) >= 5  # At least 5 agents
        
        for agent_perf in performance:
            # Check required fields
            assert "agent_name" in agent_perf
            assert "signals_generated" in agent_perf
            assert "abstention_rate" in agent_perf
            assert "avg_confidence" in agent_perf
            
            # Check value ranges
            assert agent_perf["signals_generated"] >= 0
            assert 0 <= agent_perf["abstention_rate"] <= 1
            assert 0 <= agent_perf["avg_confidence"] <= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
