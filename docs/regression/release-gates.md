# mySQLBot 发布门禁说明

## 目标

这套当前门禁用于保证 **最小可运行发布路径**：服务能启动、回归数据环境成立、核心 happy path / failure-path 可执行。

它 **不等于** 全功能验收，也不覆盖完整真实生产环境、所有前端页面、所有 chat 分支或所有外部 provider 集成。

## 门禁分层

| Gate | 名称 | 保证内容 | 不保证内容 |
|---|---|---|---|
| G0 | Runtime Health | `docker compose` 服务可启动，登录页与登录参数接口最小可用 | 业务链路正确性 |
| G1 | Backend Quality | backend 类型检查、lint、startup smoke、pytest/coverage 保持通过 | 真实运行环境可用性 |
| G2 | Frontend Quality | frontend lint 与构建保持通过 | 浏览器运行时行为 |
| G3 | Fixture & Metadata | `demo_sales` fixture 与 datasource 元数据满足 G4 前置条件 | chat / SQL / 图表行为正确 |
| G4 | Functional Happy Path | 核心智能问数 happy path 可执行并产出证据 | 全功能、全异常矩阵 |
| G5 | Failure Path Regression | 受控 failure-path 场景可观测、可恢复并产出证据 | 所有异常矩阵 |
| G2a | Frontend Playwright Smoke | 基于构建产物的 mocked 浏览器 smoke 覆盖保持可运行 | 真实后端/真实登录/全页面回归 |

## 当前执行入口

- 代码质量门禁：`.github/workflows/quality-check.yml`
- 运行时/回归门禁：`.github/workflows/integration-test.yml`
- 详细回归玩法：`docs/regression/full-regression-playbook.md`
- Required checks 落地清单：`docs/regression/required-checks-rollout.md`

当前 `quality-check.yml` 的 backend quality job 会先执行定向 startup smoke（`backend/tests/test_startup_smoke.py`），再执行更广的 backend pytest/coverage。

`integration-test.yml` 当前在以下场景运行：

- `pull_request` 到 `main` / `master`，且改动命中前后端、Compose、Dockerfile、启动脚本或相关 workflow
- `schedule` 定时巡检
- `workflow_dispatch` 手动触发

其中：

- 定时巡检会执行 G4
- 定时巡检会在 G4 之后执行 G5
- 手动触发时可通过 `run_e2e` 控制是否执行 G4 / G5
- 普通 PR 默认执行到 G3；G4 / G5 作为更重的运行时回归保留给定时巡检与手动触发
- `quality-check.yml` 会执行 frontend lint/build，并额外执行 Playwright smoke

> 注意：workflow 失败是否真正阻塞 PR 合并，还取决于 GitHub branch protection 是否将对应检查（通常是 `Quality Summary` 与 `Test Summary`）设为 required status check。具体 rollout 步骤见 `docs/regression/required-checks-rollout.md`。

## 失败时的排障顺序

1. **先看 G0**
   - `docker compose ps`
- `runtime-health-artifacts` 中的 `mysqlbot-app.log` / `postgresql.log`
   - 登录页与 `/api/v1/system/parameter/login` 探针结果
2. **再看 G3**
   - `demo_sales` schema 是否存在
   - `customers` / `orders` 最小数据量
   - `core_datasource`、`core_table`、`core_field` 元数据是否满足前置条件
   - 当前 workflow 默认 fixture 合约使用 internal datasource `id=1` / `ds_id=1`
3. **最后看 G4**
   - `g4-evidence` artifact
   - `docs/regression/evidence/` 中的 happy-path 证据文件
4. **再看 G5**
   - `g5-evidence` artifact
   - failure-path 证据是否显示可解释错误与恢复能力
5. **前端回归补充看 G2a**
   - `frontend-playwright-blob-report` artifact
   - `frontend/e2e/README.md` 中声明的 mocked smoke 覆盖范围

这条顺序的含义是：

- G0 失败时，后续结果不可靠
- G3 失败时，G4 的行为结论不可信
- G4 失败时，才优先判断主链路是否真实回归
- G5 结论只在 G4 已通过时才有意义
- 在普通 PR 上，G4 / G5 为 `SKIPPED` 属于预期行为，表示重型回归未在该上下文执行

## 证据位置

- **GitHub Actions Summary**：快速看 `Quality Summary` 与 `Test Summary` 的绿红状态
- **Quality Summary**：快速看 G1 / G2 / G2a 的绿红状态
- **Test Summary**：快速看 G0 / G3 / G4 / G5 的绿红状态
- **`runtime-health-artifacts`**：运行时服务状态与 app/db 日志
- **`g4-evidence`**：happy-path 回归证据 JSON
- **`g5-evidence`**：failure-path 回归证据 JSON
- **`frontend-playwright-blob-report`**：Playwright smoke blob report
- **`docs/regression/*.md`**：历史基线与人工总结报告

## 当前未覆盖范围

以下内容仍然不在第一阶段强制门禁范围内：

- 真实 provider / datasource 的全链路集成
- 完整登录认证浏览器流程
- 所有 chat 变体、分析/预测/导出路径
- 全量前端交互矩阵
- 生产部署差异与性能压测

## 下一阶段可扩展方向

- 逐步扩展更多真实运行路径与异常路径覆盖
