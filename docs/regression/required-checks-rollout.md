# mySQLBot Required Checks 落地清单

## 目标

这份清单用于把仓库中已经实现的 CI 门禁，真正落到 GitHub 仓库设置里，避免出现“workflow 会失败，但 PR 仍可合并”的假保护状态。

## 当前建议设置为 required 的检查

在目标受保护分支上，至少将以下两个检查设为 required status checks：

- `Quality Summary`
- `Test Summary`

> 注意：这里要求的是 **check/job 名称**，不是 PR 页面上展示的 workflow 名称。PR 页面上的 workflow 名称当前是 `Quality Check (G1-G2)` 与 `Integration Test (G0-G5)`，它们主要用于人工确认 workflow 是否被触发。

原因：

- `Quality Summary` 聚合了 **G1 Backend Quality**、**G2 Frontend Quality**、**G2a Frontend Playwright Smoke**
- `Test Summary` 聚合了 **G0 Runtime Health**、**G3 Fixture Check**、**G4 Happy Path Regression**、**G5 Failure Path Regression**

优先要求 summary，而不是要求底层每一个 job，原因是：

- summary job 已经表达了当前门禁的最终阻塞语义
- 后续如果底层 job 继续细分，branch protection 不需要每次同步改很多项

## 建议保护的分支

至少覆盖：

- `main`
- `master`

如果团队把 `dev` / `develop` 也作为常规集成分支，可以按同样策略追加，但要先确认这些分支是否真的需要同等级阻塞。

## GitHub 仓库设置建议

### Branch protection / Ruleset

建议至少开启：

1. Pull request merge 前必须通过 required status checks
2. 要求分支与目标分支保持最新（如果团队流程需要严格串行集成）
3. 禁止直接 push 到受保护分支（如果当前仓库治理如此要求）

这份文档只约束 **required checks** 的最小落地，不强行规定审批人数、stale review、merge strategy 等团队治理策略。

## 首次 rollout 操作步骤

1. 打开仓库设置中的 branch protection / rulesets
2. 选择目标分支（`main` / `master`）
3. 添加 required checks：
   - `Quality Summary`
   - `Test Summary`
4. 保存规则
5. 新建一个测试 PR，改动命中 `backend/**` 或 `frontend/**`
6. 确认 PR 页面出现：
   - `Quality Check (G1-G2)` workflow
   - `Integration Test (G0-G5)` workflow
7. 故意制造一个可控失败，确认 PR 无法合并
8. 修复失败后再次确认 PR 恢复可合并

## 首轮验收清单

首轮 rollout 至少验证这 4 件事：

- `Quality Summary` 失败时 PR 被阻塞
- `Test Summary` 失败时 PR 被阻塞
- 两个 summary 都通过时 PR 不再被 CI 阻塞
- artifact 与 summary 名称和文档一致，评审者能快速找到证据

## 常见误区

### 1. 只要求底层 job，不要求 summary

这会让仓库设置变得脆弱：

- job 改名时容易漏改 branch protection
- 某些 job 被拆分/合并后，阻塞语义容易漂移

### 2. workflow 已红，但 PR 仍能合并

这通常不是 workflow 本身的问题，而是：

- 对应检查没有被设为 required
- required 的是旧名字，而不是当前 summary job 名称

### 3. 改了 workflow 名称或 summary 名称，但没同步仓库设置

这类改动会直接导致保护失效。每次修改下列名称时，都必须同步检查 branch protection：

- `Quality Summary`
- `Test Summary`
- workflow 展示名称（如果团队按 workflow 级别观察状态）

## 运维维护约定

出现以下任一情况时，应回看本清单并复核 branch protection：

- 新增/删除 summary job
- 修改 summary job 名称
- 修改 workflow 展示名称
- 调整 G0~G5 / G1~G2a 的门禁归属
- 将某些门禁从 blocking 改为 optional

## 与现有文档的关系

- 门禁语义说明：`docs/regression/release-gates.md`
- 回归执行细则：`docs/regression/full-regression-playbook.md`

这份文档只负责 **GitHub 仓库设置与 rollout 操作**，不重复解释每个 gate 的测试细节。
