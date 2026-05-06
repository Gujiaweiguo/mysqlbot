## Context

Assistant and embedded chat already have a direct-entry branch that skips the datasource picker when `auto_ds` is enabled, but today that branch creates a datasource-less chat session. That behavior is too ambiguous for multi-datasource workspaces, where users need the speed of direct entry without losing clarity about which datasource is active.

This change is intentionally scoped to assistant and embedded chat. The main mysqlbot chat page remains a multi-datasource surface whose existing explicit datasource selection flow should not change.

## Goals / Non-Goals

**Goals:**
- Let assistant and embedded chat start directly with a configured default datasource.
- Make the active datasource visible in assistant and embedded chat after entry.
- Allow datasource switching from assistant and embedded chat.
- Force datasource switching to create a new chat session so one session never mixes datasource context.
- Preserve the current standard mysqlbot chat entry behavior.

**Non-Goals:**
- Add workspace-level automatic datasource selection.
- Change the standard mysqlbot `/chat/index` entry contract.
- Support in-place datasource mutation for an existing chat session.
- Introduce datasource inference from recent history or question content.

## Decisions

### Decision: Default datasource is assistant-scoped, not workspace-scoped
Assistant and embedded surfaces usually carry narrower business intent than the main mysqlbot workspace. In a workspace that commonly uses multiple datasources side by side, a workspace default would create silent misrouting risk. Assistant-level configuration keeps the default specific, predictable, and explainable.

**Alternatives considered:**
- Workspace default datasource: rejected because it is too coarse for multi-datasource workspaces.
- Recent datasource reuse: rejected because it is convenient but not reliably explainable.

### Decision: Direct entry SHALL create a chat session already bound to the default datasource
The assistant direct-entry flow should call the same assistant start path with an explicit datasource instead of creating a datasource-less session and deferring selection. This keeps backend chat state, visible datasource state, and follow-up question behavior aligned from the first turn.

**Alternatives considered:**
- Keep datasource-less direct entry and only show a label in the UI: rejected because the session state would not actually be bound.
- Bind the datasource only on first question send: rejected because the entry session and first-turn behavior would diverge.

### Decision: Datasource switching SHALL create a new chat session
Switching datasource in the same session would mix incompatible chat history, recommended questions, and SQL/chart context. The safer contract is to treat datasource switching as a context reset that creates a fresh session bound to the newly selected datasource.

**Alternatives considered:**
- In-place datasource reassignment: rejected because historical records and future records would no longer share one reliable datasource context.

### Decision: Assistant/embedded chat SHALL show visible datasource state when a datasource is bound
The UI should render the currently active datasource and a switch action even in the assistant direct-entry layout. This makes the implicit default explicit to the user and reduces the risk of asking against the wrong datasource without noticing.

**Alternatives considered:**
- Keep datasource hidden for a cleaner embedded UI: rejected because hidden context is unsafe in multi-datasource workspaces.

## Risks / Trade-offs

- **[Risk]** Assistant configuration may reference a datasource that is deleted or no longer accessible. → **Mitigation:** validate configured default datasource at save time and fail direct entry gracefully if the datasource later becomes unavailable.
- **[Risk]** Users may perceive “switch datasource” as changing the current conversation rather than starting over. → **Mitigation:** label the action clearly and explain that switching opens a new chat.
- **[Risk]** Embedded surfaces may have less room for datasource status and switch controls. → **Mitigation:** reuse compact datasource presentation and keep switch affordance lightweight.

## Migration Plan

1. Extend assistant configuration to persist an optional default datasource alongside the existing direct-entry control path.
2. Update assistant start-chat orchestration so direct entry passes the configured datasource when present.
3. Expose active datasource state and a switch action in assistant and embedded chat.
4. Route datasource switching through new-chat creation rather than in-place chat mutation.
5. Add regression coverage for assistant default entry and switch-to-new-session behavior.

Rollback is straightforward: disable use of the stored default datasource in assistant start-chat and fall back to the current explicit picker flow.

## Open Questions

- Should assistant configuration require `auto_ds` to be enabled whenever a default datasource is set, or should the default datasource be stored independently and only applied when direct entry is enabled?
- Should the switch action reuse the existing datasource drawer copy verbatim, or should assistant/embedded wording explicitly warn that a new chat will be created?
