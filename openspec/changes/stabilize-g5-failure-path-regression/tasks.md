## 1. Define deterministic G5 CI contract

- [x] 1.1 Add the new `ci-deterministic-failure-path-regression` capability spec and update regression gate/reporting/resilience specs for deterministic G5 behavior
- [x] 1.2 Identify and document the exact CI-specific failure mode in the current G5 workflow/script path

## 2. Stabilize G5 workflow and script behavior

- [x] 2.1 Update `.github/workflows/integration-test.yml` so G5 has an explicit CI-safe mock-provider connectivity/configuration path
- [x] 2.2 Update `backend/scripts/regression/g5_failure_path_demo_sales.py` or related helpers as needed so HTTP 429 and transient scenarios are evaluated deterministically on GitHub Actions

## 3. Preserve evidence and validate the gate

- [x] 3.1 Update G5 evidence/reporting output if needed to record deterministic execution mode and mock-provider observations
- [ ] 3.2 Re-run `Integration Test (G0-G5)` and verify G5 passes after G4 while preserving the intended resilience assertions
