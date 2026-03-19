## Why

The current Embedding Configuration UI (`EmbeddingConfig.vue`) does not fully align with the AI Model Configuration UI pattern (`Model.vue`). Key gaps include:
1. **Hardcoded supplier list** - Uses a local `SUPPORTED_SUPPLIERS` array instead of the shared `supplierList` used by AI model config
2. **Manual model input** - Requires users to type model names manually instead of selecting from a dropdown
3. **Missing supplier icons** - No visual icons for suppliers unlike the AI model config
4. **i18n key mismatch** - Some UI labels show English keys instead of Chinese translations due to incorrect i18n key paths

This creates an inconsistent user experience and makes the embedding configuration feel disconnected from the rest of the system.

## What Changes

- Replace hardcoded `SUPPORTED_SUPPLIERS` with the shared `supplierList` from `@/entity/supplier`
- Add a model dropdown selection that fetches available embedding models from the backend
- Display supplier icons in the supplier selection UI
- Fix i18n key paths so labels display in Chinese (e.g., `model.embedding_supplier` → use correct nested path)
- Optionally: Implement a 2-step wizard UI (select supplier → configure model) to match AI model config pattern

## Capabilities

### New Capabilities
- `embedding-model-selection`: Defines the UX for selecting embedding models from a curated list, including supplier icons, model dropdown, and i18n support.

### Modified Capabilities
- `embedding-admin-config`: Update the admin workflow to include model selection dropdown and supplier icons, aligning with the AI model configuration interaction pattern.

## Impact

**Frontend:**
- `frontend/src/views/system/model/EmbeddingConfig.vue` - Main UI component
- `frontend/src/api/embedding.ts` - Add API call for fetching embedding models
- `frontend/src/i18n/zh-CN.json` - Fix i18n key paths for embedding labels
- `frontend/src/i18n/en.json` - Ensure English translations exist
- `frontend/src/entity/supplier.ts` - May need to add embedding-specific supplier metadata

**Backend:**
- `backend/apps/system/api/embedding.py` - Add endpoint to list available embedding models per supplier
- `backend/apps/system/schemas/embedding_schema.py` - Add response schema for model list

**No breaking changes** - Existing configuration format remains compatible.
