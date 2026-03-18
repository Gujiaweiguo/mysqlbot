## Why

The backend chat flow is concentrated in a few oversized files that mix API handling, orchestration, LLM interaction, SQL parsing, streaming, and persistence. We need an explicit backend module contract now so future chat work can be delivered with lower regression risk, clearer ownership, and better testability.

## What Changes

- Define a backend decomposition contract for the chat flow so HTTP handlers, orchestration, LLM pipeline, stream formatting, and persistence responsibilities are separated.
- Introduce a dedicated chat orchestration boundary that coordinates multi-step chat generation without embedding persistence and serialization details directly in the LLM implementation.
- Define a reusable streaming response contract for success, progress, and error events instead of repeating ad hoc SSE formatting in chat endpoints.
- Require persistence and record/log updates to flow through explicit backend adapters/services instead of direct cross-module coupling from the LLM layer.
- Preserve existing external chat API behavior while reorganizing backend internals behind stable boundaries.

## Capabilities

### New Capabilities
- `chat-backend-boundaries`: Defines required responsibility boundaries and dependency direction for backend chat API, orchestration, LLM processing, and persistence layers.
- `chat-streaming-contract`: Defines how backend chat streaming responses and streaming errors must be serialized and emitted consistently.

### Modified Capabilities
- None.

## Impact

- Affected backend areas will likely include `backend/apps/chat/api/chat.py`, `backend/apps/chat/task/llm.py`, `backend/apps/chat/curd/chat.py`, and related shared utilities/tests.
- No user-facing feature expansion is intended; the main impact is a safer internal contract for future chat/backend work.
- Verification scope should include existing chat API flows, stream/error behavior, and targeted backend tests around the new orchestration boundaries.
