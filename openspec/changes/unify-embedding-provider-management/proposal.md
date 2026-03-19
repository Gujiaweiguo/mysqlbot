## Why

The repository now has two separate embedding-oriented changes: one for provider abstraction and one for admin configuration flow. They solved important pieces, but they still leave a structural mismatch between the current AI model UI (supplier + model selection) and the embedding subsystem. A unified change is needed to define the final embedding management architecture in one pass and avoid repeated refactors, starting with the subset of suppliers that can share a stable OpenAI-compatible embeddings contract.

## What Changes

- Unify embedding management around a provider-type architecture that separates frontend supplier UX from backend protocol/runtime adapters.
- Replace the current `remote/local` embedding selection contract with a provider-type model, while limiting the first rollout to suppliers that can share an `openai_compatible` embedding contract.
- Align the embedding admin UI with the existing supplier/model interaction pattern used by AI model configuration, while preserving singleton runtime state and validation-before-enable semantics.
- In the first rollout, support only these suppliers for embedding: 阿里云百炼, DeepSeek, 火山引擎, 通用OpenAI.
- Defer Tencent-specific and other provider-specific embedding protocols to a later phase rather than pretending they are generically compatible.
- Preserve explicit runtime states such as disabled, validated, enabled, and reindex-required.

## Capabilities

### New Capabilities
- `embedding-provider-management`: Defines a unified supplier-driven embedding management model for the first supported supplier set, using an OpenAI-compatible embedding contract and singleton activation state.

### Modified Capabilities
- `embedding-provider-routing`: Changes the requirement model from simple local/remote routing to provider-type-based routing with provider-specific validation behavior.
- `embedding-admin-config`: Changes the admin workflow from a generic remote/local configuration form to a supplier + model driven flow that still preserves singleton lifecycle semantics.

## Impact

- Affected code includes frontend supplier/model UI, embedding admin forms, backend embedding schemas/CRUD/APIs, provider routing, runtime gating, and deployment guidance.
- Existing persisted embedding configuration must be migrated from `remote/local` shape to the new provider-type shape.
- Supplier-specific embedding providers outside the initial OpenAI-compatible set are explicitly out of the first rollout.
