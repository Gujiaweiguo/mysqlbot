## Context

The current deployment shape is a bundled runtime: the application image embeds PostgreSQL, `start.sh` starts the database process inside the app container, and `docker-compose.yaml` points the backend to `POSTGRES_SERVER=localhost`. This makes the stack easy to launch from a single image, but it couples application lifecycle, database lifecycle, storage, and debugging into one container boundary.

The requested target shape is a standard Compose deployment with explicit service separation:

- `gosqlbot-app`
- `postgresql`
- optional `redis`

The backend application code is already mostly environment-driven for database connectivity, so the main complexity is in runtime packaging, startup sequencing, and operator contract changes rather than business logic.

## Goals / Non-Goals

**Goals:**
- Support a Compose deployment where PostgreSQL runs in its own container.
- Support two operator-selectable deployment modes:
  - `app + postgresql`
  - `app + redis + postgresql`
- Make the application container responsible only for application processes (FastAPI, SSR, MCP if enabled), not PostgreSQL process management.
- Define explicit startup/readiness behavior so the app starts only after required backing services are ready.
- Clarify persistence boundaries for application files, PostgreSQL data, and optional Redis service wiring.

**Non-Goals:**
- Splitting SSR, MCP, or other app-side processes into separate containers.
- Redesigning schema/migrations or changing core application features.
- Making Redis mandatory.
- General production hardening beyond what is needed to support the new container topology.

## Decisions

### Decision 1: Keep one application container and separate only infrastructure services

The new topology will separate PostgreSQL and optional Redis from the app, but keep backend/SSR/MCP bundled in `gosqlbot-app`.

**Why:**
- This delivers the debugging and installation benefits the user wants without turning the change into a broader service decomposition effort.
- The current app image already manages several app-side processes together; separating only DB/cache is the smallest meaningful architecture shift.

**Alternatives considered:**
- Split every process into its own container: rejected as too broad for the current goal.
- Keep the all-in-one image and add optional external DB mode only: rejected because it preserves the main operator confusion around image responsibility.

### Decision 2: Compose owns PostgreSQL lifecycle

PostgreSQL will be a dedicated Compose service with its own volume, healthcheck, and hostname-based discovery. The app container will no longer start Postgres internally.

**Why:**
- This is the core contract change needed to make the deployment topology understandable and debuggable.
- It enables direct inspection of PostgreSQL logs, lifecycle, and storage without app-container coupling.

**Alternatives considered:**
- Continue using a postgres-enabled runtime image but skip startup conditionally: acceptable as an interim step, but inferior to making image responsibility explicit.

### Decision 3: Redis remains optional and profile-driven

Redis support will be modeled as an optional Compose mode rather than a mandatory third service.

**Why:**
- The current application defaults to in-memory cache behavior.
- For local install/debug workflows, forcing Redis would add operational burden without guaranteed benefit.

**Alternatives considered:**
- Make Redis always-on: rejected because it expands operational requirements for no default-value gain.

### Decision 4: Readiness and migrations are part of the deployment contract

The app service must wait for PostgreSQL readiness using Compose service health, and startup behavior must remain compatible with migration execution and internal datasource initialization.

**Why:**
- The backend runs migrations and startup initialization early; this change only works reliably if database readiness is explicit.

**Alternatives considered:**
- Rely on container start order only: rejected as too brittle.

## Risks / Trade-offs

- **[Startup sequencing drift]** → Use explicit PostgreSQL healthchecks and service dependency gating.
- **[Image responsibility ambiguity]** → Remove or conditionally bypass embedded-Postgres startup from the app container entrypoint.
- **[Operator confusion across two supported modes]** → Document the difference between `app + postgresql` and `app + redis + postgresql` clearly in Compose/docs.
- **[Internal datasource assumptions]** → Validate startup behaviors that compare configured `POSTGRES_*` values against datasource records still work with hostname-based service discovery.
- **[More moving parts than the current all-in-one image]** → Accept this as the trade-off for better debugging and standard deployment ergonomics.

## Migration Plan

1. Introduce the new Compose topology and environment contract.
2. Update the application image/runtime so it no longer requires in-container PostgreSQL startup.
3. Validate the `app + postgresql` mode first.
4. Validate the optional `app + redis + postgresql` mode.
5. Document operator setup, persistence paths, and fallback/rollback behavior.

Rollback should remain possible by keeping the current bundled deployment path available until the split topology is validated.

## Open Questions

- Should the bundled all-in-one runtime remain supported temporarily, or should the new change replace it entirely?
- Should Redis mode be exposed via Compose profiles, override files, or separate example manifests?
- Is MCP setup expected to stay enabled by default in the split deployment, or remain operator-configurable as it is now?
