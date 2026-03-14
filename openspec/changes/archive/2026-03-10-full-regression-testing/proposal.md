## Why

The project has many cross-cutting changes (frontend UX, backend datasource flow, deployment/runtime behavior, and LLM integration), but there is no single, repeatable full-regression baseline. We need a formal test change now to prevent release risk, quickly catch regressions, and make troubleshooting reproducible.

## What Changes

- Define an end-to-end regression testing baseline for mysqlbot covering environment health, backend checks, frontend build and smoke flows, and intelligent-query core paths.
- Standardize demo data validation with `demo_sales` as the shared functional test fixture for NL2SQL/chat verification.
- Add explicit failure-path validation for upstream LLM limits/errors (including HTTP 429/rate-limit scenarios) and expected user-facing behavior.
- Define a consistent regression report format (scope, execution, evidence, failures, rerun status, and release decision).

## Capabilities

### New Capabilities
- `regression-test-gates`: Defines mandatory full-regression gates and pass/fail criteria across container health, backend/frontend quality checks, key product flows, and failure scenarios.
- `demo-fixture-validation`: Defines fixture data requirements and verification steps using `demo_sales` so intelligent-query tests run on deterministic data.
- `llm-rate-limit-resilience-check`: Defines validation behavior and acceptance criteria when model providers return rate-limit and transient failures.
- `regression-reporting`: Defines the required structure and evidence standard for regression test reports.

### Modified Capabilities
- None.

## Impact

- Affected systems: Docker Compose runtime checks, frontend build pipeline, backend quality and API verification, intelligent-query execution path, and release verification workflow.
- Affected code areas for test execution context: `frontend/`, `backend/`, datasource and chat paths, and deployment scripts.
- Team/process impact: introduces a formal, reusable regression contract for release readiness.
