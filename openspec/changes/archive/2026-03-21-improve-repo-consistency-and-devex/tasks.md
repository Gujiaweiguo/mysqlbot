## 1. Canonical developer workflow

- [x] 1.1 Add the supported root-level developer command entry points for install, dev, lint, and test workflows
- [x] 1.2 Update README and agent/contributor guidance so documented commands and workspace paths match the canonical workflow

## 2. Repository structure normalization

- [x] 2.1 Normalize backend `curd` directories and related imports/documentation to the canonical `crud` naming
- [x] 2.2 Verify repository-wide path and import stability after the naming normalization

## 3. Frontend shared client consistency

- [x] 3.1 Extract shared auth-header construction for standard and streaming request paths into the frontend client layer
- [x] 3.2 Centralize normalized async error handling in the shared frontend client path and migrate callers away from view-local parsing
- [x] 3.3 Apply consistency cleanup in touched shared client modules so duplicated support logic does not remain alongside the new contract

## 4. Verification

- [x] 4.1 Validate the canonical root commands and targeted frontend/backend workflows after the consistency pass
