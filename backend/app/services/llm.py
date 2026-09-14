"""Shared OpenRouter-backed chat model factory."""

from functools import lru_cache

from langchain_openai import ChatOpenAI

from app.config import get_settings


def _validate_openrouter_key(api_key: str) -> None:
    if not api_key.startswith("sk-or-"):
        raise RuntimeError(
            "OPENROUTER_API_KEY must be an OpenRouter key (starts with sk-or-v1-). "
            "Create one at https://openrouter.ai/keys and set it in backend/.env."
        )


@lru_cache(maxsize=8)
def get_chat_model(*, temperature: float, max_tokens: int) -> ChatOpenAI:
    settings = get_settings()
    if not settings.openrouter_api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not set. Copy backend/.env.example to "
            "backend/.env and add your key."
        )
    _validate_openrouter_key(settings.openrouter_api_key)
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
