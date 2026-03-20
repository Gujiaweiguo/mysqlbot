## Context

`sqlbot_xpack` is a compiled external package installed into the backend virtual environment rather than maintained in this repository. The current application depends on it in three especially sensitive ways:

- `backend/main.py` calls xpack startup hooks during import and lifespan startup.
- `backend/common/utils/crypto.py` and `backend/common/utils/aes_crypto.py` bind core encryption/decryption wrappers directly to xpack implementations, and those wrappers are used by login, model credentials, datasource configuration, assistant configuration, and embedding configuration flows.
- The frontend depends on `LicenseGenerator` and `/xpack_static/*` behavior for login encryption, model configuration encryption, and route/license bootstrap.

Additional xpack-derived behavior exists in logout/auth integration, license checks, datasource permissions, custom prompts, parameter/config flows, file utilities, and audit resource resolution. The team wants maintainable first-party ownership of these behaviors without breaking startup, cross-tier encryption compatibility, or existing persisted data.

## Goals / Non-Goals

**Goals:**
- Introduce first-party backend and frontend seams so business code no longer imports or calls xpack directly.
- Preserve current runtime behavior while migration is in progress through legacy adapters and compatibility tests.
- Support phased replacement of xpack-backed capabilities instead of a big-bang rewrite.
- Reach an end state where runtime and build paths no longer require `sqlbot-xpack`.

**Non-Goals:**
- Redesign product behavior for licensing, permissions, prompts, or authentication during this migration.
- Replace every xpack-backed domain in a single release.
- Assume undocumented internals of the closed-source package beyond currently observed call contracts.

## Decisions

### 1. Introduce compat-first boundaries before replacing implementations

The migration will first add first-party compatibility modules on both backend and frontend:

- `backend/common/xpack_compat/`
- `frontend/src/xpack-compat/`

Business modules will depend on these boundaries instead of importing `sqlbot_xpack` or using the global `LicenseGenerator` directly.

**Why:** This reduces blast radius, creates a single place to hold the legacy adapter, and allows later implementation swaps without repeated callsite churn.

**Alternatives considered:**
- Directly replacing xpack usage file-by-file was rejected because it would mix boundary creation and behavior replacement, making regressions harder to localize.
- Big-bang package replacement was rejected because startup, encryption, and persisted data compatibility are too risky.

### 2. Move startup seam earlier than other domain migrations

`backend/main.py` will stop calling `sqlbot_xpack` directly as one of the earliest steps. Startup hooks will instead be accessed through a compat startup provider.

**Why:** Boot failure is the highest-risk regression. Isolating startup first makes later migrations safer and keeps the entrypoint from depending on the closed package.

**Alternatives considered:**
- Delaying startup changes until after crypto was rejected because `main.py` is already a hard dependency edge and should be neutralized early.

### 3. Treat backend crypto and frontend encryption as a coupled migration

The backend crypto/AES provider and the frontend `LicenseGenerator` encryption facade will be migrated as a paired stage, even if they land in separate PRs.

**Why:** Login submission, model configuration submission, and persisted secrets depend on cross-tier compatibility. Changing one side without controlling the other increases the chance of silently incompatible ciphertext.

**Alternatives considered:**
- Migrating backend-only first and leaving the frontend global contract untouched for too long was rejected because it obscures compatibility issues until late.

### 4. Keep legacy adapters until parity is proven per capability

Each capability area will keep a legacy adapter backed by `sqlbot_xpack` until first-party implementations pass characterization, contract, and parity checks.

**Why:** Different capability areas carry different risk profiles. Startup, crypto, license, and permissions should not all switch at once.

**Alternatives considered:**
- One global migration flag for the entire xpack dependency was rejected because it couples unrelated domains and makes rollback too coarse.

### 5. Assign new first-party ownership by domain

- `common/*` owns cross-cutting compatibility, crypto, startup, and license boundaries.
- `apps/system/*` owns auth/logout and parameter/config flows.
- `apps/datasource/*` owns datasource permissions.
- `apps/chat/*` owns custom prompts and chat-time license-gated behavior.
- `frontend/src/xpack-compat/*` owns browser compatibility and static bootstrap facades.

**Why:** This matches current module responsibilities and prevents the compat layer from becoming a permanent dumping ground.

## Risks / Trade-offs

- **[Startup side effects are broader than current callsites reveal]** → Introduce startup seam before implementation replacement, and keep legacy adapter until boot smoke tests remain green.
- **[Cross-tier encryption drift breaks login or secret storage]** → Add characterization and compare tests, keep old-data decrypt compatibility, and migrate backend/frontend encryption as a coordinated stage.
- **[Permissions migration changes business semantics without obvious failures]** → Migrate permissions late, require parity tests for row/column filtering, and avoid semantic redesign in the same change.
- **[License behavior is entangled with frontend bootstrap]** → Separate the browser facade from backend policy decisions so `/xpack_static/*` compatibility can remain temporarily while backend logic moves.
- **[Compat layer becomes permanent technical debt]** → Restrict it to stable interfaces and legacy adapters, then remove adapters once first-party implementations are proven.

## Migration Plan

1. Add characterization tests for startup hooks, crypto wrappers, and frontend `LicenseGenerator` contract.
2. Introduce backend and frontend compat layers plus legacy adapters.
3. Move `backend/main.py` startup behavior behind compat providers.
4. Route backend crypto/AES and frontend encryption calls through first-party facades.
5. Add first-party crypto implementations with mixed-mode compatibility and parity validation.
6. Migrate auth/logout, license, permissions, custom prompts, parameter/config flows, and file utilities in phases.
7. Remove `sqlbot-xpack`, legacy adapters, test stubs, and build/runtime assumptions after runtime and test parity are proven.

Rollback strategy during migration is per capability: keep the legacy adapter available until the replacement has passed tests and targeted runtime validation.

## Open Questions

- What exact ciphertext compatibility rules must the first-party crypto implementation preserve for historical data already stored in the database?
- Should `/xpack_static/license-generator.umd.js` remain as a long-term compatibility path, or should it become a short-lived bridge to a fully local typed frontend module?
- Do datasource permissions require schema migration, or can current runtime model expectations be preserved with first-party models only?
