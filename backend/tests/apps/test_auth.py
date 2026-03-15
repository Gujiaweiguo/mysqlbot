"""Tests for authentication endpoints."""

import pytest
from fastapi.testclient import TestClient


class TestAuthEndpoints:
    """Tests for authentication API endpoints."""

    def test_login_without_credentials(self, test_app: TestClient) -> None:
        """Test login endpoint rejects missing credentials."""
        response = test_app.post(
            "/api/v1/login/access-token",
            data={"username": "", "password": ""},
        )
        assert response.status_code in [400, 422]

    def test_login_with_invalid_credentials(self, test_app: TestClient) -> None:
        """Test login endpoint rejects invalid credentials."""
        response = test_app.post(
            "/api/v1/login/access-token",
            data={"username": "invalid_user", "password": "wrong_password"},
        )
        assert response.status_code in [400, 401]

    def test_protected_endpoint_without_token(self, test_app: TestClient) -> None:
        """Test protected endpoint rejects unauthenticated requests."""
        response = test_app.get("/api/v1/system/user")
        assert response.status_code == 401

    def test_protected_endpoint_with_invalid_token(self, test_app: TestClient) -> None:
        """Test protected endpoint rejects invalid tokens."""
        response = test_app.get(
            "/api/v1/system/user",
            headers={"Authorization": "Bearer invalid_token"},
        )
        assert response.status_code == 401

    def test_protected_endpoint_with_auth_headers(
        self, test_app: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = test_app.get("/api/v1/user/info", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["data"]["account"] == "test-admin"
