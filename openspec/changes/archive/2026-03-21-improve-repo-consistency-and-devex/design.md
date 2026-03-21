## Context

The codebase is functional, but several low-level inconsistencies now tax routine development: commands are spread across docs and service-specific scripts, backend modules still mix `crud` and `curd` naming, and frontend request/auth/error logic is duplicated between standard and streaming paths. None of these issues is a release blocker by itself, but together they make onboarding slower and increase the cost of small changes.

This change is a consistency pass that creates a cleaner baseline for future feature work. It is intentionally scoped to conventions, shared helper contracts, and developer ergonomics rather than product behavior.

## Goals / Non-Goals

**Goals:**
- Establish one supported root-level developer workflow for common install/dev/lint/test actions.
- Normalize repository naming conventions around backend service-layer structure.
- Centralize frontend client logic that is currently repeated across standard and streaming request paths.
- Align human-facing documentation with the canonical commands and paths.

**Non-Goals:**
- Rewriting business logic in backend domain modules.
- Performing a broad frontend architecture rewrite outside shared client handling.
- Introducing a new build system or replacing the current Python/Node toolchains.

## Decisions

### Decision 1: Define root-level command entry points as the canonical developer interface

The repository will expose a small set of root-level commands for common workflows and treat service-specific commands as implementation details documented underneath that contract.

**Why:**
- Contributors currently have to stitch together commands from `README.md`, `AGENTS.md`, and service-specific scripts.
- A canonical entry point lowers onboarding cost and reduces command drift.

**Alternatives considered:**
- Keep documentation-only command guidance: rejected because it does not give contributors a stable executable interface.

### Decision 2: Normalize `curd` → `crud` through explicit migration work, not permanent shims

Existing backend directories and imports that use `curd` will be migrated to the canonical `crud` naming with coordinated import and documentation updates.

**Why:**
- Keeping both names indefinitely preserves confusion and weakens the convention.
- A deliberate migration has one-time cost but removes recurring cognitive overhead.

**Alternatives considered:**
- Keep both spellings and document them: rejected because it institutionalizes drift.

### Decision 3: Centralize frontend client behavior before touching feature views

Auth header construction, normalized async error handling, and stream-capable request concerns will live behind shared frontend client helpers/composables rather than being repeated in views or duplicated request branches.

**Why:**
- Shared client behavior changes for different reasons than feature rendering code.
- Centralization reduces regression risk when auth or streaming behavior changes.

**Alternatives considered:**
- Fix duplication opportunistically in feature files only: rejected because the inconsistency would remain structural.

### Decision 4: Keep documentation and agent guidance in the same consistency pass

Documentation and agent-facing path references will be updated alongside command and naming changes so the repository has one coherent story for contributors.

**Why:**
- Path/reference drift is part of the current problem.
- These changes are cheap once the canonical workflow is decided.

**Alternatives considered:**
- Defer docs until after code cleanup: rejected because contributors would continue following stale instructions.

## Risks / Trade-offs

- **[Rename churn breaks imports]** → Sequence directory renames with repository-wide import updates and verification in the same pass.
- **[Root task runner becomes another layer of drift]** → Keep the command surface intentionally small and map each command to existing underlying scripts.
- **[Client helper extraction changes request behavior]** → Preserve current request/stream semantics and validate unchanged auth and error behavior.
- **[Consistency pass expands into broad refactor]** → Limit scope to shared contracts, naming, and docs rather than domain-level redesign.

## Migration Plan

1. Define the command, structure, and shared-client capabilities through proposal/spec artifacts.
2. Introduce the root-level developer command entry points and document their mapping.
3. Migrate backend `curd` directories/imports/docs to canonical `crud` naming.
4. Extract shared frontend client helpers for auth/error/stream handling and switch callers to them.
5. Verify root commands, import/path stability, and unchanged request behavior.

Rollback is incremental: command entry points can coexist during transition, and naming/helper changes can be reverted in bounded commits if regressions appear.

## Open Questions

- None for this pass.
