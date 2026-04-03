## Context

The current login experience has feedback gaps at three distinct moments. First, login bootstrap can block the page behind a generic loading state while authentication providers and redirect logic are being resolved. Second, the credential submit button does not communicate in-progress state clearly enough during account verification. Third, users can still encounter a silent pause between successful authentication and arrival at the destination application view because route/bootstrap initialization continues after the token is accepted.

The goal of this change is to improve user confidence during those waits, not to solve every performance cause in the authentication stack. This is a communication and interaction change, not a full login-path performance rewrite.

## Goals / Non-Goals

**Goals:**
- Show clear waiting feedback during login bootstrap before the form is fully interactive.
- Show explicit in-progress feedback on credential submission and prevent duplicate submits while a login attempt is active.
- Show a user-visible transition state after authentication succeeds but before the destination page is ready.
- Keep success/failure auth behavior unchanged while making wait states understandable.

**Non-Goals:**
- Parallelizing or redesigning all login bootstrap/network steps.
- Changing authentication provider configuration, validation, or backend auth semantics.
- Introducing fake percentage progress that is not backed by real measurable progress.

## Decisions

### Decision 1: Prefer stage messaging over percentage progress

The login experience will use stage-specific waiting text and component-level loading states rather than a numeric progress bar.

**Why:**
- The current login flow is composed of asynchronous steps whose durations are not predictable enough to support truthful percentages.
- Stage text communicates forward motion without inventing precision the system does not have.

**Alternatives considered:**
- Determinate progress bar: rejected because the flow has no reliable progress signal.
- Indeterminate top-level spinner only: rejected because it still leaves users guessing what is happening.

### Decision 2: Keep primary submission feedback anchored to the login action

Credential submission feedback will live on the login action itself (for example, loading/disabled button state) rather than only in a global full-screen overlay.

**Why:**
- Users need immediate confirmation that the click was registered.
- Anchoring feedback to the button reduces repeat submissions and keeps the mental model close to the action they just triggered.

**Alternatives considered:**
- Full-screen overlay during submit: rejected because it is heavier than necessary for a credential form action.

### Decision 3: Distinguish bootstrap wait from post-login transition wait

The login UX will communicate different wait states for pre-form bootstrap and post-auth transition rather than treating them as one generic loading mask.

**Why:**
- These phases have different meanings from the user's perspective.
- Distinguishing them makes it easier to understand whether the system is preparing sign-in options or entering the application after a successful login.

**Alternatives considered:**
- Reuse one generic “Loading...” message for all waits: rejected because it remains too opaque.

### Decision 4: Preserve authentication outcomes and only improve visibility

This change will not alter who can log in, which routes they land on, or how providers are chosen; it only changes how wait states are surfaced.

**Why:**
- Login correctness is higher risk than login feedback polish.
- Keeping auth semantics fixed lets us verify UX changes without conflating them with auth regressions.

**Alternatives considered:**
- Bundle UX feedback with login-path performance refactors: rejected because it expands scope and weakens validation clarity.

## Risks / Trade-offs

- **[Too much messaging feels noisy]** → Limit stage text to major user-visible waits only.
- **[Feedback drifts from real state]** → Derive wait messages from actual async boundaries already present in the frontend flow.
- **[Overlay blocks correction after failure]** → Use lightweight button-level feedback during submission and keep errors attached to the form flow.
- **[Scope expands into auth performance optimization]** → Treat deeper latency reduction as a separate future change.

## Migration Plan

1. Define the login wait-feedback capability and required user-visible states.
2. Add bootstrap-stage messaging for the login entry flow before the form is ready.
3. Add credential-submit loading/disabled behavior and duplicate-submit prevention for supported login forms.
4. Add post-login transition messaging until the destination page is ready.
5. Verify visible wait states and unchanged login success/failure outcomes in targeted frontend tests.

Rollback is straightforward: remove the new feedback states and restore the previous generic waiting behavior without changing auth logic.

## Open Questions

- None for this pass.
