## ADDED Requirements

### Requirement: Assistant configuration SHALL support an explicit default datasource for direct entry
The system SHALL allow assistant and embedded configuration to persist an optional default datasource used for direct chat entry. The configured default datasource SHALL be assistant-scoped and SHALL NOT change standard mysqlbot chat behavior outside assistant and embedded surfaces.

#### Scenario: Administrator configures a default datasource for an assistant
- **WHEN** an administrator saves an assistant with direct-entry behavior enabled and selects a default datasource
- **THEN** the assistant configuration stores that datasource association for future assistant and embedded chat entry

#### Scenario: Assistant has no configured default datasource
- **WHEN** an assistant or embedded configuration does not define a default datasource
- **THEN** the system SHALL NOT infer a datasource from workspace defaults, recent usage, or question content

### Requirement: Assistant direct entry SHALL bind the new chat to the configured default datasource
When assistant or embedded direct entry is enabled and a default datasource is configured, the system SHALL create the new chat session already bound to that datasource instead of creating a datasource-less session.

#### Scenario: User enters assistant chat with a configured default datasource
- **WHEN** a user opens assistant or embedded chat whose configuration enables direct entry and defines a default datasource
- **THEN** the first created chat session is bound to that configured datasource
- **AND** the user can ask a question immediately without opening the datasource picker first

#### Scenario: Configured default datasource is unavailable at entry time
- **WHEN** the configured default datasource no longer exists or is no longer available to the assistant at chat start time
- **THEN** the system SHALL refuse to silently substitute another datasource
- **AND** the user SHALL receive a clear failure or recovery path instead of entering a misbound session

### Requirement: Assistant direct-entry chat SHALL show the active datasource and allow switching
Assistant and embedded chat sessions that are bound to a datasource through direct entry SHALL display the active datasource to the user and SHALL expose a datasource switch action.

#### Scenario: User views assistant chat started from a default datasource
- **WHEN** the assistant or embedded chat page renders a session created from a configured default datasource
- **THEN** the UI shows the active datasource name
- **AND** the UI provides an affordance to switch datasource

### Requirement: Datasource switching from assistant direct-entry chat SHALL create a new session
When a user switches datasource from an assistant or embedded direct-entry chat, the system SHALL create a new chat session bound to the selected datasource and SHALL NOT mutate the datasource of the existing session.

#### Scenario: User switches datasource from assistant chat
- **WHEN** the user chooses a different datasource from the assistant or embedded datasource switch control
- **THEN** the system creates a new chat session bound to the selected datasource
- **AND** the previous chat session keeps its original datasource and history unchanged
