# openclaw-group-session-isolation Specification

## Purpose
Define how OpenClaw-originated traffic maps to mysqlbot sessions so different channel conversations stay isolated while valid follow-up turns can reuse the correct session.

## Requirements
### Requirement: Group-chat traffic SHALL map to deterministic external session identities
The system SHALL derive or accept a deterministic external session identity for OpenClaw-originated traffic that preserves the correct conversation boundary for each supported channel type. Group-chat traffic MUST NOT reuse direct-chat or unrelated group-chat context accidentally.

#### Scenario: Two unrelated group chats use the same bot identity
- **WHEN** two separate group conversations invoke mysqlbot through the same shared OpenClaw bot identity
- **THEN** the system SHALL map them to separate mysqlbot session identities and SHALL NOT reuse chat context across those groups

### Requirement: Session reuse SHALL stay inside the declared channel conversation boundary
The system SHALL reuse existing mysqlbot chat context only when the incoming OpenClaw request matches the previously established external session identity for that channel conversation.

#### Scenario: Follow-up message arrives in the same channel conversation
- **WHEN** a supported channel sends a follow-up tool invocation with the same declared external session identity
- **THEN** the system SHALL reuse the matching mysqlbot session instead of creating a new unrelated chat record

### Requirement: Session mismatch SHALL fail safely
The system SHALL reject or rebind requests that present incompatible session identity, ownership, or datasource context instead of silently attaching the request to the wrong mysqlbot chat.

#### Scenario: Request attempts to reuse a session from another channel scope
- **WHEN** an incoming OpenClaw request references session context that does not belong to the resolved external session identity
- **THEN** the system SHALL return a documented session-scope failure and SHALL NOT attach the request to the mismatched chat context
