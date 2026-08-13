# 运维手册
- PostgreSQL：localhost:5432，数据库 insight，业务账号 insight，只读账号 insight_readonly
- Redis：localhost:6379，任务输入流 task:input，结果流 task:result
- Java API：8080；前端：5173；Worker 消费 Redis 任务执行 LangGraph

## 排查步骤
1. 检查 /api/health，确认 postgres 和 redis 均为 UP
2. 查看 Java API 日志，确认任务是否进入 Redis
3. 查看 Worker 日志，确认模型调用是否成功
4. 检查 task 状态：pending、running、waiting_approval、done、error
