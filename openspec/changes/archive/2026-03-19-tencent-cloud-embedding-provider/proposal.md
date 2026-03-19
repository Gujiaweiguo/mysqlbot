## Why

腾讯云 LKEAP 的 OpenAI 兼容接口 (`api.lkeap.cloud.tencent.com`) 只支持聊天接口 (`/v1/chat/completions`)，**不支持 Embedding 接口** (`/v1/embeddings`)。用户如果使用腾讯云服务，目前无法在系统中配置 Embedding 功能。

腾讯云原生 API (`lkeap.tencentcloudapi.com`) 提供了 `GetEmbedding` 接口，但需要使用腾讯云签名认证 (SecretId + SecretKey)，与当前系统的 OpenAI 兼容方式 (Bearer Token) 完全不同。

## What Changes

- 新增 `provider_type: tencent_cloud` 作为 Embedding Provider 类型
- 实现腾讯云签名 v3 认证方式
- 调用腾讯云 LKEAP 原生 API (`lkeap.tencentcloudapi.com`) 的 `GetEmbedding` 接口
- 前端配置表单支持腾讯云的认证字段 (SecretId, SecretKey)
- 在供应商列表中添加腾讯云 (id: 9) 作为 Embedding 可选项

## Capabilities

### New Capabilities

- `tencent-cloud-embedding`: 腾讯云原生 Embedding Provider 实现，支持 SecretId/SecretKey 认证和腾讯云签名 v3

### Modified Capabilities

- `embedding-admin-config`: 扩展配置结构以支持腾讯云原生认证方式，前端表单新增 SecretId/SecretKey 字段

## Impact

**Backend:**
- `backend/apps/system/schemas/embedding_schema.py` - 添加 `EmbeddingProviderType.TENCENT_CLOUD`，新增 `tencent_secret_id`、`tencent_secret_key` 字段
- `backend/apps/ai_model/embedding.py` - 添加 `TencentCloudEmbeddingProvider` 类
- `backend/apps/system/crud/embedding_admin.py` - 添加腾讯云到支持的供应商列表，处理腾讯云配置验证
- `backend/pyproject.toml` - 添加 `tencentcloud-sdk-python-lkeap` 依赖

**Frontend:**
- `frontend/src/views/system/model/EmbeddingConfig.vue` - 支持 `provider_type: tencent_cloud`，显示 SecretId/SecretKey 输入框
- `frontend/src/entity/supplier.ts` - 在 Embedding 供应商列表中添加腾讯云 (id: 9)
- `frontend/src/i18n/zh-CN.json` - 添加腾讯云相关翻译

**No breaking changes** - 现有的 OpenAI 兼容配置继续正常工作。
