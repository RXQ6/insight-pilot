# 简历项目描述（可直接复制）

> 用法：`[X%]` 等占位符在重跑评测后填入真实数字（`agent/data/eval_report.json`）。
> 两个版本按投递方向选择；投后端岗用 B，投 Agent 岗用 A，通用岗位用 A 的骨架 + B 的工程化条目。

---

## 版本 A（Agent 岗，突出 Agent 能力与评测闭环）

**InsightPilot · 数据分析自主 Agent（ChatBI）**
GitHub：https://github.com/RXQ6/insight-pilot ｜ 一键演示：`agent/scripts/demo_api.py`（API 层跑通完整闭环）

技术栈：Python · LangGraph · LangChain · Spring Boot · PostgreSQL(pgvector) · Redis Streams · SSE · React + TypeScript

**项目简介**：全链路闭环的自然语言数据分析 Agent。用户用自然语言提问，Agent 自主完成意图分类 → 任务规划 → 生成并执行只读 SQL → Python 沙箱分析 → 图表生成 → 结果解释，全程流式可见，支持人工确认断点恢复与 CSV 导出。

**核心亮点**：
1. **LangGraph 状态机 + ReAct 工具循环**：意图分类/规划/工具循环/反思/回答五节点 + 条件路由；LLM 自主决策"调用工具还是 finish"（Python 沙箱计算/补充查询/图表），步数与成本预算兜底；基于 checkpoint 与 interrupt/resume 实现人工确认断点恢复——审批被拒时查询不执行
2. **自我纠错**：reflect 质检节点把 SQL 执行错误回喂给模型重新生成，评测驱动 prompt 迭代
3. **评测驱动迭代**：116 条评测集覆盖基础 SQL、多表关联、时间趋势、图表推荐、安全、追问及窗口函数/留存/同比/异常等进阶垂直场景；SQL 准确率从 48% 迭代到 74.7%，总通过率 54% → 78.4%，安全拦截率 100%，单次成本 ¥0.006，自动化报告 + 三端 CI；RAG 检索关键词+向量（bge-m3）混合召回 + RRF 融合，30 条内容级标注 recall@1 83.3% / recall@3 96.7%
4. **成本与安全控制**：每任务成本上限强制中断、token/延迟/费用回传；只读 SQL 纵深防御 + Docker 无网络沙箱 + 多租户数据隔离

**量化**：116 条评测 · 10 类场景 · SQL 准确率 74.7% · 端到端延迟 ~7.3s · 单次成本 ¥0.006 · GitHub Actions 三端流水线全绿

---

## 版本 B（后端岗，突出工程化与架构）

**InsightPilot · 数据分析 Agent 全栈平台（Java 控制面 + Python Worker）**
GitHub：https://github.com/RXQ6/insight-pilot ｜ 一键演示：`agent/scripts/demo_api.py`（API 层跑通完整闭环）

技术栈：Java 17 · Spring Boot 3 · Spring Security(JWT) · PostgreSQL · Redis Streams · SSE · Python · LangGraph · React + TypeScript · Docker

**项目简介**：面向数据分析场景的 ChatBI 全栈平台，Java 控制面与 Python Agent Worker 通过 Redis Streams 解耦，SSE 流式推送，支持多租户数据接入、人工确认、结果导出。

**核心亮点**：
1. **异步任务架构**：Redis Streams 消费组解耦任务提交与执行（多 worker 水平扩展、XACK 确认），结果流回写 + SSE 逐 token 推送；失败任务投递死信队列（DLQ），提供查询接口
2. **安全纵深**：只读数据库账号 + 事务只读 + SQL 关键字拦截 + 行数上限 + Python Docker 无网络沙箱 + 多租户表隔离（按用户建表/白名单拦截）；JWT + BCrypt + 审计日志
3. **安全复盘**：主动发现并修复任务/审批接口越权漏洞（IDOR，越权返回 403）与"审批拒绝仍执行查询"逻辑缺陷，均以单测锁定
4. **工程质量**：32 个 Python 单测 + 11 个 JUnit 单测（覆盖越权/DLQ/JWT），GitHub Actions 三端 CI 全绿，README 含架构图与指标

**量化**：100+ 自动化测试用例 · 三端 CI · 任务端到端延迟 ~7.3s · 单次成本 ¥0.006 · 多租户隔离 · DLQ 可观测

---

## 面试追问对应的"证据位置"（写进简历的每条都要能指到代码）

| 简历条目 | 代码证据 |
|---|---|
| 人工确认断点恢复 | `agent/insight_agent/nodes.py`（interrupt/resume）、`worker.py` |
| 自我纠错 reflect | `nodes.py` reflect() + fix_hint 回喂 |
| 评测体系 116 条 | `agent/data/eval_cases.json`、`scripts/run_eval.py`、`docs/eval-optimization.md` |
| 成本上限强制 | `nodes.py` `_budget_exceeded` |
| DLQ | `worker.py` `_publish_dlq`、`GET /api/tasks/dlq` |
| IDOR 修复 | `TaskService.requireOwned` + `TaskServiceTest` |
| 多租户隔离 | `tools/db.py` `fetch_rows` 表名白名单 |
| CI | `.github/workflows/ci.yml` + README 徽章 |
| 演示 | `docs/demo-checklist.md` + `scripts/demo_api.py` |
