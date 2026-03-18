## Why

The Playwright suite now covers the primary chat success flow, a historical chat load, and a streamed error path, but it still does not verify what happens when a user clicks a recommended follow-up question. We need one deterministic browser-level replay test now so regressions in suggested-question continuation do not slip past the current coverage.

## What Changes

- Extend the existing Playwright chat E2E suite with one deterministic recommended-question replay journey.
- Reuse the current mocked chat fixture layer and add only the fixture support needed for a second-turn replay response.
- Assert user-visible continuation behavior in the browser, including the replayed user turn, the follow-up assistant result, and the cleared active streaming state.
- Update E2E documentation so the baseline scope includes recommended-question replay while still calling out what remains deferred.

## Capabilities

### New Capabilities
- `chat-recommended-question-replay-journeys`: Defines deterministic browser-level coverage for recommended-question replay on top of the existing Playwright chat baseline.

### Modified Capabilities
- None.

## Impact

- Likely affected areas include `frontend/e2e/chat.spec.ts`, `frontend/e2e/fixtures/chat-fixtures.ts`, and `frontend/e2e/README.md`.
- Reuses the existing Playwright harness under `frontend/` without changing backend APIs or broadening into analysis, predict, or live-provider coverage.
- Adds one focused browser regression check for chat continuation from a recommended follow-up question while keeping the E2E suite intentionally small.
