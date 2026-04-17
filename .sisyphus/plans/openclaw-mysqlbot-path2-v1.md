# OpenClaw × mysqlbot Path 2 Integration Plan v1

## TL;DR
> **Summary**: Keep mysqlbot as the sole NL-query/analysis engine. Expose a stable OpenClaw-facing MCP/tool contract, add a thin adapter on both sides, and use skill only for invocation policy.
> **Deliverables**:
> - mysqlbot-side OpenClaw-facing contract and adapter
> - service-to-service auth/session strategy
> - normalized response/error schema
> - OpenClaw tool + skill integration package
> - end-to-end verification and rollback package
> **Effort**: Large
> **Parallel**: YES - 3 waves
> **Critical Path**: OCINT-001 → OCINT-002 → OCINT-003 → OCINT-005 → OCINT-007 → OCINT-008

## Context
### Original Request
基于路径2生成唯一执行计划：mysqlbot 保持自然语言查询分析核心能力，OpenClaw 通过 MCP/tool 接入，skill 仅做调用策略；计划输出到 `.sisyphus/plans/*.md`，不写 OpenSpec；每个任务包含任务ID、输入/输出、验收标准、回滚方案，标注依赖顺序与风险等级，并给出建议的 change ID。该计划作为 Atlas/Hephaestus 唯一执行依据。

### Interview Summary
- 已比较 3 条路径，明确选择路径 2。
- mysqlbot 已具备完整 NL2SQL / analysis / predict / chart / RAG / 会话能力，核心入口位于 `backend/apps/chat/api/chat.py`、`backend/apps/chat/orchestration/coordinator.py`、`backend/apps/chat/task/llm.py`。
- mysqlbot 已存在 `backend/apps/mcp/mcp.py` 与 `main.py` 中的 MCP 暴露，但当前认证方式与返回合同不适合作为 OpenClaw v1 的最终边界。
- OpenClaw 适合通过 MCP/tool + skill 接入已有能力，而非重做 mysqlbot 引擎。

### Metis Review (gaps addressed)
- 采用 **服务集成认证**，不使用 `mcp_start` 的用户名/密码换 token 流程。
- v1 默认 **稳定非流式 JSON 合同优先**；流式作为可选增强，不阻塞首发。
- 明确 **chat/session 复用策略**，避免每轮创建孤儿 chat。
- 明确 **OpenClaw-facing 合同与错误合同**，避免直接暴露 mysqlbot 当前内部/前端导向响应形态。
- v1 约束为 **mysqlbot 核心复用 + OpenClaw 轻量 adapter/skill**，不扩张到通用 MCP 网关或重构整个 orchestration。

## Change Control
- **Suggested Change ID**: `integrate-openclaw-mysqlbot-mcp-tool-v1`
- **Plan Authority**: This file is the sole execution basis for Atlas/Hephaestus.
- **Plan Version**: v1

## Work Objectives
### Core Objective
让 OpenClaw 以 MCP/tool 方式稳定调用 mysqlbot 的自然语言查询分析能力，同时保持 mysqlbot 作为唯一 NL-query/analysis 执行引擎，并以 skill 仅负责调用时机与参数组织。

### Deliverables
- mysqlbot OpenClaw-facing adapter contract
- OpenClaw service auth + session lifecycle design and implementation
- normalized request/response/error contract
- OpenClaw tool registration and skill policy package
- observability, integration tests, rollout and rollback artifacts

### Definition of Done (verifiable conditions with commands)
- mysqlbot 仓库新增并启用 OpenClaw-facing 对接面，且不破坏既有 `/chat/*` 与 `/mcp/*` 行为
- OpenClaw 能通过 tool 成功完成：鉴权 → 建立/复用会话 → 提问 → 获取结构化结果 → 触发 analysis
- 至少存在一条失败路径验证：认证失败、无效 datasource、LLM/SQL 执行失败时返回稳定错误合同
- 关键验证命令在实现后应全部通过：
  - `bash scripts/lint.sh` (backend)
  - `uv run pytest tests/apps/chat tests/apps/mcp` (backend)
  - `npm run typecheck` (frontend/OpenClaw side if repo-local)
  - 适配方自定义集成测试命令（由执行者补充到对应 repo）

### Must Have
- mysqlbot 继续承载 NL2SQL / analysis / predict 核心逻辑
- OpenClaw 通过受控 tool/MCP 边界调用 mysqlbot
- service-to-service 认证，不暴露最终用户密码给 OpenClaw
- 统一结构化成功/失败合同
- 可复用的 chat/session 生命周期
- Atlas/Hephaestus 可按本计划逐任务执行并验证

### Must NOT Have (guardrails, AI slop patterns, scope boundaries)
- 不在 OpenClaw 内重写 mysqlbot LLM pipeline
- 不直接将前端专用 `/chat/question` 原始流式细节裸暴露为 OpenClaw 的唯一合同
- 不引入新的泛化“AI 网关平台”作为 v1 范围
- 不使用明文用户名密码给 OpenClaw 换取用户 token
- 不在未定义稳定错误合同前直接联通生产流量

## Verification Strategy
> ZERO HUMAN INTERVENTION - all verification is agent-executed.
- Test decision: tests-after + existing backend pytest / frontend typecheck + OpenClaw integration verification
- QA policy: Every task includes executable happy-path + failure-path scenarios
- Evidence: `.sisyphus/evidence/task-{N}-{slug}.{ext}`

## Execution Strategy
### Parallel Execution Waves
> Target: 5-8 tasks per wave. <3 per wave (except final) = under-splitting.
> Extract shared dependencies as Wave-1 tasks for max parallelism.

Wave 1: contract and boundary lock-in
- OCINT-001 Contract + transport decision
- OCINT-002 Auth and session strategy

Wave 2: implementation surfaces
- OCINT-003 mysqlbot adapter endpoint implementation
- OCINT-004 response/error normalization
- OCINT-005 OpenClaw tool + skill integration

Wave 3: hardening and rollout
- OCINT-006 observability + rate/timeout guardrails
- OCINT-007 end-to-end integration verification
- OCINT-008 rollout + rollback package

### Dependency Matrix (full, all tasks)
| Task ID | Depends On | Blocks |
|---|---|---|
| OCINT-001 | none | OCINT-002, OCINT-003, OCINT-005 |
| OCINT-002 | OCINT-001 | OCINT-003, OCINT-005, OCINT-007 |
| OCINT-003 | OCINT-001, OCINT-002 | OCINT-004, OCINT-006, OCINT-007 |
| OCINT-004 | OCINT-003 | OCINT-005, OCINT-007 |
| OCINT-005 | OCINT-001, OCINT-002, OCINT-004 | OCINT-007 |
| OCINT-006 | OCINT-003 | OCINT-007, OCINT-008 |
| OCINT-007 | OCINT-002, OCINT-004, OCINT-005, OCINT-006 | OCINT-008 |
| OCINT-008 | OCINT-006, OCINT-007 | Final Verification Wave |

### Agent Dispatch Summary (wave → task count → categories)
| Wave | Tasks | Categories |
|---|---:|---|
| 1 | 2 | deep, ultrabrain |
| 2 | 3 | deep, quick, writing |
| 3 | 3 | unspecified-high, deep, writing |
| Final | 4 | oracle, unspecified-high, deep |

## TODOs
> Implementation + Test = ONE task. Never separate.
> EVERY task MUST have: Agent Profile + Parallelization + QA Scenarios.

- [x] 1. OCINT-001 — Lock OpenClaw-facing contract and transport

  **Risk Level**: High
  **What to do**: Decide and document the exact OpenClaw-facing integration contract. Confirm mysqlbot remains system-of-record for NL-query/analysis. Define whether OpenClaw talks to mysqlbot through existing MCP transport, a normalized MCP-compatible adapter, or a thin tool-facing HTTP facade backed by the same orchestration. v1 decision: keep MCP/tool semantics, but publish a normalized contract that OpenClaw can rely on without depending on mysqlbot frontend stream internals. Freeze endpoint names, request schema, response schema, error schema, transport mode, timeout policy, and versioning strategy.
  **Must NOT do**: Do not reuse `mcp_start` username/password exchange as the final service auth contract. Do not leave response shape “same as current implementation.”

  **Inputs**:
  - Current mysqlbot surfaces in `backend/apps/mcp/mcp.py`, `backend/apps/chat/api/chat.py`, `backend/apps/api.py`, `backend/main.py`
  - OpenClaw tool/MCP integration requirements from its target environment
  - Selected path-2 architecture constraints

  **Outputs**:
  - Versioned OpenClaw-facing API/tool contract
  - Transport decision note (non-streaming default, optional streaming extension)
  - Error envelope and compatibility rules

  **Recommended Agent Profile**:
  - Category: `deep` - Reason: contract design with cross-system implications
  - Skills: `[]` - no special skill required beyond repository analysis
  - Omitted: [`frontend-ui-ux`] - no UI design work

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: OCINT-002, OCINT-003, OCINT-005 | Blocked By: none

  **References**:
  - Pattern: `backend/apps/mcp/mcp.py` - existing external integration surface to evaluate and refine
  - Pattern: `backend/apps/chat/api/chat.py` - current chat/question and analysis endpoints used by the core flow
  - Pattern: `backend/apps/chat/orchestration/coordinator.py` - orchestration boundary to preserve
  - Pattern: `backend/apps/chat/task/llm.py` - underlying NL-query/analysis execution pipeline to reuse
  - Pattern: `backend/main.py` - current MCP app exposure and middleware stack

  **Acceptance Criteria**:
  - [ ] A single contract document or code-adjacent spec exists in-repo and names the exact OpenClaw-facing operations, schemas, auth mode, timeout policy, and versioning rule.
  - [ ] The contract explicitly states that mysqlbot is the sole NL-query/analysis engine and OpenClaw is a caller only.
  - [ ] The contract defines a stable non-streaming success envelope and stable error envelope.
  - [ ] The contract lists any optional streaming behavior as non-blocking to v1.

  **QA Scenarios**:
  ```
  Scenario: Contract freeze review
    Tool: Bash
    Steps: Run repository validation commands plus any schema snapshot comparison chosen by the implementer; confirm new contract files or endpoint docs exist and map 1:1 to implementation symbols.
    Expected: Contract artifact exists, names each operation unambiguously, and matches the implementation entrypoints.
    Evidence: .sisyphus/evidence/task-1-contract-freeze.txt

  Scenario: Contract ambiguity rejection
    Tool: Bash
    Steps: Execute a schema validation or test case with an intentionally omitted required field and inspect the documented/implemented rejection path.
    Expected: Request is rejected with the documented stable error envelope, not an opaque 500 or framework-default trace.
    Evidence: .sisyphus/evidence/task-1-contract-error.txt
  ```

  **Rollback**: Revert only the new OpenClaw-facing contract artifacts and route registrations introduced for v1; leave existing `/chat/*` and `/mcp/*` behaviors untouched.
  **Commit**: YES | Message: `feat(integration): define openclaw mysqlbot contract v1` | Files: `[backend/apps/**, docs/spec files if added]`

- [x] 2. OCINT-002 — Establish service auth and chat/session lifecycle

  **Risk Level**: High
  **What to do**: Define and implement the service-to-service auth path OpenClaw will use. Preferred default: API key or service token path compatible with mysqlbot middleware/security model, not end-user credentials. Define how OpenClaw obtains or stores credentials, how mysqlbot maps them to workspace/user context, how chat IDs are created/reused, how session expiry is handled, and how orphaned chats are avoided. Decide whether each OpenClaw conversation maps to one mysqlbot chat or one mysqlbot record sequence.
  **Must NOT do**: Do not require OpenClaw to store human usernames/passwords. Do not create a new mysqlbot chat for every single tool invocation without reuse policy.

  **Inputs**:
  - OCINT-001 contract
  - Existing auth flows in `backend/apps/system/api/login.py`, `backend/apps/system/api/apikey.py`, `apps/system/middleware/auth.py`
  - Existing chat creation flow in `backend/apps/chat/api/chat.py` and `backend/apps/chat/crud/chat.py`

  **Outputs**:
  - Auth flow implementation or adaptation
  - Session lifecycle rules
  - Workspace/chat mapping contract

  **Recommended Agent Profile**:
  - Category: `ultrabrain` - Reason: auth/session coupling and tenancy decisions are high-impact
  - Skills: `[]`
  - Omitted: [`git-master`] - no git operation needed in implementation guidance

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: OCINT-003, OCINT-005, OCINT-007 | Blocked By: OCINT-001

  **References**:
  - Pattern: `backend/apps/system/api/apikey.py` - external/service auth candidate
  - Pattern: `backend/apps/system/middleware/auth.py` - middleware-supported token patterns
  - Pattern: `backend/apps/mcp/mcp.py` - current MCP auth pattern to avoid as final v1 contract
  - Pattern: `backend/apps/chat/crud/chat.py` - chat creation and record persistence behavior
  - API/Type: `backend/common/core/deps.py` - current user resolution pattern

  **Acceptance Criteria**:
  - [ ] OpenClaw can authenticate without end-user password exchange.
  - [ ] A documented chat/session reuse rule exists and is implemented.
  - [ ] Expired or invalid credentials return documented auth errors.
  - [ ] Workspace/user scoping is explicit and test-covered.

  **QA Scenarios**:
  ```
  Scenario: Valid service auth and session reuse
    Tool: Bash
    Steps: Obtain or configure the OpenClaw service credential, create/reuse one chat/session through the chosen endpoint, send two sequential questions tied to the same conversation context.
    Expected: Both requests succeed under one documented chat/session strategy; no duplicate orphan chats are created beyond the policy.
    Evidence: .sisyphus/evidence/task-2-auth-session.txt

  Scenario: Invalid or expired credential
    Tool: Bash
    Steps: Call the OpenClaw-facing endpoint with an invalid, disabled, or expired service credential.
    Expected: Request is rejected with the documented auth error envelope and no chat side effects are persisted.
    Evidence: .sisyphus/evidence/task-2-auth-error.txt
  ```

  **Rollback**: Disable the new service credential path and fall back to no OpenClaw integration while preserving existing login/API key behavior for other callers.
  **Commit**: YES | Message: `feat(auth): add openclaw service auth and session policy` | Files: `[backend/apps/system/**, backend/apps/chat/**, backend/common/**]`

- [x] 3. OCINT-003 — Implement mysqlbot OpenClaw adapter endpoints

  **Risk Level**: High
  **What to do**: Implement the mysqlbot-side adapter surface that OpenClaw calls. Reuse `question_answer_inner` / orchestration rather than duplicating NL-query logic. Provide explicit operations for the minimum viable capability set: create-or-bind session, ask natural-language question, request analysis on an existing record, and optionally list datasources if required by OpenClaw tool policy. Ensure route registration and middleware behavior are intentional.
  **Must NOT do**: Do not fork `LLMService` logic. Do not expose raw internal persistence models as public contract.

  **Inputs**:
  - OCINT-001 contract
  - OCINT-002 auth/session decisions
  - Core execution flow in `backend/apps/chat/api/chat.py` and orchestration modules

  **Outputs**:
  - New or revised adapter routes
  - Request/response models for OpenClaw integration
  - Route registration and middleware alignment

  **Recommended Agent Profile**:
  - Category: `deep` - Reason: thin integration layer over sensitive orchestration code
  - Skills: `[]`
  - Omitted: [`review-work`] - post-implementation review belongs to final verification, not task execution

  **Parallelization**: Can Parallel: NO | Wave 2 | Blocks: OCINT-004, OCINT-006, OCINT-007 | Blocked By: OCINT-001, OCINT-002

  **References**:
  - Pattern: `backend/apps/chat/api/chat.py` - existing reusable orchestration entrypoint
  - Pattern: `backend/apps/chat/orchestration/coordinator.py` - question/analysis orchestration
  - Pattern: `backend/apps/chat/orchestration/runtime.py` - runtime response creation
  - Pattern: `backend/apps/mcp/mcp.py` - prior external integration surface for comparison
  - Pattern: `backend/apps/api.py` - router registration pattern

  **Acceptance Criteria**:
  - [ ] OpenClaw-facing routes compile and register correctly.
  - [ ] Adapter routes reuse mysqlbot orchestration and do not duplicate NL-query pipeline logic.
  - [ ] Minimum capability set is callable through the stable contract.
  - [ ] Existing web chat and legacy MCP paths remain unaffected by regression tests.

  **QA Scenarios**:
  ```
  Scenario: Ask question through adapter
    Tool: Bash
    Steps: Start from a valid OpenClaw-authenticated session, call the ask-question operation with a representative NL question and inspect the structured response.
    Expected: mysqlbot executes the existing orchestration path and returns the contract-defined payload without exposing internal-only fields.
    Evidence: .sisyphus/evidence/task-3-ask-question.txt

  Scenario: Unsupported operation payload
    Tool: Bash
    Steps: Call one adapter endpoint with an invalid enum, missing record reference, or malformed body.
    Expected: Adapter returns the documented validation/error envelope and does not crash the underlying orchestration service.
    Evidence: .sisyphus/evidence/task-3-invalid-payload.txt
  ```

  **Rollback**: Unregister only the new adapter routes/models and revert to the pre-existing mysqlbot API surface.
  **Commit**: YES | Message: `feat(mcp): add openclaw adapter endpoints` | Files: `[backend/apps/mcp/** or backend/apps/openclaw/**, backend/apps/api.py]`

- [x] 4. OCINT-004 — Normalize response, error, and timeout behavior

  **Risk Level**: Medium
  **What to do**: Wrap the adapter endpoints in a stable output contract. Normalize success payloads for question, analysis, and metadata calls. Normalize failure payloads for auth errors, validation errors, datasource errors, SQL execution errors, and LLM failures. Define timeout behavior and partial-result behavior. Keep the non-streaming contract as the mandatory v1 interface; document how streaming may be exposed later without breaking v1.
  **Must NOT do**: Do not leak raw stack traces or framework-default exceptions. Do not leave different endpoint families returning incompatible envelopes.

  **Inputs**:
  - OCINT-003 adapter implementation
  - Existing response behaviors from `backend/apps/chat/streaming/events.py`, `backend/apps/chat/task/runner.py`, `backend/apps/chat/task/stages.py`

  **Outputs**:
  - Stable response envelope implementation
  - Stable error envelope implementation
  - Timeout and retry semantics for callers

  **Recommended Agent Profile**:
  - Category: `quick` - Reason: bounded surface once contract and endpoints exist
  - Skills: `[]`
  - Omitted: [`dev-browser`] - no browser interaction needed

  **Parallelization**: Can Parallel: NO | Wave 2 | Blocks: OCINT-005, OCINT-007 | Blocked By: OCINT-003

  **References**:
  - Pattern: `backend/apps/chat/streaming/events.py` - current streaming event vocabulary to adapt, not expose directly
  - Pattern: `backend/apps/chat/task/runner.py` - async task/result boundaries
  - Pattern: `backend/apps/chat/task/stages.py` - result stage parsing and failure points
  - Pattern: `backend/common/core/response_middleware.py` - existing response wrapping behavior to align with or intentionally bypass

  **Acceptance Criteria**:
  - [ ] Every OpenClaw-facing endpoint returns one documented success envelope and one documented error envelope family.
  - [ ] Timeout behavior is deterministic and test-covered.
  - [ ] SQL/LLM/datasource failures are machine-parseable by OpenClaw.
  - [ ] No raw traceback or inconsistent field naming escapes the adapter surface.

  **QA Scenarios**:
  ```
  Scenario: Successful normalized response
    Tool: Bash
    Steps: Call question and analysis operations through the adapter, capturing the JSON payloads.
    Expected: Both payloads follow the documented stable envelope with predictable field names and status semantics.
    Evidence: .sisyphus/evidence/task-4-success-envelope.json

  Scenario: SQL or LLM failure normalization
    Tool: Bash
    Steps: Trigger a controlled datasource/LLM error condition through the adapter.
    Expected: Failure returns the documented error envelope with a machine-parseable code and no internal trace leakage.
    Evidence: .sisyphus/evidence/task-4-error-envelope.json
  ```

  **Rollback**: Revert adapter-specific response normalization and return the system to pre-adapter behavior while disabling the OpenClaw-facing endpoints.
  **Commit**: YES | Message: `feat(api): normalize openclaw adapter responses` | Files: `[backend/apps/mcp/** or backend/apps/openclaw/**, backend/common/**]`

- [x] 5. OCINT-005 — Implement OpenClaw tool registration and skill policy

  **Risk Level**: Medium
  **What to do**: Implement the OpenClaw-side integration package. Register one or more tools that call the mysqlbot OpenClaw-facing contract. Add skill instructions that tell the OpenClaw agent when to invoke mysqlbot, required parameters to collect, when to prefer analysis over free-form reasoning, and when not to call mysqlbot. Keep skill logic thin and policy-oriented; all execution happens through the tool contract.
  **Must NOT do**: Do not encode mysqlbot business logic into the skill. Do not bypass the tool contract with ad hoc curl/exec calls in production mode.

  **Inputs**:
  - OCINT-001 contract
  - OCINT-002 auth/session flow
  - OCINT-004 normalized response contract

  **Outputs**:
  - OpenClaw tool definitions
  - Skill policy file/package
  - Mapping of tool outputs to agent-facing summaries

  **Recommended Agent Profile**:
  - Category: `writing` - Reason: skill policy quality matters as much as tool glue
  - Skills: `[]`
  - Omitted: [`openspec-propose`] - explicit instruction forbids switching to OpenSpec

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: OCINT-007 | Blocked By: OCINT-001, OCINT-002, OCINT-004

  **References**:
  - External: OpenClaw tool/MCP/skill integration docs used during research - follow its native tool registration pattern
  - Pattern: `backend/apps/mcp/mcp.py` - operation naming cues, not final contract source
  - Pattern: `backend/apps/chat/api/chat.py` - capability mapping for question and analysis operations

  **Acceptance Criteria**:
  - [ ] OpenClaw can discover and invoke the mysqlbot tool(s) without custom shell fallbacks.
  - [ ] The skill explicitly describes when to call mysqlbot and when not to.
  - [ ] Tool invocation handles auth/session according to OCINT-002.
  - [ ] Tool output mapping is stable enough for downstream agent reasoning.

  **QA Scenarios**:
  ```
  Scenario: Tool-driven successful query
    Tool: Bash
    Steps: Run the OpenClaw-side integration test or dev command that invokes the registered tool against the mysqlbot adapter using a representative NL query.
    Expected: OpenClaw chooses the tool, the tool calls mysqlbot successfully, and the agent receives a structured result it can summarize.
    Evidence: .sisyphus/evidence/task-5-tool-success.txt

  Scenario: Skill blocks unnecessary mysqlbot call
    Tool: Bash
    Steps: Run a prompt classified by the skill as general reasoning/non-database work.
    Expected: OpenClaw does not call the mysqlbot tool and instead responds per the skill policy.
    Evidence: .sisyphus/evidence/task-5-skill-no-call.txt
  ```

  **Rollback**: Disable or remove the new OpenClaw tool/skill package while leaving mysqlbot adapter endpoints dormant and undocumented to end users.
  **Commit**: YES | Message: `feat(openclaw): add mysqlbot tool and skill policy` | Files: `[OpenClaw integration files in target repo/workspace]`

- [x] 6. OCINT-006 — Add observability, concurrency, and timeout guardrails

  **Risk Level**: Medium
  **What to do**: Add logs, metrics, and correlation IDs for OpenClaw-originated traffic. Ensure request tracing can connect OpenClaw invocation → mysqlbot adapter → chat/orchestration run → datasource/LLM outcome. Add reasonable timeout, retry, and concurrency guardrails so multiple OpenClaw calls do not degrade mysqlbot unpredictably. If feature flags or config switches are needed, add them here.
  **Must NOT do**: Do not introduce a brand-new observability platform. Do not silently swallow timeout/rate-limit failures.

  **Inputs**:
  - OCINT-003 adapter surface
  - Existing middleware and observability hooks in `backend/main.py`
  - Existing logging/audit conventions

  **Outputs**:
  - Structured logs/metrics/tracing additions
  - Configurable timeout/concurrency guardrails
  - Feature flag or rollout switch if needed

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Reason: cross-cutting infra hardening
  - Skills: `[]`
  - Omitted: [`playwright`] - no browser needed

  **Parallelization**: Can Parallel: YES | Wave 3 | Blocks: OCINT-007, OCINT-008 | Blocked By: OCINT-003

  **References**:
  - Pattern: `backend/main.py` - middleware chain and observability setup
  - Pattern: `backend/common/audit/**` - audit/log patterns already used in the repo
  - Pattern: `backend/apps/chat/task/runner.py` - concurrency/task behavior to monitor

  **Acceptance Criteria**:
  - [ ] OpenClaw-origin requests are distinguishable in logs/metrics.
  - [ ] Timeout policy is configurable and enforced.
  - [ ] Concurrency/rate failure paths are observable and machine-parseable.
  - [ ] A feature flag or rollout switch exists if rollout requires staged enablement.

  **QA Scenarios**:
  ```
  Scenario: Correlated success path logging
    Tool: Bash
    Steps: Execute one successful OpenClaw-driven request and collect logs/metrics for the full path.
    Expected: A correlation identifier or equivalent trace can connect request entry, orchestration, and response completion.
    Evidence: .sisyphus/evidence/task-6-observability.txt

  Scenario: Timeout or concurrency guardrail
    Tool: Bash
    Steps: Trigger concurrent or intentionally slow requests within the configured limits.
    Expected: System enforces the configured guardrail and emits the documented machine-parseable failure signal.
    Evidence: .sisyphus/evidence/task-6-guardrail.txt
  ```

  **Rollback**: Turn off the OpenClaw feature flag and revert only the adapter-specific observability/guardrail configuration.
  **Commit**: YES | Message: `chore(integration): add openclaw observability guardrails` | Files: `[backend/main.py, backend/common/**, adapter config files]`

- [x] 7. OCINT-007 — Execute end-to-end integration and regression verification

  **Risk Level**: High
  **What to do**: Build automated integration coverage that validates the full path: auth → session bind/reuse → question → answer → analysis → failure handling. Add regression coverage to ensure existing mysqlbot web chat and legacy MCP surfaces still work. Capture evidence artifacts for both success and failure paths.
  **Must NOT do**: Do not rely on manual screenshots or ad hoc local verification only. Do not skip regression on existing chat APIs.

  **Inputs**:
  - OCINT-002 auth/session implementation
  - OCINT-004 response/error normalization
  - OCINT-005 OpenClaw tool/skill integration
  - OCINT-006 guardrails

  **Outputs**:
  - Automated E2E integration tests
  - Regression test updates
  - Evidence bundle for release gate

  **Recommended Agent Profile**:
  - Category: `deep` - Reason: multi-system verification and regression analysis
  - Skills: `[]`
  - Omitted: [`ai-slop-remover`] - not relevant to integration verification

  **Parallelization**: Can Parallel: NO | Wave 3 | Blocks: OCINT-008 | Blocked By: OCINT-002, OCINT-004, OCINT-005, OCINT-006

  **References**:
  - Test: `backend/tests/apps/chat/test_chat_orchestration.py` - orchestration test style to extend
  - Test: `frontend/e2e/chat.spec.ts` - existing chat experience contracts to protect
  - Pattern: `frontend/e2e/fixtures/chat-fixtures.ts` - request mocking patterns if frontend regressions need extension
  - Pattern: `backend/tests/apps/chat/**` and `backend/tests/apps/mcp/**` - target areas for contract/regression coverage

  **Acceptance Criteria**:
  - [ ] Automated tests cover at least one successful question flow and one successful analysis flow from OpenClaw to mysqlbot.
  - [ ] Automated tests cover at least auth failure and datasource/LLM failure paths.
  - [ ] Regression tests demonstrate no breakage to existing mysqlbot chat and MCP behavior.
  - [ ] Evidence artifacts are saved in the expected `.sisyphus/evidence/` paths during execution.

  **QA Scenarios**:
  ```
  Scenario: End-to-end success path
    Tool: Bash
    Steps: Run the full automated integration suite against a configured test environment covering auth, question, and analysis.
    Expected: All success-path assertions pass and evidence artifacts are emitted.
    Evidence: .sisyphus/evidence/task-7-e2e-success.txt

  Scenario: End-to-end failure path
    Tool: Bash
    Steps: Run the suite with invalid credentials or a forced downstream failure.
    Expected: Failure path returns the documented error contract and tests pass by asserting correct degradation behavior.
    Evidence: .sisyphus/evidence/task-7-e2e-failure.txt
  ```

  **Rollback**: If verification uncovers instability, disable feature rollout and revert OCINT-003 through OCINT-006 in reverse dependency order.
  **Commit**: YES | Message: `test(integration): verify openclaw mysqlbot path2 e2e` | Files: `[backend/tests/**, frontend/e2e/**, OpenClaw integration tests]`

- [x] 8. OCINT-008 — Prepare rollout, release notes, and operational rollback package

  **Risk Level**: Medium
  **What to do**: Prepare the release package for Atlas/Hephaestus execution completion. Document enablement flags, deployment ordering, credential provisioning steps, smoke-test commands, rollback sequencing, and operator runbook notes. Ensure rollout can be staged and reversed without affecting existing mysqlbot consumers. This task closes the execution package and makes the change operable.
  **Must NOT do**: Do not assume one-shot cutover with no rollback path. Do not leave credential provisioning undocumented.

  **Inputs**:
  - OCINT-006 guardrails
  - OCINT-007 verification evidence
  - Suggested change ID and deployment environment assumptions

  **Outputs**:
  - Rollout checklist
  - Operational runbook
  - Ordered rollback steps
  - Release note summary for stakeholders

  **Recommended Agent Profile**:
  - Category: `writing` - Reason: operator-facing precision matters most here
  - Skills: `[]`
  - Omitted: [`git-master`] - no git workflow work required in the task itself

  **Parallelization**: Can Parallel: NO | Wave 3 | Blocks: Final Verification Wave | Blocked By: OCINT-006, OCINT-007

  **References**:
  - Pattern: `README.md` - existing environment/runbook style
  - Pattern: `docs/regression/**` - release gate and regression documentation style
  - Pattern: `backend/apps/system/api/apikey.py` - credential lifecycle reference if API key path is used

  **Acceptance Criteria**:
  - [ ] Rollout sequence is explicit, staged, and environment-aware.
  - [ ] Rollback sequence is explicit and ordered by dependency.
  - [ ] Smoke tests are executable by agents/operators without hidden context.
  - [ ] Release notes identify scope, guardrails, known limitations, and fallback path.

  **QA Scenarios**:
  ```
  Scenario: Staged rollout simulation
    Tool: Bash
    Steps: Execute the documented smoke-test commands in a staging or isolated environment with the feature flag enabled.
    Expected: The documented rollout sequence works as written and passes smoke verification.
    Evidence: .sisyphus/evidence/task-8-rollout.txt

  Scenario: Rollback simulation
    Tool: Bash
    Steps: Execute the documented rollback steps in the same environment.
    Expected: OpenClaw integration is disabled cleanly, existing mysqlbot chat behavior remains healthy, and no orphaned partial state blocks recovery.
    Evidence: .sisyphus/evidence/task-8-rollback.txt
  ```

  **Rollback**: This task defines the rollback package itself; if incomplete, do not enable production rollout.
  **Commit**: YES | Message: `docs(release): add openclaw mysqlbot rollout package` | Files: `[docs/**, deployment/config docs, operator notes]`

## Final Verification Wave (MANDATORY — after ALL implementation tasks)
> 4 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.
> **Do NOT auto-proceed after verification. Wait for user's explicit approval before marking work complete.**
> **Never mark F1-F4 as checked before getting user's okay.** Rejection or user feedback -> fix -> re-run -> present again -> wait for okay.
- [x] F1. Plan Compliance Audit — oracle
- [x] F2. Code Quality Review — unspecified-high
- [x] F3. Real Manual QA — unspecified-high (+ playwright if UI)
- [x] F4. Scope Fidelity Check — deep

## Commit Strategy
- Commit per task group, not one monolithic commit.
- Suggested sequence:
  1. `feat(integration): define openclaw mysqlbot contract v1`
  2. `feat(auth): add openclaw service auth and session policy`
  3. `feat(mcp): add openclaw adapter endpoints`
  4. `feat(api): normalize openclaw adapter responses`
  5. `feat(openclaw): add mysqlbot tool and skill policy`
  6. `chore(integration): add openclaw observability guardrails`
  7. `test(integration): verify openclaw mysqlbot path2 e2e`
  8. `docs(release): add openclaw mysqlbot rollout package`

## Success Criteria
- OpenClaw can reliably invoke mysqlbot NL-query/analysis through the v1 contract without reimplementing mysqlbot logic.
- Auth/session behavior is service-safe and does not require human credential sharing.
- The OpenClaw-facing contract is stable, versioned, and machine-parseable.
- Existing mysqlbot chat/MCP behaviors remain regression-safe.
- Rollout and rollback are both executable without hidden tribal knowledge.
