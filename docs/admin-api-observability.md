# Admin API Observability and Alerting Runbook

## Covered endpoint groups

- `auth`: `/api/v1/system/authentication*`
- `platform`: `/api/v1/system/platform*`
- `audit`: `/api/v1/system/audit*`
- `custom_prompt`: `/api/v1/system/custom_prompt*`
- `appearance`: `/api/v1/system/appearance*`
- `aimodel`: `/api/v1/system/aimodel*`
- `permission`: `/api/v1/ds_permission*`
- `openclaw`: `/api/v1/openclaw*`

Each monitored request emits a structured log event with:

- `group`
- `path`
- `method`
- `status_code`
- `latency_ms`
- `severity`
- `alert_candidate`
- `user_id`
- `user_name`
- `oid`

OpenClaw request logs also include:

- `operation`
- `error_code`

## Suggested alert conditions

### Authentication and platform
- Alert on repeated `401/403/5xx`
- Alert on latency above `1200ms`

First checks:
- Confirm recent config changes in authentication/platform pages
- Inspect login and provider-specific backend logs
- Verify external dependency or credential status if applicable

### Audit and AI model validation
- Alert on repeated `5xx`
- Alert on latency above `2000ms`

First checks:
- Confirm DB responsiveness
- Check export/query workload and recent data volume
- Inspect backend error logs around the specific endpoint path

### Custom prompts, appearance, permissions
- Alert on repeated `4xx/5xx`
- Alert on latency above `1200ms`

First checks:
- Confirm recent admin save operations
- Verify payload shape and file upload handling where applicable
- Check whether the issue is isolated to one workspace (`oid`) or user

### OpenClaw integration
- Alert on repeated `429/5xx`
- Alert on repeated `AUTH_*`, `EXECUTION_TIMEOUT`, `CONCURRENCY_EXCEEDED`, or `LLM_FAILURE`
- Alert on latency approaching `OPENCLAW_REQUEST_TIMEOUT_SECONDS`

First checks:
- Confirm `OPENCLAW_ENABLED` is set as intended for the target environment
- Inspect `openclaw_api_observability` events and group by `operation` / `error_code`
- Check `sqlbot_openclaw_requests_total` and `sqlbot_openclaw_request_duration_seconds`
- Verify the service credential and datasource scope for the affected workspace

## Known intent

This observability layer is intentionally request-level and low risk. It does not change business behavior; it only records signals that help operators detect regressions in restored admin/runtime flows.
