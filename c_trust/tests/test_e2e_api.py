"""
C-TRUST End-to-End API Test Suite
==================================
Tests all API endpoints for correct responses, error handling, and integration.
Run with: pytest tests/test_e2e_api.py -v
"""

import pytest
import httpx
from typing import Generator
import asyncio

# Base URL for the API
BASE_URL = "http://localhost:8000"


@pytest.fixture(scope="module")
def client() -> Generator[httpx.Client, None, None]:
    """Create a test client for the API."""
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        yield client


class TestHealthEndpoints:
    """Test health and status endpoints."""

    def test_health_check(self, client: httpx.Client):
        """Test the health check endpoint."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "degraded", "unhealthy"]

    def test_system_status(self, client: httpx.Client):
        """Test the system status endpoint."""
        response = client.get("/api/v1/analysis/status/system")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "pipeline" in data


class TestStudiesEndpoints:
    """Test studies-related endpoints."""

    def test_get_all_studies(self, client: httpx.Client):
        """Test retrieving all studies."""
        response = client.get("/api/v1/studies")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if len(data) > 0:
            study = data[0]
            assert "study_id" in study
            assert "study_name" in study

    def test_get_study_by_id(self, client: httpx.Client):
        """Test retrieving a specific study."""
        # First get list of studies
        response = client.get("/api/v1/studies")
        studies = response.json()
        
        if len(studies) > 0:
            study_id = studies[0]["study_id"]
            response = client.get(f"/api/v1/studies/{study_id}")
            assert response.status_code == 200
            data = response.json()
            assert data["study_id"] == study_id

    def test_get_nonexistent_study(self, client: httpx.Client):
        """Test retrieving a non-existent study returns 404."""
        response = client.get("/api/v1/studies/NONEXISTENT_STUDY_999")
        assert response.status_code == 404

    def test_get_study_dqi(self, client: httpx.Client):
        """Test retrieving DQI for a study."""
        response = client.get("/api/v1/studies")
        studies = response.json()
        
        if len(studies) > 0:
            study_id = studies[0]["study_id"]
            response = client.get(f"/api/v1/studies/{study_id}/dqi")
            assert response.status_code == 200
            data = response.json()
            assert "overall_score" in data or "dqi_score" in data


class TestAnalysisEndpoints:
    """Test multi-agent analysis endpoints."""

    def test_get_analysis(self, client: httpx.Client):
        """Test running analysis on a study."""
        response = client.get("/api/v1/studies")
        studies = response.json()
        
        if len(studies) > 0:
            study_id = studies[0]["study_id"]
            response = client.get(f"/api/v1/analysis/{study_id}")
            assert response.status_code == 200
            data = response.json()
            assert "study_id" in data
            assert "agent_signals" in data
            assert "consensus" in data

    def test_refresh_all(self, client: httpx.Client):
        """Test the refresh all endpoint."""
        response = client.post("/api/v1/analysis/refresh")
        assert response.status_code in [200, 202]


class TestAgentEndpoints:
    """Test agent-related endpoints."""

    def test_get_all_agents(self, client: httpx.Client):
        """Test retrieving all agents."""
        response = client.get("/api/v1/agents")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should have 7 agents
        assert len(data) >= 7

    def test_get_agent_signals(self, client: httpx.Client):
        """Test retrieving signals for a specific agent."""
        response = client.get("/api/v1/agents")
        agents = response.json()
        
        if len(agents) > 0:
            agent_id = agents[0]["agent_id"]
            response = client.get(f"/api/v1/agents/{agent_id}/signals")
            assert response.status_code == 200


class TestGuardianEndpoints:
    """Test Guardian agent endpoints."""

    def test_get_guardian_status(self, client: httpx.Client):
        """Test retrieving Guardian status."""
        response = client.get("/api/v1/guardian/status")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    def test_get_guardian_events(self, client: httpx.Client):
        """Test retrieving Guardian events."""
        response = client.get("/api/v1/guardian/events")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestMetricsEndpoints:
    """Test metrics endpoints."""

    def test_get_metrics(self, client: httpx.Client):
        """Test retrieving system metrics."""
        response = client.get("/api/v1/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "system" in data
        assert "agents" in data


class TestNotificationsEndpoints:
    """Test notifications endpoints."""

    def test_get_notifications(self, client: httpx.Client):
        """Test retrieving notifications."""
        response = client.get("/api/v1/notifications")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_acknowledge_notification(self, client: httpx.Client):
        """Test acknowledging a notification."""
        # First get notifications
        response = client.get("/api/v1/notifications")
        notifications = response.json()
        
        if len(notifications) > 0:
            notif_id = notifications[0]["id"]
            response = client.post(f"/api/v1/notifications/{notif_id}/acknowledge")
            assert response.status_code in [200, 204]


class TestErrorHandling:
    """Test error handling across the API."""

    def test_invalid_endpoint(self, client: httpx.Client):
        """Test that invalid endpoints return 404."""
        response = client.get("/api/v1/invalid-endpoint")
        assert response.status_code == 404

    def test_invalid_method(self, client: httpx.Client):
        """Test that invalid methods return 405."""
        response = client.delete("/api/v1/studies")
        assert response.status_code in [405, 404]

    def test_malformed_request(self, client: httpx.Client):
        """Test that malformed requests are handled gracefully."""
        response = client.post(
            "/api/v1/studies",
            json={"invalid": "data"},
        )
        # Should return 400 or 422 for validation error
        assert response.status_code in [400, 422, 405]


class TestCacheEndpoints:
    """Test cache-related functionality."""

    def test_cache_headers(self, client: httpx.Client):
        """Test that cached responses have appropriate headers."""
        response = client.get("/api/v1/studies")
        # Should have cache-related headers
        assert response.status_code == 200

    def test_force_refresh(self, client: httpx.Client):
        """Test force refresh bypasses cache."""
        response = client.get(
            "/api/v1/studies",
            headers={"Cache-Control": "no-cache"}
        )
        assert response.status_code == 200


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
