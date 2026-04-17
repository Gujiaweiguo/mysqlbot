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

Canonical MCP service logs include:

- `event = openclaw_mcp_observability`
- `group = openclaw_mcp`
- `channel_path` (`mcp`, `health`, or `metrics`)
- `result`
- `connection_failed`
- `capability_discovery_failed`

Degraded MCP health checks also emit:

- `event = openclaw_mcp_health_state`
- `ready`
- `issues`

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

### Canonical MCP service
- Alert on repeated non-success `openclaw_mcp_observability` events on `channel_path = mcp` or `health`
- Alert when `capability_discovery_failed = true`
- Alert when `openclaw_mcp_health_state.ready = false`
- Alert on sustained latency in `sqlbot_openclaw_mcp_request_duration_seconds`

First checks:
- `curl http://localhost:8001/health` and inspect `ready` / `issues`
- Query `GET /api/v1/system/openclaw/mcp-config` and compare the returned endpoint/auth metadata with the OpenClaw registration
- Check `sqlbot_openclaw_mcp_requests_total` and `sqlbot_openclaw_mcp_request_duration_seconds`
- Confirm `SKIP_MCP_SETUP`, `MCP_PUBLIC_BASE_URL`, `MCP_BIND_HOST`, and `MCP_PORT` are correct in the active environment

## Known intent

This observability layer is intentionally request-level and low risk. It does not change business behavior; it only records signals that help operators detect regressions in restored admin/runtime flows.
