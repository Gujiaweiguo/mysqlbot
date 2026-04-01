# Plan v1: Async Datasource Sync for 1000-Table Support

## TL;DR
> **Summary**: Replace large datasource table selection saves with a datasource-scoped async sync job that stages work durably, reports progress via polling-first APIs with optional SSE enhancement, and refactors sync internals to batch writes and reuse external connections.
> **Deliverables**:
> - DB-backed datasource sync job model and API contract
> - Refactored backend sync pipeline with batching/finalization rules
> - Frontend progress UX for large sync jobs
> - Feature-flagged rollout for async path
> - Automated verification for 1000-table-safe behavior
> **Effort**: XL
> **Parallel**: YES - 3 waves
> **Critical Path**: DSYNC-001 → DSYNC-002 → DSYNC-003 → DSYNC-004 → DSYNC-007 → DSYNC-009

## Context
### Original Request
Generate a single execution plan, saved under `.sisyphus/plans/*.md`, as the sole execution basis for Atlas/Hephaestus. The plan must include task IDs, inputs/outputs, acceptance criteria, rollback plans, dependency order, risk levels, a suggested change ID, and reflect the discussion that 1000-table support is desired with async preferred over long synchronous saves.

### Interview Summary
- Current `>30` table behavior is a frontend-only warning, not a backend limit.
- Current datasource save flow is synchronous and scales poorly because it performs per-table remote schema introspection and per-field writes/commits.
- 1000 selected tables is considered the target scale.
- A 30-second user experience target was stated.
- Async job submission with progress visibility is preferred over a long blocking save request.

### Metis Review (gaps addressed)
- Async job architecture is mandatory, not optional optimization.
- Plan must define datasource-level single-active-job semantics.
- Plan must define finalization/visibility rules to avoid partial-state ambiguity.
- Plan must remain scoped to datasource sync only, not a generic job platform.
- Polling must be first-class; SSE may be additive, not a hard dependency.
- Rollout must be feature-flagged and acceptance criteria must cover duplicate submit, restart recovery, and flag on/off behavior.

## Suggested Change ID
`improve-datasource-1000-table-async-sync`

## Work Objectives
### Core Objective
Enable reliable datasource table selection and schema sync at ~1000 selected tables by moving large syncs to a durable async job model with explicit progress, bounded resource usage, and feature-flagged rollout.

### Deliverables
- New datasource sync job persistence model, migration, enums, and API schemas
- Backend submit/status/stream/finalize orchestration for datasource sync jobs
- Refactored sync execution pipeline with batching, connection reuse, and bounded concurrency
- Frontend datasource sync UX with progress dialog/status recovery for async jobs
- Feature flag and compatibility behavior for small-vs-large sync entry
- Tests and evidence proving correctness, resilience, and rollout behavior

### Definition of Done (verifiable conditions with commands)
- Async datasource sync job models, API endpoints, and feature flag path are implemented and pass backend tests.
- Large table selection submits quickly without waiting for full schema sync completion.
- Progress/status can be recovered after page reload.
- Duplicate submit/conflict behavior is deterministic for the same datasource.
- Final visible datasource schema remains previous-complete state until finalize succeeds.
- `cd backend && uv run pytest tests/...` covering new sync-job scenarios passes.
- `cd backend && bash scripts/lint.sh` passes.
- `cd frontend && npm run typecheck && npm run build` passes.

### Must Have
- Polling-first progress contract
- Optional SSE enhancement sharing the chat event payload style
- One active sync job per datasource
- Durable phase/state tracking
- Batched DB writes and remote metadata connection reuse
- Explicit finalization semantics
- Feature flag default-off rollout

### Must NOT Have
- No generic multi-domain task center in v1
- No Celery/Dramatiq/Redis queue introduction in v1
- No silent partial visibility of half-synced schema rows
- No per-table engine creation or per-field commit in the hot path after refactor
- No frontend-only policy enforcement for large sync behavior

## Verification Strategy
> ZERO HUMAN INTERVENTION — all verification is agent-executed.
- Test decision: tests-after + existing `pytest`/frontend typecheck+build
- QA policy: Every task includes agent-executed scenarios
- Evidence: `.sisyphus/evidence/task-{N}-{slug}.{ext}`

## Execution Strategy
### Parallel Execution Waves
Wave 1: contract/foundation (`DSYNC-001` to `DSYNC-004`)
Wave 2: backend execution/refactor (`DSYNC-005` to `DSYNC-008`)
Wave 3: frontend UX/rollout/validation (`DSYNC-009` to `DSYNC-011`)

### Dependency Matrix (full, all tasks)
- `DSYNC-001` blocks `DSYNC-002`, `DSYNC-003`, `DSYNC-009`
- `DSYNC-002` blocks `DSYNC-004`, `DSYNC-005`, `DSYNC-006`
- `DSYNC-003` blocks `DSYNC-007`, `DSYNC-008`, `DSYNC-010`
- `DSYNC-004` blocks `DSYNC-005`, `DSYNC-007`, `DSYNC-009`
- `DSYNC-005` blocks `DSYNC-007`, `DSYNC-008`
- `DSYNC-006` blocks `DSYNC-008`, `DSYNC-011`
- `DSYNC-007` blocks `DSYNC-009`, `DSYNC-010`, `DSYNC-011`
- `DSYNC-008` blocks `DSYNC-010`, `DSYNC-011`
- `DSYNC-009` blocks `DSYNC-010`
- `DSYNC-010` blocks `DSYNC-011`

### Agent Dispatch Summary
- Wave 1 → 4 tasks → unspecified-high / deep / quick
- Wave 2 → 4 tasks → unspecified-high / deep
- Wave 3 → 3 tasks → visual-engineering / writing / unspecified-high

## Defaults Applied
- Visibility model: previously completed datasource schema remains visible until job finalize succeeds; in-progress staged data is not user-visible.
- Cancellation: v1 includes status model support for `cancelled` but no mid-table hard interruption requirement; cancellation stops future chunks and marks unfinished work cancelled.
- Progress transport: polling is required; SSE is optional enhancement if implementation cost stays low.
- Large-sync entry rule: feature flag on + selected tables above threshold routes to async submit path; threshold becomes backend-backed config/constant, not UI-only heuristic.

## TODOs
> Implementation + Test = ONE task. Never separate.
> EVERY task MUST have: Agent Profile + Parallelization + QA Scenarios.

- [ ] DSYNC-001. Lock async sync contract and rollout policy

  **Risk**: High
  **Depends On**: None
  **Inputs**:
  - Current datasource save entrypoints in `backend/apps/datasource/api/datasource.py`
  - Current frontend datasource form flows in `frontend/src/views/ds/DatasourceForm.vue`
  - This plan's defaults for visibility, single-job semantics, and polling-first progress
  **Outputs**:
  - Backend API/schema contract for submit/status/list/optional stream endpoints
  - Feature flag contract and threshold routing rule
  - Compatibility contract describing visible-state behavior during running job
  **What to do**:
  - Define new datasource sync job states (`pending/running/finalizing/succeeded/failed/cancelled`)
  - Define one-active-job-per-datasource behavior and duplicate-submit response
  - Define submission response payload, status payload, per-table summary payload, and recovery behavior after refresh
  - Define flag-off fallback path and flag-on threshold routing behavior
  **Must NOT do**:
  - Do not build a generic task framework
  - Do not make SSE mandatory for v1
  **Recommended Agent Profile**:
  - Category: `unspecified-high` — Reason: contract design across backend/frontend
  - Skills: `[]` — existing repo patterns are sufficient
  - Omitted: `openspec-propose` — not writing OpenSpec artifacts
  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: DSYNC-002, DSYNC-003, DSYNC-009 | Blocked By: None
  **References**:
  - Pattern: `backend/apps/datasource/api/datasource.py:133-172` — existing submit entrypoints to replace/branch
  - Pattern: `backend/apps/chat/streaming/events.py:7-26` — SSE payload style if stream endpoint added
  - Pattern: `frontend/src/utils/request.ts:348-371` — stream transport pattern
  - Pattern: `frontend/src/views/ds/DatasourceForm.vue:246-301` — current save flow and warning branch
  **Acceptance Criteria**:
  - [ ] Contract tests define exact response shape and conflict behavior for second submit on same datasource
  - [ ] Feature flag on/off behavior is codified in tests and docs/comments
  - [ ] Compatibility rule “previous complete schema remains visible until finalize” is encoded in backend test expectations
  **QA Scenarios**:
  ```
  Scenario: Submit contract success
    Tool: Bash
    Steps: Run targeted backend API tests covering large-sync submit and assert 202/accepted-style payload contract.
    Expected: Tests verify job id, datasource id, status, and recovery fields exactly.
    Evidence: .sisyphus/evidence/task-1-contract.txt

  Scenario: Duplicate submit conflict
    Tool: Bash
    Steps: Run targeted backend test submitting two large-sync requests for the same datasource.
    Expected: Second request returns deterministic conflict/dedupe behavior defined by contract.
    Evidence: .sisyphus/evidence/task-1-conflict.txt
  ```
  **Rollback**: Revert new contract/flag files and keep current synchronous `chooseTables` flow unchanged.
  **Commit**: YES | Message: `feat(datasource): define async sync contract` | Files: `backend/apps/datasource/**`, `frontend/src/api/**` as needed

- [ ] DSYNC-002. Add datasource sync job persistence model and migration

  **Risk**: High
  **Depends On**: DSYNC-001
  **Inputs**:
  - Contract from DSYNC-001
  - Existing SQLModel/Alembic conventions
  **Outputs**:
  - New sync job model/table(s), enums, indexes, and Alembic migration
  - Persistence helpers for status, counts, timestamps, and error details
  **What to do**:
  - Add datasource sync job SQLModel following datasource/log model conventions
  - Add indexes supporting lookup by datasource, status, created time, and active job checks
  - Add schemas for job summary/detail payloads
  - Add migration and register metadata imports required by Alembic
  **Must NOT do**:
  - Do not add queue infra or unrelated job tables
  - Do not store chatty per-row event logs unless required by acceptance criteria
  **Recommended Agent Profile**:
  - Category: `unspecified-high` — Reason: migration + persistence correctness
  - Skills: `[]`
  - Omitted: `visual-engineering` — backend-only task
  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: DSYNC-004, DSYNC-005, DSYNC-006 | Blocked By: DSYNC-001
  **References**:
  - Pattern: `backend/apps/datasource/models/datasource.py:10-82` — model conventions
  - Pattern: `backend/common/audit/models/log_model.py:9-34` — enum conventions
  - Pattern: `backend/alembic/versions/065_user_bind_var.py:1-29` — migration shape
  - Pattern: `backend/alembic/env.py:27-35` — metadata registration
  **Acceptance Criteria**:
  - [ ] Migration upgrades and downgrades cleanly in test environment
  - [ ] Model supports single-active-job query without full table scan in tests/index assertions
  - [ ] Status transitions and timestamp fields persist correctly in unit tests
  **QA Scenarios**:
  ```
  Scenario: Migration lifecycle
    Tool: Bash
    Steps: Run alembic upgrade test DB to head and downgrade one step around the new migration.
    Expected: Migration applies and reverts without schema errors.
    Evidence: .sisyphus/evidence/task-2-migration.txt

  Scenario: Active job uniqueness lookup
    Tool: Bash
    Steps: Run backend tests creating multiple jobs across datasources and asserting active-job query semantics.
    Expected: Only one active job per datasource is allowed by service logic and index-backed queries pass.
    Evidence: .sisyphus/evidence/task-2-uniqueness.txt
  ```
  **Rollback**: Revert model/schema/migration files; run migration rollback; remove imports.
  **Commit**: YES | Message: `feat(datasource): add sync job persistence` | Files: `backend/apps/datasource/models/**`, `backend/alembic/**`, `backend/apps/datasource/schemas/**`

- [ ] DSYNC-003. Extract sync engine primitives and batching rules

  **Risk**: High
  **Depends On**: DSYNC-001
  **Inputs**:
  - Current `sync_table`/`sync_fields` implementation
  - Existing executor/session patterns from embeddings
  **Outputs**:
  - Refactored service-layer primitives separating orchestration, remote metadata fetch, staging writes, finalize, and post-processing
  - Explicit batching rules and bounded concurrency constants
  **What to do**:
  - Split current sync path into restartable phases: snapshot request, introspect, stage writes, finalize, post-process
  - Remove per-field commit and per-table engine creation patterns from planned hot path
  - Define datasource-scoped worker/session lifecycle and remote connection reuse strategy
  **Must NOT do**:
  - Do not change visible behavior yet; this task prepares internal primitives/contracts
  - Do not trigger embeddings inline with request thread
  **Recommended Agent Profile**:
  - Category: `deep` — Reason: structural refactor with correctness constraints
  - Skills: `[]`
  - Omitted: `writing` — not a docs-only task
  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: DSYNC-007, DSYNC-008, DSYNC-010 | Blocked By: DSYNC-001
  **References**:
  - Pattern: `backend/apps/datasource/crud/datasource.py:451-585` — current sync hot path
  - Pattern: `backend/apps/db/db.py:545-728` — remote metadata fetch primitives
  - Pattern: `backend/common/utils/embedding_runtime.py:1-8` — thread-safe session pattern
  - Pattern: `backend/common/utils/embedding_threads.py:60-83` — background dispatch style
  **Acceptance Criteria**:
  - [ ] Internal service tests prove batch write helpers issue bounded commits instead of per-field commits
  - [ ] Remote metadata fetch helpers can reuse a single datasource connection/engine per job chunk in tests/mocks
  - [ ] Orchestration code exposes restartable phase boundaries without frontend coupling
  **QA Scenarios**:
  ```
  Scenario: Batched write path
    Tool: Bash
    Steps: Run backend unit tests asserting refactored sync helpers commit in batches, not per field.
    Expected: Tests pass and instrumentation/mocks show bounded commit count.
    Evidence: .sisyphus/evidence/task-3-batching.txt

  Scenario: Connection reuse path
    Tool: Bash
    Steps: Run backend unit tests with mocked external datasource engine/session factory across multiple tables.
    Expected: Tests confirm one reused connection/engine per chunk/job instead of per table.
    Evidence: .sisyphus/evidence/task-3-connreuse.txt
  ```
  **Rollback**: Restore original synchronous helper implementations from pre-refactor commit; remove unused extracted services.
  **Commit**: YES | Message: `refactor(datasource): extract batched sync primitives` | Files: `backend/apps/datasource/crud/**`, `backend/apps/db/**`, `backend/common/utils/**`

- [ ] DSYNC-004. Implement submit/status APIs and feature flag routing

  **Risk**: High
  **Depends On**: DSYNC-001, DSYNC-002
  **Inputs**:
  - Contract from DSYNC-001
  - Persistence from DSYNC-002
  **Outputs**:
  - Submit job endpoint, status/detail endpoint, list/recover endpoint, optional SSE endpoint scaffold
  - Feature-flagged routing from existing datasource save flow
  **What to do**:
  - Add backend APIs for submit and progress retrieval
  - Add datasource-level conflict handling when job already active
  - Branch existing `chooseTables`/create flows by threshold + feature flag
  - Keep current synchronous path only as flag-off fallback
  **Must NOT do**:
  - Do not force all saves async when flag is off
  - Do not expose partial staged rows through status endpoints
  **Recommended Agent Profile**:
  - Category: `unspecified-high` — Reason: API compatibility + rollout logic
  - Skills: `[]`
  - Omitted: `artistry` — no need for unconventional approach
  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: DSYNC-005, DSYNC-007, DSYNC-009 | Blocked By: DSYNC-001, DSYNC-002
  **References**:
  - Pattern: `backend/apps/datasource/api/datasource.py:133-172` — current save endpoints
  - Pattern: `backend/apps/api.py:37-65` — router registration
  - Pattern: `backend/apps/chat/api/chat.py:356-451` — optional stream endpoint style
  **Acceptance Criteria**:
  - [ ] API tests verify flag-off path preserves current synchronous behavior
  - [ ] API tests verify flag-on large-submit path returns job payload quickly without full sync completion
  - [ ] API tests verify status/detail endpoints hide staged rows and expose durable counts/state
  **QA Scenarios**:
  ```
  Scenario: Flag-off fallback
    Tool: Bash
    Steps: Run backend API tests with async flag disabled and submit below/above threshold table sets.
    Expected: Existing synchronous route remains active and tests assert legacy behavior.
    Evidence: .sisyphus/evidence/task-4-flagoff.txt

  Scenario: Flag-on async submit
    Tool: Bash
    Steps: Run backend API tests with async flag enabled for a large table set.
    Expected: Submit returns quickly with job identifier and running/pending state, without waiting for full sync.
    Evidence: .sisyphus/evidence/task-4-submit.txt
  ```
  **Rollback**: Disable flag and revert new routes; retain persistence for later reintroduction if necessary.
  **Commit**: YES | Message: `feat(datasource): add async sync endpoints` | Files: `backend/apps/datasource/api/**`, `backend/apps/api.py`, config files

- [ ] DSYNC-005. Build datasource-scoped async executor and job lifecycle runner

  **Risk**: High
  **Depends On**: DSYNC-002, DSYNC-004
  **Inputs**:
  - Sync job persistence
  - Submit API entrypoints
  **Outputs**:
  - Background runner for datasource sync jobs with durable status transitions
  - Single-active-job enforcement, stale-job recovery, restart-safe lifecycle handling
  **What to do**:
  - Add datasource sync executor/dispatcher using repo-native thread/session isolation pattern
  - Implement job lifecycle transitions, heartbeat or stale-run detection, and retry/restart-safe ownership rules
  - Ensure repeated submits reuse/reject active job according to contract
  **Must NOT do**:
  - Do not oversubscribe DB pools with uncontrolled worker counts
  - Do not mark succeeded before finalize and post-final checks complete
  **Recommended Agent Profile**:
  - Category: `deep` — Reason: concurrency and restart safety
  - Skills: `[]`
  - Omitted: `visual-engineering`
  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: DSYNC-007, DSYNC-008 | Blocked By: DSYNC-002, DSYNC-004
  **References**:
  - Pattern: `backend/common/utils/embedding_runtime.py:1-8` — executor/session isolation
  - Pattern: `backend/common/utils/embedding_threads.py:60-83` — dispatch wrappers
  - Pattern: `backend/tests/conftest.py:36-137` — backend test harness
  **Acceptance Criteria**:
  - [ ] Backend tests prove one active job per datasource across duplicate submits
  - [ ] Backend tests prove stale-running job recovery or safe failure marking after simulated worker interruption
  - [ ] Worker concurrency is bounded by explicit config/constant in code and tested
  **QA Scenarios**:
  ```
  Scenario: Duplicate submit while running
    Tool: Bash
    Steps: Run backend tests that start a job and immediately submit another for the same datasource.
    Expected: Second request is rejected or deduped exactly per contract, with no second active runner.
    Evidence: .sisyphus/evidence/task-5-duplicate.txt

  Scenario: Worker interruption recovery
    Tool: Bash
    Steps: Run backend tests simulating runner crash/interruption mid-job, then status reconciliation.
    Expected: Job becomes recoverable failed/stale state and does not remain falsely running forever.
    Evidence: .sisyphus/evidence/task-5-recovery.txt
  ```
  **Rollback**: Disable dispatcher path behind flag; keep submit/status API returning unsupported/legacy behavior.
  **Commit**: YES | Message: `feat(datasource): add sync job runner` | Files: `backend/common/utils/**`, `backend/apps/datasource/services/**`

- [ ] DSYNC-006. Add progress persistence, polling contract, and optional SSE event adapter

  **Risk**: Medium
  **Depends On**: DSYNC-002
  **Inputs**:
  - Job model/state machine
  - Repo chat SSE formatting patterns
  **Outputs**:
  - Durable progress-update mechanism with bounded write frequency
  - Polling response contract and optional SSE adapter consistent with chat events
 **What to do**:
  - Persist phase, completed/failed/skipped counts, current chunk/table markers, and terminal summaries
  - Add polling-friendly status snapshots as primary UX source
  - If implemented, add SSE event emission reusing chat payload formatting conventions
 **Must NOT do**:
  - Do not write progress for every field mutation
  - Do not make frontend rely on ephemeral in-memory runner state
  **Recommended Agent Profile**:
  - Category: `unspecified-high` — Reason: API/state observability contract
  - Skills: `[]`
  - Omitted: `writing`
  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: DSYNC-008, DSYNC-011 | Blocked By: DSYNC-002
  **References**:
  - Pattern: `backend/apps/chat/streaming/events.py:7-26` — event payload format
  - Pattern: `backend/apps/chat/orchestration/runtime.py:39-42` — streaming response wrapper
  - Pattern: `frontend/src/views/chat/composables/useChatStream.ts:1-77` — stream consumer expectations
  **Acceptance Criteria**:
  - [ ] Status endpoint tests verify durable counts for queued/running/succeeded/failed/cancelled work
  - [ ] Progress persistence frequency is bounded and validated in tests
  - [ ] Optional SSE endpoint, if included, emits event payloads parsable by existing stream utility style
  **QA Scenarios**:
  ```
  Scenario: Polling progress snapshot
    Tool: Bash
    Steps: Run backend tests advancing job phases and polling status endpoint between transitions.
    Expected: Responses expose durable state/counts without leaking staged schema rows.
    Evidence: .sisyphus/evidence/task-6-polling.txt

  Scenario: SSE progress compatibility
    Tool: Bash
    Steps: Run backend tests against optional stream endpoint and assert `data:{json}\n\n` event framing.
    Expected: Stream output matches chat SSE framing conventions.
    Evidence: .sisyphus/evidence/task-6-sse.txt
  ```
  **Rollback**: Keep polling endpoint only and remove SSE adapter; retain stored progress columns.
  **Commit**: YES | Message: `feat(datasource): add sync progress reporting` | Files: `backend/apps/datasource/api/**`, `backend/apps/datasource/services/**`

- [ ] DSYNC-007. Refactor schema sync execution for batching, staging, finalize, and cleanup

  **Risk**: High
  **Depends On**: DSYNC-003, DSYNC-004, DSYNC-005
  **Inputs**:
  - Extracted primitives from DSYNC-003
  - Job orchestration and API contract
  **Outputs**:
  - End-to-end async sync execution path honoring staging/finalization rules
  - Batched table/field writes, remote metadata connection reuse, and deferred cleanup/finalize behavior
  **What to do**:
  - Implement actual worker execution for table discovery snapshot, per-chunk introspection, batched writes, finalize swap/visibility, and cleanup
  - Ensure previous complete schema remains visible until finalize succeeds
  - Define handling for table-level failures: fail whole job or record failed subset per contract; do not silently continue ambiguously
  - Trigger post-finalization embedding only after schema finalize succeeds
  **Must NOT do**:
  - Do not expose half-written schema to normal readers
  - Do not keep legacy per-field commit path under async route
  **Recommended Agent Profile**:
  - Category: `deep` — Reason: core correctness-critical refactor
  - Skills: `[]`
  - Omitted: `quick`
  **Parallelization**: Can Parallel: NO | Wave 2 | Blocks: DSYNC-009, DSYNC-010, DSYNC-011 | Blocked By: DSYNC-003, DSYNC-004, DSYNC-005
  **References**:
  - Pattern: `backend/apps/datasource/crud/datasource.py:451-585` — legacy logic to replace
  - Pattern: `backend/apps/datasource/crud/datasource.py:750-769` — datasource selected count updates
  - Pattern: `backend/apps/datasource/crud/table.py:75-237` — post-sync embedding hooks
  - API/Type: `backend/apps/datasource/api/datasource.py:155-172` — submit path currently used by frontend
  **Acceptance Criteria**:
  - [ ] Integration tests verify previous schema stays visible while job runs and only updates after finalize success
  - [ ] Integration tests verify failure path leaves prior visible schema intact and marks job terminal state correctly
  - [ ] Integration tests verify embedding dispatch occurs only after finalize success
  **QA Scenarios**:
  ```
  Scenario: Finalize visibility protection
    Tool: Bash
    Steps: Run backend integration test starting a sync job, read datasource schema during running phase, then after finalize.
    Expected: Pre-finalize reads show previous schema; post-finalize reads show new schema.
    Evidence: .sisyphus/evidence/task-7-finalize.txt

  Scenario: Mid-job table failure
    Tool: Bash
    Steps: Run backend integration test injecting one failing table during async sync.
    Expected: Job ends in defined failed/partial-failed terminal state and previous visible schema remains intact.
    Evidence: .sisyphus/evidence/task-7-failure.txt
  ```
  **Rollback**: Disable async route via flag and preserve legacy synchronous sync while keeping job plumbing dormant.
  **Commit**: YES | Message: `feat(datasource): implement staged async schema sync` | Files: `backend/apps/datasource/crud/**`, `backend/apps/datasource/services/**`

- [ ] DSYNC-008. Bound post-sync embedding and operational safeguards

  **Risk**: Medium
  **Depends On**: DSYNC-003, DSYNC-005, DSYNC-006
  **Inputs**:
  - Existing embedding executor
  - Async sync lifecycle rules
  **Outputs**:
  - Safe post-finalization embedding dispatch with bounded worker counts and observability hooks
  - Explicit timeout/retry/failure linkage between sync job and embedding follow-up
  **What to do**:
  - Reduce or parameterize embedding concurrency to avoid DB pool starvation
  - Ensure sync job terminal state records whether embedding follow-up succeeded, failed, or was deferred
  - Preserve datasource sync correctness even if embedding follow-up fails
  **Must NOT do**:
  - Do not couple sync job success solely to embedding success unless contract says so
  - Do not leave 200-thread oversubscription unbounded
  **Recommended Agent Profile**:
  - Category: `unspecified-high` — Reason: operational tuning and correctness boundaries
  - Skills: `[]`
  - Omitted: `visual-engineering`
  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: DSYNC-010, DSYNC-011 | Blocked By: DSYNC-003, DSYNC-005, DSYNC-006
  **References**:
  - Pattern: `backend/common/utils/embedding_runtime.py:1-8` — current executor and session maker
  - Pattern: `backend/common/utils/embedding_threads.py:60-83` — dispatch helper style
  - Pattern: `backend/apps/datasource/crud/table.py:75-237` — embedding functions and commit points
  **Acceptance Criteria**:
  - [ ] Tests prove embedding worker count is bounded by explicit config/constant
  - [ ] Tests prove sync job remains terminally correct even when embedding follow-up fails
  - [ ] No connection-pool starvation regression is introduced in targeted tests/mocks
  **QA Scenarios**:
  ```
  Scenario: Embedding failure after finalize
    Tool: Bash
    Steps: Run backend test with forced embedding error after successful schema finalize.
    Expected: Schema remains finalized; job/follow-up status records embedding failure without corrupting sync result.
    Evidence: .sisyphus/evidence/task-8-embedfail.txt

  Scenario: Bounded worker configuration
    Tool: Bash
    Steps: Run backend unit test asserting configured sync/embedding worker limits remain below DB pool exhaustion assumptions.
    Expected: Tests pass with explicit worker-limit constants.
    Evidence: .sisyphus/evidence/task-8-workers.txt
  ```
  **Rollback**: Restore prior embedding dispatch settings and decouple from job status linkage.
  **Commit**: YES | Message: `feat(datasource): harden post-sync embedding` | Files: `backend/common/utils/**`, `backend/apps/datasource/crud/table.py`

- [ ] DSYNC-009. Add frontend async sync workflow and recoverable progress UI

  **Risk**: High
  **Depends On**: DSYNC-001, DSYNC-004, DSYNC-007
  **Inputs**:
  - Backend submit/status contract
  - Existing datasource form and FixedSizeList table selection UI
  **Outputs**:
  - Frontend async submit flow, progress dialog/panel, conflict/recovery handling, and success/failure summaries
  **What to do**:
  - Update datasource save flow to branch to async submit path when feature flag + threshold match
  - Add progress UI using polling-first contract and repo-consistent loading/message patterns
  - Recover active job status when user reloads or reopens datasource screen
  - Reuse FixedSizeList for 1000-table selection rendering; do not regress existing selection UX
  **Must NOT do**:
  - Do not rely on endless spinner-only UX
  - Do not hide terminal failure details
  **Recommended Agent Profile**:
  - Category: `visual-engineering` — Reason: frontend workflow and progress UX
  - Skills: `[]`
  - Omitted: `openspec-apply-change`
  **Parallelization**: Can Parallel: NO | Wave 3 | Blocks: DSYNC-010 | Blocked By: DSYNC-001, DSYNC-004, DSYNC-007
  **References**:
  - Pattern: `frontend/src/views/ds/DatasourceForm.vue:246-301` — current save flow + warnings
  - Pattern: `frontend/src/views/ds/DatasourceForm.vue:797-817` — large-list virtualization
  - Pattern: `frontend/src/utils/request.ts:348-371` — optional streaming transport
  - Pattern: `frontend/src/views/chat/composables/useChatStream.ts:1-77` — stream consumer style
  - Pattern: `frontend/src/views/system/excel-upload/UploaderRemark.vue:81-101` — partial success/result summary pattern
  **Acceptance Criteria**:
  - [ ] Frontend tests/QA verify large sync submit returns control immediately and shows recoverable progress UI
  - [ ] Refresh/reopen restores in-progress job status without duplicate submission
  - [ ] Success and failure summaries surface counts and per-table failure access points defined by contract
  **QA Scenarios**:
  ```
  Scenario: Large sync submit UI
    Tool: interactive_bash
    Steps: Start frontend dev app, open datasource form, select mock large-table fixture, click save under async-enabled threshold rule.
    Expected: Save returns quickly, progress UI appears, and datasource form is not frozen behind a spinner-only state.
    Evidence: .sisyphus/evidence/task-9-ui.txt

  Scenario: Refresh recovery
    Tool: interactive_bash
    Steps: Begin async sync, reload the page, reopen datasource screen.
    Expected: UI rehydrates current job status instead of submitting a second job or showing no state.
    Evidence: .sisyphus/evidence/task-9-recovery.txt
  ```
  **Rollback**: Revert frontend to legacy synchronous save flow while keeping backend flag off.
  **Commit**: YES | Message: `feat(frontend): add datasource sync progress workflow` | Files: `frontend/src/views/ds/**`, `frontend/src/api/datasource.ts`, i18n files

- [ ] DSYNC-010. Add full contract, integration, and resilience test matrix

  **Risk**: Medium
  **Depends On**: DSYNC-003, DSYNC-007, DSYNC-008, DSYNC-009
  **Inputs**:
  - Implemented backend/frontend behavior
  - Metis-required edge cases
  **Outputs**:
  - Backend and frontend automated coverage for submit, duplicate submit, stale job recovery, visibility rules, flag on/off, and large-list UX
  **What to do**:
  - Add pytest suites for job creation, state transitions, duplicate submit, stale-job reconciliation, failure semantics, and visibility/finalize guarantees
  - Add frontend tests where available and mandatory typecheck/build coverage
  - Add targeted fixtures/mocks for large-table and failing-table scenarios
  **Must NOT do**:
  - Do not rely on manual-only validation
  - Do not skip failure-path coverage
  **Recommended Agent Profile**:
  - Category: `unspecified-high` — Reason: broad verification matrix
  - Skills: `[]`
  - Omitted: `artistry`
  **Parallelization**: Can Parallel: YES | Wave 3 | Blocks: DSYNC-011 | Blocked By: DSYNC-003, DSYNC-007, DSYNC-008, DSYNC-009
  **References**:
  - Test: `backend/tests/conftest.py:36-137` — fixtures and auth harness
  - Pattern: `backend/tests/test_startup_smoke.py` — current smoke style for new behavior checks
  - Pattern: `frontend/src/views/chat/**` — stream consumer logic reference if SSE path is added
  **Acceptance Criteria**:
  - [ ] Named tests exist for each mandated edge case from Metis review
  - [ ] `bash scripts/lint.sh`, targeted pytest suites, `npm run typecheck`, and `npm run build` all pass
  - [ ] Test evidence includes both polling and feature-flag on/off scenarios
  **QA Scenarios**:
  ```
  Scenario: Full backend matrix
    Tool: Bash
    Steps: Run targeted pytest modules covering submit, status, duplicate submit, recovery, finalize visibility, and embedding follow-up failure.
    Expected: All targeted tests pass.
    Evidence: .sisyphus/evidence/task-10-backend.txt

  Scenario: Frontend build matrix
    Tool: Bash
    Steps: Run `npm run typecheck` and `npm run build` in `frontend` after UI changes.
    Expected: Typecheck and production build pass with no new errors.
    Evidence: .sisyphus/evidence/task-10-frontend.txt
  ```
  **Rollback**: Revert failing test scaffolds only if they block merge after implementation logic is reverted; otherwise keep tests aligned with shipped behavior.
  **Commit**: YES | Message: `test(datasource): cover async sync resilience` | Files: `backend/tests/**`, `frontend/**` if frontend tests added

- [ ] DSYNC-011. Rollout guardrails, observability, and operational documentation-in-code

  **Risk**: Medium
  **Depends On**: DSYNC-006, DSYNC-007, DSYNC-008, DSYNC-010
  **Inputs**:
  - Final backend/frontend implementation
  - Feature flag strategy
  **Outputs**:
  - Final config defaults, rollout guardrails, operator-facing comments/constants, and evidence bundle for staged enablement
  **What to do**:
  - Finalize default-off flag, threshold constant/config, concurrency caps, stale-job timeout, and polling cadence constants
  - Add concise code comments where hidden control-flow or safety assumptions exist
  - Document rollout steps inside repo-adjacent code/config comments sufficient for implementers/operators
  **Must NOT do**:
  - Do not add broad docs-site work outside touched code/config unless required
  - Do not turn feature flag on by default in v1
  **Recommended Agent Profile**:
  - Category: `writing` — Reason: guardrails and operational clarity
  - Skills: `[]`
  - Omitted: `visual-engineering`
  **Parallelization**: Can Parallel: NO | Wave 3 | Blocks: None | Blocked By: DSYNC-006, DSYNC-007, DSYNC-008, DSYNC-010
  **References**:
  - Pattern: `backend/main.py` startup guard comments — concise control-flow documentation style
  - Pattern: `frontend/src/i18n/*.json` — user-facing copy conventions
  - Pattern: existing config/constants near embedding/runtime modules
  **Acceptance Criteria**:
  - [ ] Flag remains default-off and is validated by tests
  - [ ] All rollout-critical constants are centralized and referenced by tests
  - [ ] Evidence bundle demonstrates how staged enablement can be validated without code changes
  **QA Scenarios**:
  ```
  Scenario: Default-off rollout validation
    Tool: Bash
    Steps: Run backend/frontend tests with feature flag disabled and verify legacy path remains valid.
    Expected: Legacy path still works and new async UI path stays inactive.
    Evidence: .sisyphus/evidence/task-11-flagdefault.txt

  Scenario: Opt-in rollout validation
    Tool: Bash
    Steps: Run targeted tests with feature flag enabled and threshold exceeded.
    Expected: Async path activates with configured polling cadence and concurrency limits.
    Evidence: .sisyphus/evidence/task-11-rollout.txt
  ```
  **Rollback**: Keep flag disabled and revert config/constant changes if rollout safety assumptions prove wrong.
  **Commit**: YES | Message: `chore(datasource): finalize async sync rollout guardrails` | Files: config/constants/comments/tests

## Final Verification Wave (MANDATORY — after ALL implementation tasks)
> 4 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.
> **Do NOT auto-proceed after verification. Wait for user's explicit approval before marking work complete.**
> **Never mark F1-F4 as checked before getting user's okay.** Rejection or user feedback -> fix -> re-run -> present again -> wait for okay.
- [ ] F1. Plan Compliance Audit — oracle
- [ ] F2. Code Quality Review — unspecified-high
- [ ] F3. Real Manual QA — unspecified-high (+ playwright if UI)
- [ ] F4. Scope Fidelity Check — deep

## Commit Strategy
- Use small atomic commits aligned to the task groups below.
- Preferred sequence:
  1. `feat(datasource): add sync job contract and flag scaffolding`
  2. `feat(datasource): refactor async sync execution pipeline`
  3. `feat(frontend): add datasource sync progress workflow`
  4. `test(datasource): cover async sync rollout and recovery`

## Success Criteria
- Submit request for large sync returns quickly and deterministically.
- Same datasource cannot run overlapping sync jobs.
- Failed jobs do not corrupt visible datasource schema.
- 1000-table scenario is supported through async workflow with observable progress and recoverable status.
- Repo quality gates pass and rollout is protected by feature flag.
