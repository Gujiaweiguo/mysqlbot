## Context

The scheduled `Integration Test (G0-G5)` workflow currently reaches G4 successfully at the environment and fixture layers, but the happy-path regression still depends on the runtime resolving a real default LLM configuration. In CI, the workflow prepares `demo_sales` data and datasource metadata, yet it does not seed an `ai_model` default model row or stable provider configuration, so `/api/v1/chat/question` can fail before SQL generation begins.

This is more than a flaky script problem. The repository already defines G4 as a mandatory regression gate with evidence-backed pass/fail reporting. A reliable repair therefore needs to preserve the NL-to-SQL pipeline contract while removing dependence on external provider credentials, quota, or output variability.

## Goals / Non-Goals

**Goals:**
- Make the G4 happy-path regression deterministic in CI.
- Preserve end-to-end coverage of the G4 path through chat request, model invocation, SQL generation, and data-return validation.
- Keep G4 evidence output meaningful and traceable for reviewers.
- Avoid requiring external LLM secrets for scheduled and workflow-dispatch regression runs.

**Non-Goals:**
- Changing production model-provider behavior.
- Reworking G5 failure-path regression, which already has its own mock-driven contract.
- Expanding the regression suite to cover new user journeys beyond the existing G4 `demo_sales` cases.

## Decisions

### Decision 1: Use a deterministic CI-only mock LLM provider for G4

G4 will use a deterministic mock provider in CI instead of a real external provider.

**Why:** This preserves the real G4 application path while removing secrets, cost, model drift, and rate-limit flakiness from a mandatory gate.

**Alternative considered:** Inject a real provider API key into CI. Rejected because it keeps the gate nondeterministic and operationally fragile.

### Decision 2: Seed explicit default-model configuration as part of CI setup

The integration workflow will seed the minimum AI model/runtime configuration required for G4, including an explicit default model pointing at the deterministic CI provider path.

**Why:** The current failure is partly caused by the application having no stable default model in CI. Seeding that state makes the gate contract explicit instead of relying on ambient database contents.

**Alternative considered:** Add a codepath that bypasses model resolution entirely in the G4 script. Rejected because it would stop testing the real chat/model orchestration path.

### Decision 3: Preserve G4 evidence shape while reporting provider mode

The G4 output should continue to report per-case pass/fail, SQL presence, and returned data, but it should also identify that the run used the deterministic CI provider path.

**Why:** Reviewers still need the same pass/fail evidence, and they also need to know the execution mode when auditing regression results.

**Alternative considered:** Leave reporting unchanged. Rejected because it hides an important piece of regression context.

### Decision 4: Keep G5 independent from the G4 stabilization path

G5 will continue to validate rate-limit and transient-failure behavior separately from the deterministic G4 provider path.

**Why:** G4 and G5 serve different purposes: G4 validates happy-path correctness; G5 validates failure-path resilience. Combining them would blur acceptance criteria.

## Risks / Trade-offs

- **[Risk]** The mock provider could become too unrealistic and mask prompt/SQL regressions. → **Mitigation:** keep the mock contract focused on deterministic question-to-SQL coverage for the existing `demo_sales` cases and still require SQL/data evidence.
- **[Risk]** CI-only model seeding could drift from the workflow's fixture setup. → **Mitigation:** seed model state in the same workflow section that prepares `demo_sales` and datasource metadata.
- **[Risk]** Reporting may become harder to compare across old and new runs. → **Mitigation:** explicitly include provider mode in regression evidence so reviewers can distinguish historical external-provider runs from deterministic CI runs.

## Migration Plan

1. Add the deterministic CI regression capability and update regression specs to describe the new G4 contract.
2. Implement the CI-only deterministic provider and seed the required default-model configuration during G4 setup.
3. Update reporting/evidence to record the provider mode used in G4.
4. Run the integration workflow locally or via GitHub Actions to confirm G4 passes without external provider credentials.

## Open Questions

- Resolved in implementation: use an in-process CI-only provider type registered through the existing LLM factory seam instead of a separate HTTP mock boundary.
- Resolved in implementation: record provider mode in both the G4 evidence JSON and the regression report template.
