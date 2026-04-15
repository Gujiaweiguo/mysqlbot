# OpenClaw Integration Contract v1

This document is the repository-adjacent contract reference for the OpenClaw integration described by `integrate-openclaw-mysqlbot-mcp-tool-v1`.

For OpenClaw-facing tool registration and policy artifacts, also see:

- `docs/openclaw-tools.md`
- `docs/openclaw-rollout-runbook.md`
- `docs/openclaw-release-notes.md`
- `.openclaw/skills/mysqlbot-openclaw/SKILL.md`

## Role boundary

- **mysqlbot** is the sole NL-query and analysis engine.
- **OpenClaw** is a caller that invokes mysqlbot through a stable contract.
- v1 does **not** allow OpenClaw to depend on mysqlbot frontend-specific streaming behavior.

## Contract version

- Version: `v1`
- Code reference: `backend/apps/openclaw/contract.py`

## Supported operations

- `session.bind`
  - Purpose: bind or create an OpenClaw conversation context against a mysqlbot chat/session
- `question.execute`
  - Purpose: execute a natural-language question against mysqlbot
- `analysis.execute`
  - Purpose: trigger analysis for an existing mysqlbot record
- `datasource.list`
  - Purpose: list datasources available to the authenticated caller scope

## Request schemas

The versioned request models are defined in `backend/apps/openclaw/contract.py`:

- `OpenClawSessionBindRequest`
- `OpenClawQuestionRequest`
- `OpenClawAnalysisRequest`
- `OpenClawDatasourceListRequest`

All request models:

- include `version = "v1"`
- include an `operation` field
- reject unknown fields (`extra = forbid`)

## Success envelope

Success responses use `OpenClawSuccessEnvelope`:

- `version`
- `status = "success"`
- `operation`
- `data`

## Error envelope

Failure responses use `OpenClawErrorEnvelope`:

- `version`
- `status = "error"`
- `operation`
- `error_code`
- `message`
- `detail` (optional)

Registered v1 error codes:

- `AUTH_INVALID`
- `AUTH_EXPIRED`
- `AUTH_DISABLED`
- `VALIDATION_ERROR`
- `DATASOURCE_NOT_FOUND`
- `SESSION_INVALID`
- `EXECUTION_TIMEOUT`
- `CONCURRENCY_EXCEEDED`
- `INTEGRATION_DISABLED`
- `EXECUTION_FAILURE`
- `LLM_FAILURE`
- `INTERNAL_ERROR`

The adapter normalizes all OpenClaw-facing failures into this error envelope family, including request validation failures, route-level execution timeouts, and upstream mysqlbot execution failures.

## Auth mode

The v1 contract reserves service-to-service authentication via:

- Header: `X-SQLBOT-ASK-TOKEN`
- Scheme: `sk`

This contract decision aligns with the existing mysqlbot service-style auth path in `backend/apps/system/middleware/auth.py`. The actual OpenClaw-facing auth/session implementation is completed in the follow-up auth task; this document only locks the v1 contract decision.

## Session lifecycle rule

- OpenClaw conversation scope is represented by `conversation_id`.
- If a valid `chat_id` is supplied on bind, mysqlbot reuses that chat only when it belongs to the authenticated caller and workspace scope.
- If `chat_id` is missing, mysqlbot creates a new chat for the authenticated caller.
- v1 bind creates or reuses the chat context only; it does not require streaming and does not create a question record by itself.
- If a supplied `chat_id` is missing, belongs to another caller scope, or conflicts with an explicitly requested datasource, mysqlbot rejects the bind as `SESSION_INVALID`.

This rule avoids creating orphan chats for every operation while keeping recovery behavior explicit for invalid session references.

## Transport mode

- Default transport: `http-json`
- Content type: `application/json`
- Default timeout: `120` seconds
- Streaming support in v1: `false`

Operational guardrails:

- `OPENCLAW_ENABLED` toggles the integration on or off for staged rollout.
- `OPENCLAW_REQUEST_TIMEOUT_SECONDS` controls the enforced request timeout used by question and analysis execution.
- `OPENCLAW_MAX_CONCURRENT_REQUESTS` controls route-level concurrency admission for the OpenClaw adapter surface.

Question and analysis operations enforce the documented timeout at the OpenClaw adapter boundary. When the timeout is exceeded, the adapter returns `EXECUTION_TIMEOUT` with the stable error envelope instead of leaking transport- or framework-specific timeout shapes.

Streaming may be added later as an optional extension, but it must not replace or break the mandatory non-streaming v1 contract.

## Compatibility rule

Breaking changes to request fields, success envelopes, error envelopes, auth mode, or timeout semantics require a new contract version.
