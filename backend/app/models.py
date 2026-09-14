"""Pydantic request / response models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class UploadResponse(BaseModel):
    message: str
    document_id: str
    filename: str
    page_count: int
    chunk_count: int


class QueryRequest(StrictRequest):
    question: str = Field(..., min_length=3, max_length=4000)
    document_id: str | None = None
    evaluate: bool = Field(
        default=True,
        description="If true, run RAGAS in the background after answering.",
    )

    @field_validator("question")
    @classmethod
    def normalize_question(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 3:
            raise ValueError("Question must contain at least 3 non-space characters.")
        return normalized


class SourceChunk(BaseModel):
    chunk_id: str
    content: str
    page: int | None = None
    section: str | None = None
    source: str | None = None
    retrieval_score: float | None = None
    rerank_score: float | None = None


class RankedChunk(BaseModel):
    chunk_id: str
    page: int | None = None
    section: str | None = None
    snippet: str
    score_type: Literal["retrieval", "rerank"]
    score: float | None = Field(
        default=None,
        description="Higher values indicate greater relevance.",
    )


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]
    route_type: Literal["lookup", "multi_part", "summarization"]
    sub_queries: list[str]
    document_id: str | None = None
    pre_rerank: list[RankedChunk]
    post_rerank: list[RankedChunk]


class EvalRequest(StrictRequest):
    question: str = Field(min_length=3, max_length=4000)
    answer: str = Field(min_length=1, max_length=20_000)
    contexts: list[str] = Field(min_length=1)
    ground_truth: str | None = None


class EvalMetrics(BaseModel):
    faithfulness: float | None = None
    answer_relevancy: float | None = None
    context_precision: float | None = None


class EvalResponse(BaseModel):
    metrics: EvalMetrics
    logged: bool
    evaluated: bool
