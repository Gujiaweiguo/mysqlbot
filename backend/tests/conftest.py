import os
import sys
import types
from pathlib import Path

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


def _install_sqlbot_xpack_stub() -> None:
    if "sqlbot_xpack" in sys.modules:
        return

    package = types.ModuleType("sqlbot_xpack")
    package.__path__ = []  # type: ignore[attr-defined]

    core_module = types.ModuleType("sqlbot_xpack.core")

    async def clean_xpack_cache() -> None:
        return None

    async def monitor_app(_app: object) -> None:
        return None

    async def sqlbot_decrypt(text: str) -> str:
        return text

    async def sqlbot_encrypt(text: str) -> str:
        return text

    setattr(core_module, "clean_xpack_cache", clean_xpack_cache)
    setattr(core_module, "monitor_app", monitor_app)
    setattr(core_module, "sqlbot_decrypt", sqlbot_decrypt)
    setattr(core_module, "sqlbot_encrypt", sqlbot_encrypt)

    aes_utils_module = types.ModuleType("sqlbot_xpack.aes_utils")

    class SecureEncryption:
        @staticmethod
        def encrypt_to_single_string(text: str, _key: str) -> str:
            return text

        @staticmethod
        def decrypt_from_single_string(text: str, _key: str) -> str:
            return text

        @staticmethod
        def simple_aes_encrypt(text: str, _key: str, _ivtext: str) -> str:
            return text

        @staticmethod
        def simple_aes_decrypt(text: str, _key: str, _ivtext: str) -> str:
            return text

    setattr(aes_utils_module, "SecureEncryption", SecureEncryption)

    authentication_module = types.ModuleType("sqlbot_xpack.authentication")
    authentication_manage_module = types.ModuleType(
        "sqlbot_xpack.authentication.manage"
    )

    async def logout(_session: object, _request: object, _dto: object) -> None:
        return None

    setattr(authentication_manage_module, "logout", logout)

    def init_fastapi_app(_app: object) -> None:
        return None

    setattr(package, "core", core_module)
    setattr(package, "init_fastapi_app", init_fastapi_app)
    setattr(package, "authentication", authentication_module)

    sys.modules["sqlbot_xpack"] = package
    sys.modules["sqlbot_xpack.core"] = core_module
    sys.modules["sqlbot_xpack.aes_utils"] = aes_utils_module
    sys.modules["sqlbot_xpack.authentication"] = authentication_module
    sys.modules["sqlbot_xpack.authentication.manage"] = authentication_manage_module


_install_sqlbot_xpack_stub()

from collections.abc import AsyncGenerator, Generator
from typing import Any

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlmodel import Session, SQLModel, create_engine

from apps.system.schemas.system_schema import UserInfoDTO
from common.core.config import settings


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
    import apps.system.api.login as login_api
    from main import app
    from common.core.deps import get_session

    def override_get_session() -> Generator[Session, None, None]:
        yield test_db

    def fake_authenticate(*, session: Session, account: str, password: str) -> None:
        _ = session
        _ = account
        _ = password
        return None

    app.dependency_overrides[get_session] = override_get_session
    original_authenticate = login_api.authenticate
    login_api.authenticate = fake_authenticate
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client
    login_api.authenticate = original_authenticate
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def async_client(test_db: Session) -> AsyncGenerator[AsyncClient, None]:
    import apps.system.api.login as login_api
    from main import app
    from common.core.deps import get_session

    def override_get_session() -> Generator[Session, None, None]:
        yield test_db

    def fake_authenticate(*, session: Session, account: str, password: str) -> None:
        _ = session
        _ = account
        _ = password
        return None

    app.dependency_overrides[get_session] = override_get_session
    original_authenticate = login_api.authenticate
    login_api.authenticate = fake_authenticate
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client
    login_api.authenticate = original_authenticate
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

    async def fake_validate_token(
        self: TokenMiddleware, token: str | None, trans: object
    ) -> tuple[bool, UserInfoDTO]:
        _ = self
        _ = trans
        assert token == "Bearer test-token"
        return True, auth_user

    monkeypatch.setattr(TokenMiddleware, "validateToken", fake_validate_token)

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
