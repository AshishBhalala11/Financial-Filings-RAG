"""Lightweight query routing and multi-part decomposition."""

from __future__ import annotations

import logging
import re
from typing import Literal

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.config import get_settings
from app.services.llm import get_chat_model

logger = logging.getLogger(__name__)

RouteType = Literal["lookup", "multi_part", "summarization"]


class RouteResult(BaseModel):
    route_type: RouteType
    sub_queries: list[str] = Field(default_factory=list)


_ROUTE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "You classify questions about a single SEC 10-K / annual report.\n"
                "Return JSON only with keys:\n"
                '  route_type: one of "lookup", "multi_part", "summarization"\n'
                "  sub_queries: array of search queries (1 for lookup/summarization, "
                "2-4 for multi_part)\n\n"
                "Rules:\n"
                "- lookup: one factual ask (a number, a named risk, a single clause).\n"
                "- multi_part: two or more distinct asks joined by and/or/compare, "
                "or 'X and Y'.\n"
                "- summarization: overview, summarize, list the main points, "
                "or walk through.\n"
                "Rewrite each sub-query using 10-K language (net sales, Item 1A, "
                "MD&A, liquidity) when it helps retrieval. No markdown."
            ),
        ),
        ("human", "{question}"),
    ]
)


def _heuristic_route(question: str) -> RouteResult:
    normalized_question = question.lower()
    if any(
        keyword in normalized_question
        for keyword in (
            "summarize",
            "summary",
            "overview",
            "walk through",
            "key points",
        )
    ):
        return RouteResult(route_type="summarization", sub_queries=[question])
    is_multi_part = bool(
        re.search(
            r"\band\s+(?:what|how|why|which|who|where|when|does|did|is|are)\b"
            r"|\bcompare\b|\bversus\b|\bvs\.?\b",
            normalized_question,
        )
    )
    if is_multi_part:
        parts = re.split(
            r"\band\s+(?=(?:what|how|why|which|who|where|when|does|did|is|are)\b)"
            r"|\bcompare(?:d)?\s+to\b|\bversus\b|\bvs\.?\b",
            question,
            flags=re.I,
        )
        sub = [p.strip(" ?.,") for p in parts if len(p.strip(" ?.,")) > 8]
        if len(sub) >= 2:
            return RouteResult(route_type="multi_part", sub_queries=sub[:4])
    return RouteResult(route_type="lookup", sub_queries=[question])


def route_query(question: str) -> RouteResult:
    """Classify the question; fall back to heuristics if the LLM call fails."""
    settings = get_settings()
    if not settings.openrouter_api_key:
        return _heuristic_route(question)

    try:
        model = get_chat_model(temperature=0, max_tokens=400)
        structured_model = model.with_structured_output(
            RouteResult,
            method="json_mode",
        )
        result = (_ROUTE_PROMPT | structured_model).invoke({"question": question})
        if not result.sub_queries:
            result.sub_queries = [question]
        if result.route_type != "multi_part":
            result.sub_queries = result.sub_queries[:1] or [question]
        logger.info(
            "Routed as %s with %d sub-queries",
            result.route_type,
            len(result.sub_queries),
        )
        return result
    except Exception as exc:
        logger.warning("LLM routing failed (%s); using heuristic", exc)
        return _heuristic_route(question)
