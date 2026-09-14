from pathlib import Path

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from app.services import vector_store


class KeywordEmbeddings(Embeddings):
    """Small deterministic embedding model for FAISS unit tests."""

    @staticmethod
    def _embed(text: str) -> list[float]:
        lowered = text.lower()
        vector = [
            float("revenue" in lowered),
            float("risk" in lowered),
            float("liquidity" in lowered),
        ]
        return vector if any(vector) else [0.01, 0.01, 0.01]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


def configure_test_store(monkeypatch, tmp_path: Path) -> None:
    vector_store.reset_store_cache()
    monkeypatch.setattr(
        vector_store,
        "index_path",
        lambda: tmp_path / "faiss_index",
    )
    monkeypatch.setattr(vector_store, "get_embeddings", KeywordEmbeddings)


def make_document(
    chunk_id: str,
    content: str,
    document_id: str,
) -> Document:
    return Document(
        page_content=content,
        metadata={
            "chunk_id": chunk_id,
            "document_id": document_id,
            "page": 1,
        },
    )


def test_inner_product_retrieval_and_persistence(monkeypatch, tmp_path):
    configure_test_store(monkeypatch, tmp_path)
    vector_store.replace_documents(
        [
            make_document("revenue", "Annual revenue increased.", "filing-1"),
            make_document("risk", "Supply chain risk increased.", "filing-1"),
        ]
    )

    first_results = vector_store.query_index("revenue", k=2)
    vector_store.reset_store_cache()
    reloaded_results = vector_store.query_index("revenue", k=2)

    assert first_results[0][0].metadata["chunk_id"] == "revenue"
    assert first_results[0][1] > first_results[1][1]
    assert [doc.metadata["chunk_id"] for doc, _ in first_results] == [
        doc.metadata["chunk_id"] for doc, _ in reloaded_results
    ]


def test_replacing_index_removes_previous_filing(monkeypatch, tmp_path):
    configure_test_store(monkeypatch, tmp_path)
    vector_store.replace_documents(
        [make_document("old", "Revenue from old filing.", "filing-1")]
    )
    vector_store.replace_documents(
        [make_document("new", "Liquidity in new filing.", "filing-2")]
    )

    results = vector_store.query_index("revenue", k=5)

    assert [doc.metadata["chunk_id"] for doc, _ in results] == ["new"]
    assert vector_store.query_index("revenue", k=5, document_id="filing-1") == []


def test_query_results_do_not_mutate_cached_docstore(monkeypatch, tmp_path):
    configure_test_store(monkeypatch, tmp_path)
    vector_store.replace_documents(
        [make_document("revenue", "Annual revenue increased.", "filing-1")]
    )

    first_document = vector_store.query_index("revenue", k=1)[0][0]
    first_document.metadata["rerank_score"] = 0.99
    second_document = vector_store.query_index("revenue", k=1)[0][0]

    assert "rerank_score" not in second_document.metadata
