## Why

Chat is the highest-change path in the codebase, but key responsibilities are still concentrated in a few oversized frontend and backend files. We need a staged decomposition contract now so future chat work can move faster with lower regression risk while preserving the existing user-facing chat behavior.

## What Changes

- Extend the backend chat boundary contract so staged extraction from monolithic modules happens through explicit orchestration and migration-safe seams.
- Define a frontend chat composition contract that separates page-shell concerns from message rendering, input handling, and stream/session state coordination.
- Extend the streaming contract so frontend chat surfaces consume stream events through one shared adapter path instead of view-local parsing.
- Preserve current external chat journeys and transport behavior while reorganizing internals behind better boundaries.

## Capabilities

### New Capabilities
- `chat-frontend-boundaries`: Defines required responsibility boundaries for the chat page shell, child components, and shared state/composables in the frontend.

### Modified Capabilities
- `chat-backend-boundaries`: Extend the backend boundary contract with staged-migration requirements for decomposition of the current monolithic chat modules.
- `chat-streaming-contract`: Extend the streaming contract so frontend consumers use one shared event-consumption path during and after the decomposition.

## Impact

- Affected areas will likely include `frontend/src/views/chat/index.vue`, new chat-focused frontend components/composables/stores, `backend/apps/chat/task/llm.py`, `backend/apps/chat/curd/chat.py`, and related chat tests.
- The compatibility target is unchanged chat behavior for users and integrations; the main impact is lower-maintenance internal structure.
- Verification should cover chat happy paths, streaming/error paths, and parity between embedded and standard chat surfaces after the split.
