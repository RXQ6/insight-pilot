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
    login = post("/auth/login", {"username": "smoke", "password": "pass1234"})
    headers = {"Authorization": f"Bearer {login['token']}"}
    session = post("/sessions", {"title": "demo off test"}, headers)
    task = post(
        "/tasks",
        {"sessionId": session["sessionId"], "message": "2026年4月订单总数是多少？"},
        headers,
    )
    status = None
    for _ in range(15):
        time.sleep(2)
        status = get(f"/tasks/{task['taskId']}", headers)
        if status["status"] in ("done", "error"):
            break
    answer = (status.get("output") or {}).get("answer") or ""
    print(
        json.dumps(
            {
                "status": status["status"],
                "answerLen": len(answer),
                "hasGuidance": ("启用示例" in answer) or ("没有可用数据" in answer) or ("上传" in answer),
            },
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    main()
