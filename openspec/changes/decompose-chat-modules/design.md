## Context

The chat path now concentrates a large amount of behavior in a few files, especially `backend/apps/chat/task/llm.py`, `backend/apps/chat/curd/chat.py`, and `frontend/src/views/chat/index.vue`. Those files mix concerns that change for different reasons: transport handling, orchestration, streaming, state coordination, rendering, and persistence. As a result, even moderate chat changes carry more regression risk than they should.

This change is a staged decomposition contract, not a chat feature redesign. The core requirement is to preserve current chat behavior for users and integrations while replacing oversized ownership boundaries with focused collaborators on both the frontend and backend.

## Goals / Non-Goals

**Goals:**
- Preserve current chat journeys while creating clearer backend and frontend ownership boundaries.
- Extract backend chat work behind stable orchestration and migration-safe collaborator seams.
- Split the frontend chat page into a shell plus focused state/rendering/input units.
- Route frontend stream consumption through one shared adapter path.
- Improve testability for chat happy paths and failure paths without changing transport semantics.

**Non-Goals:**
- Redesigning chat UX, prompts, SQL generation semantics, or datasource behavior.
- Changing public chat endpoints or integration-facing request/response formats.
- Refactoring unrelated application areas outside the chat flow.

## Decisions

### Decision 1: Preserve a stable backend orchestration entrypoint during extraction

The backend decomposition will proceed behind a stable orchestration boundary so chat endpoints do not need to know which internal collaborator currently owns each stage.

**Why:**
- This allows staged extraction from the monolith files without forcing broad transport-level rewrites.
- A stable entrypoint reduces the chance of partially migrated flows diverging.

**Alternatives considered:**
- Rewrite the backend chat path in one step: rejected because the blast radius is too large.

### Decision 2: Treat the frontend chat page as a composition shell

`frontend/src/views/chat/index.vue` will become a page shell that delegates rendering, input, and stateful behaviors to focused child components and shared composables/controllers.

**Why:**
- The current root view has too many reasons to change.
- A shell-and-composables model makes it easier to test and evolve individual chat behaviors.

**Alternatives considered:**
- Split only visual markup and keep state/orchestration in the root page: rejected because the largest maintenance problem would remain.

### Decision 3: Use one shared stream-consumption adapter on the frontend

Frontend chat surfaces will consume stream events through one shared adapter/composable layer instead of parsing chunks directly inside page-level code.

**Why:**
- Stream event handling is contract logic, not view-specific rendering logic.
- A shared adapter is the safest place to keep parity between embedded and full-page chat surfaces.

**Alternatives considered:**
- Keep local parsing in each view mode: rejected because it recreates drift during the decomposition.

### Decision 4: Preserve external chat behavior as the compatibility target

The decomposition will treat current chat journeys, stream completion behavior, and error-path semantics as the compatibility contract.

**Why:**
- This keeps the change scoped to maintainability instead of turning into a product redesign.
- Existing regression checks remain meaningful when compatibility is explicit.

**Alternatives considered:**
- Combine decomposition with UX/API changes: rejected because it would obscure regressions and expand scope too far.

## Risks / Trade-offs

- **[Partial decomposition leaves duplicate logic alive]** → Sequence extraction so new collaborators replace old ownership instead of wrapping it indefinitely.
- **[Frontend split introduces state regressions]** → Centralize stream/session state in shared composables/controllers and verify embedded/full-page parity.
- **[Backend staging breaks stream/error behavior]** → Keep stream serialization behind one contract and verify happy-path and failure-path streaming explicitly.
- **[Scope grows into feature redesign]** → Treat current user-visible chat behavior as a non-goal boundary for the change.

## Migration Plan

1. Finalize specs for frontend boundaries and the backend/streaming deltas.
2. Introduce the backend orchestration seam and shared stream-consumption adapter without changing chat transport contracts.
3. Extract frontend page-shell responsibilities into focused components/composables.
4. Migrate backend monolith responsibilities into explicit collaborators behind the stable entrypoint.
5. Remove obsolete duplicated logic once parity tests confirm unchanged behavior.

Rollback can happen at each extraction step because the public chat contract stays stable. If a decomposition slice proves risky, the implementation can stop at the last compatible seam without forcing external migration.

## Open Questions

- None for this pass.
