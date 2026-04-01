## Context

The current datasource sync implementation is synchronous and request-bound. Large table selections trigger per-table remote metadata fetches and per-field local writes inside the request path, which makes 1000-table support incompatible with the desired user experience. Existing repo patterns are sufficient for a first version: backend already uses thread executors with scoped DB sessions for embeddings, chat already uses SSE framing conventions, and the frontend already has large-list virtualization plus stream/polling-capable request helpers.

The new design must avoid creating a generic task platform. It should stay scoped to datasource sync, remain rollout-safe behind a feature flag, and preserve a stable visible schema until a new sync successfully finalizes.

## Goals / Non-Goals

**Goals:**
- Add a datasource-scoped async sync job model with one active job per datasource.
- Move large sync execution off the request thread and make submission return quickly.
- Define durable state transitions, progress snapshots, and terminal summaries.
- Refactor schema sync internals to batch writes, reuse remote connections, and avoid per-field commits in the hot path.
- Keep the previous completed datasource schema visible until finalize succeeds.
- Add frontend UX for progress, recovery after refresh, and deterministic conflict/error handling.
- Roll out behind a default-off feature flag.

**Non-Goals:**
- Building a reusable cross-domain background job framework.
- Introducing Celery, Redis queues, or other new worker infrastructure in v1.
- Replacing all datasource CRUD flows with async behavior.
- Making SSE mandatory; polling-first support is sufficient for v1.
- Guaranteeing full 1000-table end-to-end completion within 30 seconds; v1 optimizes submission latency and execution safety first.

## Decisions

### 1. Use a DB-backed datasource sync job model
- **Decision**: Persist datasource sync jobs in the application database with status, counts, phase markers, timestamps, and terminal summaries.
- **Why**: This gives reload-safe recovery, deterministic single-active-job enforcement, and a durable source of truth for polling.
- **Alternatives considered**:
  - In-memory runner state only: rejected because it breaks on restart and cannot support recovery.
  - Generic task framework: rejected because it broadens scope and delays datasource-specific delivery.

### 2. Async submit is the default architecture for large syncs
- **Decision**: Large datasource syncs submit a job and return quickly; worker execution performs the heavy work out-of-band.
- **Why**: A 1000-table sync cannot safely live inside a single blocking HTTP request.
- **Alternatives considered**:
  - Keep synchronous path and just raise timeout: rejected because it remains brittle and unobservable.
  - Make every sync async immediately: rejected for rollout risk; v1 keeps flag-off fallback and threshold routing.

### 3. Finalize-only visibility
- **Decision**: Existing visible datasource schema remains authoritative until the new sync reaches finalize success. In-progress staged writes are not exposed to normal readers.
- **Why**: This avoids partial-state ambiguity and matches the need for safe retries/failures.
- **Alternatives considered**:
  - Incremental visible updates during sync: rejected because failed jobs would leave mixed schema state.

### 4. Polling-first progress, optional SSE enhancement
- **Decision**: Polling status endpoints are mandatory; SSE may be added as an enhancement using the existing chat event framing style.
- **Why**: Polling is simpler, durable, and sufficient for v1. SSE can reuse existing repo patterns without becoming a hard dependency.
- **Alternatives considered**:
  - SSE-only progress: rejected because polling remains the more robust baseline and easier to recover from refresh/re-entry.

### 5. Reuse repo-native thread execution with bounded concurrency
- **Decision**: Reuse the executor + scoped session pattern already used by embeddings, but add datasource-sync-specific worker limits and stale-run handling.
- **Why**: It matches current repo conventions and avoids introducing new infrastructure.
- **Alternatives considered**:
  - Celery/Redis queue: rejected for v1 scope and operational overhead.
  - Unlimited/background threads: rejected because current pool oversubscription is already a risk.

### 6. Refactor sync internals around phased execution
- **Decision**: Decompose execution into submit → introspect → stage/write → finalize → post-processing.
- **Why**: Restartable phase boundaries make progress durable and let failure/rollback rules stay clear.
- **Alternatives considered**:
  - Wrap existing `sync_table()` wholesale inside a background thread: rejected because it preserves the same scaling pathologies.

### 7. Feature-flagged rollout with small-sync fallback
- **Decision**: Default-off async flag plus backend-controlled threshold routing. Small syncs can continue to use the legacy path until rollout confidence is high.
- **Why**: This lowers migration risk and allows staged adoption.
- **Alternatives considered**:
  - Frontend-only threshold gating: rejected because policy must be backend-backed.

## Risks / Trade-offs

- **[Risk] Partial failure semantics may become confusing** → Mitigation: keep previous schema visible until finalize; define terminal summaries clearly.
- **[Risk] Duplicate submit races for the same datasource** → Mitigation: enforce one active job per datasource with deterministic conflict/dedupe behavior.
- **[Risk] Worker crashes can leave jobs stuck as running** → Mitigation: add stale-run reconciliation and restart-safe status ownership rules.
- **[Risk] Polling may increase status-query load** → Mitigation: bound update frequency and keep polling payloads compact.
- **[Risk] Embedding follow-up can still starve DB pools** → Mitigation: cap concurrency explicitly and decouple sync correctness from embedding follow-up success.
- **[Risk] Scope creep toward a generic platform** → Mitigation: keep all artifacts and tasks specific to datasource sync only.

## Migration Plan

1. Add sync job persistence model, migration, schemas, and feature flag default-off.
2. Introduce submit/status APIs and async worker runner under the feature flag.
3. Refactor schema sync internals to support batching, staging, finalize, and deferred post-processing.
4. Add frontend async progress workflow and recovery UX behind the same flag.
5. Validate flag-off legacy behavior and flag-on async behavior with automated tests.
6. Roll out gradually by enabling the flag only for targeted environments or datasources.

**Rollback strategy**:
- Immediate rollback is to keep the async feature flag off.
- If necessary, revert the async endpoints/UI branch while preserving dormant persistence for a later retry.
- If migration rollback is required before release, revert the sync-job migration and related model imports.

## Open Questions

- Whether v1 should expose explicit user-triggered cancellation in the UI, or only support terminal cancellation semantics in the backend.
- Whether per-table failure details should be stored in the main job row or a companion detail table when failures become large.
- Whether SSE should ship in v1 or remain a near-term follow-up after polling-first delivery stabilizes.
