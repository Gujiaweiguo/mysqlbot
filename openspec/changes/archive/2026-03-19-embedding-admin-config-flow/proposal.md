## Why

Embedding execution is now provider-based, but operators still manage it only through environment variables and deployment files. We need a safe admin workflow that lets teams configure embedding visually, validate the configuration, and enable it only after the system proves the selected provider is usable.

## What Changes

- Add a dedicated admin flow for embedding configuration instead of requiring environment-only management.
- Introduce explicit embedding runtime states such as disabled, configured-but-unverified, verified-disabled, enabled, and reindex-required.
- Require configuration validation before embedding can be enabled.
- Surface provider/model changes as reindex-risk events rather than silently assuming old vectors remain valid.
- Reuse the existing system model administration experience where helpful, but keep embedding configuration as a system-level workflow rather than a generic model list.

## Capabilities

### New Capabilities
- `embedding-admin-config`: Defines the admin workflow for configuring, validating, enabling, disabling, and monitoring embedding provider state.

### Modified Capabilities
- `embedding-provider-routing`: Adds requirement-level behavior for admin-driven provider activation and validation state, not just backend provider routing.

## Impact

- Affected areas include frontend system settings/model UI, backend configuration APIs, embedding validation logic, and operator-facing status handling.
- Product behavior changes: embedding should no longer be treated as implicitly active just because configuration exists.
- Provider/model updates will require explicit operator acknowledgement of re-embedding impact.
