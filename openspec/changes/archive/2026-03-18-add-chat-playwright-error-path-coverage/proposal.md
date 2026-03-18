## Why

The Playwright baseline now proves the primary chat success flows, but it still explicitly excludes streamed chat failures. We need one deterministic browser-level error-path check now so regressions in chat error rendering and recovery do not slip past the current success-only baseline.

## What Changes

- Extend the existing Playwright chat E2E suite with one deterministic streamed error-path journey for the primary chat question flow.
- Reuse the current mocked chat streaming harness and add only the fixture support needed to emit a contract-shaped `error` event.
- Assert user-visible error and recovery behavior in the browser, not just network activity.
- Update E2E documentation so the baseline scope includes the covered chat error path and still clearly states what remains deferred.

## Capabilities

### New Capabilities
- `chat-error-journeys`: Defines the first deterministic browser-level chat error-path coverage added on top of the existing Playwright baseline.

### Modified Capabilities
- None.

## Impact

- Likely affected areas include `frontend/e2e/chat.spec.ts`, `frontend/e2e/fixtures/chat-fixtures.ts`, and `frontend/e2e/README.md`.
- Reuses the existing Playwright harness under `frontend/` without changing backend APIs or expanding into live-provider coverage.
- Adds one focused browser regression check for chat streamed failure handling while keeping the E2E suite intentionally small.
