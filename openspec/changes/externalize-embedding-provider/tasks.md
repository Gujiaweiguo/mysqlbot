## 1. Provider Boundary and Configuration

- [x] 1.1 Inventory every code path that currently calls `EmbeddingModelCache.get_model()` and classify it as startup backfill, CRUD-triggered write, or query-time embedding
- [x] 1.2 Introduce embedding provider configuration covering provider type, model identifier, and remote connection settings
- [x] 1.3 Define the stable provider interface for `embed_query` and `embed_documents`

## 2. Provider Implementations and Routing

- [x] 2.1 Refactor the current local HuggingFace path into a local embedding provider implementation
- [x] 2.2 Add a remote embedding provider implementation for the selected external API contract
- [x] 2.3 Route terminology, data-training, datasource, and table embedding operations through provider selection instead of direct local-model construction

## 3. Migration and Backfill Strategy

- [x] 3.1 Define the operator workflow for re-embedding persisted vectors when provider or model changes
- [x] 3.2 Decide and document how startup backfill behaves for remote embedding deployments (eager, deferred, or manually triggered)
- [x] 3.3 Add provider-aware validation for similarity thresholds and retrieval quality after migration

## 4. Verification and Rollout

- [x] 4.1 Verify local provider mode still supports existing embedding writers and query-time retrieval paths
- [x] 4.2 Verify remote provider mode can generate embeddings for startup backfill and CRUD-triggered updates without requiring local torch runtime
- [x] 4.3 Document recommended deployment modes: remote-default, local-fallback, and rollback strategy
