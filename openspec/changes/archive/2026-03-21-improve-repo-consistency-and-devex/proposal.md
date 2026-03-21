## Why

The repository already has the right major building blocks, but day-to-day work is slowed by inconsistent module naming, scattered developer commands, and repeated frontend client logic that makes small edits harder than they should be. We need a consistency pass now so future feature work lands on clearer conventions instead of deepening local drift.

## What Changes

- Define a supported root-level developer command workflow for install, dev, lint, and test operations.
- Standardize repository structure conventions for backend service-layer naming and related documentation references.
- Define a shared frontend client contract for auth headers, async error handling, and stream-capable request flows so feature code stops duplicating that logic.
- Use the consistency pass to reduce avoidable tool and import drift in touched frontend/backend support code.

## Capabilities

### New Capabilities
- `developer-command-workflows`: Defines the supported root-level command entry points for common local development tasks.
- `repository-structure-consistency`: Defines canonical repository naming and migration expectations for shared module patterns such as `crud` directories.
- `frontend-shared-client-contract`: Defines shared frontend request/auth/error-handling behavior for standard and streaming requests.

### Modified Capabilities
- None.

## Impact

- Affected files will likely include root task-runner files such as `Makefile`, `README.md`, `AGENTS.md`, backend module paths under `backend/apps/**`, and frontend shared utilities such as `frontend/src/utils/request.ts`.
- The change is internal-facing: it reduces cognitive load, lowers duplication, and makes future refactors cheaper without changing user-visible features.
- Verification should focus on command ergonomics, import/path stability, and unchanged frontend request behavior after helper extraction.
