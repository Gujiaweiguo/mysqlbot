## ADDED Requirements

### Requirement: OpenClaw-facing tool operations SHALL use a versioned stable contract
The system SHALL expose a versioned OpenClaw-facing contract for mysqlbot-backed tool operations. The contract MUST define the supported operations, request schema, response schema, error schema, timeout behavior, and compatibility rules without requiring OpenClaw to depend on frontend-only chat stream details.

#### Scenario: OpenClaw invokes a supported operation
- **WHEN** OpenClaw calls a supported mysqlbot-backed operation such as session binding, question execution, analysis execution, or datasource discovery through the OpenClaw-facing contract
- **THEN** the system SHALL accept or reject the request according to the versioned contract schema
- **AND** the operation SHALL return the documented success or error envelope for that contract version

### Requirement: OpenClaw-facing v1 responses SHALL be non-streaming and machine-parseable
The v1 OpenClaw-facing contract SHALL define non-streaming success and failure envelopes that tools can parse deterministically. The system MUST NOT require streaming as the only supported behavior for v1.

#### Scenario: OpenClaw receives a successful question result
- **WHEN** a question or analysis request completes successfully through the v1 contract
- **THEN** the system SHALL return one normalized non-streaming success envelope with predictable field names and status semantics

#### Scenario: OpenClaw receives an execution failure
- **WHEN** authentication, validation, datasource, SQL execution, timeout, or LLM execution fails through the v1 contract
- **THEN** the system SHALL return one normalized non-streaming error envelope with a machine-parseable error code and message

### Requirement: Optional streaming behavior SHALL NOT break the mandatory v1 contract
If the system exposes streaming for future OpenClaw integrations, that behavior SHALL remain optional and MUST NOT change or remove the mandatory non-streaming v1 contract.

#### Scenario: Streaming is introduced after v1
- **WHEN** a later integration path adds optional streaming support for OpenClaw
- **THEN** the mandatory non-streaming v1 request and response semantics SHALL remain valid for callers that continue using them
