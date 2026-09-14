"""FAISS index persistence and query_index(question, k)."""

from __future__ import annotations

import logging
import shutil
import threading
import uuid
from copy import deepcopy
from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_community.vectorstores.utils import DistanceStrategy
from langchain_core.documents import Document

from app.config import get_settings
from app.services.embeddings import get_embeddings

logger = logging.getLogger(__name__)

_store: FAISS | None = None
_store_lock = threading.RLock()


def index_path() -> Path:
    return Path(get_settings().faiss_index_path)


def save_vector_store(store: FAISS) -> None:
    """Persist the index with an atomic directory swap."""
    path = index_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(f".{path.name}-{uuid.uuid4().hex}.tmp")
    backup_path = path.with_name(f".{path.name}.backup")

    store.save_local(str(temporary_path))
    if backup_path.exists():
        shutil.rmtree(backup_path)
    try:
        if path.exists():
            path.rename(backup_path)
        temporary_path.rename(path)
    except Exception:
        if not path.exists() and backup_path.exists():
            backup_path.rename(path)
        if temporary_path.exists():
            shutil.rmtree(temporary_path)
        raise
    else:
        if backup_path.exists():
            shutil.rmtree(backup_path)
    logger.info("FAISS index saved to %s", path)


def load_vector_store() -> FAISS:
    global _store
    with _store_lock:
        if _store is not None:
            return _store
        path = index_path()
        required_files = (path / "index.faiss", path / "index.pkl")
        if not all(file.exists() for file in required_files):
            raise FileNotFoundError(
                f"No complete FAISS index at {path}. Upload a 10-K PDF first."
            )
        # Safe here because only this application writes the local index.
        _store = FAISS.load_local(
            str(path),
            get_embeddings(),
            allow_dangerous_deserialization=True,
        )
        return _store


def reset_store_cache() -> None:
    global _store
    with _store_lock:
        _store = None


def replace_documents(documents: list[Document]) -> int:
    """Replace the single-source index with the supplied document chunks."""
    global _store
    if not documents:
        raise ValueError("Cannot create a FAISS index without document chunks.")

    with _store_lock:
        store = FAISS.from_documents(
            documents,
            get_embeddings(),
            distance_strategy=DistanceStrategy.MAX_INNER_PRODUCT,
        )
        save_vector_store(store)
        _store = store
    return len(documents)


def query_index(
    question: str,
    k: int | None = None,
    document_id: str | None = None,
) -> list[tuple[Document, float]]:
    """
    Return top-k (document, similarity) pairs.
    Identical questions yield identical ranking (IndexFlatIP + normalized vectors).
    """
    settings = get_settings()
    k = k or settings.retrieval_top_k
    if k < 1:
        raise ValueError("k must be at least 1.")

    with _store_lock:
        store = load_vector_store()
        if document_id:
            results = store.similarity_search_with_score(
                question,
                k=k,
                filter={"document_id": document_id},
                fetch_k=max(k * 4, 40),
            )
        else:
            results = store.similarity_search_with_score(question, k=k)

        # FAISS returns references owned by its docstore. Scoring stages mutate
        # metadata, so return detached copies to prevent cross-query leakage.
        return [
            (
                Document(
                    page_content=document.page_content,
                    metadata=deepcopy(document.metadata),
                ),
                score,
            )
            for document, score in results
        ]
