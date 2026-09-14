from fastapi.testclient import TestClient

from app.main import app
from app.services.ingestion import chunk_pages, tag_section
from app.services.router import _heuristic_route

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "financial-filings-analyst"


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "docs" in response.json()


def test_item_tagging_prefers_1a_over_item_1():
    text = "ITEM 1A. RISK FACTORS  The Company faces risks including..."
    assert tag_section(text) == "Item 1A"


def test_item_7_mda():
    text = "Item 7. Management's Discussion and Analysis of Financial Condition"
    assert tag_section(text) == "Item 7"


def test_heuristic_multi_part():
    result = _heuristic_route(
        "What were total net sales and what does Item 1A say about supply-chain risk?"
    )
    assert result.route_type == "multi_part"
    assert len(result.sub_queries) >= 2


def test_heuristic_summarization():
    result = _heuristic_route("Summarize Apple's business as described in the filing")
    assert result.route_type == "summarization"


def test_heuristic_does_not_split_a_compound_noun():
    result = _heuristic_route("What were Research and Development expenses?")
    assert result.route_type == "lookup"


def test_upload_rejects_non_pdf():
    response = client.post(
        "/api/upload",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 400


def test_upload_rejects_fake_pdf():
    response = client.post(
        "/api/upload",
        files={"file": ("fake.pdf", b"not a pdf", "application/pdf")},
    )
    assert response.status_code == 400


def test_chunk_pages_keep_page_and_section():
    pages = [
        (1, "Item 1. Business\nApple designs, manufactures and markets smartphones."),
        (
            2,
            "Item 1A. Risk Factors\n"
            "The Company relies on outsourcing partners in Asia.",
        ),
    ]
    docs = chunk_pages(pages, source="aapl.pdf", document_id="doc-1")
    assert docs
    assert docs[0].metadata["page"] == 1
    assert docs[0].metadata["section"] == "Item 1"
    assert any(
        document.metadata["page"] == 2 and document.metadata["section"] == "Item 1A"
        for document in docs
    )


def test_item_tagging_uses_last_heading_in_reading_order():
    text = "Item 1. Business\nContents\nItem 1A. Risk Factors\nRisk text"
    assert tag_section(text) == "Item 1A"


def test_item_tagging_supports_later_form_sections():
    assert tag_section("ITEM 9. Changes in and Disagreements With Accountants") == (
        "Item 9"
    )
    assert tag_section("Item 10. Directors, Executive Officers") == "Item 10"


def test_suggest_falls_back_to_generic_without_api_key(monkeypatch):
    from app.services import suggest as suggest_service

    fake_settings = type("FakeSettings", (), {"openrouter_api_key": ""})()
    monkeypatch.setattr(suggest_service, "get_settings", lambda: fake_settings)

    response = client.post("/api/suggest", json={})
    assert response.status_code == 200
    body = response.json()
    assert "questions" in body
    assert isinstance(body["questions"], list)
    assert len(body["questions"]) > 0
