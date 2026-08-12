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


QUESTIONS = [
    "2026年4月订单总数是多少？",
    "用柱状图展示各区域销售额",
]


def run_question(headers, session, question):
    task = post(
        "/tasks",
        {"sessionId": session["sessionId"], "message": question},
        headers,
    )
    for _ in range(30):
        time.sleep(2)
        status = get(f"/tasks/{task['taskId']}", headers)
        if status["status"] in ("done", "error"):
            return status
    return {"status": "timeout"}


def main():
    try:
        post("/auth/register", {"username": "smoke", "password": "pass1234"})
    except requests.HTTPError:
        pass

    login = post("/auth/login", {"username": "smoke", "password": "pass1234"})
    headers = {"Authorization": f"Bearer {login['token']}"}
    session = post("/sessions", {"title": "真实问答验证"}, headers)

    for question in QUESTIONS:
        status = run_question(headers, session, question)
        output = status.get("output") or {}
        chart = output.get("chartSpec") or {}
        print(
            json.dumps(
                {
                    "question": question,
                    "status": status["status"],
                    "hasChart": bool(chart.get("type")),
                    "chartType": chart.get("type"),
                    "answerLen": len(output.get("answer") or ""),
                    "tokenIn": status.get("tokenIn"),
                    "tokenOut": status.get("tokenOut"),
                    "costCny": status.get("costCny"),
                },
                ensure_ascii=True,
            )
        )


if __name__ == "__main__":
    main()
