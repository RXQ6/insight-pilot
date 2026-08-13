import json
import time

import requests

BASE = "http://localhost:8080/api"


def post(path, payload, headers=None):
    response = requests.post(BASE + path, json=payload, headers=headers or {}, timeout=10)
    response.raise_for_status()
    return response.json()


def main():
    login = post("/auth/login", {"username": "smoke", "password": "pass1234"})
    token = login["token"]
    headers = {"Authorization": f"Bearer {token}"}
    session = post("/sessions", {"title": "stream test"}, headers)
    task = post("/tasks", {"sessionId": session["sessionId"], "message": "用柱状图展示各区域销售额"}, headers)

    counts = {"token": 0, "tool_call": 0, "chart": 0, "result": 0, "done": 0}
    url = f"http://localhost:8080/api/tasks/{task['taskId']}/events?token={token}"
    with requests.get(url, stream=True, timeout=60) as response:
        event_name = None
        for raw in response.iter_lines():
            if not raw:
                continue
            line = raw.decode("utf-8", errors="replace")
            if line.startswith("event:"):
                event_name = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                try:
                    data = json.loads(line.split(":", 1)[1].strip())
                except Exception:
                    continue
                event_type = data.get("type") or event_name
                counts[event_type] = counts.get(event_type, 0) + 1
                if event_type == "done":
                    break
    print(json.dumps(counts))


if __name__ == "__main__":
    main()
