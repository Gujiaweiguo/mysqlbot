## 1. Backend Dependencies

- [x] 1.1 Add `tencentcloud-sdk-python-lkeap` to `backend/pyproject.toml` dependencies
- [x] 1.2 Run `uv sync` to install the new dependency

## 2. Backend Schema Updates

- [x] 2.1 Add `TENCENT_CLOUD = "tencent_cloud"` to `EmbeddingProviderType` enum in `embedding_schema.py`
- [x] 2.2 Add `tencent_secret_id: str | None` field to `EmbeddingConfigPayload`
- [x] 2.3 Add `tencent_secret_key: str = ""` field to `EmbeddingConfigPayload`
- [x] 2.4 Add `tencent_secret_key_configured: bool = False` field to `EmbeddingConfigPayload`
- [x] 2.5 Add `tencent_region: str = "ap-guangzhou"` field to `EmbeddingConfigPayload`

## 3. Backend Provider Implementation

- [x] 3.1 Create `TencentCloudEmbeddingModelInfo` model in `backend/apps/ai_model/embedding.py`
- [x] 3.2 Create `TencentCloudEmbeddingProvider` class with SecretId/SecretKey/Region configuration
- [x] 3.3 Implement `embed_query` method using Tencent Cloud SDK
- [x] 3.4 Implement `embed_documents` method using Tencent Cloud SDK
- [x] 3.5 Add error handling for Tencent Cloud API errors

## 4. Backend CRUD Updates

- [x] 4.1 Add `SUPPORTED_TENCENT_CLOUD_SUPPLIER = {9}` in `embedding_admin.py`
- [x] 4.2 Add Tencent Cloud models to `EMBEDDING_MODELS_BY_SUPPLIER` for supplier id 9
- [x] 4.3 Update `validate_embedding_config` to handle `tencent_cloud` provider type
- [x] 4.4 Update `EmbeddingModelCache` to handle Tencent Cloud provider

## 5. Backend Model List API

- [x] 5.1 Update `get_embedding_models` to support Tencent Cloud supplier_id 9
- [x] 5.2 Models: `lke-text-embedding-v1`, `lke-text-embedding-v2`, `youtu-embedding-llm-v1`

## 6. Frontend Type Updates

- [x] 6.1 Add `tencent_cloud` to `EmbeddingProviderType` in `EmbeddingConfig.vue`
- [x] 6.2 Add form fields for `tencent_secret_id`, `tencent_secret_key`, `tencent_region`

## 7. Frontend Supplier Updates

- [x] 7.1 Add Tencent Cloud supplier handling (id: 9) in `EmbeddingConfig.vue`
- [x] 7.2 Import Tencent Cloud icon via `tencentCloudSupplier` computed property
- [x] 7.3 Add Tencent Cloud embedding model options via backend API

## 8. Frontend Form Updates

- [x] 8.1 Add conditional rendering for Tencent Cloud specific fields (SecretId, SecretKey, Region)
- [x] 8.2 Add Region dropdown with options: `ap-guangzhou`, `ap-shanghai`, `ap-beijing`, `ap-chengdu`, `ap-hongkong`
- [x] 8.3 Add Model dropdown for Tencent Cloud embedding models
- [x] 8.4 Update `buildConfigPayload` to include Tencent Cloud fields

## 9. i18n Updates

- [x] 9.1 Add Chinese translations for Tencent Cloud embedding labels in `zh-CN.json`
- [x] 9.2 Add English translations in `en.json`

## 10. Testing

- [ ] 10.1 Add unit tests for `TencentCloudEmbeddingProvider` class
- [ ] 10.2 Add API tests for Tencent Cloud embedding configuration endpoints
- [ ] 10.3 Verify SecretKey is encrypted and masked correctly
