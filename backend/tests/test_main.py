"""Tests for main application endpoints."""

from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """Tests for application health checks."""

    def test_app_created(self, test_app: TestClient) -> None:
        """Test that FastAPI app is created successfully."""
        assert test_app is not None

    def test_openapi_endpoint(self, test_app: TestClient) -> None:
        """Test that OpenAPI schema is accessible."""
        response = test_app.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "paths" in data

    def test_health_endpoint(self, test_app: TestClient) -> None:
        response = test_app.get("/health")
        assert response.status_code == 200
        assert response.json() == {"code": 0, "data": {"status": "ok"}, "msg": None}
