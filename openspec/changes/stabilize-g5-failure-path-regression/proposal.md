## Why

The `Integration Test (G0-G5)` workflow now reaches and passes G4 on GitHub Actions, but G5 failure-path regression still fails. That leaves the full regression pipeline red and means the repository is not yet meeting its documented resilience-validation contract for rate-limit and transient-provider behavior.

## What Changes

- Stabilize the G5 failure-path integration regression so the GitHub Actions workflow can deterministically validate both rate-limit and transient-failure behavior.
- Fix any workflow, networking, or mock-provider assumptions that make G5 fail on hosted GitHub runners even though its scenario contract is valid.
- Preserve the G5 scope as a failure-path gate distinct from the already-completed G4 deterministic happy-path gate.
- Update evidence/reporting as needed so G5 results remain auditable and clearly tied to the mock-provider execution mode.

## Capabilities

### New Capabilities

- `ci-deterministic-failure-path-regression`: Provide a deterministic CI execution contract for G5 failure-path validation using controllable mock-provider behavior.

### Modified Capabilities

- `llm-rate-limit-resilience-check`: Clarify the deterministic CI expectations for rate-limit and transient-failure validation.
- `regression-test-gates`: Clarify the independent G5 gate contract once G4 has already passed.
- `regression-reporting`: Record the execution mode and evidence expectations for G5 failure-path results.

## Impact

- Affected workflow: `.github/workflows/integration-test.yml`
- Affected regression tooling under `backend/scripts/regression/g5_failure_path_demo_sales.py`
- Affected evidence/reporting docs and regression specs
- No product-facing runtime feature changes are intended; this is CI regression stabilization work
