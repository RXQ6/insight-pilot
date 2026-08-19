# InsightPilot

> 全链路闭环的 ChatBI 自主 Agent：自然语言提问 → 意图分类 → 规划 → 只读 SQL / Python 沙箱 / 知识库工具循环 → 反思 → 流式回答 + 图表 + CSV 导出，由 Spring Boot 控制面、Redis Streams 消息队列与 React 工作台支撑，带 100 条评测集、人工确认与成本预算体系。

[![CI](https://github.com/RXQ6/insight-pilot/actions/workflows/ci.yml/badge.svg)](https://github.com/RXQ6/insight-pilot/actions/workflows/ci.yml)

## 演示

API 层一键演示完整业务闭环（注册 → 自然语言问答 → 图表 → 人工确认 → 导出 CSV → DLQ 查询）：

```bash
cd agent
.venv/Scripts/python scripts/demo_api.py
```

前端工作台访问 `http://localhost:5173` 即可体验对话、工具轨迹、图表与数据上传。

## 关键指标

| 指标 | 数值 | 说明 |
|---|---|---|
| 评测集 | 116 条 | 基础：单表/多表/时间趋势/图表/安全/追问；进阶：窗口函数/留存/同比环比/异常检测 |
| 总通过率 | 67.2%（迭代前 54%） | prompt 工程 + 反思纠错驱动迭代，`agent/data/eval_report.json` |
| SQL 准确率 | 62.7%（迭代前 48%） | 时间模板/统计口径/多表 few-shot 注入 |
| 安全拦截率 | 100% | 只读 SQL + 沙箱 + 越权防护 |
| 平均端到端延迟 | ~6.3s | 含 LLM 多轮调用 |
| 单次平均成本 | ~¥0.005 | DeepSeek，每任务成本上限强制中断 |
| 工程质量 | 测试 + CI | pytest / JUnit / GitHub Actions 三端流水线 |

## 功能

- 自然语言数据分析：查询、对比、趋势、图表推荐
- LangGraph 自主流程：意图分类、规划、工具循环、反思、回答
- 工具层：只读 SQL、Python 沙箱、ECharts 图表、知识库检索、CSV 结果导出
- Java 控制面：JWT 鉴权、会话与任务管理、Redis Streams、SSE 流式推送
- React 工作台：流式对话、图表、工具轨迹、人工确认、文件下载
- 评测体系：116 条评测集（基础 + 窗口函数/留存/同比环比/异常检测等进阶垂直场景）与自动化报告
- 成本控制：每任务成本上限强制中断，token/延迟/费用回传展示
- 可靠性与安全：失败任务进入死信队列（DLQ）可查询；任务/会话接口越权防护

## 开源贡献

- [langchain-ai/docs PR #5585](https://github.com/langchain-ai/docs/pull/5585)：向 LangGraph 官方文档的 Reducers 章节补充 "Resetting a reducer field"——本项目中 `Annotated[list, operator.add]` 的 errors 字段无法被 `[]` 清空导致 Agent 反思循环死循环，修复（[`7510aa5`](https://github.com/RXQ6/insight-pilot/commit/7510aa5)）后回馈官方文档（全部 CI 检查通过，review 中）

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


## 预生成数据

不想运行生成脚本时，可以直接导入仓库里的示例数据：

```bash
psql -U insight -d insight -f agent/data/sample_data.sql
```
## CSV 数据上传（已实现）

- 前端「数据」页支持上传 CSV、预览前 20 行、删除数据集
- 每个用户的数据独立建表：dataset_{userId}_{id}
- Agent 的 get_schema 只暴露当前用户的数据表，SQL 查询会拦截其他用户的数据表
- 接口：POST /api/datasets/upload、GET /api/datasets、GET /api/datasets/{id}/preview、DELETE /api/datasets/{id}

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
| GET | /api/tasks/dlq | 死信队列最近失败任务 |
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

- 自动化测试（pytest / JUnit + Testcontainers）与 GitHub Actions CI
- MCP 客户端集成：Worker 通过 MCP 调用外部工具
- Langfuse 追踪：任务级工具调用链、成本与延迟可视化
- SSE 断线重连重放
- Dify 低代码对照
- 在线部署与 Docker 全栈镜像

