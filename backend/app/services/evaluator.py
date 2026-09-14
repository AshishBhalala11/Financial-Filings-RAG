"""RAGAS metrics + JSONL logging."""

from __future__ import annotations

import json
import logging
import threading
from datetime import UTC, datetime
from pathlib import Path

from app.config import get_settings
from app.services.embeddings import get_embeddings
from app.services.llm import get_chat_model

logger = logging.getLogger(__name__)
_log_lock = threading.Lock()
_evaluation_lock = threading.Lock()


def _safe_float(value) -> float | None:
    try:
        number = float(value)
        if number != number:  # NaN
            return None
        return round(number, 4)
    except (TypeError, ValueError):
        return None


def _append_jsonl(
    question: str,
    answer: str,
    metrics: dict,
    context_precision_variant: str,
) -> None:
    path = Path(get_settings().eval_log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.now(UTC).isoformat(),
        "question": question[:200],
        "answer_preview": answer[:200],
        "metrics": metrics,
        "context_precision_variant": context_precision_variant,
    }
    with _log_lock, path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")
    logger.info("ragas_eval %s", record)


def _evaluate_rag(
    question: str,
    answer: str,
    contexts: list[str],
    ground_truth: str | None = None,
) -> dict:
    context_precision_variant = (
        "with_reference" if ground_truth else "without_reference"
    )
    metrics = {
        "faithfulness": None,
        "answer_relevancy": None,
        "context_precision": None,
    }
    settings = get_settings()
    if not settings.openrouter_api_key:
        logger.warning("Skipping RAGAS evaluation: OPENROUTER_API_KEY is not set.")
        _append_jsonl(
            question,
            answer,
            metrics,
            context_precision_variant,
        )
        return metrics

    try:
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import (
            LLMContextPrecisionWithoutReference,
            answer_relevancy,
            context_precision,
            faithfulness,
        )

        data = {
            "question": [question],
            "answer": [answer],
            "contexts": [contexts],
        }
        if ground_truth:
            data["ground_truth"] = [ground_truth]

        dataset = Dataset.from_dict(data)
        context_precision_metric = (
            context_precision if ground_truth else LLMContextPrecisionWithoutReference()
        )
        result = evaluate(
            dataset,
            metrics=[faithfulness, answer_relevancy, context_precision_metric],
            llm=get_chat_model(temperature=0, max_tokens=2048),
            embeddings=get_embeddings(),
            raise_exceptions=False,
        )
        row = result.to_pandas().iloc[0].to_dict()
        precision_score = row.get("context_precision")
        if precision_score is None:
            precision_score = row.get("llm_context_precision_without_reference")
        metrics = {
            "faithfulness": _safe_float(row.get("faithfulness")),
            "answer_relevancy": _safe_float(row.get("answer_relevancy")),
            "context_precision": _safe_float(precision_score),
        }
    except Exception as exc:
        logger.warning("RAGAS evaluation failed: %s", exc)

    _append_jsonl(
        question,
        answer,
        metrics,
        context_precision_variant,
    )
    return metrics


def evaluate_rag(
    question: str,
    answer: str,
    contexts: list[str],
    ground_truth: str | None = None,
) -> dict:
    """Serialize expensive RAGAS runs while allowing API responses to proceed."""
    with _evaluation_lock:
        return _evaluate_rag(question, answer, contexts, ground_truth)
