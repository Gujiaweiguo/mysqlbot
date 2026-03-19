## Context

The Embedding Configuration feature has been partially refactored to use the supplier-based pattern. However, the frontend UI (`EmbeddingConfig.vue`) still has significant gaps compared to the AI Model Configuration UI (`Model.vue`):

1. **Hardcoded supplier list** - 4 suppliers hardcoded in component vs 11 in shared `supplierList`
2. **No model dropdown** - Model name is a text input instead of a selectable dropdown
3. **Missing supplier icons** - No visual icons for suppliers
4. **i18n key mismatch** - Keys don't match the existing `model.embedding_*` pattern in translation files

## Goals / Non-Goals

**Goals:**
- Unify Embedding Config UI to match AI Model Config UI pattern
- Use shared `supplierList` from `@/entity/supplier.ts`
- Add model dropdown with embedding-specific model options
- Add supplier icons for visual consistency
- Fix i18n keys to display Chinese translations correctly
- Add backend API to list available embedding models per supplier

**Non-Goals:**
- Changing the backend embedding provider implementation (already done)
- Changing the embedding state machine (already working)
- Adding new embedding suppliers (use existing supported set: 1, 3, 10, 15)

## Decisions

### Decision 1: Use shared supplierList with embedding-specific filter

Reuse `supplierList` from `@/entity/supplier.ts` but filter to only show embedding-supported suppliers (IDs: 1, 3, 10, 15).

**Why:**
- Maintains consistency with AI Model Config
- Single source of truth for supplier metadata (icons, i18n keys)
- Easy to add new embedding suppliers in future

### Decision 2: Add backend API for embedding model list

Create a new backend endpoint that returns embedding-specific model options per supplier. Unlike chat models, embedding models have different naming conventions.

**API:** `GET /system/embedding/models?supplier_id={id}`

**Response:**
```json
{
  "models": [
    {"name": "text-embedding-3-small"},
    {"name": "text-embedding-3-large"},
    ...
  ]
}
```

**Why:**
- Embedding models differ from chat models
- Some suppliers have different embedding model names
- Enables dropdown selection instead of manual input

### Decision 3: Update i18n keys to use model.* namespace

Move embedding-related translations under `model.*` namespace to match usage pattern.

**Why:**
- Consistent with existing translation structure
- `t('model.embedding_*')` pattern already used in component
- Translations exist in zh-CN.json under `model.*`

### Decision 4: Keep single-form UI (no 2-step wizard)

Do not convert to the 2-step wizard pattern used in AI Model Config. Keep the simpler single-form layout.

**Why:**
- Embedding is a singleton configuration (not multiple models)
- Simpler UX for a single config
- Lower implementation effort
- Can add wizard later if needed

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Embedding models differ per supplier | Backend API returns supplier-specific models |
| Some suppliers may not support embeddings | Filter to only embedding-capable suppliers |
| i18n key migration may break existing configs | Keep both old and new keys temporarily |
| Model list may become outdated | Make model list configurable in backend |

## Implementation Plan

1. **Backend**: Add `/system/embedding/models` API endpoint
2. **Frontend API**: Add `getModels(supplierId)` to embedding API
3. **Frontend Component**: Refactor `EmbeddingConfig.vue`:
   - Import and filter `supplierList`
   - Add model dropdown with dynamic options
   - Fix i18n key references
   - Add supplier icon display
4. **i18n**: Verify/fix Chinese translations for all embedding labels
5. **Testing**: Verify UI displays Chinese correctly and model dropdown works
