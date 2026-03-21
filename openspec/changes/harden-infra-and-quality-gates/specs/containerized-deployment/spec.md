## ADDED Requirements

### Requirement: Application service SHALL expose a Compose-visible health contract
The deployment contract SHALL define a health signal for `gosqlbot-app` that operators and container orchestration can observe independently from backing-service health.

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
