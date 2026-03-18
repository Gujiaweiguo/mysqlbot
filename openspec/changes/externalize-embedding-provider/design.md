## Context

The repository currently centralizes embedding creation in `backend/apps/ai_model/embedding.py`, where `EmbeddingModelCache` always instantiates `HuggingFaceEmbeddings` with a local model path. Startup invokes three background backfill flows from `backend/main.py`, and CRUD/update paths across terminology, data training, datasource, and table metadata call `EmbeddingModelCache.get_model()` to generate vectors.

Remote LLM generation is already modeled separately in `backend/apps/ai_model/model_factory.py`, so the architecture already distinguishes generation from embedding conceptually. The missing piece is that embedding execution is still hard-wired to a local HuggingFace runtime.

## Goals / Non-Goals

**Goals:**
- Introduce a first-class embedding provider abstraction with at least local and remote provider modes.
- Allow deployments to select remote embedding as the default path without carrying local torch/model runtime in the normal deployment contract.
- Keep existing embedding call sites working through a stable interface.
- Define a safe migration path for re-embedding stored vectors and retuning thresholds.
- Preserve a local provider option for offline/private deployments.

**Non-Goals:**
- Remove every HuggingFace dependency in the same change regardless of fallback needs.
- Redesign vector storage formats or retrieval algorithms beyond what provider abstraction requires.
- Change remote LLM provider behavior.
- Solve every quality-tuning question for every future embedding model in one pass.

## Decisions

### Decision 1: Add an explicit embedding provider layer

Create a provider abstraction that exposes the small interface the rest of the code actually needs (`embed_query`, `embed_documents`) and hides whether the implementation is local or remote.

**Why:**
- Existing embedding call sites are already fairly centralized around `EmbeddingModelCache.get_model()`.
- A provider seam minimizes churn in terminology/data-training/datasource modules.

**Alternatives considered:**
- Scattering provider checks across each embedding caller: rejected because it would duplicate selection/configuration logic.

### Decision 2: Keep local and remote providers side-by-side

Remote embedding should become the preferred deployment default, but the local provider should remain available as a supported fallback rather than being deleted immediately.

**Why:**
- Some deployments may still require offline or data-local embeddings.
- Keeping both modes reduces migration risk and simplifies rollback.

**Alternatives considered:**
- Hard cut directly to remote-only: rejected because it removes a practical fallback path and raises migration risk.

### Decision 3: Treat embedding model/provider changes as reindex events

Changing embedding provider or model must trigger an explicit re-embedding workflow for persisted vectors and a review of similarity thresholds.

**Why:**
- Mixing old local vectors with new remote vectors makes similarity behavior unreliable.
- Current thresholds were implicitly tuned for the local model and are not portable by default.

**Alternatives considered:**
- Allow mixed old/new vectors to coexist indefinitely: rejected because retrieval quality becomes undefined.

### Decision 4: Keep startup backfill but make its execution strategy configurable

Backfill flows should continue to exist, but the design must allow deployments to decide whether embedding backfill runs eagerly at startup, in background jobs, or through explicit operator action.

**Why:**
- Remote embeddings turn startup backfill into external API traffic bursts.
- Small deployments may prefer deferred or manual reindex behavior.

**Alternatives considered:**
- Preserve current eager startup behavior unconditionally: rejected because it is too costly and fragile for remote providers.

### Decision 5: Use an OpenAI-compatible embeddings API as the first remote contract

The first remote provider implementation will target an OpenAI-compatible embeddings API shape.

**Why:**
- It matches the broader direction of using external model services behind stable HTTP contracts.
- It is straightforward to adapt behind `embed_query` and `embed_documents` without adding another heavyweight SDK requirement.
- It leaves room to support additional provider-specific contracts later without changing the business-layer interface.

**Alternatives considered:**
- Provider-specific HTTP contracts first: rejected because they reduce portability and complicate the first implementation.
- Supporting multiple remote contracts in the first implementation: rejected because it increases surface area before the provider seam is proven.

## Risks / Trade-offs

- **[Provider abstraction hides provider-specific failure modes]** → Keep provider-specific diagnostics and configuration validation explicit.
- **[Remote embedding latency/cost can hurt startup and CRUD flows]** → Support deferred backfill and batch-oriented reindex workflows.
- **[Vector incompatibility after provider swap]** → Treat provider/model changes as reindex-required operations.
- **[Threshold drift can degrade retrieval quality]** → Re-evaluate `EMBEDDING_*_SIMILARITY` settings during migration.

## Migration Plan

1. Add provider abstraction and configuration fields without changing the default local behavior.
2. Implement a remote provider compatible with the target remote embedding service.
3. Route existing embedding writers and query-time embedding calls through the provider abstraction.
4. Add explicit reindex/backfill flow and operator documentation for provider/model changes.
5. Switch the recommended deployment default to remote embedding after validation.
6. Optionally de-emphasize or remove local torch from the default install path once remote embedding is proven in production.

Rollback is straightforward if both provider implementations remain available: switch configuration back to the local provider and re-run the local reindex path.

## Open Questions

- Should remote embedding backfill run at startup by default, or should startup only enqueue/recommend it?
- Do datasource/table embeddings need a separate batching path from terminology/data-training embeddings because of volume differences?
