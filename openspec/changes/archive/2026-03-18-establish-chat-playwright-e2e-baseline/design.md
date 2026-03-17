## Context

The frontend currently has lint and build validation but no browser-level automation. The chat experience is the riskiest user-facing area because it combines route state, chat creation, streaming updates, recommendation actions, and multiple UI states inside a large Vue page.

This first E2E change should stay intentionally small. The repository does not already have Playwright, an E2E folder, or browser test scripts, and the live chat backend depends on auth, datasource setup, and LLM-style streaming behavior that would make a first E2E suite brittle if it depended on real provider calls.

## Goals / Non-Goals

**Goals:**
- Establish a Playwright harness that runs reliably in local and CI-friendly environments.
- Cover one or two critical chat smoke journeys at the browser level.
- Verify the frontend can consume chat-style streaming responses and render key user-visible states correctly.
- Keep the first test environment deterministic enough that failures indicate UI or request-contract regressions rather than external provider instability.

**Non-Goals:**
- Full product-wide E2E coverage.
- Real LLM/provider integration in the first Playwright suite.
- Exhaustive auth, permission, or datasource matrix coverage.
- Replacing existing backend or unit/integration validation.

## Decisions

### Decision 1: Place the Playwright harness under `frontend/`

Playwright config, scripts, and tests will live under `frontend/` so the browser harness stays close to the Vite app, its TypeScript tooling, and its npm scripts.

**Why:**
- The frontend already owns the build toolchain and package management for browser-facing code.
- This keeps installation and execution straightforward: frontend developers can run one set of npm scripts without needing a second JavaScript workspace.

**Alternatives considered:**
- Put E2E assets at repo root: rejected because this repo does not have a root JavaScript toolchain to host them cleanly.

### Decision 2: Start with deterministic mocked or controlled API responses

The first Playwright suite will use a controlled environment strategy for chat APIs, including deterministic list/create/stream responses, rather than depending on real datasource and provider execution.

**Why:**
- The initial objective is regression coverage for browser behavior and frontend request/stream handling, not provider correctness.
- Deterministic responses make CI failures actionable and keep setup cost low.

**Alternatives considered:**
- Full live backend + live LLM E2E: rejected for the first baseline because it introduces too many external failure modes.
- Pure component tests only: rejected because they would miss route, browser, and network orchestration behavior.

### Decision 3: Cover only critical chat smoke journeys first

The first suite will target 1-2 critical user journeys such as starting a new chat and receiving a streamed answer, plus one follow-up chat action like recommended-question replay or viewing a loaded chat history.

**Why:**
- The main value is catching breakage in the paths users hit first and most often.
- A narrow scope keeps the first E2E setup maintainable and easier to adopt.

**Alternatives considered:**
- Cover all chat actions immediately: rejected because the setup and fixture matrix would grow too quickly.

### Decision 4: Make execution available through explicit npm scripts

The baseline will define frontend npm scripts for running Playwright headless in CI and optionally in interactive/local debug mode.

**Why:**
- The repository currently exposes frontend quality checks through npm scripts, so E2E should follow the same entrypoint style.
- Clear scripts reduce ambiguity for both developers and CI wiring.

## Risks / Trade-offs

- **[Mocked E2E can miss backend contract drift]** → Keep existing backend tests as the contract layer and ensure Playwright fixtures mirror real event shapes used by chat streaming.
- **[Large chat page is hard to select reliably]** → Use stable selectors or purposeful test ids for the first covered flows.
- **[Streaming assertions can be flaky]** → Use deterministic mocked event ordering and assert on stable rendered states rather than arbitrary timing.
- **[Baseline scope may expand too fast]** → Limit the first change to 1-2 journeys and document excluded scenarios.

## Migration Plan

1. Add Playwright dependency, config, and npm scripts under `frontend/`.
2. Add test helpers/fixtures for deterministic chat API and streaming behavior.
3. Implement the first critical chat smoke tests.
4. Document how to run the suite locally and in CI.

Rollback is straightforward: remove the Playwright dependency, config, scripts, and E2E test files if the baseline proves unsuitable.

## Open Questions

- Which specific chat journey should be the second smoke path: recommended-question replay or chat-history reload?
- Do we want to add dedicated test ids in the same implementation change, or rely on existing selectors first?
- Should CI run the E2E baseline on every frontend-affecting change immediately, or land the harness first and wire CI in a follow-up?
