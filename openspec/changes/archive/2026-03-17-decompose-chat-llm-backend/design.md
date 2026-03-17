## Context

The backend chat flow is currently concentrated in `backend/apps/chat/task/llm.py`, `backend/apps/chat/curd/chat.py`, and `backend/apps/chat/api/chat.py`. Those files currently mix transport concerns, orchestration, LLM interaction, SQL parsing, stream serialization, and persistence updates, which makes the chat path difficult to reason about and expensive to test safely.

The goal of this change is not to redesign chat features or change public API semantics. The goal is to define a backend architecture that keeps the current chat behavior while making future work safer by introducing explicit boundaries between request handling, orchestration, pipeline stages, streaming, and persistence.

## Goals / Non-Goals

**Goals:**
- Establish a backend module contract for chat request handling, orchestration, LLM pipeline stages, stream emission, and persistence.
- Reduce direct cross-module coupling between `LLMService` and chat CRUD helpers.
- Define a shared streaming contract so chat endpoints stop repeating ad hoc SSE formatting and error emission.
- Preserve the current external `/chat` API behavior while moving internals behind better seams.
- Enable more targeted backend testing around orchestration, parsing, streaming, and persistence.

**Non-Goals:**
- Changing frontend behavior or frontend request contracts.
- Redesigning SQL generation prompts, recommendation behavior, or chart semantics.
- Replacing the model provider stack or changing supported datasource types.
- Broad application-wide refactoring outside the backend chat path.

## Decisions

### Decision 1: Split transport, orchestration, and persistence into separate layers

Chat HTTP handlers will remain responsible for transport concerns only: request decoding, dependency/context resolution, and selecting the response mode. A dedicated orchestration layer will own chat flow sequencing, while persistence adapters/services will own record and log mutation behavior.

**Why:**
- The current API handlers and `LLMService` both know too much about persistence and stream mechanics.
- Thin handlers and explicit orchestration boundaries make it easier to test chat logic without HTTP transport setup.

**Alternatives considered:**
- Keep the current monolithic `LLMService` and add helper functions around it: rejected because it preserves the main ownership problem.
- Move all chat logic into API handlers: rejected because it would worsen coupling.

### Decision 2: Decompose the LLM path into stage-focused collaborators

The backend chat pipeline will be broken into focused collaborators such as prompt/context preparation, model invocation, response parsing, and post-processing/persistence-facing stage handlers. The orchestrator coordinates these stages and passes typed intermediate results between them.

**Why:**
- `backend/apps/chat/task/llm.py` currently mixes many responsibilities that change for different reasons.
- Stage-focused collaborators allow narrower tests and lower-risk edits when only parsing, prompting, or persistence changes.

**Alternatives considered:**
- One smaller but still central “chat service” class: acceptable as an intermediate implementation step, but insufficient as the target contract.

### Decision 3: Introduce a shared streaming response contract

Streaming event serialization and streaming error emission will move behind a shared utility/adapter contract used by chat endpoints and orchestration.

**Why:**
- `backend/apps/chat/api/chat.py` currently repeats `_err(...)` SSE formatting patterns across multiple endpoints.
- A shared contract reduces duplication and keeps stream payload behavior consistent during refactors.

**Alternatives considered:**
- Preserve endpoint-local formatting helpers: rejected because consistency would remain fragile.

### Decision 4: Preserve external chat behavior during the internal split

The public `/chat` endpoints, request/response shape, and overall user-visible flow remain the compatibility target. Internal modules may move, but callers should not need frontend or integration changes for this refactor alone.

**Why:**
- This keeps the change scoped to backend maintainability rather than turning it into a feature or migration project.
- Existing regression and integration checks remain meaningful if external behavior stays stable.

**Alternatives considered:**
- Redesign response formats while refactoring internals: rejected as too broad and higher risk.

## Risks / Trade-offs

- **[Boundary drift during extraction]** → Define the dependency direction in specs first and reject convenience imports that recreate old coupling.
- **[Regression in stream behavior]** → Add shared stream contract tests and verify existing happy-path/error-path streaming responses.
- **[Partial refactor leaves two architectures at once]** → Sequence the implementation so old responsibilities are removed as new collaborators land.
- **[Session and transaction confusion]** → Keep persistence responsibilities behind explicit adapters/services and avoid hidden writes inside parsing/model helpers.
- **[Refactor scope expands into unrelated chat behavior]** → Keep prompt logic, datasource behavior, and frontend contracts out of scope unless required to preserve compatibility.

## Migration Plan

1. Define the target capability specs for backend boundaries and streaming behavior.
2. Introduce the orchestration and streaming contracts without changing public endpoint signatures.
3. Move persistence mutations behind dedicated adapters/services.
4. Extract stage-focused LLM collaborators from the current monolithic implementation.
5. Remove obsolete direct imports/cross-calls once the new path is verified.

Rollback remains straightforward because the change targets internal boundaries. If a decomposition step proves unstable, the implementation can pause at a compatible intermediate layer while keeping the current API contract intact.

## Open Questions

- Should `LLMService` remain as a thin facade during migration, or should orchestration move directly to a new top-level coordinator?
- Which existing xpack/dynamic-import hooks need stable extension points before persistence and orchestration are separated further?
- Should thread-pool and session lifecycle cleanup be included in this change, or handled in a follow-up performance-focused change once boundaries exist?
