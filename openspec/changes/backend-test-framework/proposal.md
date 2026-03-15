## Why

The repository now has an initial backend test framework, but this change still needs to capture the final hardening step from local baseline confidence to CI enforcement. During baseline verification, backend tests exposed several issues that prevented a reliable green run:
- import-time failures from runtime type annotations
- eager loading of optional LLM / embedding dependencies during app import
- startup side effects (MCP setup, migrations, runtime initialization) interfering with smoke tests
- brittle auth and middleware paths that were not yet covered by tests

This change now records both the completed stabilization work and the remaining remote verification step so the team can distinguish what is already shipped from what still remains before archive.

## What Changes

- Establish pytest-based backend test infrastructure with shared fixtures and coverage reporting
- Add smoke tests for app creation, OpenAPI, login failure behavior, and protected endpoint authorization
- Add broad unit coverage for common utilities, middleware, schemas, logging helpers, and response handling
- Stabilize the backend test baseline by isolating optional runtime integrations and startup side effects from test runs
- Verify the backend baseline locally with a passing coverage gate

## Capabilities

### New Capabilities

- `test-infrastructure`: pytest configuration, fixtures, test database setup, and CI integration
- `unit-testing`: Unit tests for utility functions and core business logic
- `api-testing`: Integration tests for FastAPI endpoints using httpx AsyncClient

### Modified Capabilities

None - this is new infrastructure with no existing specs to modify.

## Impact

- **Dependencies**: pytest / pytest-asyncio / pytest-cov are now in use for backend validation
- **Files**: `backend/tests/` now contains shared fixtures plus smoke and unit coverage across `apps/` and `common/`
- **CI**: `.github/workflows/quality-check.yml` now treats backend test failures as blocking, uploads `coverage.xml`, and has been verified green in GitHub Actions (`Quality Check (G1-G2)` run `23101653996`)
- **Coverage Target**: Initial 30% target is now met locally (`136 passed`, `30.03%` coverage)
