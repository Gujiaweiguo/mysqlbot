## ADDED Requirements

### Requirement: Unit tests for common utilities

The system SHALL have unit tests for utilities in `common/utils/`:
- Date/time formatting functions
- String manipulation helpers
- Validation utilities

#### Scenario: date formatting utility tested
- **WHEN** `formatTimestamp` is called with a valid timestamp
- **THEN** output matches expected date string format

#### Scenario: validation utility tested
- **WHEN** validation function receives valid input
- **THEN** function returns success

#### Scenario: validation utility handles invalid input
- **WHEN** validation function receives invalid input
- **THEN** function raises appropriate exception

### Requirement: Unit tests for core business logic

The system SHALL have unit tests for critical business logic:
- SQL parsing and validation
- Query building functions
- Data transformation utilities

#### Scenario: SQL parsing extracts table names
- **WHEN** SQL parser receives a SELECT query
- **THEN** all referenced table names are extracted correctly

#### Scenario: query builder generates valid SQL
- **WHEN** query builder constructs a query with filters
- **THEN** generated SQL is syntactically valid

### Requirement: Tests use mocks for external dependencies

Unit tests SHALL NOT make real calls to:
- LLM APIs (OpenAI, DashScope, etc.)
- Database connections (use in-memory or mocks)
- External HTTP services

#### Scenario: LLM API call is mocked
- **WHEN** code under test calls an LLM API
- **THEN** a mock returns predefined response without network call
