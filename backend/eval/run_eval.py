"""Batch RAGAS evaluation. Requires an indexed filing and OPENROUTER_API_KEY.

Usage (from backend/):

    python -m eval.run_eval
    python -m eval.run_eval --limit 3 --document-id <uuid>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.evaluator import evaluate_rag  # noqa: E402
from app.services.rag_chain import run_rag  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--eval-set",
        default=str(Path(__file__).with_name("eval_set.json")),
    )
    parser.add_argument("--document-id")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    payload = json.loads(Path(args.eval_set).read_text(encoding="utf-8"))
    items = payload["items"]
    if args.limit:
        items = items[: args.limit]

    print(f"{'id':<6} {'faith':>8} {'relev':>8} {'prec':>8}  question")
    print("-" * 88)
    rows = []
    for item in items:
        result = run_rag(item["question"], document_id=args.document_id)
        metrics = evaluate_rag(
            question=item["question"],
            answer=result["answer"],
            contexts=result["contexts"],
            ground_truth=item.get("ground_truth"),
        )
        rows.append(metrics)
        print(
            f"{item['id']:<6} "
            f"{_fmt(metrics.get('faithfulness')):>8} "
            f"{_fmt(metrics.get('answer_relevancy')):>8} "
            f"{_fmt(metrics.get('context_precision')):>8}  "
            f"{item['question'][:56]}"
        )

    def avg(key: str) -> str:
        vals = [r[key] for r in rows if r.get(key) is not None]
        if not vals:
            return "n/a"
        return f"{sum(vals) / len(vals):.4f}"

    print("-" * 88)
    print(
        f"{'AVG':<6} {avg('faithfulness'):>8} "
        f"{avg('answer_relevancy'):>8} {avg('context_precision'):>8}"
    )
    print("JSONL log: see EVAL_LOG_PATH (default backend/logs/ragas_eval.jsonl)")


def _fmt(value) -> str:
    if value is None:
        return "n/a"
    return f"{value:.4f}"


if __name__ == "__main__":
    main()
