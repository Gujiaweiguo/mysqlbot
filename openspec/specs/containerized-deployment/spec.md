# containerized-deployment Specification

## Purpose
Define the supported containerized deployment shapes, readiness expectations, and configuration boundaries for running the application with externalized backing services.
## Requirements
### Requirement: Compose SHALL support separated application and PostgreSQL services
The system SHALL provide a supported Docker Compose deployment mode where the application runs in a dedicated `mysqlbot-app` service and PostgreSQL runs in a dedicated `postgresql` service.

#### Scenario: Start app with external PostgreSQL service
- **WHEN** an operator starts the supported Compose deployment for `app + postgresql`
- **THEN** PostgreSQL SHALL run as its own containerized service
- **AND** the application SHALL connect to PostgreSQL by service hostname and port instead of assuming localhost inside the app container

#### Scenario: Persist PostgreSQL data independently from the app container
- **WHEN** an operator recreates the application container
- **THEN** PostgreSQL data SHALL remain attached to PostgreSQL service storage boundaries rather than app-container-local process state

### Requirement: The application container SHALL not require in-container PostgreSQL startup
The system SHALL define the application container so that it can start successfully without launching a PostgreSQL process inside the same container.

#### Scenario: App startup under split topology
- **WHEN** the app container is started in the supported split Compose topology
- **THEN** its startup behavior SHALL only require reachable backing services defined by configuration
- **AND** it SHALL not depend on starting PostgreSQL inside the app container itself

### Requirement: Compose SHALL support an optional Redis-backed mode
The system SHALL support an optional Compose deployment mode that adds Redis as a third service while preserving a simpler `app + postgresql` mode.

#### Scenario: Run without Redis
- **WHEN** an operator starts the supported `app + postgresql` mode
- **THEN** the application SHALL run without requiring a Redis container

#### Scenario: Run with Redis
- **WHEN** an operator starts the supported `app + redis + postgresql` mode
- **THEN** Redis SHALL run as its own service
- **AND** the application SHALL connect to Redis through explicit configuration rather than localhost assumptions

### Requirement: Service readiness SHALL gate application startup
The deployment contract SHALL define readiness behavior so the application starts only after required backing services are ready enough for migrations and startup initialization.

#### Scenario: PostgreSQL readiness before app start
- **WHEN** PostgreSQL is not yet ready to accept connections
- **THEN** the application SHALL wait on the declared readiness contract instead of starting blindly

#### Scenario: Startup initialization after dependencies are ready
- **WHEN** backing services are healthy
- **THEN** the application SHALL be able to run its startup initialization and migrations against the configured external PostgreSQL service

### Requirement: Deployment documentation SHALL describe supported container modes
The system SHALL document the supported Compose deployment shapes, required environment variables, and persistence boundaries for operators.

#### Scenario: Operator chooses deployment mode
- **WHEN** an operator reads the deployment documentation
- **THEN** they SHALL be able to determine how to run `app + postgresql`
- **AND** how to enable the optional `app + redis + postgresql` mode
- **AND** which volumes and environment values belong to each service

### Requirement: Application service SHALL expose a Compose-visible health contract
The deployment contract SHALL define a health signal for `mysqlbot-app` that operators and container orchestration can observe independently from backing-service health.

#### Scenario: Operator inspects application readiness
- **WHEN** the Compose deployment starts the application service
- **THEN** the application service exposes a health status that can transition to healthy only after the app is ready to serve
- **AND** operators can distinguish app readiness from PostgreSQL readiness

### Requirement: Sensitive deployment values SHALL be environment sourced
The deployment contract SHALL source sensitive runtime values through environment variables or environment files rather than embedding active secrets directly in committed deployment manifests.

#### Scenario: Operator configures deployment secrets
- **WHEN** an operator prepares a supported containerized deployment
- **THEN** sensitive values such as application secrets are supplied through environment-driven configuration
- **AND** committed deployment manifests do not require active secret material to remain checked in
