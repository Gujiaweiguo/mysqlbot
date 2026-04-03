# frontend-shared-client-contract Specification

## Purpose
Centralize frontend auth-header construction and async error handling into shared client helpers so that standard and streaming request paths avoid duplicating token assembly and error parsing.
## Requirements
### Requirement: Frontend requests SHALL use shared auth-header construction
The frontend SHALL construct auth-sensitive headers for standard and streaming requests through shared client helpers rather than duplicating token assembly in multiple request paths.

#### Scenario: Standard request and stream request include auth context
- **WHEN** the frontend sends a normal API request and a stream-capable request that require the same auth context
- **THEN** both request paths derive their auth headers through the same shared client contract
- **AND** feature views do not duplicate token/header assembly logic locally

### Requirement: Frontend async failures SHALL use one normalized handling path
The frontend SHALL normalize async request failures through shared handling so user-facing error behavior does not depend on ad hoc parsing in individual views.

#### Scenario: Async request fails in a feature view
- **WHEN** a standard or streaming request fails and returns an error payload
- **THEN** the frontend resolves that failure through the shared client error-handling contract
- **AND** feature views do not need custom low-level error-body parsing to surface a consistent message
