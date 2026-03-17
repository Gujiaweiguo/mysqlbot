# chat-e2e-baseline Specification

## Purpose
Define the minimal Playwright-based end-to-end harness for frontend chat verification, including deterministic execution and clear developer usage expectations.

## Requirements
### Requirement: The frontend SHALL provide a Playwright E2E harness
The system SHALL provide a Playwright-based browser test harness for the frontend application, including project configuration, installable dependencies, and explicit execution scripts for local and CI-friendly runs.

#### Scenario: Developer runs the E2E baseline locally
- **WHEN** a developer executes the documented Playwright E2E command for the frontend
- **THEN** the project starts the required frontend runtime and executes the Playwright suite through a supported npm script

### Requirement: The E2E baseline SHALL run against deterministic chat test inputs
The system SHALL provide a deterministic environment strategy for the initial Playwright suite so that the first browser tests do not depend on live provider or datasource behavior.

#### Scenario: Baseline suite runs in CI-friendly mode
- **WHEN** the initial Playwright chat suite runs in an automated environment
- **THEN** the browser tests use controlled chat API and streaming inputs with stable expected outputs
- **THEN** a failure indicates a frontend or request-contract regression rather than non-deterministic provider output

### Requirement: The E2E baseline SHALL be documented
The system SHALL document how to install, run, and interpret the initial Playwright suite, including what the first baseline covers and what it intentionally excludes.

#### Scenario: Developer reads the E2E usage docs
- **WHEN** a developer needs to run or extend the Playwright baseline
- **THEN** the repository documents the supported commands, setup expectations, and current coverage scope
