from types import SimpleNamespace

from langchain_core.documents import Document

from app.services import reranker


class FakeCrossEncoder:
    def predict(self, pairs):
        scores = {
            ("sales", "sales evidence"): 0.9,
            ("sales", "risk evidence"): 0.1,
            ("risk", "sales evidence"): 0.2,
            ("risk", "risk evidence"): 0.8,
        }
        return [scores[pair] for pair in pairs]


def test_multi_part_reranking_preserves_each_sub_query(monkeypatch):
    monkeypatch.setattr(reranker, "_get_cross_encoder", FakeCrossEncoder)
    monkeypatch.setattr(
        reranker,
        "get_settings",
        lambda: SimpleNamespace(reranker_top_k=2),
    )
    documents = [
        Document(page_content="sales evidence", metadata={"chunk_id": "sales"}),
        Document(page_content="risk evidence", metadata={"chunk_id": "risk"}),
    ]

    ranked = reranker.rerank(
        "sales and risk",
        documents,
        sub_queries=["sales", "risk"],
        log=False,
    )

    assert [document.metadata["chunk_id"] for document in ranked] == [
        "sales",
        "risk",
    ]
