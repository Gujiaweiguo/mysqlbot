## Context

mysqlbot already owns the full natural-language query and analysis pipeline through the existing chat orchestration, LLM execution, datasource resolution, persistence, and analysis stages. OpenClaw needs to call those capabilities as an external agent, but the current mysqlbot surfaces are split between frontend-oriented chat APIs and an MCP path that still assumes username/password token exchange and implementation-shaped responses.

This change is not an NL2SQL redesign. It is an integration boundary change that adds an OpenClaw-facing contract, service-safe authentication, explicit session reuse, normalized non-streaming responses, and the OpenClaw-side tool/skill policy needed to call mysqlbot safely. The change also affects observability, regression coverage, and rollout safety because the new caller is an external agent surface.

## Goals / Non-Goals

**Goals:**
- Keep mysqlbot as the sole NL-query and analysis engine.
- Expose a stable OpenClaw-facing MCP/tool contract that delegates to existing mysqlbot orchestration.
- Use service-to-service authentication and explicit workspace/chat/session rules.
- Standardize non-streaming success and failure envelopes for v1 tool consumption.
- Provide OpenClaw tool registration plus invocation-policy skill guidance without embedding mysqlbot business logic into the skill.
- Make OpenClaw-originated traffic observable, testable, and rollback-safe.

**Non-Goals:**
- Rewriting mysqlbot NL2SQL, SQL execution, chart generation, or analysis logic inside OpenClaw.
- Replacing current mysqlbot chat endpoints or the legacy MCP surface for existing consumers.
- Building a generic organization-wide AI gateway platform.
- Making streaming the only supported v1 contract.
- Introducing end-user credential exchange between OpenClaw and mysqlbot.

## Decisions

### Decision 1: Introduce a normalized OpenClaw-facing contract instead of exposing current chat or MCP internals directly

OpenClaw will consume a versioned contract that is designed for agent tools, not frontend streaming internals. The contract will provide explicit operations, normalized schemas, and stable error envelopes while continuing to delegate execution to mysqlbot chat orchestration.

**Why:**
- OpenClaw needs machine-parseable, long-lived semantics.
- Current frontend-oriented responses and `mcp_start` auth flow are too implementation-shaped for service integration.

**Alternatives considered:**
- Reuse `POST /chat/question` directly: rejected because it exposes frontend stream behavior as the primary integration contract.
- Reuse current `/mcp/*` unchanged: rejected because the auth and response model are not the intended v1 boundary.

### Decision 2: Use service-safe API key or service token authentication

The OpenClaw-facing integration will authenticate through a service credential path that maps to workspace/user context without requiring end-user username/password exchange.

**Why:**
- It removes the need for OpenClaw to store or proxy human credentials.
- It aligns better with service-to-service operation, revocation, and auditing.

**Alternatives considered:**
- Keep `mcp_start` username/password exchange: rejected because it increases security exposure and couples OpenClaw to user login flows.
- Anonymous or whitelisted access: rejected because workspace scoping, auditability, and rollback need explicit identity.

### Decision 3: Treat OpenClaw adapter routes as transport adapters over the stable chat orchestration entrypoint

The adapter layer will reuse existing orchestration entrypoints such as `question_answer_inner` and analysis flows rather than duplicating pipeline stages or persistence sequencing.

**Why:**
- mysqlbot already contains the mature execution path and compatibility target.
- Duplication would create behavior drift between web chat, legacy MCP, and OpenClaw.

**Alternatives considered:**
- Fork an OpenClaw-specific pipeline: rejected because it would create a second NL-query implementation surface.

### Decision 4: Make non-streaming JSON the mandatory v1 contract and keep streaming optional

The v1 contract will guarantee deterministic non-streaming success and failure envelopes. Streaming may be added later as an optional extension without changing the mandatory v1 behavior.

**Why:**
- Tool invocations need stable completion semantics and consistent error parsing.
- It reduces the number of transport and timeout edge cases in the first integration release.

**Alternatives considered:**
- Require streaming from day one: rejected because it increases contract complexity before the core service boundary is stable.

### Decision 5: Separate OpenClaw tool execution from skill policy

Tool definitions own execution against mysqlbot. The OpenClaw skill only tells the agent when to call mysqlbot, what minimum inputs to collect, and when not to call it.

**Why:**
- It preserves a single execution path and keeps the skill from becoming a second logic layer.
- It makes tool behavior testable and keeps policy changes independent from backend semantics.

**Alternatives considered:**
- Use skill-only HTTP calls: rejected because it is less stable, less testable, and easier to drift.

## Risks / Trade-offs

- **[OpenClaw-facing contract drifts from mysqlbot orchestration reality]** → Keep the adapter thin, base operations on existing entrypoints, and add contract-level integration tests.
- **[Service auth is secure but too rigid for multi-workspace use]** → Define explicit workspace scoping and revocation rules in the auth/session capability and cover them with failure-path tests.
- **[Session reuse policy creates hidden state bugs or orphaned chats]** → Make chat reuse explicit in the contract and verify sequential multi-turn behavior plus invalid-session recovery.
- **[Non-streaming v1 delays desired UX richness]** → Treat streaming as an optional extension that can be added after the stable base contract is verified.
- **[Observability is incomplete for the new caller path]** → Extend existing runtime observability and operator guidance rather than creating a separate monitoring stack.

## Migration Plan

1. Freeze the OpenClaw-facing contract and capability deltas in OpenSpec.
2. Implement service auth and session reuse rules before exposing any new adapter route.
3. Add the mysqlbot adapter endpoints that delegate to existing orchestration.
4. Normalize non-streaming success and failure envelopes.
5. Add the OpenClaw tool and invocation-policy skill.
6. Add observability, timeout, and concurrency guardrails.
7. Run end-to-end integration and regression coverage.
8. Roll out behind a staged enablement path with documented rollback order.

Rollback follows the reverse dependency order: disable rollout/feature flag, disable adapter routes or service credentials, and revert adapter-specific normalization and observability changes while leaving existing mysqlbot chat and legacy MCP behavior intact.

## Open Questions

- None for v1. Streaming remains an optional follow-up once the mandatory non-streaming contract is validated.
