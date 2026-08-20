# InsightPilot

> 全链路闭环的 ChatBI 自主 Agent：用户用自然语言提问，Agent 自主完成意图分类 → 任务规划 → 只读 SQL / Python 沙箱 / 知识库工具循环 → 反思纠错 → 流式回答 + 图表 + CSV 导出。Spring Boot 控制面 + Redis Streams 消息队列 + React 工作台，带人工确认、成本预算与评测驱动迭代体系。

[![CI](https://github.com/RXQ6/insight-pilot/actions/workflows/ci.yml/badge.svg)](https://github.com/RXQ6/insight-pilot/actions/workflows/ci.yml)

---

## 演示

API 层一键跑通完整业务闭环（注册 → 自然语言问答 → 图表 → 人工确认 → 导出 CSV → DLQ 查询）：

```bash
cd agent
.venv/Scripts/python scripts/demo_api.py
```

前端工作台访问 `http://localhost:5173`，可体验流式对话、工具轨迹、图表渲染、人工确认弹窗、CSV 下载与数据上传。

## 关键指标

| 指标 | 数值 | 说明 |
|---|---|---|
| 评测集 | **116 条 · 10 类场景** | 基础：单表/多表/时间趋势/图表/安全/追问；进阶：窗口函数/留存/同比环比/异常检测 |
| 总通过率 | **78.4%**（91/116，迭代前 54%） | 评测驱动迭代：prompt 工程 + 反思纠错 + ReAct 工具循环，报告见 `agent/data/eval_report.json` |
| SQL 准确率 | **74.7%**（迭代前 48%） | 时间模板 / 统计口径 / 多表 few-shot 注入 SQL 系统提示词 |
| 安全拦截率 | **100%** | 只读 SQL + 沙箱 + 越权防护，10 条安全攻击用例全拦截 |
| 端到端平均延迟 | ~7.3s | 含 LLM 多轮调用与 ReAct 决策循环 |
| 单次平均成本 | ~¥0.006 | DeepSeek，每任务成本上限强制中断 |
| 工程质量 | 测试 + CI | 34 个 Python 单测 + 11 个 JUnit 单测，GitHub Actions 三端流水线 |

## 核心亮点

1. **LangGraph 状态机 + ReAct 工具循环**：意图分类 / 规划 / 工具循环 / 反思 / 回答五节点条件路由；`agent_step` 内 LLM 自主决策"调用工具还是 finish"（可执行 Python 计算 / 补充查询 / 生成图表），带步数与成本预算兜底；checkpoint + interrupt/resume 实现**人工确认断点恢复**——审批被拒时查询不执行
2. **自我纠错（reflect）**：SQL 执行失败时把错误回喂给模型重新生成（fix_hint 机制），评测驱动 prompt 迭代；期间发现并修复了 `Annotated[list, operator.add]` 无法清空字段导致的反思死循环
3. **异步任务架构**：Redis Streams 消费组解耦任务提交与执行，SSE 逐 token 流式推送；失败任务进**死信队列（DLQ）**可查询；每任务成本上限强制中断
4. **纵深安全**：数据库只读账号 + 事务只读 + SQL 关键字拦截 + Docker 无网络沙箱 + 多租户表隔离；主动发现并修复任务/审批接口越权（IDOR）
5. **评测驱动迭代**：116 条评测集 + 自动化报告 + 失败用例诊断脚本，SQL 准确率 48% → 74.7%（详见 `docs/eval-optimization.md`）

## 功能

- 自然语言数据分析：查询、对比、趋势、图表推荐
- LangGraph 自主流程：意图分类、规划、ReAct 工具循环（LLM 自主选工具）、反思、回答
- 工具层：只读 SQL、Python 沙箱、ECharts 图表、知识库 RAG（关键词+向量混合检索，recall@1 86.7%）、CSV 结果导出
- Java 控制面：JWT 鉴权、会话与任务管理、Redis Streams、SSE 流式推送
- React 工作台：流式对话、图表、工具轨迹、人工确认、文件下载
- 多租户数据接入：示例数据开关 + CSV 上传，按用户建表隔离
- 可靠性与安全：DLQ 可查询、越权防护、成本预算、token/延迟/费用回传展示

## 架构

```mermaid
flowchart LR
    U[用户] --> R[React 工作台]
    R --> J[Java 控制面 Spring Boot]
    J --> PG[(PostgreSQL + pgvector)]
    J --> RS[(Redis Streams)]
    RS --> W[Python Worker LangGraph Agent]
    W --> TOOL[工具层]
    TOOL --> DB[(业务库只读)]
    TOOL --> SB[Python Docker 沙箱]
    TOOL --> KB[知识库 RAG]
    W --> RES[结果流回写 Redis]
    RES --> J
    J --> SSE[SSE 流式推送]
    SSE --> R
```

**数据流**：用户提问 → Java 入队 `task:input` → Python Worker（LangGraph）消费并执行工具循环 → 事件（token/工具调用/图表/文件）写回 `task:result` → Java 消费组读取 → SSE 推送到前端；高风险查询触发 `interrupt` 等待人工确认，审批结果通过 `resume` 从断点继续。

## 技术选型（为什么这么设计）

| 选型 | 理由 |
|---|---|
| **LangGraph** 而非手写 agent loop | 状态机显式建模；checkpoint 持久化是人工确认断点恢复的前提；interrupt/resume 框架级支持 |
| **Redis Streams** 而非 HTTP 直调 / Kafka | 任务提交与执行解耦（削峰、恢复）；消费组支持多 worker 水平扩展；同一组件同时承担任务队列与结果回写通道；单机即可，运维成本低 |
| **Java 控制面 + Python Worker** | 控制面要工程化（鉴权/审计/事务），Agent 生态在 Python，按职责拆分两个进程 |
| **PostgreSQL + pgvector** | 业务数据与 RAG 向量同一存储；只读账号做数据库层安全兜底 |
| **SSE** 而非 WebSocket | 单向流式输出场景更简单，原生 EventSource 支持，断线重连成本低 |

## 快速启动

### 1. 启动基础设施

```bash
docker compose up -d db redis
```

### 2. 导入示例数据（两种方式任选）

方式 A（Docker 内导入，无需安装 psql）：

```bash
Get-Content agent/data/sample_data.sql -Raw | docker compose exec -T db psql -U insight -d insight
```

方式 B（本机有 psql）：

```bash
psql -U insight -d insight -f agent/data/sample_data.sql
```

### 3. 配置模型 Key

在 `agent/.env` 中填写（参考 `agent/.env.example`）：

```env
LLM_API_KEY=sk-xxx
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
REDIS_URL=redis://localhost:6379/0
POSTGRES_DSN=postgresql://insight:insight@localhost:5432/insight
```

### 4. 启动三端

```bash
cd java && mvn -DskipTests package && java -jar target/insight-pilot-control-plane-0.1.0.jar
cd agent && .venv/Scripts/python -m insight_agent.worker
cd frontend && npm install && npm run dev
```

前端 `http://localhost:5173`，Java API `http://localhost:8080`，OpenAPI 文档 `/swagger-ui.html`。

## 评测

```bash
cd agent
.venv/Scripts/python scripts/run_eval.py                 # 全部 116 条
.venv/Scripts/python scripts/run_eval.py --type time_trend   # 按场景
.venv/Scripts/python scripts/diagnose_case.py sql_single_022 # 诊断单条失败用例
```

- 评测集：`agent/data/eval_cases.json`（116 条，10 类场景）
- 报告：`agent/data/eval_report.json`（通过率/SQL 准确率/安全拦截率/延迟/成本）
- 迭代方法论：`docs/eval-optimization.md`（失败用例 → 归类根因 → few-shot 反哺 → 重跑）

## 测试与 CI

- **Python**：34 个单测（预算强制、审批拒绝、导出、SQL 拦截、reflect 纠错、事件流、DLQ），mock LLM/DB/Redis，无外部依赖
- **Java**：11 个 JUnit 单测（JWT、越权 403、DLQ 解析）
- **CI**：GitHub Actions 三端流水线（Agent pytest / Java mvn test / React build），见 `.github/workflows/ci.yml`

## 安全设计

- 数据库只读：连接内强制 `SET TRANSACTION READ ONLY` + 独立只读账号
- SQL 防护：禁止 INSERT/UPDATE/DELETE/DROP/TRUNCATE 等关键字、禁止多条语句、`statement_timeout` + 行数上限
- Python 沙箱：Docker `--network none` + 限内存/CPU（`SANDBOX_MODE=docker`）
- 多租户隔离：`get_schema` 只暴露当前用户可见表，查询按表名白名单拦截
- 鉴权与审计：JWT + BCrypt + 审计日志；任务/审批接口归属校验（越权返回 403）
- API Key 只放 `agent/.env`，不提交到 Git

## 核心 API

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | /api/auth/register · /login | 注册 / 登录 |
| POST | /api/sessions | 创建会话 |
| GET | /api/sessions/{id}/messages | 会话消息 |
| POST | /api/tasks | 提交分析任务 |
| GET | /api/tasks/{taskId} | 查询任务结果 |
| GET | /api/tasks/{taskId}/events | SSE 事件流 |
| GET | /api/tasks/{taskId}/trace | 工具调用轨迹 |
| POST | /api/tasks/{taskId}/approve | 人工确认 |
| GET | /api/tasks/dlq | 死信队列最近失败任务 |
| POST | /api/datasets/upload | CSV 数据上传（按用户隔离建表） |
| GET | /api/eval/summary | 评测摘要 |
| GET | /api/health | 健康检查 |

## 开源贡献

- [langchain-ai/docs PR #5585](https://github.com/langchain-ai/docs/pull/5585)：向 LangGraph 官方文档 Reducers 章节补充 *Resetting a reducer field*——本项目踩坑 `Annotated[list, operator.add]` 无法清空字段导致反思死循环，修复（commit `7510aa5`）后回馈官方文档，CI 全绿（review 中）

## 目录结构

```text
agent/       Python LangGraph Worker（节点/工具/评测/MCP Server）
  ├── insight_agent/   graph 状态机、nodes 节点、tools 工具层、rag 知识库
  ├── scripts/         run_eval 评测、diagnose_case 诊断、demo_api 演示
  └── tests/           34 个单元测试
java/        Spring Boot 控制面（JWT/任务/会话/数据集/DLQ/SSE）
frontend/    React 工作台（对话/数据/历史/评测四页）
docs/        评测迭代方法论、面试问答弹药、简历素材、开源贡献记录
```

## 后续规划

- MCP 客户端集成：Worker 通过 MCP 调用外部工具
- Langfuse 追踪：任务级工具调用链、成本与延迟可视化
- SSE 断线重连重放
- 在线部署与 Docker 全栈镜像
- 长短期记忆：会话摘要压缩、用户偏好持久化
