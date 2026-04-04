import os
import sys
from collections.abc import AsyncGenerator, Generator
from pathlib import Path
from typing import Any, cast

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlmodel import Session, create_engine

from apps.system.schemas.system_schema import UserInfoDTO
from common.core.config import settings

# Add backend to path for imports
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

test_runtime_dir = backend_dir / ".pytest-runtime"
test_runtime_dir.mkdir(exist_ok=True)

_ = os.environ.setdefault("EMBEDDING_ENABLED", "false")
_ = os.environ.setdefault("TABLE_EMBEDDING_ENABLED", "false")
_ = os.environ.setdefault("SKIP_MCP_SETUP", "true")
_ = os.environ.setdefault("SKIP_STARTUP_TASKS", "true")
_ = os.environ.setdefault("BASE_DIR", str(test_runtime_dir))
_ = os.environ.setdefault("MCP_IMAGE_PATH", str(test_runtime_dir / "images"))
_ = os.environ.setdefault("UPLOAD_DIR", str(test_runtime_dir / "data" / "file"))
_ = os.environ.setdefault("EXCEL_PATH", str(test_runtime_dir / "data" / "excel"))
_ = os.environ.setdefault("LOCAL_MODEL_PATH", str(test_runtime_dir / "models"))
_ = os.environ.setdefault("LOG_DIR", str(test_runtime_dir / "logs"))


@pytest.fixture(scope="session")
def test_db_engine() -> Generator[Any, None, None]:
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    yield engine


@pytest.fixture
def test_db(test_db_engine: Any) -> Generator[Session, None, None]:
    with Session(test_db_engine) as session:
        yield session


@pytest.fixture
def test_app(test_db: Session) -> Generator[TestClient, None, None]:
    # Import here to avoid circular import issues
    from apps.system.api import login as login_api
    from common.core import deps as deps_module
    from main import app

    def override_get_session() -> Generator[Session, None, None]:
        yield test_db

    def fake_authenticate(*, session: Session, account: str, password: str) -> None:
        _ = session
        _ = account
        _ = password
        return None

    get_session = cast(Any, deps_module).get_session
    app.dependency_overrides[get_session] = override_get_session
    original_authenticate = cast(Any, login_api).authenticate
    cast(Any, login_api).authenticate = fake_authenticate
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client
    cast(Any, login_api).authenticate = original_authenticate
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def async_client(test_db: Session) -> AsyncGenerator[AsyncClient, None]:
    from apps.system.api import login as login_api
    from common.core import deps as deps_module
    from main import app

    def override_get_session() -> Generator[Session, None, None]:
        yield test_db

    def fake_authenticate(*, session: Session, account: str, password: str) -> None:
        _ = session
        _ = account
        _ = password
        return None

    get_session = cast(Any, deps_module).get_session
    app.dependency_overrides[get_session] = override_get_session
    original_authenticate = cast(Any, login_api).authenticate
    cast(Any, login_api).authenticate = fake_authenticate
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client
    cast(Any, login_api).authenticate = original_authenticate
    app.dependency_overrides.clear()


@pytest.fixture
def auth_user() -> UserInfoDTO:
    return UserInfoDTO(
        id=1,
        account="test-admin",
        oid=1,
        name="Test Admin",
        email="test-admin@example.com",
        status=1,
        origin=0,
        oid_list=[1],
        system_variables=[],
        language="en",
        weight=1,
        isAdmin=True,
    )


@pytest.fixture
def auth_headers(
    monkeypatch: pytest.MonkeyPatch, auth_user: UserInfoDTO
) -> dict[str, str]:
    from apps.system.middleware.auth import TokenMiddleware
    from apps.system.schemas import permission as permission_module

    async def fake_validate_token(
        self: TokenMiddleware, token: str | None, trans: object
    ) -> tuple[bool, UserInfoDTO]:
        _ = self
        _ = trans
        assert token == "Bearer test-token"
        return True, auth_user

    async def fake_get_ws_resource(oid: int, type: str) -> list[int]:
        _ = oid
        _ = type
        return list(range(1, 1000))

    monkeypatch.setattr(TokenMiddleware, "validateToken", fake_validate_token)
    monkeypatch.setattr(permission_module, "get_ws_resource", fake_get_ws_resource)

    return {
        settings.TOKEN_KEY: "Bearer test-token",
    }


@pytest.fixture
def mock_llm_stream(monkeypatch: pytest.MonkeyPatch) -> Any:
    class FakeLLM:
        def __init__(
            self, chunks: list[str | dict[str, object]], error: Exception | None
        ) -> None:
            self._chunks = chunks
            self._error = error

        async def astream(
            self, prompt: str
        ) -> AsyncGenerator[str | dict[str, object], None]:
            _ = prompt
            if self._error is not None:
                raise self._error
            for chunk in self._chunks:
                yield chunk

    class FakeLLMInstance:
        def __init__(
            self, chunks: list[str | dict[str, object]], error: Exception | None
        ) -> None:
            self.llm = FakeLLM(chunks, error)

    def install(
        *,
        chunks: list[str | dict[str, object]] | None = None,
        error: Exception | None = None,
    ) -> None:
        from apps.ai_model import model_factory

        def fake_create_llm(config: object) -> FakeLLMInstance:
            _ = config
            return FakeLLMInstance(chunks or ["ok"], error)

        monkeypatch.setattr(
            model_factory.LLMFactory, "create_llm", staticmethod(fake_create_llm)
        )

    return install
