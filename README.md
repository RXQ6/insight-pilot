# InsightPilot

InsightPilot 是一个面向数据分析场景的自主 Agent 项目：用户用自然语言提问，Agent 自主完成意图理解、任务规划、SQL 生成与执行、Python 分析、图表生成和结果解释，并通过 Java 控制面、Redis 消息队列和 React 工作台形成完整产品闭环。

## 功能

- 自然语言数据分析：查询、对比、趋势、图表推荐
- LangGraph 自主流程：意图分类、规划、工具循环、反思、回答
- 工具层：只读 SQL、Python 沙箱、ECharts 图表、知识库检索
- Java 控制面：JWT 鉴权、会话与任务管理、Redis Streams、SSE 流式推送
- React 工作台：流式对话、图表、工具轨迹、人工确认
- 评测体系：100 条评测集与自动化报告

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

## 快速启动

1. 启动基础设施：

```bash
docker compose up -d db redis
```

2. 生成业务数据：

```bash
cd agent
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python scripts/generate_business_data.py
```

3. 配置模型 Key：

在 `agent/.env` 中填写：

```env
LLM_API_KEY=sk-xxx
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
REDIS_URL=redis://localhost:6379/0
POSTGRES_DSN=postgresql://insight:insight@localhost:5432/insight
```

4. 启动三端：

```bash
cd java && mvn -DskipTests package && java -jar target/insight-pilot-control-plane-0.1.0.jar
cd agent && .venv/Scripts/python -m insight_agent.worker
cd frontend && npm install && npm run dev
```

前端访问 `http://localhost:5173`，Java API 访问 `http://localhost:8080`，OpenAPI 文档在 `/swagger-ui.html`。

## 核心 API

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | /api/auth/register | 注册 |
| POST | /api/auth/login | 登录 |
| GET | /api/auth/me | 当前用户 |
| POST | /api/sessions | 创建会话 |
| GET | /api/sessions | 会话列表 |
| GET | /api/sessions/{id}/messages | 会话消息 |
| POST | /api/tasks | 提交分析任务 |
| GET | /api/tasks/{taskId} | 查询任务结果 |
| GET | /api/tasks/{taskId}/events | SSE 事件流 |
| GET | /api/tasks/{taskId}/trace | 工具调用轨迹 |
| POST | /api/tasks/{taskId}/approve | 人工确认 |
| GET | /api/eval/summary | 评测摘要 |
| GET | /api/health | 健康检查 |

## 评测

```bash
cd agent
.venv/Scripts/python scripts/run_eval.py
```

评测集位于 `agent/data/eval_cases.json`，报告输出到 `agent/data/eval_report.json`，支持 `--limit` 和 `--type` 参数。

## 安全设计

- 数据库只读：查询走独立只读账号，连接内强制 `SET TRANSACTION READ ONLY`
- Python 沙箱：`SANDBOX_MODE=docker` 时通过 Docker 无网络、限内存/CPU 执行
- SQL 防护：禁止 INSERT/UPDATE/DELETE/DROP 等关键字
- 鉴权与审计：JWT + 审计日志
- API Key 只放在 `agent/.env`，不提交到 Git

## 目录结构

```text
agent/       Python LangGraph Worker 与评测
java/        Spring Boot 控制面
frontend/    React 工作台
```

## 后续规划

- 人工确认后 Worker 断点恢复
- MCP 工具标准化
- Dify 低代码对照
- 在线部署与 Docker 全栈镜像

