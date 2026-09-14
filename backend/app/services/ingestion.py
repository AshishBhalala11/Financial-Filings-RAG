"""PDF ingestion: page-preserving extraction, 10-K item tagging, recursive chunking."""

from __future__ import annotations

import io
import logging
import re
import uuid
from dataclasses import dataclass

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import get_settings

logger = logging.getLogger(__name__)

_ITEM_HEADING = re.compile(
    r"^\s*item\s+"
    r"(1a|1b|1c|7a|[1-9]|1[0-6])"
    r"\s*[.:\-]",
    re.IGNORECASE | re.MULTILINE,
)


@dataclass(frozen=True)
class IngestionResult:
    document_id: str
    filename: str
    page_count: int
    documents: list[Document]

    @property
    def chunk_count(self) -> int:
        return len(self.documents)


def tag_section(text: str, current: str = "Unknown") -> str:
    """Return the last 10-K heading in reading order, else keep `current`."""
    latest_match: tuple[int, str] | None = None
    for match in _ITEM_HEADING.finditer(text):
        item_number = match.group(1).upper()
        if latest_match is None or match.start() > latest_match[0]:
            latest_match = (match.start(), f"Item {item_number}")
    return latest_match[1] if latest_match else current


def extract_pages(pdf_bytes: bytes) -> list[tuple[int, str]]:
    """Extract 1-based pages, filling pdfplumber gaps with pypdf output."""
    try:
        primary_pages = _extract_pdfplumber(pdf_bytes)
    except Exception as exc:
        logger.warning("pdfplumber extraction failed: %s", exc)
        primary_pages = []

    missing_page_numbers = {
        page_number for page_number, text in primary_pages if not text.strip()
    }
    if not primary_pages or missing_page_numbers:
        try:
            fallback_pages = dict(_extract_pypdf(pdf_bytes))
        except Exception as exc:
            logger.warning("pypdf extraction failed: %s", exc)
            fallback_pages = {}
        if not primary_pages:
            return sorted(fallback_pages.items())
        return [
            (
                page_number,
                text if text.strip() else fallback_pages.get(page_number, ""),
            )
            for page_number, text in primary_pages
        ]
    return primary_pages


def _extract_pdfplumber(pdf_bytes: bytes) -> list[tuple[int, str]]:
    import pdfplumber

    out: list[tuple[int, str]] = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for idx, page in enumerate(pdf.pages, start=1):
            text = (page.extract_text() or "").strip()
            out.append((idx, text))
    return out


def _extract_pypdf(pdf_bytes: bytes) -> list[tuple[int, str]]:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(pdf_bytes))
    out: list[tuple[int, str]] = []
    for idx, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        out.append((idx, text.strip()))
    return out


def chunk_pages(
    pages: list[tuple[int, str]],
    *,
    source: str,
    document_id: str,
) -> list[Document]:
    settings = get_settings()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    documents: list[Document] = []
    current_section = "Unknown"
    chunk_index = 0

    for page_num, text in pages:
        if not text.strip():
            continue
        pieces = splitter.split_text(text)
        for piece in pieces:
            piece = piece.strip()
            if not piece:
                continue
            current_section = tag_section(piece, current_section)
            documents.append(
                Document(
                    page_content=piece,
                    metadata={
                        "document_id": document_id,
                        "source": source,
                        "page": page_num,
                        "chunk_index": chunk_index,
                        "chunk_id": f"{document_id}:{chunk_index}",
                        "section": current_section,
                    },
                )
            )
            chunk_index += 1

    logger.info(
        "Chunked %s into %d chunks across %d pages (document_id=%s)",
        source,
        len(documents),
        len(pages),
        document_id,
    )
    return documents


def ingest_pdf(pdf_bytes: bytes, filename: str) -> IngestionResult:
    """Full ingest path used by upload: extract → chunk. Indexing is separate."""
    document_id = str(uuid.uuid4())
    pages = extract_pages(pdf_bytes)
    documents = chunk_pages(pages, source=filename, document_id=document_id)
    return IngestionResult(
        document_id=document_id,
        filename=filename,
        page_count=len(pages),
        documents=documents,
    )
