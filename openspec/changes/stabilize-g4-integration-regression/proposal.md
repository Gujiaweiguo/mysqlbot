## Why

The scheduled `Integration Test (G0-G5)` workflow currently fails in G4 because the happy-path regression depends on a real LLM execution path, but CI does not seed a usable default model or provider configuration. That makes a mandatory regression gate non-deterministic and breaks the repository's documented full-regression contract.

## What Changes

- Introduce a deterministic CI-only LLM regression path for G4 so the happy-path regression can exercise the NL-to-SQL pipeline without depending on external provider credentials or model variability.
- Seed the minimum AI model/runtime configuration needed for G4 inside the integration workflow so the app has an explicit default model during the CI run.
- Record in regression reporting that G4 used the deterministic CI provider path, while preserving G4 as a mandatory gate with the same evidence-driven pass/fail expectations.
- Keep G5 failure-path regression separate so it can continue validating rate-limit and transient failure handling independently.

## Capabilities

### New Capabilities

- `ci-deterministic-llm-regression`: Provide a deterministic CI-only model-provider path for G4 happy-path regression so functional NL-to-SQL coverage does not depend on external LLM availability.

### Modified Capabilities

- `regression-test-gates`: Clarify that the mandatory G4 gate uses the deterministic CI provider path when running in automated regression.
- `regression-reporting`: Require regression evidence to identify the provider mode used for G4 and link the resulting artifacts to that execution context.

## Impact

- Affected workflow: `.github/workflows/integration-test.yml`
- Affected regression tooling under `backend/scripts/regression/`
- Affected AI model/runtime setup used only for CI regression execution
- Affected canonical specs: `regression-test-gates`, `regression-reporting`, plus a new CI regression capability spec
