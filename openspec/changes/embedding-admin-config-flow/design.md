## Context

The repository now supports local and remote embedding providers at the infrastructure layer, but the operator workflow is still environment-driven. Existing visual model administration under `frontend/src/views/system/model` and `backend/apps/system/api/aimodel.py` is designed for managing multiple generation-model records, not for managing a single system-level embedding state machine.

Embedding behavior has broader operational consequences than generation-model edits: it affects terminology lookup, data-training retrieval, datasource selection, table selection, startup backfill, and vector compatibility after provider/model changes. Because of that, the system needs a safer configuration lifecycle than a simple save form.

## Goals / Non-Goals

**Goals:**
- Add a visual embedding configuration flow that lets administrators edit provider settings without editing environment variables directly.
- Make embedding **disabled by default** at the product level until configuration validation succeeds.
- Separate configuration save, configuration validation, and embedding enablement into explicit state transitions.
- Warn operators when provider/model changes imply re-embedding or threshold review.
- Reuse existing admin-page patterns where practical, while keeping embedding configuration modeled as a system-level singleton workflow.

**Non-Goals:**
- Build a full background reindex orchestration UI in the first version.
- Support multiple active embedding providers at the same time.
- Replace the existing generation model list UI.
- Solve every post-migration retrieval quality issue in the same change.

## Decisions

### Decision 1: Model embedding config as a singleton admin workflow, not a model list

Embedding configuration will be treated as one system-level configuration record with lifecycle state, rather than as one more item in the generation model list.

**Why:**
- Operators choose one active embedding provider/model at a time.
- Embedding enablement has global impact across retrieval and backfill paths.

**Alternatives considered:**
- Reusing the generation model list one-for-one: rejected because list semantics do not express global activation state or reindex risk cleanly.

### Decision 2: Saving config does not enable embeddings

The workflow will explicitly separate:
- save configuration
- validate configuration
- enable embeddings

**Why:**
- A syntactically saved configuration can still be unusable.
- Enabling embedding with an invalid provider would degrade multiple downstream flows.

**Alternatives considered:**
- Auto-enable on save: rejected because it couples persistence to runtime activation unsafely.

### Decision 3: Default product state is disabled until validation succeeds

The admin flow will treat embedding as disabled until the currently saved configuration has passed validation.

**Why:**
- This creates an explicit safety gate for remote/local provider misconfiguration.
- It avoids a false sense that “configured” means “working.”

**Alternatives considered:**
- Enabled by default with warning banners only: rejected because warnings alone are too weak given the blast radius.

### Decision 4: Provider/model edits can force a reindex-required state

Changing provider, model, or key connection settings will move the system into a cautionary state that signals re-embedding risk.

**Why:**
- Existing vectors may no longer be semantically compatible.
- Thresholds may need review.

**Alternatives considered:**
- Assume changes are safe and keep the enabled state untouched: rejected because it hides a real operational risk.

### Decision 5: Validation should test the real provider contract, not just field presence

Validation must perform a real provider-specific probe, such as generating a tiny embedding against the selected provider.

**Why:**
- Field presence alone does not prove the provider is reachable or the model ID is valid.

**Alternatives considered:**
- Static config validation only: rejected because it is insufficient for safe enablement.

## Risks / Trade-offs

- **[Operators may confuse configured state with enabled state]** → Show explicit lifecycle state and separate actions for validate/enable.
- **[Validation may pass once but become stale later]** → Mark provider/model edits as invalidating prior verification.
- **[UI complexity grows if reindex orchestration is added too early]** → Keep first version focused on config, validation, enable/disable, and warnings only.
- **[Backend env defaults and admin state can diverge]** → Define precedence clearly between persisted admin config and environment bootstrap defaults.

## Migration Plan

1. Add backend persistence and API surface for a singleton embedding configuration state.
2. Add provider validation API that exercises the selected provider.
3. Build frontend admin flow that saves config, validates config, and gates enablement.
4. Add runtime behavior so embedding-aware paths respect the enabled/disabled state.
5. Add operator messaging for reindex-required scenarios after provider/model edits.

Rollback is straightforward: keep embedding disabled and continue operating with non-embedding paths while reverting to environment-only management if necessary.

## Open Questions

- Should the visual flow live as a new page under system settings or as a tab beside the existing model page?
- Should enablement be blocked only by validation, or also by explicit operator acknowledgement of reindex risk?
- Should the first version expose startup backfill policy changes in the same page, or keep that as advanced settings?
