"""POST /api/upload — ingest a 10-K PDF into FAISS."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from starlette.concurrency import run_in_threadpool

from app.models import UploadResponse
from app.services.ingestion import ingest_pdf
from app.services.vector_store import replace_documents

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_BYTES = 50 * 1024 * 1024


@router.post("/upload", response_model=UploadResponse)
async def upload_pdf(file: Annotated[UploadFile, File()]) -> UploadResponse:
    filename = Path(file.filename or "").name
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please upload a PDF file.",
        )
    data = await file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="PDF exceeds 50 MB.",
        )
    if not data:
        raise HTTPException(status_code=400, detail="Empty file.")
    if not data.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is not a valid PDF.",
        )

    try:
        result = await run_in_threadpool(ingest_pdf, data, filename)
        if result.chunk_count == 0:
            raise HTTPException(
                status_code=400,
                detail="No extractable text. Try a text-based (not scanned) 10-K PDF.",
            )
        await run_in_threadpool(replace_documents, result.documents)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Upload failed")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {exc}") from exc

    return UploadResponse(
        message="Filing indexed.",
        document_id=result.document_id,
        filename=result.filename,
        page_count=result.page_count,
        chunk_count=result.chunk_count,
    )
