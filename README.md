# Domain
Upload one Form 10-K / annual-report PDF. Ask questions about revenue, segment mix, Item 1A risk factors, MD&A, liquidity, and stated guidance. Answers are generated only from retrieved chunks, with **page citations**.

This stack uses **local sentence-transformers + FAISS** (not serverless). Plan on a laptop or Docker host with ~2 GB disk for models on first run.

**Out of scope:** investment advice, live market data, multi-document hybrid search, GraphRAG, agents.

---

## Features

- **Single-source 10-K RAG** — upload one annual-report PDF; uploading another atomically replaces the active index.
- **Cited, grounded answers** — answers are generated only from retrieved chunks with page citations, and the assistant refuses when the filing does not support the question.
- **Smart query routing** — questions are classified as lookup / multi-part / summarization (LLM with a deterministic heuristic fallback); multi-part questions are decomposed, retrieved per part, merged, and re-ranked.
- **Two-stage retrieval** — local MiniLM embeddings + FAISS, then a cross-encoder re-ranker (pre/post order logged for transparency).
- **Filing-aware suggested questions** — after upload, the LLM proposes analyst questions that are answerable from that filing's content (generic fallback without an API key).
- **Background RAGAS evaluation** — faithfulness, answer relevancy, and context precision are appended to JSONL on every turn.
- **Analyst-oriented UI** — drag-and-drop upload, conversation with auto-scroll, expandable cited sources, clear-chat, and one-click example questions.
- **Runs without an LLM for retrieval** — embeddings and re-ranking are local; upload/indexing (and generic suggestions) still work with no API key.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16, React 19, Tailwind CSS |
| Backend | Python 3.11+, FastAPI, LangChain LCEL |
| LLM | Gemini 2.5 Flash via OpenRouter (OpenAI-compatible API) |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` (local, no API key) |
| Vector store | FAISS `IndexFlatIP` on L2-normalized vectors, persisted to disk |
| Re-ranking | Cross-encoder `ms-marco-MiniLM-L-6-v2` |
| Query handling | LLM (or heuristic fallback) routing: lookup / multi_part / summarization |
| Evaluation | RAGAS: faithfulness, answer relevancy, context precision → JSONL |
| DevOps | Docker Compose |

---

## Architecture

```
PDF upload
    → pdfplumber (pypdf fallback), page numbers preserved
    → recursive chunks (~2400 chars, 300 overlap) + Item 1 / 1A / 7 / 8 tags
    → MiniLM embeddings → FAISS inner-product index on disk
    → after upload: LLM proposes suggested questions from a sample of chunks
User question
    → route + optional sub-query decomposition
    → FAISS top-k per sub-query (merged, de-duplicated)
    → cross-encoder re-rank (pre/post order logged)
    → LCEL prompt + LLM (cite pages; refuse if not in filing)
    → UI sources panel
    → RAGAS metrics appended to JSONL (background)
```

---

## Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.11 or 3.12 |
| Node.js + npm | 20.9+ |
| Docker + Compose | optional, 20+ |
| OpenRouter key | https://openrouter.ai/keys |

Embeddings and the reranker download from Hugging Face on first backend start (~90 MB MiniLM + ~80 MB cross-encoder). `pip install` pulls PyTorch — **first install is ~1.5 GB and can take 5–15 minutes. Do not cancel it.**

---

## Option A — Run locally (without Docker)

### 1. Clone

```bash
git clone <your-fork-url>
cd AI-Phase-1-project
```

### 2. Backend secrets

```bash
cp backend/.env.example backend/.env
```

Set `OPENROUTER_API_KEY=sk-or-v1-...` in `backend/.env`.

### 3. Install dependencies and download the sample 10-K

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
cd ..
python scripts/download_sample_10k.py
```

Writes `sample_docs/aapl-10k-sample.pdf` (Apple FY2024 10-K text from EDGAR). The PDF is gitignored because of size.

### 4. Start API

```bash
cd backend  # from the repository root
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

Wait until you see `Uvicorn running`. Check http://localhost:8000/health → `{"status":"ok","service":"financial-filings-analyst"}`.

### 5. Frontend (new terminal)

```bash
cd frontend
cp .env.local.example .env.local
npm ci
npm run dev
```

Open **http://localhost:3000**. Upload `sample_docs/aapl-10k-sample.pdf`, then ask a question.

---

## Option B — Docker Compose

```bash
cp backend/.env.example backend/.env
# edit OPENROUTER_API_KEY
docker compose up --build
```

| Service | URL |
|---|---|
| UI | http://localhost:3000 |
| API | http://localhost:8000 |
| Swagger | http://localhost:8000/docs |

First build compiles wheels and Next.js (several minutes). The backend image also downloads embedding weights on first query/upload.

```bash
docker compose down
```

FAISS and eval logs live in named volumes.

---

## Usage

1. Drop a text-based 10-K PDF (≤ 50 MB) on the desk. Uploading another PDF atomically replaces the active single-source index.
2. Ask a question — or tap one of the **suggested-question chips** generated from this filing. Multi-part questions (e.g. sales **and** Item 1A) are split; each part is retrieved, then merged and re-ranked.
3. Expand **sources** to see chunk text, 10-K item tag, and page number.
4. Use **Clear chat** to start a fresh conversation against the same filing.
5. RAGAS scores for that turn are appended to `backend/logs/ragas_eval.jsonl` (async; not shown in the UI).

The assistant will say the fact is **not in the uploaded filing** if retrieval cannot support it (try asking for Tesla automotive revenue on an Apple 10-K).

---

## API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | `{"status":"ok","service":"financial-filings-analyst"}` |
| `/api/upload` | POST | multipart `file`; returns `document_id`, page and chunk counts |
| `/api/query` | POST | `{question, document_id?, evaluate?}` → answer, sources, `route_type`, `sub_queries`, pre/post rerank lists |
| `/api/suggest` | POST | `{document_id?}` → up to 5 analyst questions grounded in the indexed filing |
| `/api/evaluate` | POST | `{question, answer, contexts, ground_truth?}` → RAGAS metrics, evaluation status + JSONL |
| `/docs` | GET | Swagger UI |

### `POST /api/query` body

```json
{
  "question": "What were total net sales and what does Item 1A say about supply-chain risk?",
  "document_id": null,
  "evaluate": true
}
```

### `POST /api/suggest` body

```json
{
  "document_id": null
}
```

Returns `{"questions": ["What were total net sales in the most recent fiscal year?", ...]}`. Falls back to generic 10-K questions when there is no indexed filing, no API key, or the generation call fails.

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENROUTER_API_KEY` | Yes (for answers) | empty | LLM + routing + RAGAS |
| `CHAT_MODEL` | No | `google/gemini-2.5-flash` | OpenRouter model id |
| `ALLOWED_ORIGINS` | No | `http://localhost:3000` | CORS |
| `FAISS_INDEX_PATH` | No | `./data/faiss_index` | Persisted index |
| `EVAL_LOG_PATH` | No | `./logs/ragas_eval.jsonl` | RAGAS JSONL |
| `RERANK_LOG_PATH` | No | `./logs/rerank.jsonl` | Pre/post rerank traces |
| `RETRIEVAL_TOP_K` | No | `12` | FAISS candidates |
| `RERANKER_TOP_K` | No | `5` | Chunks sent to the LLM |

### Frontend (`frontend/.env.local`)

| Variable | Default | Description |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | empty | Optional direct browser → FastAPI URL |

By default, the browser uses same-origin `/api` requests and Next.js proxies them to FastAPI. Docker Compose bakes `INTERNAL_API_URL=http://backend:8000` into the frontend build. Set `NEXT_PUBLIC_API_URL` only when the frontend and backend are intentionally hosted on different origins.

---

## CLI checks (before you trust the UI)

From `backend/` with the venv active and a PDF already uploaded (or indexed via the API):

```bash
# Same question twice → identical top-k
python -m scripts.query_cli --repeat --k 5 "What were total net sales for fiscal 2024?"

# Different question → different chunks
python -m scripts.query_cli --k 5 "What does Item 1A disclose about competition?"

# Re-rank before/after (capture this for evidence)
python -m eval.rerank_demo

# Batch RAGAS (8–12 labeled items; not all scores will be 1.0)
python -m eval.run_eval
```

---

## Re-ranking before / after (example)

Run `python -m eval.rerank_demo` after indexing the sample Apple 10-K. A typical reshuffle looks like this (chunk ids and pages depend on your pagination):

| Rank | Before (FAISS) | After (cross-encoder) |
|---|---|---|
| 1 | Generic “Item 1 Business” chunk (lexical overlap on “manufacturing”) | Item 1A paragraph on outsourcing partners / Asia concentration |
| 2 | Risk-factor body | Adjacent 1A supply-chain paragraph |
| 3 | MD&A operations | Item 1 manufacturing description |

`top1_changed: true` is written into `backend/logs/rerank.jsonl` together with scores. If a given question does **not** move rank 1, try the default demo query (manufacturing concentration / outsourcing partners) or another Item 1A-vs-Item 1 clash.

---

## Evaluation logs

Each `/api/query` with `evaluate: true` (the UI default) and each `run_eval` row appends:

```json
{
  "timestamp": "2026-09-14T12:00:00+00:00",
  "question": "What were Apple's total net sales for fiscal 2024?",
  "answer_preview": "According to the filing, total net sales were $391,035 million...",
  "metrics": {
    "faithfulness": 0.83,
    "answer_relevancy": 0.91,
    "context_precision": 0.72
  },
  "context_precision_variant": "without_reference"
}
```

Scores are LLM-judged and **should not all be 1.0**. Nulls mean that RAGAS call failed (check OpenRouter quota / logs).
Live queries use RAGAS context precision **without a reference**; labeled batch evaluation uses reference-based context precision. Each JSONL record identifies the variant in `context_precision_variant`.

Labeled set: [`backend/eval/eval_set.json`](backend/eval/eval_set.json) (12 questions, including a negative control about Tesla).

---

## Project Structure

```
AI-Phase-1-project/
├── backend/
│   ├── app/main.py, config.py, models.py
│   ├── app/routes/   upload.py, query.py, suggest.py, evaluate.py
│   ├── app/services/ ingestion, embeddings, vector_store,
│   │                 router, reranker, rag_chain, evaluator, suggest
│   ├── eval/         eval_set.json, run_eval.py, rerank_demo.py
│   ├── scripts/      query_cli.py
│   ├── tests/        API, retrieval, and reranking unit tests
│   ├── requirements.txt, requirements-dev.txt, requirements-tools.txt
│   └── Dockerfile
├── frontend/         Next.js App Router (upload + cited chat)
├── sample_docs/      generated 10-K PDF (gitignored)
├── scripts/download_sample_10k.py
├── docker-compose.yml
└── README.md
```

---

## Troubleshooting

**`OPENROUTER_API_KEY` empty** — upload/indexing still works; `/api/query` returns 503 until the key is set.

**Blank pages / no chunks** — use a text-based PDF. The download script produces one from EDGAR HTML.

**SEC download 403** — EDGAR requires a User-Agent. The script already sends one. Retry once; do not hammer the endpoint.

**Port in use** — `lsof -i :8000` or `:3000` and stop the other process.

**Docker UI cannot upload** — rebuild the frontend after changing `INTERNAL_API_URL`; browser requests should go to same-origin `/api`.

**First query is slow** — models load into memory on first use (embeddings + cross-encoder).

---

## Tests

```bash
# All backend and frontend checks
make check

# Backend only
cd backend
source .venv/bin/activate
ruff check .
ruff format --check .
pytest -q
```

Covers `/health`, PDF validation, 10-K item tagging, query routing, persisted inner-product retrieval, single-source replacement, multi-part reranking, and question-suggestion fallback. Full LLM/RAGAS behavior requires an API key and is verified with the CLI steps above.
