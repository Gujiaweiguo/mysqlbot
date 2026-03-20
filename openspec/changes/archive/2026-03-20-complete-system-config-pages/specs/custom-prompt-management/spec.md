## ADDED Requirements

### Requirement: Administrators can browse custom prompts by prompt type
The system SHALL allow administrators to retrieve paginated custom prompt records filtered by prompt type.

#### Scenario: Prompt management page loads prompts for one type
- **WHEN** an administrator opens the custom prompt page for a specific prompt type
- **THEN** the backend SHALL return a paginated list of prompt records for that type

### Requirement: Administrators can manage individual custom prompts
The system SHALL allow administrators to read, create/update, and delete custom prompt records.

#### Scenario: Administrator reads one custom prompt
- **WHEN** the administrator opens an existing custom prompt for editing
- **THEN** the backend SHALL return the stored prompt content, name, specific-datasource flag, and datasource assignments

#### Scenario: Administrator saves a custom prompt
- **WHEN** the administrator saves a custom prompt record
- **THEN** the backend SHALL persist the prompt and return success without breaking runtime prompt lookup behavior

#### Scenario: Administrator deletes one or more custom prompts
- **WHEN** the administrator deletes one or more prompt records
- **THEN** the backend SHALL remove those records and return success

### Requirement: Administrators can export custom prompts
The system SHALL allow administrators to export custom prompts for a selected prompt type.

#### Scenario: Administrator exports prompt records
- **WHEN** the administrator triggers export for a prompt type
- **THEN** the backend SHALL return an Excel file containing the matching prompt records
