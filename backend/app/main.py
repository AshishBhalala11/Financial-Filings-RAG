"""FastAPI entry: Financial Filings Analyst."""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from app.config import get_settings
from app.routes import evaluate, query, upload
from app.services.embeddings import get_embeddings

logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

settings = get_settings()
logging.getLogger().setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Load the embedding model at startup so first upload is not blocked on download."""
    logger.info("Warming embedding model: %s", settings.embedding_model)
    await run_in_threadpool(lambda: get_embeddings().embed_query("warmup"))
    logger.info("Embedding model ready.")
    yield


app = FastAPI(
    lifespan=lifespan,
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
@app.get("/api/health", tags=["System"], include_in_schema=False)
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
