"""
Frontend Integration Test Utilities
====================================
Helper utilities for testing frontend integration with the backend API.
"""

import httpx
import json
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class APIResponse:
    """Structured API response for testing."""
    status_code: int
    data: Any
    headers: Dict[str, str]
    success: bool
    error: Optional[str] = None


class TestAPIClient:
    """
    API client for integration testing.
    Provides convenient methods for testing all C-TRUST endpoints.
    """
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.Client(base_url=base_url, timeout=30.0)
    
    def close(self):
        """Close the HTTP client."""
        self.client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()
    
    def _make_request(
        self,
        method: str,
        path: str,
        **kwargs
    ) -> APIResponse:
        """Make an HTTP request and return structured response."""
        try:
            response = self.client.request(method, path, **kwargs)
            try:
                data = response.json()
            except json.JSONDecodeError:
                data = response.text
            
            return APIResponse(
                status_code=response.status_code,
                data=data,
                headers=dict(response.headers),
                success=200 <= response.status_code < 300,
                error=None if response.is_success else str(data)
            )
        except Exception as e:
            return APIResponse(
                status_code=0,
                data=None,
                headers={},
                success=False,
                error=str(e)
            )
    
    # Studies endpoints
    def get_studies(self) -> APIResponse:
        """Get all studies."""
        return self._make_request("GET", "/api/v1/studies")
    
    def get_study(self, study_id: str) -> APIResponse:
        """Get a specific study by ID."""
        return self._make_request("GET", f"/api/v1/studies/{study_id}")
    
    def get_study_dqi(self, study_id: str) -> APIResponse:
        """Get DQI for a study."""
        return self._make_request("GET", f"/api/v1/studies/{study_id}/dqi")
    
    # Analysis endpoints
    def get_analysis(self, study_id: str) -> APIResponse:
        """Get multi-agent analysis for a study."""
        return self._make_request("GET", f"/api/v1/analysis/{study_id}")
    
    def refresh_all(self) -> APIResponse:
        """Trigger refresh of all analysis data."""
        return self._make_request("POST", "/api/v1/analysis/refresh")
    
    def get_system_status(self) -> APIResponse:
        """Get system status."""
        return self._make_request("GET", "/api/v1/analysis/status/system")
    
    # Agent endpoints
    def get_agents(self) -> APIResponse:
        """Get all agents."""
        return self._make_request("GET", "/api/v1/agents")
    
    def get_agent_signals(self, agent_id: str) -> APIResponse:
        """Get signals for a specific agent."""
        return self._make_request("GET", f"/api/v1/agents/{agent_id}/signals")
    
    # Guardian endpoints
    def get_guardian_status(self) -> APIResponse:
        """Get Guardian agent status."""
        return self._make_request("GET", "/api/v1/guardian/status")
    
    def get_guardian_events(self) -> APIResponse:
        """Get Guardian events."""
        return self._make_request("GET", "/api/v1/guardian/events")
    
    # Metrics endpoints
    def get_metrics(self) -> APIResponse:
        """Get system metrics."""
        return self._make_request("GET", "/api/v1/metrics")
    
    # Notifications endpoints
    def get_notifications(self) -> APIResponse:
        """Get all notifications."""
        return self._make_request("GET", "/api/v1/notifications")
    
    def acknowledge_notification(self, notification_id: str) -> APIResponse:
        """Acknowledge a notification."""
        return self._make_request("POST", f"/api/v1/notifications/{notification_id}/acknowledge")


def run_integration_tests():
    """
    Run a quick integration test suite.
    Returns True if all tests pass.
    """
    print("🧪 Running C-TRUST Integration Tests...")
    print("=" * 50)
    
    passed = 0
    failed = 0
    
    with TestAPIClient() as client:
        # Test 1: Health check
        print("\n1. Testing health endpoint...")
        resp = client._make_request("GET", "/api/v1/health")
        if resp.success:
            print("   ✅ Health check passed")
            passed += 1
        else:
            print(f"   ❌ Health check failed: {resp.error}")
            failed += 1
        
        # Test 2: Get studies
        print("\n2. Testing studies endpoint...")
        resp = client.get_studies()
        if resp.success and isinstance(resp.data, list):
            print(f"   ✅ Got {len(resp.data)} studies")
            passed += 1
        else:
            print(f"   ❌ Get studies failed: {resp.error}")
            failed += 1
        
        # Test 3: Get agents
        print("\n3. Testing agents endpoint...")
        resp = client.get_agents()
        if resp.success and isinstance(resp.data, list):
            print(f"   ✅ Got {len(resp.data)} agents")
            passed += 1
        else:
            print(f"   ❌ Get agents failed: {resp.error}")
            failed += 1
        
        # Test 4: Get metrics
        print("\n4. Testing metrics endpoint...")
        resp = client.get_metrics()
        if resp.success:
            print("   ✅ Metrics endpoint working")
            passed += 1
        else:
            print(f"   ❌ Get metrics failed: {resp.error}")
            failed += 1
        
        # Test 5: Guardian status
        print("\n5. Testing guardian status...")
        resp = client.get_guardian_status()
        if resp.success:
            print("   ✅ Guardian status working")
            passed += 1
        else:
            print(f"   ❌ Guardian status failed: {resp.error}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Results: {passed} passed, {failed} failed")
    
    return failed == 0


if __name__ == "__main__":
    success = run_integration_tests()
    exit(0 if success else 1)
