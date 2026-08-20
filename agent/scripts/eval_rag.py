"""RAG 检索质量评测：recall@k / hit@k（默认同时输出 recall@1/@3/@5）。

用法（先 build_knowledge_base 建库）：
    .venv/Scripts/python scripts/eval_rag.py                 # recall@1/3/5
    .venv/Scripts/python scripts/eval_rag.py --top-k 10      # 只跑单个 k
    .venv/Scripts/python scripts/eval_rag.py --ks 1 3 5 10   # 自定义 k 列表

报告输出到 agent/data/rag_eval_report.json。
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from insight_agent.config import settings
from insight_agent.rag.retriever import retrieve_top_k

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
CASES_PATH = DATA_DIR / "rag_eval_cases.json"
REPORT_PATH = DATA_DIR / "rag_eval_report.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="RAG recall@k evaluation")
    parser.add_argument("--top-k", type=int, default=0, help="single k (overrides --ks)")
    parser.add_argument("--ks", type=int, nargs="+", default=[1, 3, 5], help="list of k values")
    args = parser.parse_args()
    ks = [args.top_k] if args.top_k > 0 else args.ks

    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    max_k = max(ks)
    results = []

    for case in cases:
        started = time.time()
        chunks = retrieve_top_k(case["question"], top_k=max_k)
        elapsed_ms = int((time.time() - started) * 1000)
        results.append(
            {
                "id": case["id"],
                "question": case["question"],
                "expected_title": case["expected_title"],
                "hits_at": {k: any(case["expected_title"] in c for c in chunks[:k]) for k in ks},
                "latencyMs": elapsed_ms,
                "retrieved_titles": sorted(
                    {chunk.split("|")[1].split("]")[0] if "|" in chunk else "?" for chunk in chunks}
                ),
            }
        )

    total = len(results)
    recall = {k: round(sum(1 for r in results if r["hits_at"][k]) / total, 4) for k in ks}
    by_doc = {}
    for item in results:
        doc = by_doc.setdefault(item["expected_title"], {"total": 0, **{f"hits@{k}": 0 for k in ks}})
        doc["total"] += 1
        for k in ks:
            doc[f"hits@{k}"] += 1 if item["hits_at"][k] else 0

    report = {
        "runAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "mode": "hybrid (keyword+vector, RRF)" if settings.embedding_enabled else "keyword only",
        "ks": ks,
        "total": total,
        "recallAtK": {f"recall@{k}": recall[k] for k in ks},
        "avgLatencyMs": round(sum(item["latencyMs"] for item in results) / total, 1),
        "byDoc": by_doc,
        "failed": [item["id"] for item in results if not item["hits_at"][max_k]],
        "details": results,
    }
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
