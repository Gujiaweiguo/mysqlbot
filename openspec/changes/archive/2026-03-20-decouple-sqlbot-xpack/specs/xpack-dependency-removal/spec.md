## ADDED Requirements

### Requirement: The system supports mixed-mode capability migration
The system SHALL support phased migration where first-party capability providers can replace legacy xpack-backed implementations without forcing all capability areas to migrate at once.

#### Scenario: Migrated and unmigrated capabilities coexist
- **WHEN** some capability areas have first-party implementations and others still use legacy adapters
- **THEN** the application SHALL allow both to operate through first-party provider boundaries during the migration period

### Requirement: Existing protected data remains readable during migration
The system SHALL preserve compatibility with existing encrypted or protected data needed by current application flows while first-party implementations are introduced.

#### Scenario: Historical data remains usable after provider changes
- **WHEN** the application reads previously stored secrets or protected configuration values during migration
- **THEN** the active first-party capability provider SHALL continue to read the existing data needed for supported runtime flows

### Requirement: Runtime and build paths can operate without sqlbot-xpack before dependency removal is complete
The system SHALL only remove the `sqlbot-xpack` dependency after runtime entrypoints, frontend bootstrap paths, and build/deployment flows have first-party implementations or compatibility replacements.

#### Scenario: Dependency removal occurs only after first-party replacements exist
- **WHEN** the change removes `sqlbot-xpack` from runtime or build configuration
- **THEN** application startup, frontend bootstrap, and required tests/build flows SHALL continue to operate without the external package being installed
