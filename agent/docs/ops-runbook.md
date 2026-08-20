# 运维手册

## 服务连接信息
- PostgreSQL：localhost:5432，数据库 insight，业务账号 insight，只读账号 insight_readonly
- Redis：localhost:6379，任务输入流 task:input，结果流 task:result，死信队列 task:dlq
- Java API：8080；前端：5173；Worker 消费 Redis 任务执行 LangGraph

## 启动步骤
1. docker compose up -d db redis 启动基础设施
2. 导入示例数据：psql -U insight -d insight -f agent/data/sample_data.sql
3. 启动 Java：mvn -DskipTests package && java -jar target/insight-pilot-control-plane-0.1.0.jar
4. 启动 Worker：cd agent && .venv/Scripts/python -m insight_agent.worker
5. 启动前端：cd frontend && npm run dev，访问 http://localhost:5173

## 任务状态机
- pending：任务已入队，Worker 尚未消费
- running：Worker 正在执行（LangGraph 流转中）
- waiting_approval：触发人工确认，等待审批
- done：执行完成，结果已回写
- error：执行失败，错误信息在任务详情中

## 排查步骤
1. 检查 /api/health，确认 postgres 和 redis 均为 UP
2. 查看 Java API 日志，确认任务是否进入 Redis（task:input 是否有消息）
3. 查看 Worker 日志，确认模型调用是否成功、是否有异常堆栈
4. 检查任务状态：pending 说明 Worker 没消费；waiting_approval 说明等人审批；error 看错误信息
5. 任务失败后检查死信队列 task:dlq：GET /api/tasks/dlq 查看最近失败任务

## 常见故障
- 任务一直 pending：Worker 没启动或 Redis 连接失败，检查 Worker 进程
- 查询结果为空：先确认数据表有数据（sample_data.sql 是否导入），再检查时间范围
- 审批后不继续：Worker 重启过会导致内存 checkpoint 丢失，需要重新触发任务
- 成本异常偏高：检查 LLM_API_KEY 是否生效、任务是否大量触发人工确认重试
