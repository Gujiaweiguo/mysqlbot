## Why

mysqlbot currently exposes `access_key` and `secret_key` in the API Key dialog, but external OpenClaw callers such as OrchestratorAgent do not consume those raw values directly. They require a prebuilt JWT token that operators must manually derive today, which makes onboarding error-prone and obscures the artifact users actually need.

## What Changes

- Add an API Key dialog workflow that generates the OpenClaw service token derived from an API key's `access_key` and `secret_key`.
- Allow users to reveal and copy the generated JWT token value that OrchestratorAgent stores as `mysqlbot_openclaw.auth_token`.
- Allow users to copy the header-style credential form `sk <jwt>` for external callers that need the request-header value directly.
- Add inline guidance so users understand the difference between raw API keys and the generated OpenClaw token, including which value should be pasted into OrchestratorAgent.
- Preserve the existing `X-SQLBOT-ASK-TOKEN` + `sk` authentication contract rather than introducing a new auth mode.

## Capabilities

### New Capabilities
- `api-key-openclaw-token-management`: Generate, reveal, and copy OpenClaw-ready service tokens from the API Key management UI.

### Modified Capabilities
- `openclaw-integration-config-assistant`: Clarify the operator-facing onboarding guidance so generated mysqlbot token artifacts align with the documented OpenClaw auth contract.

## Impact

- Affected frontend code: `frontend/src/components/layout/Apikey.vue` and related i18n strings.
- Affected product workflow: API Key management in the mysqlbot user menu.
- Affected integration guidance: OpenClaw onboarding docs and assistant messaging that currently assume operators can manually reconstruct the required token.
- Potential dependency decision: either introduce a frontend-safe JWT generation path or add a backend token-generation endpoint while keeping the external auth contract unchanged.
