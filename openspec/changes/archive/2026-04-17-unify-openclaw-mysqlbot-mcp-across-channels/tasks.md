## 1. MCP service exposure and runtime contract

- [x] 1.1 Audit the current MCP startup path and define the canonical endpoint, port, and health-check contract used by all OpenClaw channels.
- [x] 1.2 Update backend runtime/configuration so the dedicated MCP service starts explicitly and is reachable in supported development and production environments.
- [x] 1.3 Add deployment/configuration documentation and operator-facing environment requirements for the MCP-first topology.

## 2. Unified OpenClaw MCP channel behavior

- [x] 2.1 Update MCP capability discovery and authentication behavior so supported OpenClaw channels observe the same tool contract through the canonical MCP entrypoint.
- [x] 2.2 Replace label-only conversation handling with deterministic external session identity mapping for OpenClaw-originated traffic.
- [x] 2.3 Implement group-chat session isolation rules that prevent cross-group or cross-scope context leakage while preserving valid multi-turn reuse.

## 3. Web-based OpenClaw integration assistant

- [x] 3.1 Add backend/admin API support for exposing validated MCP connection metadata needed by the OpenClaw integration assistant.
- [x] 3.2 Build the mysqlbot web UI workflow that displays MCP connection settings, readiness state, and copyable OpenClaw configuration text.
- [x] 3.3 Prevent misleading setup output by surfacing incomplete or invalid MCP configuration directly in the assistant UI.

## 4. Observability, validation, and rollout

- [x] 4.1 Add MCP-first observability for connection failures, capability discovery failures, invocation outcomes, and latency by channel path.
- [x] 4.2 Extend runbooks and rollout guidance for MCP service health, channel onboarding failures, and group-session isolation troubleshooting.
- [x] 4.3 Add end-to-end validation covering web, Feishu direct chat, Feishu group chat, and WeChat against the unified MCP configuration model.
