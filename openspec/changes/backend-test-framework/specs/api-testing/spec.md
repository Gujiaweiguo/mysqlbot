## ADDED Requirements

### Requirement: Health endpoint test

The system SHALL have an API test for the health check endpoint:
- Tests `/health` or equivalent endpoint
- Verifies response status and structure

#### Scenario: health endpoint returns 200
- **WHEN** GET request is made to `/health`
- **THEN** response status is 200
- **AND** response body contains status field

### Requirement: Authentication endpoint tests

The system SHALL have API tests for authentication:
- Login with valid credentials
- Login with invalid credentials
- Token validation

#### Scenario: login succeeds with valid credentials
- **WHEN** POST request is made to `/api/v1/auth/login` with valid credentials
- **THEN** response status is 200
- **AND** response body contains access token

#### Scenario: login fails with invalid credentials
- **WHEN** POST request is made to `/api/v1/auth/login` with invalid credentials
- **THEN** response status is 401
- **AND** response body contains error message

### Requirement: Protected endpoint requires authentication

API tests SHALL verify that protected endpoints reject unauthenticated requests.

#### Scenario: protected endpoint rejects missing token
- **WHEN** GET request is made to protected endpoint without Authorization header
- **THEN** response status is 401

#### Scenario: protected endpoint accepts valid token
- **WHEN** GET request is made to protected endpoint with valid Bearer token
- **THEN** response status is 200

### Requirement: API tests use async client

All API tests SHALL use `httpx.AsyncClient` for testing async FastAPI endpoints.

#### Scenario: async client makes request
- **WHEN** test uses async_client fixture
- **THEN** request is handled by FastAPI async handlers correctly
