# InsightPilot 面试追问弹药库

> 用法：每个问题先自己默答，再对照要点。带 ✅ 的是项目里**已实现**的，带 ⚠️ 的是**已知短板**——短板要主动说，面试官会觉得你了解自己的系统边界。
> 规则：只讲你能在代码里指出来的东西，别背概念。

## 1. 这个项目解决什么问题？业务闭环是什么？
**要点**：面向数据分析场景的 ChatBI——业务人员用自然语言问数据，Agent 自主完成"意图分类 → 规划 → 生成 SQL → 查库 → 分析 → 图表 → 回答"，全程流式可见。
**闭环讲法**：注册登录 → 接入数据（示例数据开关 / 上传 CSV，多用户隔离）→ 自然语言提问 → Agent 工具循环 → 流式回答 + 图表 + 工具轨迹 → 高风险操作人工确认 → 结果导出 CSV → 会话历史沉淀。✅ 全链路真实可用，不是 demo 壳子。

## 2. 为什么用 Redis Streams，不用 HTTP 直调 / Kafka / RabbitMQ？
**要点**：任务提交与执行解耦，Java 只负责入队，Python worker 消费；天然支持消费组（多 worker 水平扩展）、消息确认（XACK）、失败重试；比 HTTP 直调多了削峰和恢复能力。
**为什么不是 Kafka**：数据量级和运维成本不匹配，Redis Streams 单机即可、与现有 Redis 复用；**为什么不是 RabbitMQ**：Streams 的消费组模型和"按任务 ID 流式回写结果"更贴合，且 XREADGROUP 断点续读现成。
**加分句**："当时对比过三种方案，选 Streams 是因为我们结果回写也是流式的，一个组件同时承担任务队列和结果通道。"

## 3. 为什么用 LangGraph，不自己写 while 循环？
**要点**：状态机显式建模（意图/规划/工具/反思/回答节点 + 条件路由）；**状态可持久化 + checkpoint**——这是人工确认断点恢复的前提；interrupt/resume 是框架级能力，手写循环要自己管理暂停/恢复和状态序列化。
**加分句**："人工确认不是加个 if，而是把图执行挂起、状态存进 checkpoint，审批后从断点继续——这是 LangGraph 最值钱的地方。"

## 4. 人工确认（HITL）怎么实现的？断点恢复原理？
**要点**：`agent_step` 里对"导出/全表/select *"类查询调用 `interrupt()` → 图执行暂停，状态存 MemorySaver → worker 发 `approval_required` 事件 → 前端弹窗 → Java 收到审批后往任务流发 `resume` 指令 → worker 用 `Command(resume={approved})` 恢复图 → `interrupt()` 返回审批结果，**拒绝则直接返回"已拒绝"，不执行查询**（这个拒绝分支是最近补的）。
**加分句**："审批拒绝不会执行查询——这个 bug 是我复盘时发现并修掉的。"

## 5. SQL 安全怎么防的？（纵深防御）
**要点**（从外到内讲）：
1. 只读账号 + 连接内 `SET TRANSACTION READ ONLY`（数据库层面兜底）✅
2. 关键字拦截：INSERT/UPDATE/DELETE/DROP/TRUNCATE 等直接拒绝 ✅
3. 禁止多条语句（分号检测）✅
4. `statement_timeout` 10s + 行数上限 1000 ✅
5. Python 沙箱：Docker 无网络、限内存 CPU（`--network none --memory 256m --cpus 0.5`）✅
6. 多租户表隔离：查询只允许访问自己启用的表（demo 表需开关、dataset_ 表按 user_id 过滤）✅
**加分句**："关键字拦截只是第一层，真正的兜底是数据库只读账号——即使 LLM 生成恶意 SQL 也执行不了，这是纵深防御。"

## 6. 多租户数据隔离怎么做？
**要点**：`get_schema` 只返回当前用户可见的表（示例表需 `demo_enabled` 开关 + `dataset_{userId}_{id}` 按用户建表）；`query_database` 解析 FROM/JOIN 的表名，不在白名单直接拒绝。✅

## 7. 成本怎么控制？
**要点**：每次 LLM 调用记录 prompt/completion tokens → 按计价折算（¥1e-6/token 输入、¥2e-6/token 输出）→ **每任务成本上限 `cost_cap_cny` 强制中断**（SQL 生成后、图表生成前检查累计成本，超预算立即停止）→ 完成后回传 tokenIn/tokenOut/costCny 展示在前端。
**加分句**："这是 Agent 上线必须有的东西——没有成本上限，一个失控循环能把预算烧穿。"

## 8. 越权漏洞（IDOR）？怎么发现怎么修的？
**要点**：复盘时发现 `GET /api/tasks/{id}`、`/trace`、`/events` 没校验任务归属，任何登录用户能看别人的任务；`approve` 也有同样问题。修复：`TaskService.requireOwned(userId, taskId)` 统一校验，越权返回 403，并补了单测锁定。✅
**加分句**："这个漏洞如果上线就是安全事故，我主动找出来的——安全是 Review 出来的，不是写出来的。"

## 9. 失败任务怎么处理？
**要点**：worker 处理异常时除了回写 `error` 事件，还**投递死信队列 `task:dlq`**（taskId/error/ts），Java 侧提供 `GET /api/tasks/dlq` 查询最近 50 条，运维可见；消费组 XACK 保证不重复处理。✅
**短板 ⚠️**：目前 DLQ 只"可查"，没有自动重试和告警——后续规划是带退避的重试 + 告警。

## 10. 评测体系怎么设计的？
**要点**：100 条评测集分 6 类（SQL 单表/多表/时间趋势/图表推荐/安全拦截/追问澄清），`run_eval.py` 跑图 → 自动比对结果（SQL 直接执行比行集，图表比类型，安全比拦截）→ 输出通过率/SQL 准确率/安全拦截率/平均延迟/成本 → 报告进 `eval_report.json`。✅
**数字要诚实**：基线 SQL 准确率 48%、安全拦截 100%。⚠️ reflect 反思节点当前是"检测到错误重试一次"的简化版，**错误回喂的自我纠错是当前正在做的迭代**——这块主动讲，展示迭代意识。

## 11. SSE 流式输出怎么实现的？
**要点**：worker 按 token 发布事件到 Redis Streams → Java `ResultConsumer` 消费（消费组）→ `SseService` 按 taskId 路由到 `SseEmitter` → 前端 EventSource 监听，token 事件累加成流式文本。✅
**短板 ⚠️（主动说）**：`SseService` 是单机内存态（ConcurrentHashMap 存 emitter），多实例部署会断 SSE；断线后事件不重放。多实例方案：Redis Pub/Sub 广播路由 or 按游标重放结果流。**"知道边界 + 有方案"比"不知道"强一百倍。**

## 12. 前端技术选型？
**要点**：React 18 + TypeScript + Vite；Zustand（轻量状态，chat store 管流式消息/审批/指标）；antd（成熟组件，弹窗/表单/表格快）；ECharts 渲染图表 spec；SSE 用原生 EventSource。理由：重交互的对话工作台，React 生态成熟、团队上手快。

## 13. RAG 怎么做的？
**要点**：知识库文档（数据字典/运维手册）→ Markdown 分块（按标题 + 100 字符重叠）→ 存 pgvector；检索先关键词（中文二元组 ILIKE），`embedding_enabled` 时用 bge-m3 向量相似度；供"knowledge_qa"意图（如"退款订单怎么排查"）使用。✅

## 14. 如果支撑 1000 用户 / 上线，你会改什么？
**要点**（按重要性）：① SSE 多实例化（Redis Pub/Sub 路由）② 限流防刷（注册/登录/任务接口滑动窗口）③ 任务幂等（Idempotency-Key）④ Flyway 迁移替代 ddl-auto ⑤ Micrometer 指标 + 结构化日志 + 告警（队列积压、失败率、成本）⑥ Docker 镜像一键部署 + HTTPS。**这条是"架构演进"题，答出①+⑤就赢了。**

## 15. 你这个项目 3 个月后想做成什么样？
**要点**：① SQL 准确率迭代到 80%+（评测曲线可见）② 上线给真实用户用，收集 badcase 回流评测集 ③ MCP 客户端集成——worker 通过 MCP 调外部工具 ④ 长短期记忆（会话摘要、用户偏好）。**体现"评测闭环驱动迭代"的工程思维。**

---

## 速记卡（面试前 10 分钟看这个）

- **一句话项目**：全链路闭环的 ChatBI 自主 Agent，LangGraph 状态机 + Redis Streams 解耦 + 人工确认 + 100 条评测集。
- **三个亮点**：断点恢复的人工确认 / 纵深安全（只读库+沙箱+隔离）/ 评测闭环 + 成本预算强制。
- **三个主动承认的短板**：SSE 单机内存态 / DLQ 无自动重试 / reflect 纠错迭代中。
- **一个故事**：主动发现并修复了任务接口越权漏洞 + 审批拒绝仍执行查询的 bug。
