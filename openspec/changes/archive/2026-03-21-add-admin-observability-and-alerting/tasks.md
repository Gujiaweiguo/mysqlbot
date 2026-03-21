## 1. Define the critical observability surface

- [x] 1.1 Inventory the critical admin/runtime endpoints restored in recent changes and group them by feature area.
- [x] 1.2 Identify the existing logging/request signal points that can be reused for these endpoint groups.

## 2. Add observability signals

- [x] 2.1 Add or standardize structured observability signals for authentication, platform, audit, custom prompt, appearance, AI model, and permission API flows.
- [x] 2.2 Ensure the signals capture enough information to distinguish repeated failures, elevated error rates, and latency degradation.

## 3. Define alerting and runbooks

- [x] 3.1 Define alert conditions for the critical endpoint groups.
- [x] 3.2 Document operator-facing triage guidance for each alert group.

## 4. Validation

- [x] 4.1 Validate the observability signals against known failure scenarios or recently fixed regressions.
- [x] 4.2 Confirm the final alerting surface stays scoped to observability and does not change business behavior.
