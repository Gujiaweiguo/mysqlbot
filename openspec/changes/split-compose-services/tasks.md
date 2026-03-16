## 1. Runtime Packaging

- [ ] 1.1 Identify and replace the postgres-bundled app runtime image with an app-only runtime image
- [ ] 1.2 Remove or conditionalize in-container PostgreSQL startup from `start.sh`
- [ ] 1.3 Ensure the app container still starts FastAPI, SSR, and MCP processes correctly without embedded PostgreSQL

## 2. Compose Topology

- [ ] 2.1 Add a dedicated `postgresql` service to Docker Compose with persistent volume and healthcheck
- [ ] 2.2 Update the app service to connect to PostgreSQL by service hostname instead of `localhost`
- [ ] 2.3 Define an optional Redis service mode without making Redis mandatory for the default stack

## 3. Startup and Configuration Contract

- [ ] 3.1 Wire service readiness so the app waits for PostgreSQL before startup initialization and migrations
- [ ] 3.2 Validate environment variables and defaults for `POSTGRES_*`, cache settings, and optional Redis mode
- [ ] 3.3 Confirm internal datasource initialization still behaves correctly under the split topology

## 4. Operator Experience

- [ ] 4.1 Document how to run the `app + postgresql` mode
- [ ] 4.2 Document how to run the `app + redis + postgresql` mode
- [ ] 4.3 Document persistence boundaries, ports, and rollback/fallback expectations for operators

## 5. Verification

- [ ] 5.1 Verify the default `app + postgresql` mode boots cleanly and serves the application successfully
- [ ] 5.2 Verify the optional `app + redis + postgresql` mode boots cleanly and the app uses configured cache wiring
- [ ] 5.3 Validate container healthchecks, migration behavior, and data persistence across container recreation
