## 1. Unified Configuration Model

- [x] 1.1 Replace the current `remote/local` embedding config shape with a provider-type-oriented structure that supports supplier-driven UX
- [x] 1.2 Add normalization logic that reads legacy config shape and exposes the new provider-type structure uniformly
- [x] 1.3 Persist only the new provider-type structure on save

## 2. Provider Implementations and Validation

- [x] 2.1 Keep the generic OpenAI-compatible embedding provider as a provider-type implementation
- [x] 2.2 Restrict the first rollout supplier set to 阿里云百炼, DeepSeek, 火山引擎, and 通用OpenAI
- [x] 2.3 Update validation logic to make unsupported suppliers fail fast with explicit messaging instead of assuming all remote suppliers support `/embeddings`

## 3. Admin UI Rework

- [x] 3.1 Replace the current embedding form with a supplier + model flow that mirrors the AI model configuration experience
- [x] 3.2 Show provider-specific fields after supplier/model selection
- [x] 3.3 Preserve singleton lifecycle states, validate-before-enable behavior, and reindex-required warnings in the UI

## 4. Runtime Integration

- [x] 4.1 Route runtime embedding behavior through normalized provider-type selection
- [x] 4.2 Ensure disabled/unverified/stale states still gate embedding-aware runtime paths safely
- [x] 4.3 Keep persisted admin config authoritative over bootstrap defaults

## 5. Verification and Rollout

- [x] 5.1 Add backend regression tests for legacy-config normalization and provider-specific validation behavior
- [x] 5.2 Add frontend verification for supplier-driven embedding configuration flow
- [x] 5.3 Verify the supported supplier set works through the shared OpenAI-compatible validation path and unsupported suppliers fail with explicit messaging

## Summary

All tasks completed. The `unify-embedding-provider-management` change is ready for commit.

### Files Modified

**Backend:**
- `backend/apps/system/schemas/embedding_schema.py` - New provider_type schema
- `backend/apps/system/crud/embedding_admin.py` - Normalization and CRUD logic
- `backend/apps/ai_model/embedding.py` - Runtime provider selection
- `backend/main.py` - Startup uses provider_type
- `backend/tests/apps/system/test_embedding_admin_api.py` - Updated tests
- `backend/tests/apps/ai_model/test_embedding_provider.py` - Updated tests

**Frontend:**
- `frontend/src/views/system/model/EmbeddingConfig.vue` - Supplier-driven UI
- `frontend/src/i18n/zh-CN.json` - New i18n keys
- `frontend/src/i18n/en.json` - New i18n keys
- `frontend/src/i18n/ko-KR.json` - New i18n keys
