"""Show FAISS order vs cross-encoder order for a query that typically reshuffles.

Usage (from backend/, after a 10-K is indexed):

    python -m eval.rerank_demo
    python -m eval.rerank_demo --question "What risks does Apple disclose about China?"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import get_settings  # noqa: E402
from app.services.reranker import rerank  # noqa: E402
from app.services.vector_store import query_index  # noqa: E402

DEFAULT_QUESTION = (
    "What does the filing disclose about manufacturing concentration "
    "and supply chain dependence on outsourcing partners in Asia?"
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--question", default=DEFAULT_QUESTION)
    parser.add_argument("--document-id")
    args = parser.parse_args()
    settings = get_settings()

    pairs = query_index(
        args.question,
        k=settings.retrieval_top_k,
        document_id=args.document_id,
    )
    docs = []
    print("BEFORE re-ranking (FAISS similarity)")
    print(f"{'rank':<6}{'page':<8}{'section':<12}{'faiss':<10}chunk")
    for i, (doc, score) in enumerate(pairs, start=1):
        doc.metadata["retrieval_score"] = round(float(score), 4)
        docs.append(doc)
        print(
            f"{i:<6}{str(doc.metadata.get('page')):<8}"
            f"{str(doc.metadata.get('section')):<12}"
            f"{score:<10.4f}{doc.metadata.get('chunk_id')}"
        )

    ranked = rerank(args.question, docs, log=True)
    print("\nAFTER re-ranking (cross-encoder)")
    print(f"{'rank':<6}{'page':<8}{'section':<12}{'rerank':<10}chunk")
    for i, doc in enumerate(ranked, start=1):
        print(
            f"{i:<6}{str(doc.metadata.get('page')):<8}"
            f"{str(doc.metadata.get('section')):<12}"
            f"{doc.metadata.get('rerank_score'):<10}"
            f"{doc.metadata.get('chunk_id')}"
        )

    pre_id = docs[0].metadata.get("chunk_id") if docs else None
    post_id = ranked[0].metadata.get("chunk_id") if ranked else None
    print("\nTop-1 changed:", pre_id != post_id)
    print(f"  FAISS top-1:     {pre_id}")
    print(f"  Reranker top-1:  {post_id}")
    print("Full JSONL row appended to", settings.rerank_log_path)


if __name__ == "__main__":
    main()
