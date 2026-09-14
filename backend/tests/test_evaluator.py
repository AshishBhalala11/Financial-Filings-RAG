import json
from types import SimpleNamespace

from app.services import evaluator


def test_missing_api_key_logs_null_metrics(monkeypatch, tmp_path):
    log_path = tmp_path / "ragas.jsonl"
    monkeypatch.setattr(
        evaluator,
        "get_settings",
        lambda: SimpleNamespace(
            openrouter_api_key="",
            eval_log_path=str(log_path),
        ),
    )

    metrics = evaluator.evaluate_rag(
        question="What was revenue?",
        answer="Revenue was $1 million.",
        contexts=["Revenue was $1 million."],
    )

    assert metrics == {
        "faithfulness": None,
        "answer_relevancy": None,
        "context_precision": None,
    }
    record = json.loads(log_path.read_text(encoding="utf-8"))
    assert record["context_precision_variant"] == "without_reference"
    assert record["metrics"] == metrics
