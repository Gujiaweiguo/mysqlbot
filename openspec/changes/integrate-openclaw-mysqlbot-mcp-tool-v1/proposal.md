## Why

mysqlbot already contains the mature NL-query, SQL execution, analysis, and chart-generation pipeline that OpenClaw needs, but its current HTTP/MCP surfaces are not a stable agent-facing contract for service-to-service use. We need a change now so OpenClaw can call mysqlbot through a normalized MCP/tool boundary without reimplementing mysqlbot logic or depending on user-password exchange and frontend-specific stream details.

## What Changes

- Add a versioned OpenClaw-facing integration contract that keeps mysqlbot as the sole NL-query/analysis engine and exposes agent-safe request, response, and error schemas.
- Add service-to-service authentication and chat/session lifecycle rules so OpenClaw can reuse conversations safely without storing end-user credentials or creating orphan chats.
- Add mysqlbot adapter endpoints that delegate to existing chat orchestration entrypoints for question and analysis operations instead of duplicating the NL-query pipeline.
- Add normalized response, timeout, and failure behavior so OpenClaw tools can consume machine-parseable results consistently in non-streaming mode for v1.
- Add OpenClaw tool registration and invocation-policy skill guidance that tells the agent when to call mysqlbot and when not to.
- Extend observability, regression coverage, and operator rollout/rollback guidance for OpenClaw-originated traffic.

## Capabilities

### New Capabilities
- `openclaw-tool-contract`: Defines the stable OpenClaw-facing operations, versioning, request/response envelopes, and non-streaming v1 behavior for mysqlbot-backed tool calls.
- `openclaw-service-auth-session`: Defines service-to-service authentication, workspace scoping, and chat/session reuse behavior for OpenClaw integrations.
- `openclaw-agent-invocation-policy`: Defines the OpenClaw tool registration and skill-policy behavior that governs when mysqlbot is invoked and how tool results are returned to the agent.

### Modified Capabilities
- `chat-backend-boundaries`: Extend the backend chat boundary contract so OpenClaw-facing adapter routes are transport adapters that delegate to the stable orchestration entrypoint.
- `admin-api-observability`: Extend critical runtime observability requirements to cover OpenClaw-originated adapter traffic, timeout behavior, and failure signals.
- `operator-alert-runbooks`: Extend operator guidance so rollout, alert triage, and rollback cover the OpenClaw integration path.

## Impact

- Affected backend areas include `backend/apps/mcp/mcp.py` or a new OpenClaw adapter module, `backend/apps/chat/api/chat.py`, `backend/apps/chat/orchestration/*`, auth/session boundaries under `backend/apps/system/**`, and observability hooks in `backend/main.py` and `backend/common/**`.
- Affected integration surfaces include the OpenClaw-side tool/skill package and the mysqlbot contract OpenClaw consumes.
- Verification must cover auth, session reuse, question, analysis, timeout/failure behavior, regression on existing chat and MCP paths, and staged rollout/rollback safety.
