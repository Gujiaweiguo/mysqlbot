# gs_scrm 会员分析覆盖与提问清单

- Scope: `gs_scrm` 会员发展、结构、营销、消费主题回归检查
- Datasource: `core_datasource.id=3`
- Verified At: `2026-03-17`
- Source Evidence:
  - `backend/scripts/regression/gs_scrm_member_analytics_seed.sql`
  - `backend/scripts/regression/gs_scrm_member_analytics_validation.sql`
  - `docs/regression/evidence/g4-happy-path-gs-scrm-analytics-20260317.json`
  - `backend/docs/regression/evidence/g4-gs-scrm-analytics-script-20260317.json`（自动化 runner smoke，受上游额度影响）

## 1) 结论摘要

当前 `gs_scrm` 已具备稳定支撑以下四类会员分析主题的能力：

> 说明：本页中的 **PASS** 结论来自前面已完成的人工/半自动真实问数验证；新补的自动化 runner 已落地并成功产出证据文件，但在本次全量执行时被上游模型 `403 not enough quota` 阻塞，因此当前应视为 **自动化脚本已就位，自动化全量执行暂时 BLOCKED**，而不是本地脚本逻辑失败。

| 主题 | 结论 | 说明 |
|---|---|---|
| 会员发展 | PASS | 已验证按日新增、近30天新增、渠道分布 |
| 会员结构 | PASS | 已验证等级结构、性别与等级交叉、等级消费对比 |
| 会员营销/活动 | PASS | 已验证活动报名人数、营销计划触发次数/金额/积分、按店铺营销触发 |
| 会员消费 | PASS | 已验证店铺消费金额、消费人数、客单价、消费频次、活动参与后消费人数 |

## 2) 当前最稳的已勾选相关表

| 主题 | 已勾选/已验证表 |
|---|---|
| 会员发展/结构 | `em_members`, `em_member_grades`, `em_member_actives` |
| 活动 | `em_activities`, `em_activity_applies` |
| 营销 | `em_marketing_plans`, `em_market_plan_logs` |
| 消费 | `em_trades`, `em_order_write_off_records`, `em_shops` |

## 3) 标准回归用例（推荐优先跑）

以下 8 条问法已经过真实问数链路验证，推荐作为标准 G4 用例。

| Case ID | 主题 | 推荐问法 | 结果 |
|---|---|---|---|
| `member-growth-daily` | 会员发展 | 请统计最近30天会员注册人数的按日变化趋势。 | PASS |
| `member-channel` | 注册渠道 | 请统计各会员注册渠道的人数分布，并按人数从高到低排序。 | PASS |
| `member-grade-structure` | 等级结构 | 请统计各会员等级的人数及占比。 | PASS |
| `member-active-trend` | 活跃趋势 | 请统计最近30天活跃会员人数的变化趋势。 | PASS |
| `activity-applies` | 活动报名 | 请统计各会员活动的报名人数，并按报名人数从高到低排序。 | PASS |
| `marketing-effect-v2` | 营销效果 | 请基于营销计划日志统计各营销计划的触发次数、触发金额和发放积分，并显示营销计划名称。 | PASS |
| `shop-consume-aov-v2` | 店铺消费 | 请基于交易表和核销记录，按核销店铺统计会员消费金额、消费人数和客单价，并显示店铺名称。 | PASS |
| `member-frequency-v2` | 消费频率 | 请以 `TRADE_FINISHED` 状态的交易为准，统计消费频率最高的会员，显示会员ID、消费次数和消费总额。 | PASS |

## 4) 高级回归用例（跨表 / 比例 / 条件过滤）

以下 6 条问法已完成高级问题批量测试，适合作为扩展回归集。

| Case ID | 主题 | 推荐问法 | 结果 |
|---|---|---|---|
| `adv-grade-consume` | 等级消费画像 | 请结合会员表和交易表，统计不同会员等级的消费总额、消费人数和客单价，并按消费总额从高到低排序。 | PASS |
| `adv-new-member-channel-source` | 近30天渠道分布 | 请基于 `em_members` 表的 `source` 字段，统计最近30天新增会员中各注册渠道的人数分布，并按人数从高到低排序。 | PASS |
| `adv-activity-consume-members` | 活动后消费 | 请基于活动报名表和交易表，统计参与活动且发生过消费的会员人数。 | PASS |
| `adv-shop-consume-share` | 店铺消费占比 | 请基于交易表和核销记录，按核销店铺统计会员消费金额占总会员消费金额的比例，并显示店铺名称。 | PASS |
| `adv-grade57-vs13-fixed` | 高低等级对比 | 请基于 `em_members.grade_id` 和 `em_trades.member_id`，比较 `grade_id` 为 `5、6、7` 的会员与 `grade_id` 为 `1、2、3` 的会员在交易表中的消费总额和消费人数。 | PASS |
| `adv-marketing-shop` | 按店铺看营销 | 请基于营销计划日志统计各店铺触发营销计划的次数和触发金额，并显示店铺名称。 | PASS |

## 5) 提问时的约束建议

当前 `gs_scrm` 测试数据下，为提升命中率，建议遵循以下规则：

1. 跨表问题尽量显式写出事实来源：
   - 营销效果 → `营销计划日志`
   - 店铺消费 → `交易表 + 核销记录`
   - 等级消费 → `会员表 + 交易表`
2. 需要渠道分析时，优先明确：`基于 em_members.source 字段`
3. 需要交易状态过滤时，优先明确：`TRADE_FINISHED`
4. 优先问：
   - 趋势
   - 分布
   - Top 排名
   - 汇总 / 占比
   - 跨表聚合
5. 当前不建议直接问：
   - 渠道中文枚举名称（系统当前多返回数值）
   - 复杂漏斗转化
   - 退款/取消/部分履约链路
   - 高低活跃会员分层阈值未显式定义的问题

## 6) 首轮测试中暴露出的提示词风险

以下问法在首轮测试中出现过 SQL 语义偏移，建议不要直接用原问法：

1. “最近30天新增会员中各注册渠道的人数分布”
   - 首轮误用 `login_type`
   - 修正后应显式指定 `source`
2. “各营销计划的触发次数、触发金额和发放积分”
   - 首轮未自动联想到 `em_market_plan_logs`
   - 修正后应显式写“基于营销计划日志”
3. “各店铺的会员消费金额、消费人数和客单价”
   - 首轮未自动联想到 `em_order_write_off_records`
   - 修正后应显式写“基于交易表和核销记录”
4. “高等级会员与普通会员消费对比”
   - 首轮虽有返回，但走了不理想的关联路径
   - 修正后应显式写 `em_members.grade_id` + `em_trades.member_id`

## 7) 使用建议

- 如果目标是验证会员基础分析主链路，优先跑：**标准回归用例 8 条**
- 如果目标是验证跨表能力，优先跑：**高级回归用例 6 条**
- 如果目标是验证提示词鲁棒性，可先跑原始问法，再跑本清单中的“推荐问法”做对比
- 如果目标是验证新自动化脚本，请优先使用 `--case-id` 跑 1~2 条子集；当前全量执行可能被外部模型额度阻塞。
