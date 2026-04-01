# 数据源异步同步验证 Runbook

> 适用场景：本地或 staging 环境验证数据源异步同步（async sync）全链路

## 1. 目的与范围

本文档覆盖数据源异步同步功能的端到端验证流程。当 `DATASOURCE_ASYNC_SYNC_ENABLED` 开启且选择的表数量超过 `DATASOURCE_ASYNC_SYNC_TABLE_THRESHOLD`（默认 100）时，`chooseTables` 接口不再同步阻塞，而是返回一个 `job_id`，后台异步完成 introspect、stage、finalize、post_process 四个阶段。

验证范围：

- 异步同步触发条件是否正确（表数量 > 阈值）
- `chooseTables` 是否返回 `DatasourceSyncJobSubmitResponse`（含 `job_id`）
- 通过 `syncJob/{job_id}` 轮询，状态是否按预期路径流转
- 同步完成后，`core_table` / `core_field` 持久化是否完整
- 通过 `syncJobs/{ds_id}` 和 `tableList/{id}` 确认结果可查

不在范围内：同步模式的 chooseTables（表数量 <= 阈值）、embedding 后续任务细节、前端 UI 交互。

## 2. 前置条件

### 2.1 环境要求

- 本地开发环境或 staging 环境已按 `README.md` 启动（后端 :8000，数据库/Redis 容器运行中）
- 已有至少一个可用数据源（能连接到真实数据库，表数量 > 100）
- `psql` 或其他 SQL 客户端可直连后端数据库

### 2.2 环境变量

在 `.env` 文件中确认以下配置：

```bash
# 必须开启
DATASOURCE_ASYNC_SYNC_ENABLED=true

# 阈值（默认 100，可按测试数据源的实际表数量调整）
DATASOURCE_ASYNC_SYNC_TABLE_THRESHOLD=100
```

修改后重启后端生效：

```bash
# 在仓库根目录
make backend-dev
```

### 2.3 认证信息

所有 API 请求需要携带 JWT token。请求头格式：

```
X-SQLBOT-TOKEN: Bearer <jwt>
```

JWT payload 必须包含以下字段（见 `common/core/schemas.py` 中的 `TokenPayload`）：

```json
{
  "id": <用户ID>,
  "account": "<用户名>",
  "oid": <工作空间ID>
}
```

获取 token 的方式：

1. 通过前端登录后从浏览器 DevTools 抓取
2. 通过 `/api/v1/login/access-token` 接口获取

### 2.4 工具

- `curl` 或 `httpie`：发起 HTTP 请求
- `jq`：解析 JSON 响应
- `psql`：查询后端数据库验证持久化

## 3. 验证流程

以下以 `ds_id=7`（150 张表的数据源）为例，`BASE_URL` 默认 `http://127.0.0.1:8000`。

### 3.1 获取表列表

确认数据源可达、表数量超过阈值：

```bash
curl -s -X POST "${BASE_URL}/api/v1/datasource/getTables/7" \
  -H "X-SQLBOT-TOKEN: Bearer ${JWT}" \
  -H "Content-Type: application/json" | jq '.data | length'
```

期望输出：一个整数，且大于 `DATASOURCE_ASYNC_SYNC_TABLE_THRESHOLD`（如 `150`）。

记录表数量，用于后续对比。

### 3.2 触发异步同步

将全部（或超过阈值的）表提交到 `chooseTables`：

```bash
# 先获取完整表列表，构建请求体
TABLES=$(curl -s -X POST "${BASE_URL}/api/v1/datasource/getTables/7" \
  -H "X-SQLBOT-TOKEN: Bearer ${JWT}" \
  -H "Content-Type: application/json")

# 提交全量表（构建 SelectedTablePayload 数组）
PAYLOAD=$(echo "$TABLES" | jq '[.data[] | {table_name: .tableName, table_comment: (.tableComment // "")}]')

curl -s -X POST "${BASE_URL}/api/v1/datasource/chooseTables/7" \
  -H "X-SQLBOT-TOKEN: Bearer ${JWT}" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD" | jq
```

期望响应（外层是统一响应包装，`data` 内为 `DatasourceSyncJobSubmitResponse`）：

```json
{
  "code": 0,
  "data": {
    "job_id": 4,
    "datasource_id": 7,
    "status": "pending",
    "phase": "submit",
    "reused_active_job": false
  },
  "msg": null
}
```

关键断言：

- `.data.status` 为 `"pending"`
- `.data.job_id` 为正整数（记录下来，后续步骤使用）
- `.data.reused_active_job` 为 `false`（首次提交）

### 3.3 轮询同步状态

使用返回的 `job_id` 轮询状态：

```bash
JOB_ID=4

curl -s "${BASE_URL}/api/v1/datasource/syncJob/${JOB_ID}" \
  -H "X-SQLBOT-TOKEN: Bearer ${JWT}" | jq '.data | {status, phase, total_tables, completed_tables, current_table_name}'
```

#### 状态流转路径

| 时间点 | status | phase | 说明 |
|--------|--------|-------|------|
| 提交瞬间 | `pending` | `submit` | 任务已创建，等待 worker 拉取 |
| 开始执行 | `running` | `introspect` | 正在从源库采集表结构 |
| 采集完成 | `running` | `stage` | 正在写入 `core_table` / `core_field` |
| 收尾阶段（可能很短） | `finalizing` | `finalize` | 执行最终发布与收尾 |
| 全部完成 | `succeeded` | `post_process` | 同步成功，可查询结果 |

> 本地实测中稳定观察到的路径为：`pending → running/introspect → running/stage → succeeded/post_process`。`finalizing/finalize` 可能因为时间很短而在轮询中被跳过。

建议：间隔 2-3 秒轮询一次，直到 `status` 变为终态（`succeeded` / `failed` / `cancelled`）。

单次轮询示例脚本：

```bash
while true; do
  RESULT=$(curl -s "${BASE_URL}/api/v1/datasource/syncJob/${JOB_ID}" \
    -H "X-SQLBOT-TOKEN: Bearer ${JWT}")
  STATUS=$(echo "$RESULT" | jq -r '.data.status')
  PHASE=$(echo "$RESULT" | jq -r '.data.phase')
  COMPLETED=$(echo "$RESULT" | jq -r '.data.completed_tables')
  TOTAL=$(echo "$RESULT" | jq -r '.data.total_tables')
  echo "$(date +%H:%M:%S) status=${STATUS} phase=${PHASE} tables=${COMPLETED}/${TOTAL}"
  if [ "$STATUS" = "succeeded" ] || [ "$STATUS" = "failed" ] || [ "$STATUS" = "cancelled" ]; then
    echo "Final result:"
    echo "$RESULT" | jq
    break
  fi
  sleep 3
done
```

### 3.4 查询数据源同步任务列表

确认任务已记录在数据源维度下：

```bash
curl -s "${BASE_URL}/api/v1/datasource/syncJobs/7" \
  -H "X-SQLBOT-TOKEN: Bearer ${JWT}" | jq '.data[0] | {job_id, status, phase, total_tables, completed_tables}'
```

期望：返回数组中包含刚才的 `job_id`，且 `status` 为 `"succeeded"`。

### 3.5 验证持久化结果

#### 3.5.1 通过 API 验证

```bash
curl -s -X POST "${BASE_URL}/api/v1/datasource/tableList/7" \
  -H "X-SQLBOT-TOKEN: Bearer ${JWT}" \
  -H "Content-Type: application/json" | jq '.data | length'
```

期望输出：与 3.1 步骤中 `getTables` 返回的表数量一致（如 `150`）。

#### 3.5.2 通过数据库直接验证

```sql
-- 确认 core_table 记录数
SELECT count(*) FROM core_table WHERE ds_id = 7;

-- 确认 core_field 记录数
SELECT count(*) FROM core_field WHERE ds_id = 7;

-- 抽样检查表名是否合理
SELECT table_name FROM core_table WHERE ds_id = 7 ORDER BY table_name LIMIT 20;

-- 检查 sync job 记录
SELECT id, ds_id, status, phase, total_tables, completed_tables, failed_tables
FROM datasource_sync_job
WHERE ds_id = 7
ORDER BY id DESC;
```

期望：

- `core_table` 行数 = `getTables` 返回的表数量
- `core_field` 行数 > 0（每张表至少有字段）
- `datasource_sync_job` 中对应记录的 `status = 'succeeded'`

## 4. 通过标准

以下条件全部满足时，判定验证通过：

1. `getTables/{id}` 返回的表数量 > `DATASOURCE_ASYNC_SYNC_TABLE_THRESHOLD`
2. `chooseTables/{id}` 返回 `DatasourceSyncJobSubmitResponse`，含有效 `job_id`，`status = "pending"`
3. `syncJob/{job_id}` 状态按 `pending → running/introspect → running/stage → finalizing/finalize → succeeded` 流转
4. 终态为 `succeeded`，`completed_tables` = `total_tables`，`failed_tables` = 0
5. `syncJobs/{ds_id}` 能查到对应 job 记录
6. `tableList/{id}` 返回的表数量与 `getTables` 一致
7. 数据库 `core_table` / `core_field` 记录数与预期一致

## 5. 证据采集

每步执行时保存以下证据到 `docs/regression/evidence/` 目录：

| 步骤 | 证据内容 | 建议文件名 |
|------|----------|-----------|
| 3.1 | `getTables` 响应的表数量 | `async-sync-getTables-count.txt` |
| 3.2 | `chooseTables` 完整响应体 | `async-sync-chooseTables-response.json` |
| 3.3 | 轮询过程中至少 3 个关键状态的响应截图/输出 | `async-sync-polling-log.txt` |
| 3.4 | `syncJobs` 响应 | `async-sync-syncJobs-response.json` |
| 3.5 | `tableList` 表数量 + 数据库查询结果 | `async-sync-persistence-evidence.txt` |

命名建议：`async-sync-<步骤>-<日期>.<ext>`，如 `async-sync-chooseTables-20260401.json`。

## 6. 常见问题与排障

### 6.1 JWT payload 缺少必要字段

**现象**：请求返回 401 或 403，日志提示用户信息解析失败。

**原因**：`TokenPayload`（`common/core/schemas.py`）与标准登录流程生成的 payload 至少应包含 `id`、`account`、`oid`。如果 token 是手工构造的或来自非标准登录流程，常见问题是缺少 `id` 或 `oid`，导致鉴权失败。

**排查**：

```bash
# 解码 JWT 查看 payload（不验证签名）
echo "$JWT" | cut -d. -f2 | base64 -d 2>/dev/null | jq .
```

确认输出中存在：

```json
{
  "id": 1,
  "account": "admin",
  "oid": 1
}
```

Runbook 中建议与标准登录流程保持一致，确保至少包含 `id`、`account`、`oid` 三个字段；其中 `id` 与 `oid` 缺失时最容易直接触发鉴权失败。

### 6.2 数据源 configuration 存储了原始 bytes 而非 UTF-8 字符串

**现象**：`getTables/{id}` 或 `chooseTables/{id}` 报错，提示解密失败或 JSON 解析异常。

**原因**：`aes_encrypt()` 返回的是 `bytes` 类型（见 `apps/datasource/utils/utils.py`）。在创建或更新数据源时，必须调用 `.decode('utf-8')` 转为字符串后再存入数据库。

正确写法（参考 `apps/datasource/crud/datasource.py` 第 161-162 行和第 182 行）：

```python
ds.configuration = aes_encrypt(json.dumps(conf.to_dict())).decode("utf-8")
```

错误写法：

```python
# 直接存储 bytes，会导致后续 aes_decrypt 解析失败
ds.configuration = aes_encrypt(json.dumps(conf.to_dict()))
```

**排查**：

```sql
-- 检查 configuration 列的存储格式
SELECT id, name, length(configuration), left(configuration, 10)
FROM core_datasource
WHERE id = 7;
```

正常情况下 `configuration` 列应为文本类型，内容为 Base64 编码的字符串。如果看到 `b'...'` 前缀或二进制乱码，说明存储时未调用 `.decode('utf-8')`。

### 6.3 异步同步未被触发（返回空响应）

**现象**：`chooseTables` 返回 HTTP 200 但响应体为空（`null`），没有 `job_id`。

**原因**：当表数量未超过 `DATASOURCE_ASYNC_SYNC_TABLE_THRESHOLD` 时，走的是同步路径，不会返回 `DatasourceSyncJobSubmitResponse`。同步路径返回 `null`（HTTP 200），表示同步已在请求期间完成。

**排查**：

1. 确认 `.env` 中 `DATASOURCE_ASYNC_SYNC_ENABLED=true`
2. 确认提交的表数量 > `DATASOURCE_ASYNC_SYNC_TABLE_THRESHOLD`（默认 100）
3. 检查 `_should_use_async_sync` 的判断逻辑（`apps/datasource/api/datasource.py`）

### 6.4 任务卡在 pending 状态

**现象**：轮询 `syncJob/{job_id}` 始终返回 `status: "pending"`，phase 不推进。

**排查**：

1. 检查后端日志中是否有 worker 启动和 job 拉取的记录
2. 确认数据库连接正常，`datasource_sync_job` 表可读写
3. 检查是否有 stale job cleanup 误删了当前任务（超时阈值 `DATASOURCE_SYNC_JOB_STALE_TIMEOUT_SECONDS`，默认 3600 秒）
4. 确认 worker 数量配置：`DATASOURCE_SYNC_JOB_MAX_WORKERS`（默认 4）
