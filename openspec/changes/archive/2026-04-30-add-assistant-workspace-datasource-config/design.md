## Context

The proposal adds workspace and datasource configuration to the assistant application setup for both basic applications and advanced applications. This is a cross-cutting change because the assistant configuration UI, the assistant persistence contract, and the backend validation/runtime scope logic all need to agree on the same multi-select model.

Today the gap is not only missing fields in the form. The system also needs a consistent rule for how datasource choices are filtered by workspace choices, how saved selections are returned during edit flows, and how invalid historical selections are handled when workspace or datasource state changes later.

## Goals / Non-Goals

**Goals:**
- Add a shared assistant resource-selection model that works for both basic applications and advanced applications.
- Support selecting multiple workspaces and multiple datasources in create and edit flows.
- Ensure datasource candidates are constrained by the currently selected workspaces.
- Ensure assistant save/update APIs validate scope and persist the selected resources in a stable format.
- Ensure runtime assistant scope resolution consumes the saved workspace and datasource bindings consistently.

**Non-Goals:**
- Redesigning unrelated assistant authoring fields or publishing workflow.
- Introducing per-datasource custom prompt or permission rules in this change.
- Changing the platform-wide workspace or datasource ownership model.
- Defining tenant-wide auto-selection behavior when no workspace or datasource is configured.

## Decisions

### Decision 1: Use one shared resource-selection contract for both assistant application types

Basic applications and advanced applications will use the same underlying workspace/datasource selection structure rather than separate per-type schemas.

**Why:**
- The user-facing requirement is the same for both assistant types.
- A shared contract reduces drift between the two forms and makes validation/runtime behavior easier to keep consistent.

**Alternatives considered:**
- Separate schemas for basic and advanced applications: rejected because it would duplicate validation and make future assistant-scope behavior harder to reason about.

### Decision 2: Treat datasource selection as dependent on workspace selection

Datasource options will be derived from the selected workspaces, and save-time validation will reject datasources that do not belong to the chosen workspace scope.

**Why:**
- This matches the repository's workspace-level isolation model.
- It prevents assistants from being configured with cross-scope datasources that the selected workspace set does not authorize.

**Alternatives considered:**
- Allow independent datasource selection without workspace dependency: rejected because it weakens workspace boundary clarity and creates ambiguous runtime scope rules.

### Decision 3: Persist explicit selected IDs for both workspaces and datasources

The assistant configuration will store the selected workspace identifiers and datasource identifiers explicitly, and edit APIs will return those identifiers directly for form hydration.

**Why:**
- Explicit persistence makes edit flows deterministic.
- It avoids recomputing assistant scope from indirect rules that could change over time.

**Alternatives considered:**
- Persist only workspace IDs and derive datasources at runtime: rejected because it would not preserve an administrator's intended datasource subset.

### Decision 4: Reject invalid or stale selections during save instead of silently correcting them

If a submitted workspace or datasource is disabled, missing, or out of scope, the save/update request will fail with a validation error rather than auto-dropping the invalid selection.

**Why:**
- Silent correction hides configuration mistakes.
- Explicit failure keeps assistant scope auditable and predictable.

**Alternatives considered:**
- Auto-remove invalid selections on save: rejected because it can cause accidental assistant scope changes without operator awareness.

## Risks / Trade-offs

- **[Large workspace selections return too many datasource options]** → Constrain datasource queries to the selected workspace set and preserve existing pagination/search behavior if present.
- **[Basic and advanced application forms diverge in behavior after release]** → Centralize the contract and acceptance rules so both UI paths consume the same backend semantics.
- **[Historical assistants have no resource bindings]** → Treat this as a compatibility case in migration/rollout planning and keep existing assistants readable while only enforcing the new contract on edited or newly created records unless implementation proves safe for backfill.
- **[Workspace membership changes make stored datasource bindings stale]** → Revalidate bindings on every assistant update and surface clear validation errors for stale references.

## Migration Plan

1. Define the assistant resource-selection requirement in OpenSpec.
2. Update backend assistant configuration contracts and persistence to accept multi-select workspace and datasource IDs.
3. Update workspace-filtered datasource query behavior and save-time validation.
4. Update both basic-application and advanced-application forms to load, edit, and submit the new selections.
5. Verify create/edit behavior, stale-selection rejection, and runtime assistant scope consumption.

Rollback should remove the new assistant resource-selection fields from the save/load path and restore the previous assistant configuration contract. Existing assistant records created during rollout may need compatibility handling if persistence shape changes.

## Open Questions

- Should newly created assistants require at least one workspace and one datasource, or is an empty selection allowed as a draft state?
- If multiple workspaces are selected and the same datasource can appear through more than one association path, should the UI deduplicate by datasource ID or expose workspace-specific labels?
