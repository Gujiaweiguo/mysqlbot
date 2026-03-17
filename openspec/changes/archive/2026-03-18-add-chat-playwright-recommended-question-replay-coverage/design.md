## Context

The Playwright baseline now covers the primary new-chat success path, a historical chat load, and one streamed error path. It still does not verify a key continuation action already present in the chat UI: clicking a recommended follow-up question and observing the conversation continue inside the existing chat state.

This follow-up should remain intentionally small. The current harness in `frontend/e2e/` already solves the hard parts: authenticated cache seeding, app-shell bootstrap mocks, deterministic chat route interception, and stable selectors for the current smoke journeys. The safest next step is to add one replay-oriented browser test on top of a preloaded successful chat, rather than combining chat creation and replay into a larger multi-step scenario.

## Goals / Non-Goals

**Goals:**
- Add one deterministic Playwright browser test for recommended-question replay.
- Reuse the existing Playwright chat fixture layer rather than creating a second E2E architecture.
- Assert user-visible continuation behavior, including the clicked recommended question, replayed user turn, follow-up assistant result, and cleared streaming state.
- Keep the change limited to the existing Playwright harness, chat fixtures, and E2E documentation.

**Non-Goals:**
- Live backend, datasource, or provider replay testing.
- Broad multi-turn conversation matrices or multiple recommendation variants.
- Analysis, predict, export, or backend changes.
- Replacing the current deterministic baseline fixture approach.

## Decisions

### Decision 1: Drive replay from an already loaded successful chat state

The new browser journey will start from the loaded historical chat flow rather than creating a brand-new chat before replaying a recommendation.

**Why:**
- This keeps the test focused on the recommendation replay behavior itself.
- The historical chat baseline already demonstrates deterministic setup for an existing successful conversation.

**Alternatives considered:**
- Create a new chat and then replay a recommendation in the same test: rejected because it combines two separate behaviors and increases failure surface.

### Decision 2: Extend the existing fixture layer with a deterministic second-turn replay response

The implementation will reuse the current mocked chat route setup and add only the additional fixture support needed for clicking a visible recommended question and receiving a deterministic follow-up streamed answer.

**Why:**
- The current success and error-path tests already prove the route interception pattern works.
- Reusing the same fixture layer reduces maintenance drift between baseline journeys.

**Alternatives considered:**
- Build a separate replay-only fixture module: rejected because it would duplicate auth/app-shell setup and widen maintenance cost.

### Decision 3: Assert stable user-visible outcomes instead of network-only behavior

The replay test will assert that the clicked recommended question becomes the next user turn, that the follow-up assistant result becomes visible, and that active thinking/streaming clears when the replayed response completes.

**Why:**
- The value of this test is browser-level confidence in conversation continuation, not just that a request was sent.
- These assertions match the visible behavior users rely on.

**Alternatives considered:**
- Assert only network activity or route invocation: rejected because it provides weaker regression coverage.

## Risks / Trade-offs

- **[Fixture drift from current replay contract]** → Keep replay mock payloads shaped exactly like the existing chat streaming contract and reuse current fixtures where possible.
- **[Selector brittleness around recommendation UI]** → Reuse current DOM hooks if stable enough; add only the smallest missing selector hook during implementation.
- **[Scope creep into broader multi-turn coverage]** → Restrict the change to one deterministic replay journey and document remaining deferred scenarios.
- **[False confidence from deterministic mocks]** → Keep backend and lower-level tests as the contract layer; this change is only for browser-level continuation behavior.

## Migration Plan

1. Extend the existing Playwright chat fixtures with deterministic recommendation replay support.
2. Add one focused Playwright smoke test for the replay journey.
3. Update the E2E README so covered vs deferred scenarios remain explicit.
4. Verify with Playwright headless, frontend lint, and frontend build.

Rollback is straightforward: remove the replay-specific fixture support, browser test, and README update while keeping the existing baseline suite intact.

## Open Questions

- Does the current recommendation UI already expose a stable enough selector, or should a small test hook be added during implementation?
- Should the replay assertion target the exact recommended text payload or a stable visible subset in case copy formatting changes?
