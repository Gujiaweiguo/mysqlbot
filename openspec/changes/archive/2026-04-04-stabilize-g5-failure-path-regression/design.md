## Context

The full integration workflow now proves that runtime health, fixture preparation, and deterministic G4 happy-path behavior work on GitHub Actions. The remaining failure is G5, which validates rate-limit and transient-provider behavior using a local mock server plus the `/api/v1/mcp/mcp_assistant` path.

Because G5 is intentionally a failure-path gate, its success criteria are different from G4: it must prove that controlled upstream failures are surfaced predictably and that recovery or controlled fallback behavior remains explainable. The repository already has specs covering rate-limit resilience and regression reporting, so the main job now is to align the workflow/tooling with those contracts on hosted CI.

## Goals / Non-Goals

**Goals:**
- Make G5 deterministic and reliable on GitHub Actions.
- Preserve separate validation of HTTP 429 and transient 503 behavior.
- Keep evidence output sufficient for reviewers to verify pass/fail and retry observations.
- Avoid re-scoping or weakening G4 in the process.

**Non-Goals:**
- Changing the completed G4 deterministic happy-path implementation.
- Replacing G5 with a unit test-only check.
- Changing production MCP assistant behavior beyond what is necessary to support deterministic failure-path regression.

## Decisions

### Decision 1: Keep G5 as a dedicated failure-path gate

G5 remains an independent gate after G4 success.

**Why:** G4 and G5 validate different contracts: happy-path correctness vs resilience to upstream failure. Keeping them separate preserves clear failure ownership.

### Decision 2: Preserve controllable mock-provider behavior as the source of failures

G5 should continue using deterministic mock-provider responses for HTTP 429 and transient 503 scenarios rather than a real external provider.

**Why:** Failure-path acceptance criteria require reproducible upstream behavior, which real providers cannot guarantee in CI.

### Decision 3: Fix runner/container interaction at the workflow boundary if needed

If G5 currently fails due to runner/container networking or environment mismatches, the fix should be made at the workflow/script boundary rather than by weakening the G5 assertions.

**Why:** The gate contract is already valid; the repository should adapt the CI harness to the contract, not the reverse.

### Decision 4: Keep evidence/reporting explicit about the G5 execution mode

G5 evidence should continue to report mock-provider behavior, observed retry counts, and whether failures were controlled.

**Why:** Reviewers need to distinguish intentional failure-path validation from infrastructure noise.

## Risks / Trade-offs

- **[Risk]** G5 may depend on runner-specific networking assumptions (for example host/container access to the mock server). → **Mitigation:** document and stabilize the provider-host strategy in workflow and script configuration.
- **[Risk]** Fixing G5 could accidentally weaken its assertions. → **Mitigation:** keep pass/fail criteria anchored to the current resilience specs and update tests/evidence instead of relaxing expectations.
- **[Risk]** Evidence may look green while masking the wrong execution mode. → **Mitigation:** explicitly record the deterministic failure-path mode and observed mock hit counts.

## Migration Plan

1. Identify the exact CI-specific failure mode in the current G5 workflow/script path.
2. Update workflow/script configuration to make the mock-provider path deterministic on GitHub Actions.
3. Adjust evidence/reporting or specs only where needed to reflect the stabilized execution mode.
4. Re-run `Integration Test (G0-G5)` on GitHub Actions until G5 passes after G4.

## Open Questions

- Does G5 fail because the backend container cannot reliably reach the runner-hosted mock server, or because the failure-path assertions expect a different runtime behavior than `/api/v1/mcp/mcp_assistant` currently provides?
- Should the mock-provider host remain configurable via script argument only, or should the workflow set an explicit CI-safe host value as part of the gate contract?
