"""FastAPI entry: Financial Filings Analyst."""

from __future__ import annotations

import logging
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.routes import evaluate, query, upload

logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

settings = get_settings()
logging.getLogger().setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

app = FastAPI(
    title="Financial Filings Analyst",
    description=(
        "Phase 1 single-source RAG over 10-K / annual-report PDFs. "
        "Local MiniLM embeddings, FAISS, LCEL generation, cross-encoder "
        "re-ranking, query routing, and RAGAS logs."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router, prefix="/api", tags=["Documents"])
app.include_router(query.router, prefix="/api", tags=["RAG"])
app.include_router(evaluate.router, prefix="/api", tags=["Evaluation"])


@app.get("/health", tags=["System"])
async def health_check() -> JSONResponse:
    return JSONResponse({"status": "ok", "service": "financial-filings-analyst"})


@app.get("/", tags=["System"])
async def root() -> JSONResponse:
    return JSONResponse(
        {
            "message": "Financial Filings Analyst API",
            "docs": "/docs",
            "health": "/health",
        }
    )
