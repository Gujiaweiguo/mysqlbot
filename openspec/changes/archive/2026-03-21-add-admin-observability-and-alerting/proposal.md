## Why

The admin and runtime capabilities restored in recent changes are now usable in production, but they still rely on manual page checks and ad hoc log inspection to detect regressions. Critical management paths such as authentication, platform integration, operation logs, custom prompts, appearance settings, AI model validation, and permission configuration need explicit observability and alerting so failures surface quickly and operators know what to check.

## What Changes

- Add first-party observability coverage for critical admin/runtime APIs, including structured logging and request-level visibility for the most failure-prone management flows.
- Define and implement alerting for critical error-rate, failure, and latency conditions on authentication, platform, audit, custom prompt, appearance, AI model validation, and permission APIs.
- Add operator-facing guidance documenting what each alert means and which logs/endpoints should be checked first.
- Validate that the chosen signals can detect the regressions recently fixed without requiring end-user reports.

## Capabilities

### New Capabilities
- `admin-api-observability`: Monitor and alert on critical admin/runtime API health for restored first-party management flows.
- `operator-alert-runbooks`: Provide operator guidance for triaging alerts on restored admin/runtime API flows.

### Modified Capabilities
<!-- None. This change adds operational observability rather than changing functional behavior. -->

## Impact

- Affected backend systems: authentication, platform, audit, custom prompt, appearance, AI model validation, and permission endpoints
- Affected operational workflows: production monitoring, alerting, incident response, and post-deploy verification
- Affected documentation: runbooks or internal guidance for alert triage and expected signals
