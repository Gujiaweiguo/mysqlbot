## Context

The current codebase now has working but separately evolved embedding capabilities:

- `externalize-embedding-provider` introduced local/remote embedding provider routing.
- `embedding-admin-config-flow` introduced visual admin configuration, validation-before-enable, and runtime gating.

However, the current embedding model still exposes `remote` versus `local` at the configuration layer, while the AI model UI uses a supplier-driven interaction model based on `frontend/src/entity/supplier.ts`. At the same time, backend generation-model integrations are grouped by protocol/runtime type in `backend/apps/ai_model/model_factory.py`, not by UI supplier name. To avoid repeated structural change, the first rollout should be limited to the subset of suppliers that can plausibly share an OpenAI-compatible embeddings contract: 阿里云百炼, DeepSeek, 火山引擎, and 通用OpenAI.

The goal of this change is to define the final “one-shot” architecture so the system does not continue to accumulate partial embedding abstractions that later require structural rework.

## Goals / Non-Goals

**Goals:**
- Introduce a unified provider-type architecture for embeddings, beginning with a first rollout where supported suppliers normalize to `openai_compatible`.
- Keep the operator UX aligned with the current AI model page pattern: select supplier, choose/add model, then validate and enable.
- Preserve embedding as a singleton runtime state machine rather than a free-form model list.
- Define one migration path from the current `remote/local` config shape to the new provider-type structure.

**Non-Goals:**
- Build a full background reindex orchestration product in this change.
- Add every future supplier-specific adapter immediately if no embedding API contract is known yet.
- Implement Tencent-specific embedding support in the first rollout.
- Merge embedding config into the existing `AiModelDetail` table or generation model list.

## Decisions

### Decision 1: Use supplier-driven UX but protocol-driven backend routing

The frontend will follow the current supplier + model interaction style, but the backend will normalize that input into a smaller set of provider/runtime types.

**Why:**
- Users already understand supplier-based configuration from the generation model page.
- Backend integrations should remain grouped by actual protocol/runtime behavior, not by branding.

**Alternatives considered:**
- Mirror supplier names one-for-one as backend provider classes: rejected because many suppliers share OpenAI-compatible chat semantics while diverging for embeddings.

### Decision 2: Replace `remote/local` with `provider_type`

The persisted embedding configuration will use a provider-type structure, but the first rollout will support only:
- `openai_compatible`
- `local`

Each provider type owns its own configuration block.

**Why:**
- `remote` is too vague even in the first rollout, because supplier-driven UI still needs a normalized backend contract.
- A typed structure supports validation and runtime routing without more ad hoc conditionals.

**Alternatives considered:**
- Keep `remote/local` and add provider-specific special cases gradually: rejected because it guarantees repeated structural rework.

### Decision 3: Keep embedding lifecycle as a singleton state machine

Even though the UI interaction will resemble AI model configuration, embedding activation will remain a singleton lifecycle with explicit states: disabled, configured-unverified, validated-disabled, enabled, reindex-required, validation-failed.

**Why:**
- Embedding provider/model changes affect global vector compatibility and retrieval quality.
- Treating embeddings like independent model records would weaken operator safety.

**Alternatives considered:**
- Reuse the generation model list as-is: rejected because it hides system-wide activation and migration risk.

### Decision 4: First-rollout validation uses one generic OpenAI-compatible embedding contract

Validation will call the generic OpenAI-compatible embeddings contract for the supported remote supplier set in the first rollout, and a local probe for `local`.

**Why:**
- The user wants a one-shot architecture but also wants to avoid repeated structural change.
- Restricting the first rollout to suppliers that can share one remote protocol keeps the architecture coherent and reduces risk.

**Alternatives considered:**
- Include Tencent-specific validation in the first rollout: rejected because it broadens the first implementation and reintroduces protocol complexity immediately.

### Decision 5: Migrate old config transparently, write new config only

Reads will support the existing `remote/local` shape temporarily, but writes will persist only the new provider-type structure.

**Why:**
- This preserves operator continuity while converging to a final model.
- It avoids a big-bang manual config rewrite.

**Alternatives considered:**
- Hard-break old config immediately: rejected because it creates unnecessary migration pain.

## Risks / Trade-offs

- **[Unified change is broader than incremental fixes]** → Keep non-goals tight and avoid reindex job orchestration in the same scope.
- **[Supplier UX may imply all suppliers are equally supported for embeddings]** → Make the first supported supplier set explicit in both backend validation and UI messaging.
- **[Config migration bugs could create runtime mismatch]** → Centralize normalization in one backend conversion path.
- **[Trying to support too many suppliers too early]** → Freeze the first rollout to the four suppliers that share the OpenAI-compatible contract.

## Migration Plan

1. Introduce new provider-type schemas and normalization logic while still reading old config shape.
2. Implement runtime routing for `openai_compatible` and `local`.
3. Restrict the first supplier set to 阿里云百炼, DeepSeek, 火山引擎, and 通用OpenAI.
4. Replace the current embedding admin form with supplier-driven UX backed by provider-type normalization.
5. Persist only the new provider-type structure on save.
6. Verify runtime gating, validation behavior, and legacy-config compatibility.

Rollback is possible by keeping normalization support for the old shape and retaining the previous local/openai-compatible routing while disabling Tencent-specific selection if needed.

## Open Questions

- Should unsupported suppliers be shown as disabled with explanation, or hidden entirely in the first version?
- Should migration from old config happen silently on first save, or should the UI signal that the config structure has been upgraded?
