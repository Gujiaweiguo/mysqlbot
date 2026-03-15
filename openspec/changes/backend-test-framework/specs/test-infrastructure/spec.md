## ADDED Requirements

### Requirement: pytest configuration in pyproject.toml

The system SHALL have pytest configuration in `backend/pyproject.toml` with:
- testpaths pointing to `tests/` directory
- asyncio_mode set to `auto`
- Coverage reporting enabled with minimum 30% threshold

#### Scenario: pytest runs successfully
- **WHEN** developer runs `uv run pytest`
- **THEN** all tests in `tests/` directory are discovered and executed

#### Scenario: coverage report is generated
- **WHEN** developer runs `uv run pytest --cov`
- **THEN** coverage report is generated showing percentage coverage by module

### Requirement: Shared test fixtures in conftest.py

The system SHALL provide shared fixtures in `tests/conftest.py`:
- `test_app`: FastAPI TestClient for synchronous tests
- `async_client`: httpx AsyncClient for async API tests
- `test_db`: In-memory SQLite database for isolated tests
- `auth_headers`: Pre-authenticated headers for protected endpoints

#### Scenario: fixtures are available to all tests
- **WHEN** a test function requests a fixture by name
- **THEN** the fixture is automatically provided by pytest

#### Scenario: database is isolated between tests
- **WHEN** a test modifies the database
- **THEN** subsequent tests start with a fresh database state

### Requirement: CI integration for backend tests

The CI pipeline SHALL run backend tests on every pull request:
- Tests run after linting passes
- Coverage report uploaded as artifact
- Build fails if any test fails

#### Scenario: CI runs tests on pull request
- **WHEN** a pull request is opened or updated
- **THEN** backend tests are executed as part of quality-check workflow

#### Scenario: CI fails on test failure
- **WHEN** any test fails
- **THEN** the CI build is marked as failed
