# mySQLBot 全量回归执行手册

> 适用 change：`openspec/changes/full-regression-testing`

## 1. 回归 Gate 顺序与通过标准

### Gate 顺序（严格顺序）

1. **G0 Runtime Health**
2. **G1 Backend Quality**
3. **G2 Frontend Quality**
4. **G3 Fixture & Metadata Readiness**
5. **G4 Functional Happy Path（智能问数）**
6. **G5 Failure Path（429/瞬时故障）**
7. **G6 报告与发布决策**

### 每个 Gate 的通过标准

- **G0**：`docker compose ps` 为 `Up (... healthy)`，`/#/login` 与 `/api/v1/system/parameter/login` 可达（HTTP 200）。
- **G1**：后端质量命令全部通过（退出码 0）。
- **G2**：`frontend` 构建通过（退出码 0）。
- **G3**：`demo_sales` fixture 与 datasource 元数据同步检查全部通过。
- **G4**：关键智能问数 happy-path 用例通过。
- **G5**：429 与瞬时故障场景有“可观测、可恢复、可解释”的结果。
- **G6**：报告完整，证据可追溯，形成 GO/NO-GO 结论。

## 2. Stop-on-Fail 与 Waiver 规则

## 2.1 Stop-on-Fail（默认）

- G0~G5 任一失败，默认 **NO-GO**。
- 后续 Gate 可继续执行用于收集更多证据，但不改变 NO-GO 结论。

## 2.2 Waiver（例外放行）

允许放行需同时满足：

1. 明确失败项与影响范围；
2. 有可执行缓解措施与回滚路径；
3. 指定修复 owner 与截止时间；
4. 在报告中记录 waiver 审批人。

## 3. 并行与串行策略

### 必须串行

- G0 → G1/G2（环境不健康时，质量门禁结果无意义）
- G3 → G4（fixture/元数据未就绪时，智能问数结果不可信）
- G4 → G5（先验证主链路，再验证失败链路）

### 可并行

- G1 与 G2 可并行
- G5 的 429 与瞬时故障检查可在同一阶段并行执行
- 报告整理可在 G4/G5 执行中持续记录

## 4. `demo_sales` Fixture 合约（Task 2.1）

回归最小合约：

- Schema：`demo_sales`
- Tables：`customers`、`orders`
- 最小数据量：`customers >= 3`，`orders >= 4`

推荐验证 SQL：

```sql
select nspname from pg_namespace where nspname in ('demo_sales') order by 1;
select count(*) from demo_sales.customers;
select count(*) from demo_sales.orders;
```

## 5. 元数据同步校验（Task 2.2）

目标：确保智能问数读取的 `core_table` / `core_field` 与 fixture 一致。

校验项（以 ds_id=1 为例）：

```sql
select id,name,num from core_datasource where id=1;
select count(*) from core_table where ds_id=1;
select count(*) from core_field where ds_id=1;
select table_name from core_table where ds_id=1 order by table_name;
```

期望：`table_name` 至少包含 `customers`、`orders`，且字段数与真实表结构一致。

## 6. 确定性 Precheck 步骤（Task 2.3）

执行顺序：

1. `docker compose ps`
2. 登录页与登录参数接口可达检查
3. fixture schema/table/row-count 检查
4. datasource 元数据同步检查

通过条件：四步全部 exit code 0 且输出满足 Gate 标准。

## 7. 智能问数 Happy Path 用例（Task 3.1）

以 `demo_sales` 为数据域，至少覆盖：

1. **聚合查询**：
   - 问题：`最近订单总金额是多少？`
   - 验证：生成 SQL 可执行，返回单值结果。
2. **分组统计**：
   - 问题：`每个客户的订单金额汇总，按金额降序`
   - 验证：返回分组结果，排序正确。
3. **状态分布**：
   - 问题：`订单状态分别有多少条？`
   - 验证：状态维度齐全，计数正确。

可观测项：chat 结果、SQL 片段、执行日志、返回数据摘要。

推荐自动化执行命令（在 `backend/` 目录）：

```bash
bash scripts/regression/g4-happy-path-demo-sales.sh \
  --base-url http://127.0.0.1:8000 \
  --schema demo_sales
```

说明：脚本会自动完成登录、选择数据源、创建会话并执行以上 3 个 happy-path 问题，
同时在 `docs/regression/evidence/` 产出 JSON 证据文件。

如测试环境不使用默认管理员账号，可直接传入现成 JWT：

```bash
bash scripts/regression/g4-happy-path-demo-sales.sh \
  --base-url http://127.0.0.1:8000 \
  --datasource-id 1 \
  --token "<JWT_TOKEN>"
```

## 8. 429 / 限流回归场景（Task 3.2）

### 目标

- provider 返回 429 时，系统必须展示可理解错误，不可卡死在未结束状态。

### 验收项

1. 前端收到错误状态并可继续下一次提问；
2. 后端日志可定位到 provider 限流；
3. 报告记录触发条件与影响范围。

推荐自动化执行命令（在 `backend/` 目录）：

```bash
bash scripts/regression/g5-failure-path-demo-sales.sh \
  --base-url http://127.0.0.1:8000
```

说明：该脚本会启动本地 mock provider，注入可控 429 场景，
并验证错误可解释且后续请求可继续执行（不中断）。

## 9. 瞬时故障韧性检查（Task 3.3）

关注连接抖动、短暂 5xx、超时场景，验证：

1. 是否触发重试/退避策略；
2. 最终结果是否可解释（成功或受控失败）；
3. 日志与报告是否包含重试次数、耗时与最终状态。

说明：G5 脚本同一轮会注入“首次 503、次次恢复”的瞬时故障场景，
并在 evidence 中记录首轮失败、二次恢复、调用次数（可观测重试计数）与最终状态。

## 10. 报告结构（Task 4.1）

统一使用模板：`docs/regression/regression-report-template.md`

必填：范围、环境、命令、Gate 结果、证据、风险、决策、waiver。

## 11. 证据采集要求（Task 4.2）

每个 Gate 必须至少一条可复核证据：

- 命令输出（含退出码）
- API 响应头/体摘要
- 数据库查询结果
- 关键日志摘录
- 必要时截图

证据命名建议：`gate-编号-时间-类型`，确保可追踪。
