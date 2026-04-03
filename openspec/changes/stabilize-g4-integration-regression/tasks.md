## 1. Define deterministic G4 CI contract

- [x] 1.1 Add the new `ci-deterministic-llm-regression` capability spec and update regression gate/reporting specs for deterministic G4 behavior
- [x] 1.2 Decide and document whether the deterministic provider is an HTTP mock boundary or an in-process CI-only provider registration path

## 2. Implement deterministic G4 provider setup

- [x] 2.1 Add the CI-only deterministic provider/runtime support needed for G4 happy-path regression
- [x] 2.2 Seed explicit default-model configuration for G4 during CI fixture/setup so the app has a stable provider path
- [x] 2.3 Update `.github/workflows/integration-test.yml` so G4 uses the deterministic provider path without external provider secrets

## 3. Preserve evidence and verify the gate

- [x] 3.1 Update G4 evidence/reporting output to record provider mode while preserving existing pass/fail fields
- [x] 3.2 Verify the integration workflow reaches a deterministic G4 pass and still leaves G5 failure-path coverage independent
