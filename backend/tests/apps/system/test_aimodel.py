import json
from collections.abc import Callable

from fastapi.testclient import TestClient


MockLLMStreamInstaller = Callable[..., None]


class TestAiModelStatus:
    def test_status_stream_uses_mocked_llm_chunks(
        self,
        test_app: TestClient,
        auth_headers: dict[str, str],
        mock_llm_stream: MockLLMStreamInstaller,
    ) -> None:
        mock_llm_stream(chunks=["hello", {"content": "world"}])

        response = test_app.post(
            "/api/v1/system/aimodel/status",
            headers=auth_headers,
            json={
                "name": "Test Model",
                "model_type": 1,
                "base_model": "gpt-test",
                "supplier": 1,
                "protocol": 1,
                "default_model": False,
                "api_domain": "https://example.com",
                "api_key": "test-key",
                "config_list": [],
            },
        )

        assert response.status_code == 200
        lines = [
            json.loads(line) for line in response.text.splitlines() if line.strip()
        ]
        assert lines == [{"content": "hello"}, {"content": "world"}]

    def test_status_stream_returns_error_payload_on_mock_failure(
        self,
        test_app: TestClient,
        auth_headers: dict[str, str],
        mock_llm_stream: MockLLMStreamInstaller,
    ) -> None:
        mock_llm_stream(error=RuntimeError("boom"))

        response = test_app.post(
            "/api/v1/system/aimodel/status",
            headers=auth_headers,
            json={
                "name": "Test Model",
                "model_type": 1,
                "base_model": "gpt-test",
                "supplier": 1,
                "protocol": 1,
                "default_model": False,
                "api_domain": "https://example.com",
                "api_key": "test-key",
                "config_list": [],
            },
        )

        assert response.status_code == 200
        lines = [
            json.loads(line) for line in response.text.splitlines() if line.strip()
        ]
        assert len(lines) == 1
        assert "error" in lines[0]
