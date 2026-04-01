## 1. Contract and Foundation

- [x] 1.1 DSYNC-001 Lock async sync contract and rollout policy
  - **Dependencies**: None
  - **Risk**: High
  - **Inputs**: Current datasource save entrypoints; current datasource form save flow; Plan v1 defaults for visibility, single-job semantics, and polling-first progress.
  - **Outputs**: Backend API/schema contract for submit/status/list/optional stream endpoints; feature flag contract and threshold rule; compatibility contract for visible-state behavior during running jobs.
  - **Acceptance**: Contract tests define exact response shape and duplicate-submit behavior; feature flag on/off behavior is codified; previous schema visibility until finalize is encoded in backend tests.
  - **Rollback**: Revert new contract/flag files and keep current synchronous `chooseTables` flow unchanged.

- [x] 1.2 DSYNC-002 Add datasource sync job persistence model and migration
  - **Dependencies**: DSYNC-001
  - **Risk**: High
  - **Inputs**: DSYNC-001 contract; existing SQLModel/Alembic conventions.
  - **Outputs**: Sync job model/table(s), enums, indexes, Alembic migration, and persistence helpers for status/counts/timestamps/errors.
  - **Acceptance**: Migration upgrades/downgrades cleanly; single-active-job lookup is test-covered; status transitions and timestamps persist correctly in unit tests.
  - **Rollback**: Revert model/schema/migration files, run migration rollback, and remove metadata imports.

- [x] 1.3 DSYNC-003 Extract sync engine primitives and batching rules
  - **Dependencies**: DSYNC-001
  - **Risk**: High
  - **Inputs**: Current `sync_table`/`sync_fields` implementation; existing executor/session patterns from embeddings.
  - **Outputs**: Service-layer primitives for orchestration, remote metadata fetch, staging writes, finalize, and post-processing; explicit batching rules and bounded concurrency constants.
  - **Acceptance**: Tests prove bounded commit count instead of per-field commits; remote metadata helpers reuse datasource connection/engine resources; orchestration exposes restartable phase boundaries.
  - **Rollback**: Restore original synchronous helper implementations and remove unused extracted services.

- [x] 1.4 DSYNC-004 Implement submit/status APIs and feature flag routing
  - **Dependencies**: DSYNC-001, DSYNC-002
  - **Risk**: High
  - **Inputs**: DSYNC-001 contract; DSYNC-002 persistence.
  - **Outputs**: Submit endpoint, status/detail endpoint, list/recover endpoint, optional SSE endpoint scaffold, and feature-flagged routing from existing datasource save flow.
  - **Acceptance**: Flag-off path preserves current synchronous behavior; flag-on large-submit path returns job payload quickly; status/detail endpoints hide staged rows and expose durable counts/state.
  - **Rollback**: Disable flag and revert new routes; keep persistence for later reintroduction if necessary.

## 2. Backend Execution and Safeguards

- [x] 2.1 DSYNC-005 Build datasource-scoped async executor and job lifecycle runner
  - **Dependencies**: DSYNC-002, DSYNC-004
  - **Risk**: High
  - **Inputs**: Sync job persistence; submit API entrypoints.
  - **Outputs**: Background runner for datasource sync jobs with durable status transitions, single-active-job enforcement, and stale-job recovery.
  - **Acceptance**: Tests prove one active job per datasource; stale-running jobs are recovered or safely failed; worker concurrency is explicitly bounded and tested.
  - **Rollback**: Disable dispatcher path behind flag and keep submit/status API returning unsupported or legacy behavior.

- [x] 2.2 DSYNC-006 Add progress persistence, polling contract, and optional SSE event adapter
  - **Dependencies**: DSYNC-002
  - **Risk**: Medium
  - **Inputs**: Job model/state machine; chat SSE formatting patterns.
  - **Outputs**: Durable progress-update mechanism with bounded write frequency; polling response contract; optional SSE adapter aligned to chat event framing.
  - **Acceptance**: Status endpoint tests verify durable counts for queued/running/succeeded/failed/cancelled work; progress write frequency is bounded; optional SSE endpoint emits parseable event payloads.
  - **Rollback**: Keep polling endpoint only and remove SSE adapter while retaining stored progress columns.

- [x] 2.3 DSYNC-007 Refactor schema sync execution for batching, staging, finalize, and cleanup
  - **Dependencies**: DSYNC-003, DSYNC-004, DSYNC-005
  - **Risk**: High
  - **Inputs**: Extracted primitives; job orchestration and API contract.
  - **Outputs**: End-to-end async sync execution path with batched table/field writes, remote metadata connection reuse, finalize-only publication, and deferred cleanup behavior.
  - **Acceptance**: Integration tests verify previous schema remains visible while job runs; failure preserves prior visible schema; embedding dispatch occurs only after finalize success.
  - **Rollback**: Disable async route via flag and preserve legacy synchronous sync while keeping job plumbing dormant.

- [x] 2.4 DSYNC-008 Bound post-sync embedding and operational safeguards
  - **Dependencies**: DSYNC-003, DSYNC-005, DSYNC-006
  - **Risk**: Medium
  - **Inputs**: Existing embedding executor; async sync lifecycle rules.
  - **Outputs**: Safe post-finalization embedding dispatch with bounded worker counts and explicit timeout/retry/failure linkage.
  - **Acceptance**: Tests prove embedding worker count is bounded; sync job remains terminally correct even when embedding follow-up fails; no connection-pool starvation regression is introduced.
  - **Rollback**: Restore prior embedding dispatch settings and decouple embedding follow-up from job status linkage.

## 3. Frontend, Validation, and Rollout

- [x] 3.1 DSYNC-009 Add frontend async sync workflow and recoverable progress UI
  - **Dependencies**: DSYNC-001, DSYNC-004, DSYNC-007
  - **Risk**: High
  - **Inputs**: Backend submit/status contract; existing datasource form and FixedSizeList selection UI.
  - **Outputs**: Frontend async submit flow, progress dialog/panel, conflict/recovery handling, and success/failure summaries.
  - **Acceptance**: Large sync submit returns control immediately and shows recoverable progress UI; refresh/reopen restores job status without duplicate submission; terminal summaries surface counts and failure access points.
  - **Rollback**: Revert frontend to legacy synchronous save flow while keeping backend flag off.

- [x] 3.2 DSYNC-010 Add full contract, integration, and resilience test matrix
  - **Dependencies**: DSYNC-003, DSYNC-007, DSYNC-008, DSYNC-009
  - **Risk**: Medium
  - **Inputs**: Implemented backend/frontend behavior; Metis-required edge cases.
  - **Outputs**: Backend and frontend automated coverage for submit, duplicate submit, stale job recovery, visibility rules, flag on/off, and large-list UX.
  - **Acceptance**: Named tests exist for mandated edge cases; `bash scripts/lint.sh`, targeted pytest suites, `npm run typecheck`, and `npm run build` pass; evidence includes polling and feature-flag on/off scenarios.
  - **Rollback**: Revert failing test scaffolds only if logic changes are reverted; otherwise keep tests aligned with shipped behavior.

- [x] 3.3 DSYNC-011 Rollout guardrails, observability, and operational documentation-in-code
  - **Dependencies**: DSYNC-006, DSYNC-007, DSYNC-008, DSYNC-010
  - **Risk**: Medium
  - **Inputs**: Final backend/frontend implementation; feature flag strategy.
  - **Outputs**: Default-off flag, centralized threshold/concurrency/polling constants, concise rollout comments, and evidence bundle for staged enablement.
  - **Acceptance**: Flag remains default-off and is validated by tests; rollout-critical constants are centralized and referenced by tests; evidence demonstrates staged enablement without code changes.
  - **Rollback**: Keep flag disabled and revert config/constant changes if rollout safety assumptions prove wrong.
