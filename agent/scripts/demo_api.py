"""一键演示脚本：跑通 InsightPilot 完整业务闭环。

覆盖：注册/登录 -> 建会话 -> 自然语言问答(基础SQL) -> 图表推荐 -> 导出CSV(人工确认) -> 工具轨迹 -> DLQ 查询。

用法（先起好 db/redis/java/agent 四端）：
    .venv/Scripts/python scripts/demo_api.py
"""

import json
import time

import requests

BASE = "http://localhost:8080/api"


def post(path, payload, headers=None):
    response = requests.post(BASE + path, json=payload, headers=headers or {}, timeout=10)
    response.raise_for_status()
    return response.json()


def get(path, headers=None):
    response = requests.get(BASE + path, headers=headers or {}, timeout=10)
    response.raise_for_status()
    return response.json()


def wait_task(headers, task_id, timeout=90, interval=2):
    """轮询任务直到终态，返回任务详情。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        task = get(f"/tasks/{task_id}", headers)
        if task["status"] in ("done", "error", "waiting_approval"):
            return task
        time.sleep(interval)
    return {"status": "timeout"}


def step(title: str) -> None:
    print(f"\n=== {title} ===")


def main():
    username = "demo"
    password = "demo1234"

    step("1. 注册 / 登录")
    try:
        post("/auth/register", {"username": username, "password": password})
    except requests.HTTPError:
        pass
    login = post("/auth/login", {"username": username, "password": password})
    headers = {"Authorization": f"Bearer {login['token']}"}
    print(f"登录成功 user={login['user']['username']}")

    step("2. 创建会话")
    session = post("/sessions", {"title": "演示会话"}, headers)
    print(f"sessionId={session['sessionId']}")

    step("3. 基础 SQL 问答：2026年4月订单总数")
    task = post("/tasks", {"sessionId": session["sessionId"], "message": "2026年4月订单总数是多少？"}, headers)
    detail = wait_task(headers, task["taskId"])
    output = detail.get("output") or {}
    print(json.dumps({
        "status": detail["status"],
        "answer": (output.get("answer") or "")[:60],
        "tokenIn": detail.get("tokenIn"),
        "tokenOut": detail.get("tokenOut"),
        "costCny": detail.get("costCny"),
        "latencyMs": detail.get("latencyMs"),
    }, ensure_ascii=False))

    step("4. 图表推荐：用柱状图展示各区域销售额")
    task = post("/tasks", {"sessionId": session["sessionId"], "message": "用柱状图展示各区域销售额"}, headers)
    detail = wait_task(headers, task["taskId"])
    output = detail.get("output") or {}
    print(json.dumps({
        "status": detail["status"],
        "chartType": (output.get("chartSpec") or {}).get("type"),
        "answer": (output.get("answer") or "")[:60],
    }, ensure_ascii=False))

    step("5. 导出 CSV（触发人工确认）")
    task = post("/tasks", {"sessionId": session["sessionId"], "message": "导出各区域销售额到CSV"}, headers)
    detail = wait_task(headers, task["taskId"])
    if detail["status"] == "waiting_approval":
        print("已进入 waiting_approval，前端将弹出人工确认弹窗 —— 现在通过 API 批准")
        approved = post(f"/tasks/{task['taskId']}/approve", {"approved": True}, headers)
        print(f"审批结果: status={approved['status']}")
        detail = wait_task(headers, task["taskId"])
    output = detail.get("output") or {}
    print(json.dumps({
        "status": detail["status"],
        "hasFile": bool(output.get("file")),
        "filename": (output.get("file") or {}).get("filename"),
        "rowCount": (output.get("file") or {}).get("rowCount"),
    }, ensure_ascii=False))

    step("6. 工具调用轨迹")
    trace = get(f"/tasks/{task['taskId']}/trace", headers)
    for item in trace.get("steps", []):
        print(f"  tool={item['tool']} status={item['status']}")

    step("7. 死信队列（应为空列表）")
    dlq = get("/tasks/dlq", headers)
    print(json.dumps({"dlqCount": len(dlq.get("items", []))}, ensure_ascii=False))

    step("8. 会话历史")
    messages = get(f"/sessions/{session['sessionId']}/messages", headers)
    print(f"消息数: {len(messages.get('items', []))}")

    print("\n✅ 演示闭环跑通")


if __name__ == "__main__":
    main()
