## 1. Runtime Packaging

- [x] 1.1 Identify and replace the postgres-bundled app runtime image with an app-only runtime image
- [x] 1.2 Remove or conditionalize in-container PostgreSQL startup from `start.sh`
- [x] 1.3 Ensure the app container still starts FastAPI, SSR, and MCP processes correctly without embedded PostgreSQL

## 2. Compose Topology

- [x] 2.1 Add a dedicated `postgresql` service to Docker Compose with persistent volume and healthcheck
- [x] 2.2 Update the app service to connect to PostgreSQL by service hostname instead of `localhost`
- [x] 2.3 Define an optional Redis service mode without making Redis mandatory for the default stack

## 3. Startup and Configuration Contract

- [x] 3.1 Wire service readiness so the app waits for PostgreSQL before startup initialization and migrations
- [x] 3.2 Validate environment variables and defaults for `POSTGRES_*`, cache settings, and optional Redis mode
- [x] 3.3 Confirm internal datasource initialization still behaves correctly under the split topology

## 4. Operator Experience

- [x] 4.1 Document how to run the `app + postgresql` mode
- [x] 4.2 Document how to run the `app + redis + postgresql` mode
- [x] 4.3 Document persistence boundaries, ports, and rollback/fallback expectations for operators

## 5. Verification

- [x] 5.1 Verify the default `app + postgresql` mode boots cleanly and serves the application successfully
- [x] 5.2 Verify the optional `app + redis + postgresql` mode boots cleanly and the app uses configured cache wiring
- [x] 5.3 Validate container healthchecks, migration behavior, and data persistence across container recreation
