## Why

The repository now has stronger backend and frontend validation, but it still lacks any browser-level regression coverage for the chat experience. We need a minimal Playwright baseline now so the highest-risk chat journeys can be verified end-to-end when orchestration, streaming, or UI rendering changes.

## What Changes

- Add a minimal Playwright E2E harness for the frontend application, including scripts and configuration that can run locally and in CI-friendly environments.
- Define a stable, low-scope test environment strategy for browser tests so the initial suite does not depend on broad manual setup.
- Add one or two critical smoke journeys for chat, focused on the most important user-visible success paths rather than full feature coverage.
- Document the supported way to execute the E2E baseline and what the baseline intentionally does not cover yet.

## Capabilities

### New Capabilities
- `chat-e2e-baseline`: Defines the Playwright-based E2E test harness, execution contract, and minimal environment requirements for browser-level verification.
- `chat-critical-journeys`: Defines the first critical chat user journeys that the E2E baseline MUST cover.

### Modified Capabilities
- None.

## Impact

- Likely affected areas include `frontend/package.json`, new Playwright config and test files under `frontend/`, optional test fixtures/mocks, and developer/CI documentation.
- Adds a new external testing dependency and browser automation workflow to the frontend toolchain.
- Introduces a new verification layer for chat UI and streaming behavior, but intentionally does not attempt full product-wide E2E coverage in the first iteration.
