## Why

The current embedding stack is tightly coupled to a local HuggingFace model runtime, which keeps local model files and torch-adjacent dependencies in the default deployment path even when generation is already handled by an external model provider. We need a provider-based embedding architecture so deployments can choose remote embeddings by default while preserving a local option for offline or private environments.

## What Changes

- Introduce an embedding provider abstraction that separates local and remote embedding implementations.
- Add configuration and runtime selection for embedding provider, model identifier, and provider-specific connection settings.
- Move startup backfill and CRUD-triggered embedding writes onto the provider abstraction instead of directly calling local HuggingFace embeddings.
- Define a migration path for re-embedding existing vectors when provider or model changes.
- Document deployment guidance for remote-default and local-fallback embedding strategies.

## Capabilities

### New Capabilities
- `embedding-provider-routing`: Defines how the system selects, configures, and uses local or remote embedding providers for query-time and persistence-time embedding operations.

### Modified Capabilities
- None.

## Impact

- Affected code includes `backend/apps/ai_model/embedding.py`, startup embedding backfill triggers, terminology/data-training/datasource embedding writers, and environment configuration.
- Existing vectors and similarity thresholds will need an explicit migration and validation strategy when changing embedding provider or model.
- Deployment behavior changes because local torch-based runtime becomes optional rather than implicit.
