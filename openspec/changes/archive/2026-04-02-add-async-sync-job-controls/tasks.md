## 1. API and job-state controls

- [x] 1.1 Add backend cancel endpoint for datasource sync jobs in `backend/apps/datasource/api/datasource.py`
- [x] 1.2 Add backend retry endpoint for datasource sync jobs in `backend/apps/datasource/api/datasource.py`
- [x] 1.3 Add CRUD helpers to validate cancelable vs retryable job states and return deterministic errors for invalid requests

## 2. Runtime cancellation and retry behavior

- [x] 2.1 Teach `sync_job_runtime.py` to cooperatively stop cancelled jobs at safe execution boundaries before publish
- [x] 2.2 Ensure cancelled and retried flows preserve schema visibility guarantees and never publish partial work
- [x] 2.3 Implement retry by creating a new job from the source job's stored `requested_tables` while preserving the one-active-job-per-datasource rule

## 3. Tests

- [x] 3.1 Add contract tests for cancel and retry terminal-state rules
- [x] 3.2 Add runner / runtime tests for cooperative cancellation and retry behavior
- [x] 3.3 Add visibility tests proving cancelled jobs do not publish staged schema
- [x] 3.4 Run targeted async-sync tests and changed-files lint gate

## 4. Documentation

- [x] 4.1 Update staging / operational docs with cancel and retry usage for operators
