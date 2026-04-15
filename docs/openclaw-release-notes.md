# OpenClaw mysqlbot Integration Release Notes

## Change summary

This release introduces the v1 OpenClaw → mysqlbot integration described by `integrate-openclaw-mysqlbot-mcp-tool-v1`.

mysqlbot remains the sole natural-language query and analysis engine. OpenClaw now calls mysqlbot through a stable adapter contract, MCP-discoverable tool operations, and a project-local invocation policy skill.

## Included scope

- versioned OpenClaw contract and stable success/error envelopes
- service-safe auth and session binding rules
- OpenClaw adapter routes for bind, question, analysis, and datasource list
- MCP-published OpenClaw operations and project-local skill policy
- observability, timeout, concurrency, and rollout guardrails
- integration/regression verification evidence under `.sisyphus/evidence/`

## Guardrails

- `OPENCLAW_ENABLED` for staged rollout and immediate fallback
- `OPENCLAW_REQUEST_TIMEOUT_SECONDS` for adapter-level timeout enforcement
- `OPENCLAW_MAX_CONCURRENT_REQUESTS` for route-level admission control
- structured `openclaw_api_observability` log events
- Prometheus metrics for OpenClaw request counts and duration

## Known limitations

- v1 is non-streaming only
- concurrency control is process-local
- OpenClaw-side installation and runtime policy loading are outside this repository’s rollout package

## Fallback path

If rollout stability is in doubt, disable the integration first:

```bash
OPENCLAW_ENABLED=false
```

Then restart the backend and re-run the rollback-state smoke checks documented in `docs/openclaw-rollout-runbook.md`.

## Evidence

Relevant evidence artifacts:

- `.sisyphus/evidence/task-7-e2e-success.txt`
- `.sisyphus/evidence/task-7-e2e-failure.txt`
- `.sisyphus/evidence/task-7-regression.txt`
- `.sisyphus/evidence/task-8-rollout.txt`
- `.sisyphus/evidence/task-8-rollback.txt`
