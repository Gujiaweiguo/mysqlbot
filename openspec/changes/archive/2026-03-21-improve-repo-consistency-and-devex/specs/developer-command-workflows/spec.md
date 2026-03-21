## ADDED Requirements

### Requirement: Repository SHALL expose canonical root-level developer commands
The repository SHALL provide a documented root-level command surface for common workflows including install, local development, linting, and testing.

#### Scenario: Contributor starts routine development workflow
- **WHEN** a contributor works from the repository root
- **THEN** they can invoke the documented root-level commands for install, dev, lint, and test workflows
- **AND** those commands map to the supported service-specific implementations underneath

### Requirement: Root-level command documentation SHALL remain aligned with implementation
The repository SHALL document the canonical root-level command workflow in the same places contributors are expected to use for setup guidance.

#### Scenario: Contributor follows setup instructions
- **WHEN** a contributor reads repository setup or agent guidance
- **THEN** the documented commands match the supported root-level workflow
- **AND** contributors are not directed to stale paths or conflicting entry points
