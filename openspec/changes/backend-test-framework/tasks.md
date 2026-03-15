## 1. Test Infrastructure Setup

- [x] 1.1 Add pytest dependencies to `backend/pyproject.toml` (pytest, pytest-asyncio, pytest-cov)
- [x] 1.2 Add pytest configuration section to `backend/pyproject.toml`
- [x] 1.3 Create `backend/tests/` directory structure
- [x] 1.4 Create `backend/tests/conftest.py` with shared fixtures
- [x] 1.5 Create `backend/tests/__init__.py`

## 2. Core Fixtures

- [x] 2.1 Implement `test_app` fixture (sync FastAPI TestClient)
- [x] 2.2 Implement `async_client` fixture (httpx AsyncClient)
- [x] 2.3 Implement `test_db` fixture (lightweight test session override)
- [ ] 2.4 Implement `auth_headers` fixture (authenticated user headers)

## 3. Unit Tests

- [x] 3.1 Create `backend/tests/common/utils/` directory
- [x] 3.2 Add unit tests for timestamp / formatting utilities
- [x] 3.3 Add unit tests for string, locale, logging, middleware, and validation utilities
- [ ] 3.4 Create mocks for LLM API calls

## 4. API Tests

- [x] 4.1 Create `backend/tests/apps/` directory structure
- [x] 4.2 Add health endpoint test (`test_main.py`)
- [x] 4.3 Add authentication tests (`test_auth.py`)
- [x] 4.4 Add protected endpoint authorization tests

## 5. CI Integration

- [x] 5.1 Update `.github/workflows/quality-check.yml` to run backend tests
- [x] 5.2 Add coverage report upload step
- [x] 5.3 Make backend tests blocking in CI
- [ ] 5.4 Verify green in GitHub Actions

## 6. Documentation

- [x] 6.1 Update `backend/README.md` with test running instructions
- [x] 6.2 Update `AGENTS.md` with pytest commands

## 7. Baseline Stabilization

- [x] 7.1 Isolate optional startup/runtime dependencies so backend smoke tests can run locally
- [x] 7.2 Expand unit and middleware coverage until the local backend baseline reaches the 30% target
- [ ] 7.3 Decide whether to archive this change or keep it open for CI hardening follow-up
