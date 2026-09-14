"""POST /api/suggest — generate analyst questions grounded in the filing."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status
from starlette.concurrency import run_in_threadpool

from app.models import SuggestRequest, SuggestResponse
from app.services.suggest import suggest_questions

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/suggest", response_model=SuggestResponse)
async def suggest(payload: SuggestRequest) -> SuggestResponse:
    try:
        questions = await run_in_threadpool(suggest_questions, payload.document_id)
    except Exception as exc:
        logger.exception("Suggestion failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Suggestion failed.",
        ) from exc
    return SuggestResponse(questions=questions)
