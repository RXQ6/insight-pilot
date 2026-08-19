# 评测迭代工作流（Evaluation-Driven Iteration）

> 目标：用"数字曲线"证明 Agent 在变好。每次改动都要跑评测、留报告，这就是面试要讲的迭代证据。

## 怎么跑

```bash
cd agent
.venv/Scripts/python scripts/run_eval.py            # 跑全部 116 条
.venv/Scripts/python scripts/run_eval.py --limit 20 # 只跑前 20 条（快速验证）
.venv/Scripts/python scripts/run_eval.py --type time_trend  # 只跑某类场景
```

报告输出到 `agent/data/eval_report.json`，包含：
- 通过率 / SQL 准确率 / 安全拦截率 / 图表可用率
- 平均延迟、平均成本
- `failed` 失败用例 ID 列表 + `byType` 分场景统计

**注意**：跑评测需要数据库里有示例数据（先 `docker compose up -d db redis` + 导入 sample_data.sql）+ 配好 LLM Key。

## 当前基线（2026-08-12 报告，共 100 条）

| 场景 | 通过 | 根因（已定位） |
|---|---|---|
| sql_single | 25/30 | 基本稳定，个别细节（排序 LIMIT、时间边界） |
| sql_join | 8/25 | 4 表 join 漏条件；销售额口径（quantity*price）搞错；双指标/子查询 |
| time_trend | 3/20 | **不会 PG 时间函数**：to_char/date_trunc/IYYY-IW/CASE WHEN 季度 |
| chart_recommend | 3/10 | 图表类型判定不稳（占比该给 pie 给了 bar） |
| safety | 10/10 | 稳定 |
| clarify | 5/5 | 稳定 |

**已做的确定性优化**（prompts.py 重写）：
1. SQL_SYSTEM 注入：表结构与主外键关系、统计口径（销售额=quantity*price、coalesce、round）、PG 时间处理模板（月/周/季度/半开区间）、5 个 few-shot 示例
2. CHART_SYSTEM 注入：图表类型选择规则（占比→pie、趋势→line、对比/排名→bar）+ 示例
3. 新增 16 条进阶垂直场景（window_func/retention/yoy_mom/anomaly），评测集 100 → 116 条

## 迭代闭环方法论（面试重点讲这个）

```
跑评测 → 看 failed 列表 → 归类根因 → 修改 → 重跑 → 对比曲线
```

**失败根因归类模板**（把每条失败用例归到一类）：
| 类别 | 例子 | 修法 |
|---|---|---|
| 领域知识缺失 | 不会 to_char('YYYY-MM') | 进 SQL_SYSTEM 模板/few-shot |
| 业务口径错误 | 销售额用了 orders.amount 而不是 quantity*price | 进统计口径说明 |
| 语法/结构错误 | join 漏条件 | few-shot 示例 |
| 判定问题 | 语义等价但行集不同 | 先不改判定，确认是模型问题 |
| 问题本身歧义 | 时间范围没说清 | 改用例措辞或归入 clarify |

**原则**：
- 优先改 prompt（few-shot），不要放宽评测判定——放宽判定是自欺欺人，面试官一问"判定怎么保证对"就穿
- 每次只改一类问题，重跑对比，曲线才有说服力
- 报告文件用 `git commit` 记录：`eval: sql accuracy 48% -> 62% (add PG time templates)`——commit 历史 = 迭代证据

## 当前进度（2026-08-19 实测，116 条）

| 指标 | 基线（8-12） | 第一轮迭代（8-19） |
|---|---|---|
| 总通过率 | 54% | **67.2%**（78/116） |
| SQL 准确率 | 48% | **62.7%** |
| 图表可用率 | 30% | **60%** |
| 安全拦截率 | 100% | 100% |
| sql_join | 8/25 | 15/25 |
| time_trend | 3/20 | 7/20 |

第一轮优化（prompt 注入表关系/统计口径/时间模板/few-shot + reflect 错误回喂 + 死循环修复）已生效。第二轮重点：yoy_mom（1/4）、time_trend 剩余失败用例。

## 目标曲线（建议）

| 里程碑 | SQL 准确率 | 说明 |
|---|---|---|
| 基线（已有） | 48% | 优化前 |
| 第一轮（已达成） | 62.7% | 时间模板 + 口径注入 + few-shot + 反思纠错 |
| 第二轮 | 70%+ | 针对 time_trend / yoy_mom 失败列表补 few-shot |
| 进阶场景 | 单独统计 | 窗口函数 3/4、留存 3/4、异常 3/4 已较好；同比环比 1/4 待攻 |

## 面试怎么讲

- "我建了 116 条评测集，覆盖基础 SQL、多表关联、时间趋势、图表推荐、安全、追问澄清，以及窗口函数、留存、同比环比、异常检测等进阶垂直场景"
- "SQL 准确率从 48% 迭代到 X%（每次改动跑评测、留报告、用失败用例反哺 prompt）"
- "安全拦截率 100%，单次成本 ¥0.003"——数字要能背出来
