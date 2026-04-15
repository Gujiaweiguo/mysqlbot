---
name: mysqlbot-openclaw
description: Use mysqlbot for datasource-backed querying and analysis through the registered OpenClaw MCP tools.
license: MIT
---

# mysqlbot OpenClaw policy

mysqlbot is the execution engine for datasource-backed natural-language querying and follow-up analysis.
This skill governs **when** the agent should invoke mysqlbot tools and **when it must not**.

## Registered tool flow

Use the registered mysqlbot MCP tools exposed from the OpenClaw adapter surface:

- `mysqlbot__openclaw_session_bind`
- `mysqlbot__openclaw_question_execute`
- `mysqlbot__openclaw_analysis_execute`
- `mysqlbot__openclaw_datasource_list`

Do **not** replace these with ad hoc shell commands or raw HTTP calls inside the skill.

## When to call mysqlbot

Invoke mysqlbot when the user asks for any of the following:

- a question about business data, metrics, trends, or database-backed facts
- a natural-language query that should become SQL or chart-ready structured output
- follow-up analysis on an existing mysqlbot result record
- discovery of available datasources before asking a data question

## When not to call mysqlbot

Do **not** invoke mysqlbot when the request is outside datasource-backed analysis, including:

- general knowledge questions
- creative writing, brainstorming, or summarization without datasource context
- code help, debugging, or repository questions
- pure reasoning or math tasks unrelated to mysqlbot-managed data

If the request is ambiguous and a datasource-backed question is only one possibility, clarify first instead of calling mysqlbot prematurely.

## Required inputs before invocation

### For datasource discovery

Call `mysqlbot__openclaw_datasource_list` with:

- `conversation_id`
- optional `language`

### For session setup

Call `mysqlbot__openclaw_session_bind` before the first query in a new conversation, or when a `chat_id` must be validated/reused.

Provide:

- `conversation_id`
- optional `chat_id`
- optional `datasource_id`
- optional `language`

### For question execution

Call `mysqlbot__openclaw_question_execute` only after you have enough context to ask a concrete datasource-backed question.

Provide:

- `conversation_id`
- `question`
- optional `chat_id`
- optional `datasource_id`
- optional `language`

### For analysis execution

Call `mysqlbot__openclaw_analysis_execute` only when you already have an existing mysqlbot record to analyze.

Provide:

- `conversation_id`
- `chat_id`
- `record_id`
- `action_type`
- optional `language`

## Auth and session rules

- mysqlbot tool calls require a valid service credential supplied by the OpenClaw MCP server configuration.
- Reuse `chat_id` when continuing the same mysqlbot-backed conversation.
- If the user changes datasource scope materially, bind or clarify before asking the next question.

## Output interpretation

Read only the documented envelope fields.

### Success envelope

- `status = success`
- `operation`
- `data`

Use these stable fields:

- `session.bind` → `data.chat_id`, `data.reused`, `data.datasource_id`
- `question.execute` → `data.chat_id`, `data.result`
- `analysis.execute` → `data.chat_id`, `data.record_id`, `data.result`
- `datasource.list` → `data.items`

### Error envelope

- `status = error`
- `error_code`
- `message`
- optional `detail`

React by error family:

- `AUTH_*` → stop and surface credential/setup failure
- `VALIDATION_ERROR` → fix missing or malformed inputs before retrying
- `SESSION_INVALID` → re-bind or ask for correct conversation context
- `DATASOURCE_NOT_FOUND` → ask the user to choose or confirm a datasource
- `EXECUTION_TIMEOUT`, `EXECUTION_FAILURE`, `LLM_FAILURE` → explain the failure briefly and retry only when appropriate

## Decision rule

If mysqlbot is not necessary to answer correctly, do not call it.
If mysqlbot is necessary, use the registered tool that matches the operation instead of recreating logic in the skill.
