"""POST /api/evaluate — run RAGAS on a provided triple."""

from __future__ import annotations

from fastapi import APIRouter
from starlette.concurrency import run_in_threadpool

from app.models import EvalMetrics, EvalRequest, EvalResponse
from app.services.evaluator import evaluate_rag

router = APIRouter()


@router.post("/evaluate", response_model=EvalResponse)
async def evaluate(payload: EvalRequest) -> EvalResponse:
    metrics = await run_in_threadpool(
        evaluate_rag,
        payload.question,
        payload.answer,
        payload.contexts,
        payload.ground_truth,
    )
    return EvalResponse(
        metrics=EvalMetrics(**metrics),
        logged=True,
        evaluated=any(value is not None for value in metrics.values()),
    )
