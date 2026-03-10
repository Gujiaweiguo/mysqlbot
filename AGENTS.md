# AGENTS.md

Operational guide for coding agents working in this repository.
This is based on current scripts/config in `backend/`, `frontend/`, and root files.

## 1) Project Layout
- `backend/`: FastAPI + SQLModel Python service.
- `frontend/`: Vue 3 + TypeScript + Vite UI.
- `g2-ssr/`: Node SSR helper service.
- Root runtime/build files: `Dockerfile`, `Dockerfile-base`, `docker-compose.yaml`, `start.sh`.

## 2) Toolchain Snapshot
- Python: 3.11, dependency manager `uv` (`backend/pyproject.toml`).
- Backend quality tools: `ruff`, `mypy`, `pytest`, `coverage`.
- Frontend: Vue 3 + TypeScript + Vite + ESLint + Prettier.
- JavaScript package manager in scripts: `npm`.

## 3) Build / Lint / Test / Run Commands
Run from the target directory shown below.

### 3.1 Frontend (`/opt/code/SQLBot/frontend`)
- Install: `npm install`
- Dev: `npm run dev`
- Build: `npm run build`
- Preview build: `npm run preview`
- Lint (auto-fix): `npm run lint`

Notes:
- `npm run dev` and `npm run build` both include `vue-tsc -b` first.
- No frontend test script is currently defined in `frontend/package.json`.

### 3.2 Backend (`/opt/code/SQLBot/backend`)
- Sync dependencies: `uv sync`
- Sync CPU extra: `uv sync --extra cpu`
- Dev server (reload): `uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload`
- Lint/typecheck script: `bash scripts/lint.sh`
- Format script: `bash scripts/format.sh`
- Test script (coverage): `bash scripts/test.sh`

Notes:
- `scripts/lint.sh` currently runs: `mypy app`, `ruff check app`, `ruff format app --check`.
- `scripts/format.sh` currently runs: `ruff check apps scripts common --fix`, then `ruff format apps scripts common`.

### 3.3 Migrations (`/opt/code/SQLBot/backend`)
- Apply migrations: `alembic upgrade head`
- Wrapper: `bash scripts/alembic/exec.sh`
- Auto-create migration: `bash scripts/alembic/auto.sh "message"`
- Prestart setup: `bash scripts/prestart.sh`

### 3.4 Containers (`/opt/code/SQLBot`)
- Build image: `docker build -t sqlbot .`
- Start stack: `docker-compose up -d`

## 4) Single-Test Commands (Priority)
Backend has `pytest` installed, but no committed `tests/` files were detected at scan time.
When tests exist, use these patterns:

- Single file: `uv run pytest path/to/test_file.py`
- Single function: `uv run pytest path/to/test_file.py::test_name`
- Single class method: `uv run pytest path/to/test_file.py::TestClass::test_method`
- Name filter: `uv run pytest -k "keyword"`

Useful flags:
- Verbose: `-v`
- Stop on first fail: `-x`
- Show prints/stdout: `-s`

Frontend test runner status:
- No Vitest/Jest script/config is present now.
- Do not assume a frontend test command exists until a runner is added.

## 5) Backend Style Guidelines (Python)
Primary source: `backend/pyproject.toml`.

### 5.1 Formatting and Linting
- Ruff rule groups enabled: `E`, `W`, `F`, `I`, `B`, `C4`, `UP`, `ARG001`.
- Ignored: `E501`, `B008`, `W191`, `B904`.
- Keep imports grouped and deterministic.

### 5.2 Types
- Mypy strict mode is enabled (`strict = true`).
- Add/keep explicit type annotations in new code.
- Follow existing FastAPI `Annotated[...]` dependency typing patterns.
- Prefer modern Python type syntax where project already uses it.

### 5.3 Naming and Module Boundaries
- Functions/variables: `snake_case`.
- Classes/models/schemas: `PascalCase`.
- Place routers in `apps/*/api/`.
- Place business logic in `apps/*/crud/`.
- Place shared infrastructure/utilities in `common/`.

### 5.4 Error Handling
- In API layers, raise `HTTPException` with explicit status and detail.
- Do not swallow exceptions silently.
- Respect central middleware/exception flow in `main.py` and `common/core/response_middleware.py`.

## 6) Frontend Style Guidelines (Vue + TS)
Primary sources:
- `frontend/.prettierrc`
- `frontend/.editorconfig`
- `frontend/eslint.config.cjs`
- `frontend/tsconfig.app.json`

### 6.1 Formatting
- Prettier: single quote, no semicolons, trailing comma `es5`, width 100, tab width 2.
- EditorConfig: UTF-8, LF, final newline, trim trailing whitespace (markdown override exists).

### 6.2 Types and Lint Rules
- TS strict mode is enabled, including unused-local/unused-parameter checks.
- ESLint stack: Vue + TypeScript + Prettier flat config.
- Repo currently allows `any` (`@typescript-eslint/no-explicit-any` off), but prefer concrete types in new code.

### 6.3 Imports, Components, Naming
- Prefer `@/` alias imports for project modules.
- Prefer `<script setup lang="ts">` for Vue SFCs where existing code follows it.
- Variables/functions: `camelCase`.
- Types/interfaces/classes/components: `PascalCase`.
- Keep route/API symbols descriptive; avoid unclear one-letter names.

### 6.4 Error Handling
- Reuse shared request layer in `src/utils/request.ts`.
- Reuse existing UI error pattern (`ElMessage`) for consistency.

## 7) Pre-Commit and Quality Gates
- Root config: `.pre-commit-config.yaml`.
- Includes file hygiene checks plus `ruff` and `ruff-format` hooks.
- Before finalizing substantive changes, run relevant lint/type/test commands for touched modules.

## 8) Cursor / Copilot Rules Status
Scanned for:
- `.cursor/rules/`
- `.cursorrules`
- `.github/copilot-instructions.md`

Current result:
- No Cursor rule files found.
- No Copilot instruction file found.

If these files are added later, treat them as higher-priority guidance and merge updates into this document.

## 9) Agent Working Agreements
- Verify scripts/config before running commands; do not assume missing tooling exists.
- For backend targeted tests, use `uv run pytest ...` forms above.
- Keep edits small and aligned with existing module boundaries and wrappers.
- Prefer existing utilities (request wrapper, middleware, config helpers) over duplicate implementations.
- Update this file when command entrypoints or quality tooling changes.
