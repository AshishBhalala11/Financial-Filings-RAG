"""Verify retrieval from the CLI before wiring the UI.

Usage (from backend/ with venv active):

    python -m scripts.query_cli "What was total net sales?"
    python -m scripts.query_cli --k 5 --repeat "Item 1A supply chain"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.vector_store import query_index  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Query the persisted FAISS index")
    parser.add_argument("question")
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument(
        "--repeat",
        action="store_true",
        help="Run the same query twice and print whether top-k matched",
    )
    parser.add_argument("--document-id")
    args = parser.parse_args()

    def run() -> list[tuple[str, int | None, float]]:
        pairs = query_index(args.question, k=args.k, document_id=args.document_id)
        rows = []
        for doc, score in pairs:
            rows.append(
                (
                    str(doc.metadata.get("chunk_id")),
                    doc.metadata.get("page"),
                    float(score),
                )
            )
            print(
                f"  page={doc.metadata.get('page')} "
                f"section={doc.metadata.get('section')} "
                f"score={score:.4f} id={doc.metadata.get('chunk_id')}"
            )
            print(f"    {doc.page_content[:180].replace(chr(10), ' ')}…\n")
        return rows

    print(f"Query 1: {args.question}")
    first = run()
    if args.repeat:
        print("Query 2 (identical):")
        second = run()
        print("Top-k identical:", first == second)


if __name__ == "__main__":
    main()
