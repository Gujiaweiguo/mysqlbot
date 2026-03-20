## Context

The repository already contains partial admin UI for authentication settings, platform integration, and third-party user provisioning, but the backend only exposes a minimal subset of the required contracts. Frontend pages under `system/authentication`, `system/platform`, and `system/parameter/xpack/PlatformParam.vue` assume full CRUD, validation, enable/disable, and login/runtime integration behavior that is currently absent or incomplete. The recently archived xpack-decoupling work intentionally avoided redesigning these domains, so the next change must complete them as first-party capabilities rather than adding more compatibility shims.

## Goals / Non-Goals

**Goals:**
- Implement first-party backend contracts for authentication provider management, enterprise platform integration, and third-party auto-user provisioning.
- Reuse existing frontend pages where possible by making backend APIs conform to the UI and documented feature scope.
- Preserve community-edition operability without reintroducing `sqlbot-xpack`.
- Make login page behavior, provider enablement, validation, and provisioning settings coherent across admin configuration and runtime authentication flows.

**Non-Goals:**
- Implement operation log viewing/export in this change.
- Redesign custom prompts or appearance settings beyond any incidental compatibility fixes.
- Deliver every enterprise login protocol or platform callback in a single unsafe cutover without phased validation.

## Decisions

### 1. Group authentication, platform integration, and third-party provisioning into one change
These capabilities will be implemented together because they share configuration storage, login/runtime behavior, and user-creation side effects.

**Why:** Splitting them would force repeated changes to the same models, routes, and login flow. The official docs also present them as adjacent admin capabilities.

**Alternatives considered:**
- Separate change for third-party provisioning was rejected because provisioning rules only make sense after authentication/platform integrations exist.
- Combining with operation logs was rejected because logs are a separate audit/query domain.

### 2. Favor first-party management APIs that fit the existing frontend rather than rewriting the frontend first
The backend will expose explicit management endpoints for authentication providers and platform settings, aligned with the current admin pages and documented capability set.

**Why:** The frontend pages are already substantial and provide a concrete contract to implement against. Backend completion is lower risk than replacing all admin UI.

**Alternatives considered:**
- Rebuilding the frontend pages from scratch was rejected because it adds unnecessary UI churn before backend behavior is even restored.

### 3. Keep runtime login/provider behavior tied to persisted configuration, not hardcoded placeholders
Provider status, validation state, enablement, and third-party defaults should come from stored records and first-party service logic instead of hardcoded “disabled” responses.

**Why:** The current placeholder routes unblock page rendering but do not satisfy the documented or frontend-expected behavior.

**Alternatives considered:**
- Returning static community placeholders was rejected because these pages are administrative controls, not just informational surfaces.

### 4. Validate and phase by capability slice
Implementation should restore list/read behavior first, then write/update actions, then runtime login or synchronization side effects, with targeted regression checks at each slice.

**Why:** Authentication and platform integration are high-risk areas. Phasing reduces the blast radius and keeps regressions localizable.

**Alternatives considered:**
- Big-bang implementation of all providers and flows in one pass was rejected as too risky for login-critical behavior.

## Risks / Trade-offs

- **[Authentication provider configuration may exist in tables but not map cleanly to frontend expectations]** → Normalize response contracts explicitly and add focused page-level regression checks.
- **[Platform integrations require third-party callback, validation, or sync behavior that exceeds current assumptions]** → Implement management and validation contracts first; stage callback/runtime integrations behind explicit tasks.
- **[Third-party auto-created users could be assigned incorrectly]** → Centralize provisioning defaults (workspace/role) in one backend service and test cross-workspace behavior.
- **[Frontend pages may contain stale enterprise-only assumptions]** → Prefer matching the documented flows and only change frontend when a backend-compatible contract is impossible.
- **[Login regressions could block access to the whole product]** → Keep local login stable throughout and validate login page behavior after every auth/platform slice.

## Migration Plan

1. Inventory the current frontend contracts and documented scope for authentication, platform integration, and third-party provisioning.
2. Introduce/complete backend management APIs and persistence handling for each capability.
3. Wire enable/disable, validate/test connection, and fetch/list flows into the existing admin pages.
4. Restore runtime login/platform effects in a controlled sequence, validating local login remains stable.
5. Add targeted regression tests and live page checks before closing the change.

## Open Questions

- Which parts of provider-specific callback and sync logic should be considered in-scope for the first delivery versus follow-up iterations?
- Should any documented enterprise-only providers remain visible-but-disabled in community builds, or should the UI be driven strictly by configured records?
- How much of the existing `sys_authentication` and user/platform link schema can be reused directly versus requiring normalization helpers?
