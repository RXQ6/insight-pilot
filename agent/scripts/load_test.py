"""轻量压测：并发提交分析任务，统计吞吐与延迟分位。

用法（先起好 db/redis/java/agent 四端）：
    .venv/Scripts/python scripts/load_test.py --concurrency 10 --each 5
"""

import argparse
import concurrent.futures
import json
import statistics
import time

import requests

BASE = "http://localhost:8080/api"


def post(path, payload, headers=None):
    r = requests.post(BASE + path, json=payload, headers=headers or {}, timeout=15)
    r.raise_for_status()
    return r.json()


def setup(username="load", password="load1234"):
    try:
        post("/auth/register", {"username": username, "password": password})
    except requests.HTTPError:
        pass
    login = post("/auth/login", {"username": username, "password": password})
    headers = {"Authorization": f"Bearer {login['token']}"}
    session = post("/sessions", {"title": "压测会话"}, headers)
    return headers, session["sessionId"]


def submit_one(headers, session_id, question):
    started = time.time()
    post("/tasks", {"sessionId": session_id, "message": question}, headers)
    return (time.time() - started) * 1000


def main():
    parser = argparse.ArgumentParser(description="InsightPilot load test")
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--each", type=int, default=5, help="requests per worker")
    args = parser.parse_args()

    headers, session_id = setup()
    question = "2026年4月订单总数是多少？"
    latencies = []
    errors = 0

    def worker(_):
        nonlocal errors
        local = []
        for _ in range(args.each):
            try:
                local.append(submit_one(headers, session_id, question))
            except Exception:
                errors += 1
        return local

    started = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        for batch in ex.map(worker, range(args.concurrency)):
            latencies.extend(batch)
    elapsed = time.time() - started

    total = len(latencies)
    latencies.sort()
    p50 = statistics.median(latencies)
    p95 = latencies[int(len(latencies) * 0.95) - 1] if latencies else 0
    print(
        json.dumps(
            {
                "concurrency": args.concurrency,
                "total_requests": total,
                "errors": errors,
                "elapsed_sec": round(elapsed, 2),
                "throughput_qps": round(total / elapsed, 2),
                "latency_p50_ms": round(p50, 1),
                "latency_p95_ms": round(p95, 1),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
