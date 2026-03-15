## Context

The backend is a FastAPI + SQLModel application with the following structure:
- `apps/` - Domain modules (chat, datasource, dashboard, system, etc.)
- `common/` - Shared utilities, core, and audit
- `scripts/` - Build and lint scripts

Current state:
- `backend/tests/` exists with shared fixtures plus smoke and unit tests
- `pytest`, async support, and coverage reporting are configured and used in local validation
- CI workflow (`quality-check.yml`) runs backend tests and uploads a coverage artifact
- Backend baseline now passes locally with `136` tests and `30.03%` coverage
- CI configuration now treats backend test failures as blocking
- Remaining gap is remote verification in GitHub Actions before this change can be considered fully closed

## Goals / Non-Goals

**Goals:**
- Establish pytest as the test framework with async support
- Create test directory structure mirroring app layout
- Add fixtures for database, authentication, and common test data
- Integrate with existing CI pipeline
- Achieve and preserve initial 30% coverage on critical paths

**Non-Goals:**
- 100% test coverage (incremental approach)
- E2E tests requiring full stack deployment
- Performance/load testing
- Frontend testing (separate effort)

## Decisions

### 1. Test Framework: pytest with pytest-asyncio

**Rationale:** 
- pytest is the Python standard with excellent async support
- pytest-asyncio handles FastAPI's async endpoints naturally
- Rich ecosystem: pytest-cov, pytest-fixtures, parametrize

**Alternatives considered:**
- unittest: Built-in but verbose, poor async support
- nose2: Less community adoption, fewer plugins

### 2. Test Directory Structure: Mirror `apps/` Layout

```
backend/
├── apps/
│   ├── chat/
│   ├── datasource/
│   └── ...
├── tests/
│   ├── conftest.py          # Shared fixtures
│   ├── test_main.py         # API entry point tests
│   ├── apps/
│   │   ├── chat/
│   │   │   └── test_chat_api.py
│   │   └── datasource/
│   │       └── test_datasource_api.py
│   └── common/
│       └── utils/
│           └── test_utils.py
```

**Rationale:** Mirrors source structure for easy navigation and test discovery.

### 3. Database Testing: Lightweight Session Override with Test Isolation

**Rationale:**
- Keep smoke tests fast and isolated without requiring PostgreSQL, MCP, xpack, or model runtimes
- Use FastAPI's dependency overrides and narrow test doubles where full runtime initialization is unnecessary
- Avoid forcing the entire SQLModel metadata onto SQLite when some production models rely on PostgreSQL-only types

**Implementation:**
```python
# tests/conftest.py
@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    yield engine
```

Additional test-environment guards disable or stub heavyweight startup/runtime concerns such as:
- MCP setup during app import
- startup tasks like migrations and runtime warm-up work
- optional xpack integrations
- eager LLM / embedding dependency loading paths

### 4. Coverage Target: 30% Initial

**Rationale:**
- Start with critical paths: auth, core utilities, health endpoints
- Increase incrementally as tests are added for new features
- Avoid blocking PRs on coverage initially

### 5. CI Integration: Extend Existing Workflow, Then Tighten It

**Rationale:**
- Extend `.github/workflows/quality-check.yml` with test step
- Run after lint passes
- Upload coverage report as artifact
- Once the baseline is reliably green, remove `continue-on-error` so backend tests become a real gate

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Tests may be brittle with external dependencies | Use mocks for LLM APIs, external services |
| SQLite != PostgreSQL behavior | Focus on logic tests; defer complex DB tests |
| Coverage may give false confidence | Focus on critical paths, not coverage numbers |
| Async test complexity | Use pytest-asyncio auto mode, clear patterns |
