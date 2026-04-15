# OpenClaw mysqlbot tool catalog

This document describes the OpenClaw-facing mysqlbot tools registered through the repository MCP surface.

## Discovery

The backend MCP server publishes the following FastAPI operations as discoverable tools:

- `openclaw_session_bind`
- `openclaw_question_execute`
- `openclaw_analysis_execute`
- `openclaw_datasource_list`

These operations are exposed through the existing `fastapi-mcp` setup in `backend/main.py` and delegate to the normalized OpenClaw adapter routes in `backend/apps/openclaw/router.py`.

## Tool to route mapping

| MCP operation | HTTP route | Purpose |
|---|---|---|
| `openclaw_session_bind` | `POST /api/v1/openclaw/session/bind` | Create or validate reusable mysqlbot chat context |
| `openclaw_question_execute` | `POST /api/v1/openclaw/question` | Run a datasource-backed natural-language question |
| `openclaw_analysis_execute` | `POST /api/v1/openclaw/analysis` | Run follow-up analysis on an existing mysqlbot record |
| `openclaw_datasource_list` | `POST /api/v1/openclaw/datasources` | List datasource choices visible to the authenticated caller |

## Invocation contract

All tools use the v1 OpenClaw contract documented in `docs/openclaw-integration.md` and modeled in `backend/apps/openclaw/contract.py`.

Common rules:

- transport: `http-json`
- auth header: `X-SQLBOT-ASK-TOKEN`
- auth scheme: `sk`
- stable success envelope: `{ version, status, operation, data }`
- stable error envelope: `{ version, status, operation, error_code, message, detail? }`

## Agent-facing output mapping

### `openclaw_session_bind`

Read these response fields:

- `data.conversation_id`
- `data.chat_id`
- `data.reused`
- `data.datasource_id`

Use `chat_id` for subsequent question or analysis calls.

### `openclaw_question_execute`

Read these response fields:

- `data.conversation_id`
- `data.chat_id`
- `data.result`

`data.result` is the mysqlbot response payload that downstream reasoning should summarize for the user. If a follow-up analysis is needed, preserve any returned record identifiers from that payload.

### `openclaw_analysis_execute`

Read these response fields:

- `data.conversation_id`
- `data.chat_id`
- `data.record_id`
- `data.action_type`
- `data.result`

Use `data.result` as the normalized analysis payload for downstream summaries.

### `openclaw_datasource_list`

Read these response fields:

- `data.conversation_id`
- `data.items`

Each item is already filtered to remove sensitive backend-only configuration fields.

## Example OpenClaw MCP registration

Project-local OpenClaw clients can register mysqlbot with an MCP server config similar to:

```json
{
  "mcp": {
    "servers": {
      "mysqlbot": {
        "url": "http://localhost:8001/mcp",
        "headers": {
          "X-SQLBOT-ASK-TOKEN": "sk ${MYSQLBOT_OPENCLAW_TOKEN}"
        }
      }
    }
  }
}
```

The skill at `.openclaw/skills/mysqlbot-openclaw/SKILL.md` should be loaded alongside this registration so agents know when to invoke mysqlbot and when not to.
