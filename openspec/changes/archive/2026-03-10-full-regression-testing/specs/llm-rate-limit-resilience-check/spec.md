## ADDED Requirements

### Requirement: Rate-limit failure-path validation
The regression process SHALL include validation of model-provider rate-limit behavior, including HTTP 429 conditions, and verify the product responds with graceful user-facing errors.

#### Scenario: Provider returns rate limit
- **WHEN** intelligent-query calls hit provider rate limits
- **THEN** the system surfaces a controlled error state and does not leave the conversation flow in an undefined state

### Requirement: Transient failure resilience policy
The system MUST define and validate retry/backoff or equivalent resilience policy for transient LLM failures, with observable outcomes.

#### Scenario: Transient failure handling
- **WHEN** a transient LLM failure occurs during regression test execution
- **THEN** retry/backoff behavior and final outcome are captured and evaluated against acceptance criteria
