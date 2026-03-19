## 1. Backend Configuration Lifecycle

- [x] 1.1 Define persistence for the singleton embedding admin configuration and runtime state
- [x] 1.2 Add APIs to read and update embedding configuration separately from enable/disable actions
- [x] 1.3 Add a validation API that performs a real provider probe and records validation outcome

## 2. Runtime Safety Gates

- [x] 2.1 Define how runtime code determines whether embedding is disabled, verified-disabled, enabled, or stale
- [x] 2.2 Ensure embedding-dependent paths degrade safely when embedding is disabled or unverified
- [x] 2.3 Mark provider/model edits as invalidating prior verification and surfacing reindex risk
- [x] 2.4 Define precedence between persisted admin config and environment bootstrap defaults

## 3. Frontend Admin Flow

- [x] 3.1 Add a visual embedding configuration workflow that reuses existing system admin patterns where appropriate
- [x] 3.2 Separate save, validate, and enable/disable actions in the UI
- [x] 3.3 Surface current embedding state, validation result, and reindex-required warnings clearly to administrators

## 4. Verification and Rollout

- [x] 4.1 Verify administrators cannot enable embedding before validation succeeds
- [x] 4.2 Verify valid configuration can be saved, validated, and enabled successfully for the selected provider
- [x] 4.3 Verify provider/model edits move the system back into a cautionary state with clear re-embedding guidance
- [x] 4.4 Verify runtime behavior respects disabled/unverified state after failed re-validation or stale provider/model changes
