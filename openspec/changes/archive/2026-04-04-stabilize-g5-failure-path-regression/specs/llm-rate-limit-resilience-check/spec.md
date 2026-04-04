## MODIFIED Requirements

### Requirement: Rate-limit failure-path validation
The regression process SHALL include deterministic CI validation of model-provider rate-limit behavior, including HTTP 429 conditions, and verify the product responds with graceful user-facing errors.

#### Scenario: Provider returns rate limit during CI regression
- **WHEN** the G5 failure-path regression executes a controlled HTTP 429 provider response in CI
- **THEN** the system surfaces a controlled error state and does not leave the conversation flow in an undefined state

### Requirement: Transient failure resilience policy
The system MUST define and validate retry/backoff or equivalent resilience policy for transient LLM failures, with observable outcomes, under deterministic CI execution.

#### Scenario: Transient failure handling in CI regression
- **WHEN** the G5 failure-path regression executes a controlled transient failure scenario in CI
- **THEN** retry/backoff behavior and final outcome are captured and evaluated against acceptance criteria
