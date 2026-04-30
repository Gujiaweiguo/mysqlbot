## ADDED Requirements

### Requirement: Assistant application forms SHALL support multi-select workspace configuration
The system SHALL allow administrators to select one or more workspaces when configuring either a basic application or an advanced application for the assistant feature.

#### Scenario: Administrator selects multiple workspaces for a basic application
- **WHEN** the administrator configures a basic application assistant and chooses more than one workspace
- **THEN** the system SHALL accept the selected workspace set and preserve the full selection for submission

#### Scenario: Administrator selects multiple workspaces for an advanced application
- **WHEN** the administrator configures an advanced application assistant and chooses more than one workspace
- **THEN** the system SHALL accept the selected workspace set and preserve the full selection for submission

### Requirement: Assistant application forms SHALL support multi-select datasource configuration within selected workspaces
The system SHALL allow administrators to select one or more datasources for both basic applications and advanced applications, and selectable datasources SHALL be constrained to the currently selected workspaces.

#### Scenario: Datasource options are filtered by selected workspaces
- **WHEN** the administrator selects one or more workspaces in an assistant configuration form
- **THEN** the datasource selector SHALL expose only datasources that belong to the selected workspace scope

#### Scenario: Administrator selects multiple datasources
- **WHEN** the administrator chooses multiple datasources from the allowed datasource options
- **THEN** the system SHALL preserve the entire datasource selection for submission

### Requirement: Assistant configuration APIs SHALL persist and return selected workspaces and datasources
The system SHALL persist the selected workspace identifiers and datasource identifiers for basic and advanced assistant applications, and SHALL return those selections during subsequent load or edit operations.

#### Scenario: Assistant edit form loads previously saved resource selections
- **WHEN** an administrator opens an existing assistant application configuration for editing
- **THEN** the system SHALL return the previously saved workspace selection and datasource selection so the form reflects the stored configuration

#### Scenario: Assistant update replaces a prior resource selection
- **WHEN** an administrator saves a changed set of workspaces and datasources for an existing assistant application
- **THEN** the system SHALL replace the prior stored selections with the submitted valid selection set

### Requirement: Assistant configuration saves SHALL reject invalid workspace or datasource selections
The system SHALL validate that every selected workspace and datasource is valid, enabled, and within the assistant's allowed configuration scope before persisting the assistant configuration.

#### Scenario: Submitted datasource falls outside selected workspaces
- **WHEN** an assistant configuration request includes a datasource that is not in the submitted workspace scope
- **THEN** the system SHALL reject the request with a validation error and SHALL NOT persist a partial configuration

#### Scenario: Submitted workspace or datasource is disabled or missing
- **WHEN** an assistant configuration request includes a disabled or nonexistent workspace or datasource
- **THEN** the system SHALL reject the request with a validation error and SHALL NOT silently remove the invalid selection

### Requirement: Runtime assistant scope SHALL honor persisted workspace and datasource bindings
The system SHALL use the persisted workspace and datasource selections as the assistant's effective resource scope wherever assistant runtime behavior depends on resource boundaries.

#### Scenario: Runtime resolves assistant resource scope from persisted bindings
- **WHEN** the assistant runtime needs to determine which workspaces or datasources an assistant can use
- **THEN** the system SHALL derive that scope from the persisted workspace and datasource bindings saved in the assistant configuration
