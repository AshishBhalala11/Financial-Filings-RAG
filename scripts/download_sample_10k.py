"""Download Apple's FY2024 10-K from SEC EDGAR as a paginated PDF."""

from __future__ import annotations

import argparse
import html
import os
import re
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from fpdf import FPDF

DEFAULT_FILING_URL = (
    "https://www.sec.gov/Archives/edgar/data/320193/"
    "000032019324000123/aapl-20240928.htm"
)
DEFAULT_OUTPUT_PATH = (
    Path(__file__).resolve().parent.parent
    / "sample_docs"
    / "aapl-10k-sample.pdf"
)
SEC_USER_AGENT = os.getenv(
    "SEC_USER_AGENT",
    "FinancialFilingsAnalyst/1.0 (educational project; student@example.com)",
)


def download_filing_html(url: str) -> str:
    headers = {
        "User-Agent": SEC_USER_AGENT,
        "Accept-Encoding": "gzip, deflate",
    }
    with httpx.Client(
        headers=headers,
        timeout=60.0,
        follow_redirects=True,
    ) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.text


def extract_filing_text(raw_html: str) -> str:
    soup = BeautifulSoup(raw_html, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = html.unescape(soup.get_text("\n"))
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def write_paginated_pdf(text: str, output_path: Path) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf = FPDF(format="letter")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_margins(18, 18, 18)
    pdf.add_page()
    pdf.set_font("Helvetica", size=9)

    latin_text = text.encode("latin-1", errors="replace").decode("latin-1")
    for paragraph in latin_text.splitlines():
        pdf.set_x(pdf.l_margin)
        if paragraph.strip():
            pdf.multi_cell(0, 5, paragraph)
        else:
            pdf.ln(3)

    page_count = pdf.page_no()
    pdf.output(str(output_path))
    return page_count


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download a public SEC 10-K and convert it to PDF."
    )
    parser.add_argument("--url", default=DEFAULT_FILING_URL)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT_PATH)
    args = parser.parse_args()

    print(f"Fetching {args.url}", flush=True)
    filing_text = extract_filing_text(download_filing_html(args.url))
    if len(filing_text) < 5_000:
        raise RuntimeError("SEC response did not contain a complete filing.")

    page_count = write_paginated_pdf(filing_text, args.out)
    print(f"Wrote {page_count} pages to {args.out}")


if __name__ == "__main__":
    main()
