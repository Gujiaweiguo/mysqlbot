## Context

当前系统支持 OpenAI 兼容的 Embedding Provider（`provider_type: openai_compatible`），使用 Bearer Token 认证方式调用 `/v1/embeddings` 接口。支持的供应商包括：阿里云百炼、DeepSeek、火山引擎、通用 OpenAI。

腾讯云 LKEAP 提供两种 API 接入方式：
1. **OpenAI 兼容接口** (`api.lkeap.cloud.tencent.com`) - 只支持聊天，不支持 Embedding
2. **腾讯云原生 API** (`lkeap.tencentcloudapi.com`) - 支持 Embedding，需要腾讯云签名认证

用户希望使用腾讯云的 Embedding 服务，需要实现腾讯云原生 Provider。

## Goals / Non-Goals

**Goals:**
- 新增腾讯云原生 Embedding Provider (`provider_type: tencent_cloud`)
- 支持腾讯云签名 v3 认证 (SecretId + SecretKey)
- 调用腾讯云 LKEAP 的 `GetEmbedding` 接口
- 前端支持腾讯云配置（SecretId、SecretKey、Region 输入框）
- 在 Embedding 供应商列表中显示腾讯云选项

**Non-Goals:**
- 不修改现有的 OpenAI 兼容 Provider
- 不支持腾讯云的其他 API（如聊天、重排序等）
- 不实现腾讯云 Embedding 的批量操作优化

## Decisions

### Decision 1: 使用腾讯云官方 SDK

使用 `tencentcloud-sdk-python-lkeap` 官方 SDK 实现 API 调用和签名认证。

**为什么：**
- 官方 SDK 已实现腾讯云签名 v3 算法，无需自己实现复杂的签名逻辑
- SDK 自动处理请求格式、错误解析、重试等
- 长期维护，API 更新时有保障

**替代方案：** 自己实现签名算法
- 需要实现 HMAC-SHA256、请求规范化等
- 维护成本高，容易出错

### Decision 2: 新增 provider_type 而非扩展现有类型

添加新的 `EmbeddingProviderType.TENCENT_CLOUD` 枚举值，而不是在 `openai_compatible` 中添加特殊处理。

**为什么：**
- 腾讯云原生 API 与 OpenAI 兼容接口完全不同（认证方式、请求格式、响应格式）
- 清晰的类型分离，代码更易维护
- 避免在 `openai_compatible` 中添加大量条件判断

### Decision 3: SecretKey 存储方式

SecretKey 使用与现有 api_key 相同的存储方式（加密存储在数据库中）。

**为什么：**
- 与现有安全机制一致
- 不需要引入新的加密方案
- 复用现有的密钥遮蔽逻辑

### Decision 4: 支持的 Region

默认使用 `ap-guangzhou`，允许用户在配置中选择其他区域。

**为什么：**
- 腾讯云 LKEAP 服务在广州区域最早开放
- 用户可能因网络延迟选择其他区域
- Region 作为可选配置项，不强制要求

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| SDK 依赖增加项目体积 | tencentcloud-sdk-python-lkeap 是轻量级包，约 100KB |
| 腾讯云 API 变更 | 使用官方 SDK，变更时升级 SDK 版本即可 |
| 用户可能混淆 OpenAI 兼容和原生接口 | 在前端明确区分，错误提示清晰说明 |
| SecretKey 泄露风险 | 加密存储，UI 遮蔽显示，与 api_key 相同的安全措施 |

## Migration Plan

1. 后端添加 SDK 依赖和新的 Provider 实现
2. 更新 Schema 和 CRUD 逻辑
3. 前端添加腾讯云配置表单
4. 测试验证
5. 部署

**无需数据迁移** - 新功能，不影响现有配置。
