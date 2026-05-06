## ADDED Requirements

### Requirement: Critical chat coverage SHALL include assistant default-datasource entry and switch behavior
The system SHALL include regression coverage for the assistant and embedded chat journey in which a configured default datasource is applied at direct entry and a datasource switch starts a new chat session.

#### Scenario: Assistant direct-entry journey succeeds with configured default datasource
- **WHEN** a regression test opens assistant or embedded chat configured with a default datasource and submits a first question
- **THEN** the chat starts without a manual datasource picker
- **AND** the rendered session shows the configured datasource as the active datasource

#### Scenario: Datasource switching opens a new assistant chat session
- **WHEN** a regression test switches datasource from an assistant or embedded chat session started through direct entry
- **THEN** the system opens a new chat session for the newly selected datasource
- **AND** the original session remains unchanged
