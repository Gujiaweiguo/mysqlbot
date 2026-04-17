## Why

The current OpenClaw integration foundation is in place, but channel behavior is still inconsistent: some paths can work through the OpenClaw-facing REST adapter while group-chat MCP discovery and invocation fail because the standard MCP service is not yet exposed and stabilized as the single contract across channels. Since this is still a test-stage integration, now is the right time to converge on the final architecture instead of hardening a temporary dual-path model.

## What Changes

- Expose and stabilize mysqlbot's standard MCP service as the single supported OpenClaw integration entrypoint across web, Feishu direct chat, Feishu group chat, and WeChat.
- Add explicit channel-safe session isolation rules for group-chat scenarios so shared bot identities do not accidentally reuse or cross-contaminate chat context.
- Define the MCP connection, capability discovery, authentication, and compatibility contract required for OpenClaw to connect consistently across all supported channels.
- Extend deployment and runtime configuration so operators can reliably start, expose, health-check, and troubleshoot the dedicated MCP service in development and production environments.
- Add a mysqlbot web-based OpenClaw integration assistant that lets administrators configure MCP connection parameters and generate copyable OpenClaw configuration text for one-step setup.
- Add end-to-end validation, observability, and rollout guidance focused on unified multi-channel MCP traffic rather than mixed REST and MCP behavior.

## Capabilities

### New Capabilities
- `openclaw-channel-mcp-integration`: Defines the single MCP-based integration contract, capability discovery behavior, and cross-channel compatibility rules for OpenClaw callers.
- `openclaw-group-session-isolation`: Defines how group-chat conversations map to mysqlbot sessions so group members and channels do not leak or reuse context incorrectly.
- `openclaw-integration-config-assistant`: Defines the administrator-facing workflow for viewing MCP connection parameters and generating copyable OpenClaw configuration text from the mysqlbot web UI.

### Modified Capabilities
- `containerized-deployment`: Expand deployment requirements so the dedicated MCP service is explicitly started, exposed, and health-checked alongside the main web/API service.
- `admin-api-observability`: Extend observability requirements to cover MCP-originated traffic, connection failures, capability discovery issues, and cross-channel error/latency signals.
- `operator-alert-runbooks`: Extend runbook guidance to cover MCP service exposure, OpenClaw channel-specific failures, and session-isolation troubleshooting.

## Impact

- Affected backend/runtime areas include `backend/main.py`, MCP service startup/exposure paths, `backend/apps/mcp/**`, OpenClaw session-binding logic, and related runtime/configuration code.
- Affected frontend/admin areas include the mysqlbot web UI, admin APIs that surface MCP connection metadata, and any documentation or generated config text used to onboard OpenClaw.
- Affected operational areas include Docker/deployment manifests, service health checks, environment variables, observability dashboards/alerts, and rollout documentation for all OpenClaw channels.
- Verification must cover MCP startup/exposure, tool discovery, authenticated invocation, group-chat isolation behavior, generated config usability, and consistent behavior across web, Feishu direct chat, Feishu group chat, and WeChat.
