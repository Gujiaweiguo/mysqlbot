# OpenClaw mysqlbot Rollout and Rollback Runbook

> Scope: staged rollout, smoke verification, observability checks, and rollback for `integrate-openclaw-mysqlbot-mcp-tool-v1`.

## 1. Purpose and scope

This runbook covers the operational rollout of the OpenClaw → mysqlbot integration path introduced in Path 2.

In scope:

- staged enablement using the OpenClaw feature flag
- operator smoke checks for the OpenClaw adapter, chat regression, and MCP startup behavior
- observability checks for OpenClaw-origin traffic
- ordered rollback steps and fallback guidance

Out of scope:

- re-explaining the v1 contract in full
- OpenClaw client installation details outside this repository
- streaming behavior, which remains unsupported in v1

Authoritative references:

- `docs/openclaw-integration.md`
- `docs/openclaw-tools.md`
- `.openclaw/skills/mysqlbot-openclaw/SKILL.md`
- `.sisyphus/evidence/task-7-e2e-success.txt`
- `.sisyphus/evidence/task-7-e2e-failure.txt`
- `.sisyphus/evidence/task-7-regression.txt`

## 2. Prerequisites

### 2.1 Environment

- Backend can start successfully in the target environment.
- A valid OpenClaw service credential is provisioned for the target workspace/user scope.
- Operators can inspect backend logs and the `/metrics` endpoint.

### 2.2 Required settings

The rollout depends on these backend settings from `backend/common/core/config.py`:

- `OPENCLAW_ENABLED` — global rollout switch
- `OPENCLAW_REQUEST_TIMEOUT_SECONDS` — request timeout for question and analysis execution
- `OPENCLAW_MAX_CONCURRENT_REQUESTS` — route-level admission control limit

Suggested initial values:

```bash
OPENCLAW_ENABLED=false
OPENCLAW_REQUEST_TIMEOUT_SECONDS=120
OPENCLAW_MAX_CONCURRENT_REQUESTS=8
```

### 2.3 Auth and contract assumptions

OpenClaw calls the adapter using:

- Header: `X-SQLBOT-ASK-TOKEN`
- Scheme: `sk`

The stable adapter routes are:

- `POST /api/v1/openclaw/session/bind`
- `POST /api/v1/openclaw/question`
- `POST /api/v1/openclaw/analysis`
- `POST /api/v1/openclaw/datasources`

## 3. Staged rollout sequence

### 3.1 Deploy with rollout disabled

Set the feature flag off before the first deployment of this package:

```bash
OPENCLAW_ENABLED=false
```

Restart the backend using the environment’s normal control path.

### 3.2 Verify baseline regressions before enablement

From `backend/`, run:

```bash
uv run pytest tests/apps/chat/api/test_chat_orchestration.py tests/test_startup_smoke.py::test_main_import_initializes_mcp_only_when_enabled -v
```

Expected outcome:

- existing chat orchestration delegation remains green
- MCP startup initialization still behaves correctly

### 3.3 Enable OpenClaw integration

Turn the feature flag on:

```bash
OPENCLAW_ENABLED=true
```

Keep timeout and concurrency at their conservative defaults for the first rollout unless the target environment requires a different value.

### 3.4 Run OpenClaw smoke verification

From `backend/`, run:

```bash
uv run pytest tests/apps/openclaw/test_integration.py tests/apps/openclaw/test_router.py tests/apps/openclaw/test_service.py tests/apps/openclaw/test_contract.py -v
```

Expected outcome:

- bind → question success path passes
- bind → analysis success path passes
- auth failure path passes
- datasource/LLM-style normalized failure paths pass
- timeout, concurrency, and disabled-state guardrails pass

### 3.5 Confirm observability is live

Check logs for structured OpenClaw events:

- event name: `openclaw_api_observability`
- group: `openclaw`

Check `/metrics` output for:

- `sqlbot_openclaw_requests_total`
- `sqlbot_openclaw_request_duration_seconds`

## 4. Smoke test commands

These are the operator-facing smoke commands for first rollout and post-change verification.

### 4.1 OpenClaw success + failure coverage

```bash
uv run pytest tests/apps/openclaw/test_integration.py tests/apps/openclaw/test_router.py tests/apps/openclaw/test_service.py tests/apps/openclaw/test_contract.py -v
```

### 4.2 Existing chat regression

```bash
uv run pytest tests/apps/chat/api/test_chat_orchestration.py -v
```

### 4.3 MCP startup regression

```bash
uv run pytest tests/test_startup_smoke.py::test_main_import_initializes_mcp_only_when_enabled -v
```

### 4.4 Rollback-state regression

```bash
OPENCLAW_ENABLED=false uv run pytest tests/apps/chat/api/test_chat_orchestration.py tests/test_startup_smoke.py::test_main_import_initializes_mcp_only_when_enabled -v
```

## 5. Observability and triage

OpenClaw traffic is observable through the existing request-level middleware.

Look for these fields in structured logs:

- `event = openclaw_api_observability`
- `operation`
- `error_code`
- `status_code`
- `latency_ms`
- `severity`
- `alert_candidate`

### 5.1 First checks for degraded behavior

If operators observe elevated errors or latency:

1. Check whether `OPENCLAW_ENABLED` changed recently.
2. Inspect `error_code` values in OpenClaw observability logs.
3. Check whether `sqlbot_openclaw_requests_total` shows repeated `429`, `500`, or `504` outcomes.
4. Compare `OPENCLAW_MAX_CONCURRENT_REQUESTS` and `OPENCLAW_REQUEST_TIMEOUT_SECONDS` with current traffic shape.
5. Re-run the smoke commands from Section 4.

### 5.2 Common signal meanings

- `AUTH_INVALID` / `AUTH_EXPIRED` / `AUTH_DISABLED` → credential or service-token issue
- `SESSION_INVALID` → conversation/chat binding problem
- `DATASOURCE_NOT_FOUND` → wrong datasource scope or unavailable datasource
- `EXECUTION_TIMEOUT` → route-level timeout exceeded
- `CONCURRENCY_EXCEEDED` → admission control threshold hit
- `LLM_FAILURE` / `EXECUTION_FAILURE` → upstream mysqlbot execution issue
- `INTEGRATION_DISABLED` → rollout switch is off

## 6. Ordered rollback steps

### 6.1 Immediate fallback

If rollout quality is in doubt, turn the integration off first:

```bash
OPENCLAW_ENABLED=false
```

Restart the backend using the environment’s normal control path.

### 6.2 Verify safe fallback state

From `backend/`, run:

```bash
OPENCLAW_ENABLED=false uv run pytest tests/apps/chat/api/test_chat_orchestration.py tests/test_startup_smoke.py::test_main_import_initializes_mcp_only_when_enabled -v
```

Expected outcome:

- existing chat orchestration remains healthy
- MCP startup still initializes correctly
- OpenClaw adapter remains disabled rather than partially degraded

### 6.3 Code rollback order if feature-flag rollback is insufficient

Revert in reverse dependency order:

1. OCINT-006 — observability and guardrail changes
2. OCINT-005 — tool registration and skill policy artifacts
3. OCINT-004 — response/error/timeout normalization
4. OCINT-003 — adapter route surface

Do not revert earlier tasks unless the rollback explicitly requires removing the entire integration boundary.

## 7. Known limitations

- v1 is non-streaming only.
- Concurrency control is route-level and process-local.
- Timeout enforcement currently applies at the adapter boundary, not per downstream sub-stage.
- This rollout package covers mysqlbot-side behavior only; OpenClaw-side installation and policy loading are separate operator steps.

## 8. Release readiness checklist

- [ ] `OPENCLAW_ENABLED` remains off until baseline regressions pass.
- [ ] OpenClaw smoke commands from Section 4 pass in the target environment.
- [ ] Logs contain `openclaw_api_observability` events.
- [ ] Metrics contain `sqlbot_openclaw_requests_total` and `sqlbot_openclaw_request_duration_seconds`.
- [ ] Evidence files for tasks 7 and 8 are attached or preserved.
- [ ] Operators know the immediate fallback is `OPENCLAW_ENABLED=false`.
