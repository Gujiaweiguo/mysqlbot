## 1. Backend API

- [x] 1.1 Add `/system/embedding/models` API endpoint to return embedding models per supplier
- [x] 1.2 Add `get_embedding_models(supplier_id)` function in `embedding_admin.py`
- [x] 1.3 Define embedding model list for each supported supplier (阿里云百炼, DeepSeek, 火山引擎, 通用OpenAI)

## 2. Frontend API Layer

- [x] 2.1 Add `getModels(supplierId)` method to `frontend/src/api/embedding.ts`
- [x] 2.2 Define response type for embedding models API

## 3. Frontend Component Refactoring

- [x] 3.1 Replace hardcoded `SUPPORTED_SUPPLIERS` with filtered `supplierList` from `@/entity/supplier.ts`
- [x] 3.2 Filter supplier list to only include embedding-capable suppliers (ids: 1, 3, 10, 15)
- [x] 3.3 Add supplier icon display using `get_supplier(supplier_id)?.icon`
- [x] 3.4 Replace model name text input with el-select dropdown with filterable and allow-create options
- [x] 3.5 Fetch and populate model options from new backend API when supplier changes
- [x] 3.6 Keep custom model name input capability via allow-create

## 4. i18n Fixes

- [x] 4.1 Verify all i18n keys in EmbeddingConfig.vue match keys in zh-CN.json under `model.*` namespace
- [x] 4.2 Fix any mismatched i18n keys to display Chinese labels correctly
- [x] 4.3 Ensure supplier names use `i18nKey` from supplier list for localized display

## 5. Verification

- [x] 5.1 Verify supplier dropdown displays with icons and Chinese names
- [x] 5.2 Verify model dropdown populates with models for selected supplier
- [x] 5.3 Verify all labels display in Chinese when locale is zh-CN
- [x] 5.4 Verify custom model name can still be entered manually
- [x] 5.5 Verify base URL auto-fills when supplier is selected
