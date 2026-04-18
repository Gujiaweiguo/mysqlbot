## Context

mysqlbot's API Key dialog currently exposes `access_key` and `secret_key` values, including copy and reveal controls for `secret_key`, but it does not expose the OpenClaw-ready token artifact that downstream callers actually use. OrchestratorAgent's mysqlbot OpenClaw connector accepts a configured JWT in `mysqlbot_openclaw.auth_token` and prepends `sk ` when sending `X-SQLBOT-ASK-TOKEN`, so operators must currently derive that JWT outside mysqlbot.

This change spans the API Key UI, operator guidance, and OpenClaw onboarding language. The current backend already returns the `secret_key` to the frontend, and the OpenClaw auth contract is already fixed as `X-SQLBOT-ASK-TOKEN` with `sk` scheme, so the design should improve operator output without changing the service-to-service auth protocol.

## Goals / Non-Goals

**Goals:**
- Let users generate the exact JWT artifact that OrchestratorAgent expects from the existing API Key management workflow.
- Let users reveal and copy both the raw JWT and a header-style `sk <jwt>` value without manual reconstruction.
- Keep token generation aligned with the existing OpenClaw auth contract and avoid breaking current integrations.
- Make the UI explain which copied value belongs in OrchestratorAgent configuration.

**Non-Goals:**
- Redesign the broader API Key CRUD experience.
- Replace the `X-SQLBOT-ASK-TOKEN` / `sk` authentication contract.
- Introduce token expiration, rotation semantics, or a new persistent token store in this change.
- Require OrchestratorAgent changes to consume a different credential format.

## Decisions

### Decision: Generate the JWT token client-side from the API key row
The frontend will generate the OpenClaw token on demand from the existing `access_key` and `secret_key` values already present in API Key dialog state.

**Rationale:**
- The current backend already exposes `secret_key` to the UI, so client-side generation does not expand the existing secret distribution boundary.
- This avoids adding a new backend endpoint solely to derive a token from data the client already has.
- It preserves the existing backend auth contract and keeps the change scoped to operator experience.

**Alternatives considered:**
- **Backend token-generation endpoint:** avoids browser-side signing code, but adds a new server surface for a derivation the client can already perform.
- **Persist generated tokens server-side:** unnecessary because the token can be deterministically regenerated from the existing API key pair.

### Decision: Treat the raw JWT as the primary copied artifact
The UI will present the raw JWT as the primary token output because OrchestratorAgent stores it as `mysqlbot_openclaw.auth_token`, while also offering a convenience copy action for `sk <jwt>`.

**Rationale:**
- This matches OrchestratorAgent's actual configuration model.
- It reduces operator confusion between "configured token" and "header value sent on the wire."

**Alternatives considered:**
- **Only expose `sk <jwt>`:** convenient for direct HTTP callers, but mismatches OrchestratorAgent's config field and forces users to strip the prefix.
- **Only expose full header text:** too caller-specific and less reusable across integration surfaces.

### Decision: Generate on demand and keep the token ephemeral in UI state
The token will be generated when the user requests it and surfaced through reveal/copy controls in the API Key UI, without storing it as a new backend field.

**Rationale:**
- The token is derived data, not a new source of truth.
- On-demand generation avoids creating migration or synchronization problems when API keys are disabled or deleted.

**Alternatives considered:**
- **Precompute token for every table row:** simpler rendering, but needlessly increases the amount of sensitive derived data displayed and retained in memory.

### Decision: Add explicit onboarding guidance in the API Key experience
The API Key UI and related OpenClaw onboarding language will explicitly distinguish among `access_key`, `secret_key`, raw JWT token, and `sk <jwt>` header value.

**Rationale:**
- The current operator pain is largely a mental-model problem rather than missing raw data.
- Guidance in the point-of-use UI is more actionable than expecting users to infer the derivation from backend docs.

## Risks / Trade-offs

- **[Client-side JWT dependency increases frontend surface]** → Use a minimal browser-safe JWT signing path and confine it to the API Key workflow.
- **[Users may confuse raw JWT with header-style value]** → Label both artifacts clearly and explain that OrchestratorAgent config stores the raw JWT while HTTP callers may need `sk <jwt>`.
- **[Derived token remains valid as long as underlying API key remains valid]** → Document that this change preserves existing auth behavior and does not add expiration semantics.
- **[Showing another sensitive artifact may increase copy mistakes]** → Keep generation explicit and on demand instead of permanently rendering tokens in the table.

## Migration Plan

1. Update the API Key UI to support on-demand token generation, reveal, and copy flows.
2. Update operator-facing wording and documentation references to reflect the generated-token workflow.
3. Validate that copied JWT output works with the existing OpenClaw contract and that copied `sk <jwt>` continues to authenticate successfully.
4. Roll back by removing the UI affordance if needed; no backend data migration is required because the token is derived, not stored.

## Open Questions

- Should the UI expose token generation inline per row, in a secondary dialog, or both?
- Should the "copy full header" variant include only `sk <jwt>` or the full `X-SQLBOT-ASK-TOKEN: sk <jwt>` line?
