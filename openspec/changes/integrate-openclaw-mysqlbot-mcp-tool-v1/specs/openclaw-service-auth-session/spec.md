## ADDED Requirements

### Requirement: OpenClaw integration SHALL use service-safe authentication
The system SHALL authenticate OpenClaw through a service-safe credential path such as an API key or service token. The integration MUST NOT require OpenClaw to exchange or store end-user usernames and passwords in order to call mysqlbot-backed tool operations.

#### Scenario: OpenClaw authenticates with a valid service credential
- **WHEN** OpenClaw sends a valid service credential to the OpenClaw-facing contract
- **THEN** the system SHALL authenticate the request and resolve the configured workspace or caller context without requiring end-user password exchange

#### Scenario: OpenClaw sends an invalid or disabled service credential
- **WHEN** OpenClaw sends an invalid, expired, or disabled service credential
- **THEN** the system SHALL reject the request with the documented authentication error envelope
- **AND** the system SHALL NOT create chat or record side effects for that failed request

### Requirement: OpenClaw sessions SHALL define explicit workspace and chat reuse rules
The system SHALL define how an OpenClaw conversation maps to mysqlbot workspace context and chat/session reuse. The integration MUST document and enforce when to create a new chat, when to reuse an existing chat, and how invalid or expired session references are recovered.

#### Scenario: OpenClaw sends sequential requests in one conversation
- **WHEN** OpenClaw submits multiple requests that belong to the same documented conversation context
- **THEN** the system SHALL reuse the mapped mysqlbot chat/session according to the published policy
- **AND** the system SHALL avoid creating orphaned chats beyond that policy

#### Scenario: OpenClaw uses an invalid session reference
- **WHEN** OpenClaw submits a request with a missing, expired, or invalid chat/session reference
- **THEN** the system SHALL respond according to the documented recovery or rejection behavior for that policy
