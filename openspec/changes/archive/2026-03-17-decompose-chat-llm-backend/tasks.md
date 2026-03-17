## 1. Contract and module scaffolding

- [x] 1.1 Create backend chat orchestration module boundaries and typed request/result objects for chat execution flows
- [x] 1.2 Add a shared chat streaming contract module for stream event and error serialization
- [x] 1.3 Add chat persistence collaborators/adapters that wrap record and log mutation responsibilities used by chat generation

## 2. Orchestration extraction

- [x] 2.1 Refactor `backend/apps/chat/api/chat.py` so chat endpoints delegate generation work to orchestration entry points instead of embedding stage flow details
- [x] 2.2 Extract stage-focused collaborators from `backend/apps/chat/task/llm.py` for model invocation, parsing, and post-processing responsibilities
- [x] 2.3 Introduce an orchestration coordinator that sequences question creation, generation stages, persistence updates, and finalization through explicit collaborators

## 3. Persistence and streaming migration

- [x] 3.1 Replace direct chat CRUD mutation calls inside the LLM pipeline with the new persistence collaborators
- [x] 3.2 Replace repeated endpoint-local SSE/error formatting in `backend/apps/chat/api/chat.py` with the shared chat streaming contract
- [x] 3.3 Remove obsolete direct imports and cross-module coupling once the orchestrated path is active

## 4. Verification

- [x] 4.1 Add or update backend tests covering chat endpoint delegation into orchestration entry points for the affected `/chat` flows
- [x] 4.2 Add or update backend tests covering shared streaming success, error, and completion behavior plus persistence-collaborator usage in extracted stages
- [x] 4.3 Run targeted backend validation for affected chat modules, including `uv run pytest` for relevant `tests/apps/chat/...` coverage and backend lint/type checks
