## Context

The repository now has a minimal Playwright baseline for successful chat flows, including deterministic route mocks and two smoke tests. That baseline intentionally excludes error-path coverage even though chat responses can fail after streaming begins, and the frontend has dedicated UI behavior for rendering chat errors and recovering from the active thinking/loading state.

This follow-up change should remain deliberately small. The current harness in `frontend/e2e/` already solves the difficult parts: auth seeding, app-shell bootstrap mocking, deterministic chat API interception, and stable selectors for the baseline chat flows. The safest next step is to extend that existing structure with one focused error-path test rather than introduce a new test framework, a live backend dependency, or multiple new error matrices.

## Goals / Non-Goals

**Goals:**
- Add one deterministic Playwright browser test for the primary chat streamed error-event path.
- Reuse the existing mocked Playwright chat fixture pattern rather than introducing a new environment strategy.
- Assert user-visible recovery behavior, including preserved submitted question, rendered error state, and cleared active streaming/thinking state.
- Keep the change limited to the current Playwright harness, chat fixtures, and chat E2E docs.

**Non-Goals:**
- Live backend, datasource, or provider error testing.
- Broad E2E expansion into analysis, predict, export, auth, or dashboard error scenarios.
- Backend API contract changes.
- Replacing the current deterministic success-path mocks.

## Decisions

### Decision 1: Reuse the existing chat fixture layer with an error variant

The new test will extend `frontend/e2e/fixtures/chat-fixtures.ts` with an error-path variant for the existing `/api/v1/chat/question` stream instead of creating a second fixture architecture.

**Why:**
- The success-path baseline already proved the current route interception model works reliably.
- Keeping both success and error coverage in the same fixture structure reduces maintenance drift and keeps the mock contract easy to reason about.

**Alternatives considered:**
- Create a separate fixture module just for failures: rejected because it would duplicate auth/app-shell mocking and increase maintenance cost.
- Use a live backend failure: rejected because it would make the first error-path test non-deterministic.

### Decision 2: Drive the failure through a streamed chat `error` event, not a transport failure

The baseline will model the user-visible failure state by emitting a contract-shaped streamed `error` event from the mocked chat question request after submission starts.

**Why:**
- This matches the existing chat frontend behavior more closely than forcing a network timeout or HTTP transport failure.
- The current UI already distinguishes streamed chat failures from ordinary request bootstrap failures, so this is the most meaningful next regression target.

**Alternatives considered:**
- HTTP 500 for `/chat/question`: rejected because it would test a different failure surface than the streamed chat record UI.
- Browser-level network abort: rejected because it is less precise for the current frontend error-rendering path.

### Decision 3: Assert user-visible recovery, not only network completion

The Playwright test will verify that the submitted user question remains visible, the chat error UI becomes visible for the failed response, and the active thinking/loading state does not remain stuck after the error event.

**Why:**
- The value of this test is browser-level recovery confidence, not just confirming that a mocked payload was consumed.
- These assertions align with how users experience a failed chat response.

**Alternatives considered:**
- Assert only that the request was sent: rejected because it provides weak regression protection.

## Risks / Trade-offs

- **[Fixture drift from frontend event contract]** → Keep the new error mock event shaped exactly like the current chat streaming contract and limit the test to one error path.
- **[Selector instability around error rendering]** → Reuse existing stable test hooks where possible and add only the smallest missing hook if the current DOM is too brittle.
- **[Over-expanding the E2E matrix]** → Restrict this change to one error-path journey and document remaining deferred error scenarios.
- **[False confidence from deterministic mocks]** → Keep backend and lower-level tests as the contract layer; this change is only for browser-level UI recovery.

## Migration Plan

1. Extend the existing Playwright chat fixtures with one deterministic streamed error-path variant.
2. Add a focused Playwright smoke test for the primary chat error event journey.
3. Update the E2E README so covered vs deferred scenarios remain explicit.
4. Verify with Playwright headless, frontend lint, and frontend build.

Rollback is straightforward: remove the added error fixture variant, browser test, and accompanying doc update while keeping the existing success-path baseline intact.

## Open Questions

- Should the error-path assertion target the raw mocked error text or a stable localized wrapper around it?
- Does the current chat error DOM already expose a sufficiently stable selector, or should a small test hook be added during implementation?
