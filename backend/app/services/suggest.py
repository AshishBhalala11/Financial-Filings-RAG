"""Generate analyst questions grounded in the indexed filing."""

from __future__ import annotations

import logging

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.config import get_settings
from app.services.llm import get_chat_model
from app.services.vector_store import sample_documents

logger = logging.getLogger(__name__)

FALLBACK_SUGGESTIONS = [
    "What were the company's total net sales in the most recent fiscal year?",
    "What are the key risk factors described in the filing?",
    "How did net income change compared to the prior fiscal year?",
    "Which business segments contributed the most to revenue?",
    "How much cash and cash equivalents did the company hold?",
]

DEFAULT_SAMPLE = 8


class SuggestionResult(BaseModel):
    questions: list[str] = Field(default_factory=list)


_SUGGEST_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "You are a financial filings analyst. Based ONLY on excerpts from "
                "a single 10-K annual report, propose {count} short, specific "
                "questions an analyst would ask about this filing.\n"
                "Rules:\n"
                "- Each question MUST be answerable from the filing these excerpts "
                "come from.\n"
                "- Prefer named sections (Item 1A, MD&A, Item 7) and the figures "
                "actually present in the excerpts.\n"
                "- Cover different topics; avoid near-duplicate questions.\n"
                'Return JSON only with a key "questions": array of strings. '
                "No markdown, no numbering."
            ),
        ),
        ("human", "Excerpts:\n{context}\n\nPropose {count} questions:"),
    ]
)


def _fallback(count: int) -> list[str]:
    return FALLBACK_SUGGESTIONS[:count]


def suggest_questions(document_id: str | None, count: int = 5) -> list[str]:
    """Return analyst questions grounded in the indexed filing.

    Falls back to generic 10-K questions when there is no index, no API key,
    or the LLM call fails.
    """
    try:
        documents = sample_documents(n=DEFAULT_SAMPLE)
    except FileNotFoundError as exc:
        logger.warning("No filing indexed; using generic suggestions (%s)", exc)
        return _fallback(count)

    if not documents:
        return _fallback(count)

    settings = get_settings()
    if not settings.openrouter_api_key:
        return _fallback(count)

    context = "\n\n---\n\n".join(
        f"[p. {document.metadata.get('page', '?')} | "
        f"{document.metadata.get('section', 'Unknown')}]\n" + document.page_content
        for document in documents[0:DEFAULT_SAMPLE]
    )

    try:
        model = get_chat_model(temperature=0.2, max_tokens=500)
        structured_model = model.with_structured_output(
            SuggestionResult,
            method="json_mode",
        )
        result = (_SUGGEST_PROMPT | structured_model).invoke(
            {"context": context, "count": count}
        )
        questions = [q.strip() for q in result.questions if q and q.strip()]
        if not questions:
            return _fallback(count)
        return questions[0:count]
    except Exception as exc:
        logger.warning("Question suggestion failed (%s); using generic fallback", exc)
        return _fallback(count)
