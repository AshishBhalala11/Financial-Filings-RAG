"""POST /api/query — routed RAG with citations."""

from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from openai import AuthenticationError
from starlette.concurrency import run_in_threadpool

from app.models import QueryRequest, QueryResponse, RankedChunk, SourceChunk
from app.services.evaluator import evaluate_rag
from app.services.rag_chain import run_rag

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/query", response_model=QueryResponse)
async def query_filing(
    payload: QueryRequest,
    background_tasks: BackgroundTasks,
) -> QueryResponse:
    try:
        result = await run_in_threadpool(
            run_rag,
            payload.question,
            payload.document_id,
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "OpenRouter authentication failed. Set a valid OPENROUTER_API_KEY "
                "(sk-or-v1-...) in backend/.env. See https://openrouter.ai/keys"
            ),
        ) from exc
    except Exception as exc:
        logger.exception("Query failed")
        raise HTTPException(
            status_code=500,
            detail="The query pipeline failed. Check the backend logs.",
        ) from exc

    if payload.evaluate:
        background_tasks.add_task(
            evaluate_rag,
            payload.question,
            result["answer"],
            result["contexts"],
            None,
        )

    return QueryResponse(
        answer=result["answer"],
        sources=[SourceChunk(**s) for s in result["sources"]],
        route_type=result["route_type"],
        sub_queries=result["sub_queries"],
        document_id=payload.document_id,
        pre_rerank=[RankedChunk(**r) for r in result["pre_rerank"]],
        post_rerank=[RankedChunk(**r) for r in result["post_rerank"]],
    )
