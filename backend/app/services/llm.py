"""Shared OpenRouter-backed chat model factory."""

from functools import lru_cache

from langchain_openai import ChatOpenAI

from app.config import get_settings


@lru_cache(maxsize=8)
def get_chat_model(*, temperature: float, max_tokens: int) -> ChatOpenAI:
    settings = get_settings()
    if not settings.openrouter_api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not set. Copy backend/.env.example to "
            "backend/.env and add your key."
        )
    return ChatOpenAI(
        model=settings.chat_model,
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
        temperature=temperature,
        max_tokens=max_tokens,
        default_headers={
            "HTTP-Referer": "http://localhost:3000",
            "X-Title": "10-K Filings Analyst",
        },
    )
