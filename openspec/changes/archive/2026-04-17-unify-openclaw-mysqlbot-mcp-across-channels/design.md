## Context

mysqlbot already has a completed OpenClaw-facing integration foundation, but the runtime topology is still split between a REST adapter path that can be exercised in some channels and a dedicated MCP service path that is not yet the single stable entrypoint for all OpenClaw clients. This split creates three architectural problems: inconsistent channel behavior, incomplete deployment/observability for the MCP service, and an unsafe group-chat session model that can reuse chat context too broadly when a shared bot identity fronts multiple users.

This change exists to converge on the final architecture while the integration is still in test stage. The intended end state is one supported transport for all OpenClaw channels: mysqlbot's standard MCP service. That requires coordinated changes across backend startup and deployment, MCP contract behavior, group-session mapping, operator guidance, and a first-party admin workflow for generating copyable OpenClaw configuration.

## Goals / Non-Goals

**Goals:**
- Make the dedicated MCP service the single supported OpenClaw integration entrypoint across web, Feishu direct chat, Feishu group chat, and WeChat.
- Define deterministic, channel-safe session isolation for group-chat and shared-bot scenarios.
- Expose enough operator-facing configuration, health, and debugging information to reliably deploy and troubleshoot the MCP service.
- Add a mysqlbot web assistant that generates copyable OpenClaw MCP configuration text from validated runtime settings.
- Validate unified behavior end to end across all supported OpenClaw channels.

**Non-Goals:**
- Keeping a long-term mixed REST-and-MCP integration model for OpenClaw channels.
- Replacing mysqlbot's existing NL-query, analysis, or chart-generation pipeline.
- Redesigning unrelated chat UX or broad admin configuration surfaces outside the OpenClaw integration assistant.
- Solving every future multi-tenant bot policy question beyond the session-isolation rules needed for OpenClaw channel safety.

## Decisions

### Decision 1: Standardize on the dedicated MCP service instead of preserving a dual-path integration

All OpenClaw channels will target the dedicated MCP service as the only supported integration entrypoint. The existing REST adapter remains an internal compatibility layer during transition if needed, but it is no longer the target architecture for channel onboarding.

**Why:**
- A single transport removes channel-by-channel divergence and eliminates hidden differences in tool discovery and execution.
- The user explicitly wants the final architecture established now, while still in test stage, instead of shipping a temporary workaround first.

**Alternatives considered:**
- Keep REST for some channels and MCP for others: rejected because it locks in two operational models and makes support, testing, and configuration generation harder.
- Move all channels to the REST adapter and defer MCP: rejected because it works against the desired final architecture.

### Decision 2: Treat MCP service exposure as a first-class deployment contract

The dedicated MCP service must be explicitly started, health-checked, configured, and exposed in both development and production deployment shapes rather than existing as an implementation detail behind source code.

**Why:**
- The current failure mode is architectural, not feature-level: the MCP service exists in code but is not reliably running and reachable from channel clients.
- Operators need a clear contract for what port/path is canonical, how health is checked, and how regressions are detected.

**Alternatives considered:**
- Continue relying on implicit startup assumptions: rejected because it leaves the key failure mode unowned.
- Collapse MCP into the main web process: rejected because the dedicated service topology already exists and is the clearer operational boundary.

### Decision 3: Introduce deterministic external session keys for channel-safe reuse

OpenClaw-originated conversations will be mapped through an explicit external session identity that captures the channel scope required for safe reuse. Group-chat traffic must use a deterministic grouping key that distinguishes the shared conversation boundary from direct-chat identities and prevents accidental reuse across unrelated channel contexts.

**Why:**
- The current model treats `conversation_id` more like a label and relies on mysqlbot `chat_id` reuse, which is too weak for shared-bot environments.
- Group channels need context reuse within the right conversation boundary without leaking state across unrelated groups or actors.

**Alternatives considered:**
- One mysqlbot chat per request: rejected because it destroys useful multi-turn continuity.
- One mysqlbot chat per API token only: rejected because it collapses multiple channels and users into unsafe shared context.

### Decision 4: Generate OpenClaw configuration from validated runtime state in the mysqlbot web UI

mysqlbot will expose an administrator-facing integration assistant that derives the MCP endpoint, auth header expectations, and copyable configuration text from current runtime settings instead of relying on hand-written setup instructions.

**Why:**
- The user wants a productized onboarding path, not ad hoc configuration exchange.
- Generating configuration from live settings reduces drift between what operators copy and what the service actually expects.

**Alternatives considered:**
- Document the MCP settings only in markdown: rejected because it remains manual and error-prone.
- Build the assistant before the MCP service contract is stabilized: rejected because it would hard-code unstable parameters.

### Decision 5: Verify the unified contract with channel-level integration tests, not just backend unit coverage

Verification must cover tool discovery, authenticated invocation, session reuse/isolation, and error behavior across each supported OpenClaw channel shape.

**Why:**
- The current failure is channel-specific even though backend implementation exists, so backend-only tests are not enough.
- The new architecture claim is "all channels use one MCP contract"; the tests must prove that claim.

**Alternatives considered:**
- Rely on backend route tests only: rejected because they cannot prove channel integration parity.

## Risks / Trade-offs

- **[MCP service becomes the single critical path and raises rollout risk]** → Add explicit health checks, observability, and staged rollout guidance before channel cutover.
- **[Group session isolation rules are too coarse and block desired shared context]** → Define a deterministic default policy first and keep more advanced sharing controls out of scope for this change.
- **[Generated configuration text drifts from OpenClaw expectations]** → Generate from versioned runtime settings and validate the output in channel onboarding tests.
- **[Deployment differences between dev and prod hide MCP regressions]** → Require the same canonical endpoint/path expectations and health contract in both environments.

## Migration Plan

1. Freeze the unified MCP and session-isolation requirements in specs.
2. Expose the dedicated MCP service with explicit runtime/deployment configuration and health checks.
3. Implement deterministic channel session identity rules and migrate OpenClaw-facing session binding to use them.
4. Add the admin APIs and web UI for the OpenClaw integration assistant.
5. Update observability, alerts, and runbooks for MCP-first operations.
6. Validate all supported channels against the same MCP configuration model.
7. Roll out by enabling the MCP-first configuration in test/staging first, then removing remaining channel-specific setup drift.

Rollback proceeds in reverse: disable channel onboarding to the MCP-first path, revert session-isolation changes if needed, and fall back to the prior test-only integration surface while preserving existing mysqlbot chat behavior.

## Open Questions

- None blocking for proposal stage. Exact UI placement for the integration assistant can be finalized during implementation design review as long as it remains an administrator-facing first-party workflow.
