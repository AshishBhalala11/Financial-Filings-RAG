"""Cross-encoder re-ranking of FAISS candidates."""

from __future__ import annotations

import json
import logging
import threading
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path

from langchain_core.documents import Document

from app.config import get_settings

logger = logging.getLogger(__name__)
_log_lock = threading.Lock()


@lru_cache(maxsize=1)
def _get_cross_encoder():
    from sentence_transformers import CrossEncoder

    settings = get_settings()
    logger.info("Loading CrossEncoder: %s", settings.reranker_model)
    return CrossEncoder(settings.reranker_model)


def _log_rerank(question: str, pre: list[Document], post: list[Document]) -> None:
    settings = get_settings()
    path = Path(settings.rerank_log_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    def rows(docs: list[Document]) -> list[dict]:
        out = []
        for i, doc in enumerate(docs, start=1):
            out.append(
                {
                    "rank": i,
                    "chunk_id": doc.metadata.get("chunk_id"),
                    "page": doc.metadata.get("page"),
                    "section": doc.metadata.get("section"),
                    "retrieval_score": doc.metadata.get("retrieval_score"),
                    "rerank_score": doc.metadata.get("rerank_score"),
                    "snippet": doc.page_content[:160],
                }
            )
        return out

    record = {
        "timestamp": datetime.now(UTC).isoformat(),
        "question": question[:300],
        "pre_rerank": rows(pre),
        "post_rerank": rows(post),
        "top1_changed": (
            pre[0].metadata.get("chunk_id") != post[0].metadata.get("chunk_id")
            if pre and post
            else False
        ),
    }
    with _log_lock, path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")
    logger.info(
        "Rerank logged (top1_changed=%s) → %s",
        record["top1_changed"],
        path,
    )


def rerank(
    query: str,
    documents: list[Document],
    *,
    sub_queries: list[str] | None = None,
    log: bool = True,
) -> list[Document]:
    settings = get_settings()
    if not documents:
        return []

    pre = list(documents)
    encoder = _get_cross_encoder()
    ranking_queries = sub_queries or [query]
    pairs = [
        (ranking_query, doc.page_content)
        for ranking_query in ranking_queries
        for doc in documents
    ]
    scores = encoder.predict(pairs)
    score_list = scores.tolist() if hasattr(scores, "tolist") else list(scores)

    score_rows = [
        score_list[start : start + len(documents)]
        for start in range(0, len(score_list), len(documents))
    ]
    for document_index, document in enumerate(documents):
        best_query_index = max(
            range(len(ranking_queries)),
            key=lambda query_index: score_rows[query_index][document_index],
        )
        document.metadata["rerank_score"] = round(
            float(score_rows[best_query_index][document_index]),
            4,
        )
        document.metadata["matched_query"] = ranking_queries[best_query_index]

    ranked_by_best_score = sorted(
        documents,
        key=lambda d: d.metadata.get("rerank_score", 0.0),
        reverse=True,
    )

    # Preserve evidence for every part before filling remaining slots globally.
    selected: list[Document] = []
    selected_ids: set[str] = set()
    if len(ranking_queries) > 1:
        for query_index in range(len(ranking_queries)):
            best_for_query = max(
                range(len(documents)),
                key=lambda document_index: score_rows[query_index][document_index],
            )
            document = documents[best_for_query]
            chunk_id = str(document.metadata.get("chunk_id"))
            if chunk_id not in selected_ids:
                selected.append(document)
                selected_ids.add(chunk_id)

    for document in ranked_by_best_score:
        if len(selected) >= settings.reranker_top_k:
            break
        chunk_id = str(document.metadata.get("chunk_id"))
        if chunk_id not in selected_ids:
            selected.append(document)
            selected_ids.add(chunk_id)

    top_k = selected[: settings.reranker_top_k]
    if log:
        _log_rerank(query, pre, top_k)
    return top_k
