## Why

The current deployment shape bundles PostgreSQL into the application container, which makes installation, debugging, data inspection, and runtime troubleshooting harder than necessary. We need a clearer Docker Compose topology that separates application and data services while still preserving a simple local deployment experience.

## What Changes

- Split the current bundled runtime into explicit Docker Compose services for `gosqlbot-app`, `postgresql`, and optional `redis`.
- Support two supported deployment modes under Compose:
  - `app + postgresql`
  - `app + redis + postgresql`
- Move database lifecycle responsibility out of the app startup script and into Compose service orchestration.
- Update runtime configuration so the app connects to Postgres and Redis through service hostnames instead of assuming localhost inside the same container.
- Define the new deployment contract for startup order, health checks, persistence, and operator-facing configuration.

## Capabilities

### New Capabilities
- `containerized-deployment`: Defines supported Docker Compose service topology, startup behavior, and configuration boundaries for app, PostgreSQL, and optional Redis.

### Modified Capabilities
- None.

## Impact

- Affected files will likely include `docker-compose.yaml`, `Dockerfile`, `Dockerfile-base`, `start.sh`, and deployment/operator documentation.
- The app image responsibility changes: it should no longer own PostgreSQL process startup.
- Runtime environment wiring changes for `POSTGRES_*`, optional Redis/cache settings, service health checks, and persistent volumes.
- Local installation and debugging ergonomics improve, but deployment behavior becomes an explicit supported contract that must be documented and tested.
