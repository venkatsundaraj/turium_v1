# AI Knowledge Inbox

Save notes and URLs, then ask questions answered from them with citations. Built with FastAPI, Postgres with pgvector, OpenAI and Next.js.

## Run locally

Requires Docker, [uv](https://docs.astral.sh/uv/), Node 20+ with pnpm, and an OpenAI API key.

```sh
# Database (Postgres + pgvector on localhost:5433)
cd aiserver
docker compose up -d

# API on http://localhost:8000 (API docs at /docs)
cp .env.example .env              # set OPENAI_API_KEY
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000

# Web app on http://localhost:3000 (run in a new terminal)
cd client
cp .env.example .env
pnpm install
pnpm dev
```

## Design decisions

**Chunking: split at natural boundaries, about 1,000 characters with 150 overlap.** Text is split at paragraphs first, then sentences, then words, so chunks never cut a sentence in half. Each chunk is a coherent idea, which retrieves well and reads well as a citation.
*Tradeoff:* sizes are counted in characters, not tokens, and the chunker doesn't understand headings. Semantic chunking would do better on long pages but costs extra embedding calls.

**Vector store: Postgres with pgvector, instead of SQLite or in-memory.** Documents, chunks and vectors commit in one transaction, so a failed embedding never leaves half-indexed data behind. Search plus metadata is one SQL query, and there's a scaling path (HNSW index, full-text search for hybrid retrieval).
*Tradeoff:* it needs a Docker container. SQLite or numpy would be enough for one user.

**Relevance floor (0.25 similarity).** If no chunk is relevant, the LLM is skipped. That is cheaper and leaves nothing to hallucinate from.
*Tradeoff:* the value was tuned by hand for one embedding model.

**Ingestion runs inside the request.** A saved item is searchable as soon as the response returns.
*Tradeoff:* large pages make the request slow.

**URL fetching.** Internal and private addresses are blocked, which protects against SSRF. Page boilerplate is stripped with trafilatura.
*Tradeoff:* pages that need JavaScript to render can't be read.

**Next.js proxies `/api` to FastAPI.** This avoids CORS, and the backend URL is never sent to the browser.

## What breaks at scale

- **Synchronous ingestion:** slow requests and timeouts. → Move it to a job queue and return `202`.
- **pgvector filters after the index search:** a filtered search can return fewer than k results. → Use iterative scan or partial indexes.
- **Vector index size:** the HNSW index outgrows RAM. → Use `halfvec` or quantised vectors.
- **Exact-term queries** (names, IDs) are weak with vector search alone. → Use hybrid search plus a reranker.
- **The DNS-based SSRF check** can be bypassed by DNS rebinding. → Route fetches through an egress proxy.

## Production changes

Auth and per-user data, background ingestion with retries, an evaluation set (retrieval recall and answer faithfulness), automated tests, streamed answers, tracing and cost metrics, and a secret manager.
