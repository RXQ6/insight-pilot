import json
import time

import requests

BASE = "http://localhost:8080/api"


def post(path, payload, headers=None):
    response = requests.post(BASE + path, json=payload, headers=headers or {}, timeout=10)
    response.raise_for_status()
    return response.json()


def get(path, headers):
    response = requests.get(BASE + path, headers=headers, timeout=10)
    response.raise_for_status()
    return response.json()


def main():
    try:
        post("/auth/register", {"username": "approve", "password": "pass1234"})
    except requests.HTTPError:
        pass
    login = post("/auth/login", {"username": "approve", "password": "pass1234"})
    headers = {"Authorization": f"Bearer {login['token']}"}
    session = post("/sessions", {"title": "人工确认验证"}, headers)
    task = post(
        "/tasks",
        {"sessionId": session["sessionId"], "message": "查询 orders 表所有字段所有行，不要加 LIMIT"},
        headers,
    )
    print("taskId:", task["taskId"])

    status = None
    for _ in range(20):
        time.sleep(2)
        status = get(f"/tasks/{task['taskId']}", headers)
        if status["status"] in ("waiting_approval", "done", "error"):
            break
    print("beforeApprove:", status["status"])

    if status["status"] == "waiting_approval":
        post(f"/tasks/{task['taskId']}/approve", {"approved": True, "note": "同意"}, headers)
        for _ in range(40):
            time.sleep(2)
            status = get(f"/tasks/{task['taskId']}", headers)
            if status["status"] in ("done", "error"):
                break
    output = status.get("output") or {}
    print(
        json.dumps(
            {
                "status": status["status"],
                "hasAnswer": bool(output.get("answer")),
                "answerLen": len(output.get("answer") or ""),
                "hasChart": bool((output.get("chartSpec") or {}).get("type")),
            }
        )
    )


if __name__ == "__main__":
    main()
