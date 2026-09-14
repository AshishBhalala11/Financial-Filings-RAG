"""Runtime settings from environment variables. Never hard-code secrets."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    openrouter_api_key: str = ""
    chat_model: str = "google/gemini-2.5-flash"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    reranker_top_k: int = Field(default=5, ge=4, le=20)
    retrieval_top_k: int = Field(default=12, ge=1, le=100)

    chunk_size: int = Field(default=2400, ge=200, le=10_000)
    chunk_overlap: int = Field(default=300, ge=0, le=2_000)

    faiss_index_path: str = "./data/faiss_index"
    eval_log_path: str = "./logs/ragas_eval.jsonl"
    rerank_log_path: str = "./logs/rerank.jsonl"

    allowed_origins: str = "http://localhost:3000"
    log_level: str = "INFO"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @model_validator(mode="after")
    def validate_pipeline_sizes(self) -> Settings:
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE.")
        if self.reranker_top_k > self.retrieval_top_k:
            raise ValueError("RERANKER_TOP_K cannot exceed RETRIEVAL_TOP_K.")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
