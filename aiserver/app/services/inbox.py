"""Use cases behind the HTTP API. Routers translate HTTP <-> these calls; the RAG modules do the work."""

import logging

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import ConflictError
from app.models.document import Chunk, Document
from app.rag.chunkers import DEFAULT_STRATEGY
from app.rag.generation import generate_answer
from app.rag.ingest import embed_chunks, ingest_one
from app.rag.loader import LoadedDocument, load_note, load_web_page
from app.rag.retrieval import search
from app.rag.web import fetch_page
from app.schemas import (
    IngestRequest, IngestResponse, ItemOut, ItemsResponse, NoteIngest,
    QueryResponse, QueryTimings, SourceOut,
)

log = logging.getLogger(__name__)

PREVIEW_CHARS = 280
# text-embedding-3-small: on-topic chunks score ~0.4-0.7 cosine similarity, unrelated ones ~0.0-0.2.
# Below the floor we skip the LLM: cheaper, and nothing for it to hallucinate from.
MIN_SIMILARITY = 0.25
EMPTY_INBOX_ANSWER = "Your inbox has no saved content yet. Add a note or URL, then ask again."
NO_MATCH_ANSWER = "I couldn't find anything relevant to that in your saved content."


def _to_item(doc:Document, chunk_count:int)->ItemOut:
    preview = doc.content[:PREVIEW_CHARS] + ("…" if len(doc.content) > PREVIEW_CHARS else "")
    return ItemOut(
        id=doc.id, source_type=doc.source_type, source=doc.source, title=doc.title,
        preview=preview, chunk_count=chunk_count, created_at=doc.created_at,
    )


async def _chunk_count(session:AsyncSession, doc_id:int)->int:
    stmt = select(func.count()).select_from(Chunk).where(Chunk.document_id == doc_id, Chunk.strategy == DEFAULT_STRATEGY)
    return (await session.execute(stmt)).scalar_one()


async def ingest(session:AsyncSession, req:IngestRequest)->IngestResponse:
    loaded:LoadedDocument = (
        load_note(req.content, req.title) if isinstance(req, NoteIngest)
        else load_web_page(await fetch_page(str(req.url)))
    )

    # One transaction: document, chunks and embeddings land together or not at all,
    # so a failed embedding call never leaves unsearchable chunks behind.
    try:
        outcome = await ingest_one(session, loaded)
        if outcome.new_chunks:
            await embed_chunks(outcome.new_chunks)
        await session.commit()
    except IntegrityError:
        # Two concurrent requests saved the same source; the session closes (and rolls back) after the request.
        raise ConflictError("This item is being saved by another request; retry in a moment")

    await session.refresh(outcome.document)  # load server-side created_at
    log.info("ingest.done", extra={"fields": {
        "document_id": outcome.document.id, "source_type": loaded.source_type.value,
        "status": outcome.status, "new_chunks": len(outcome.new_chunks), "chars": len(loaded.content),
    }})
    return IngestResponse(status=outcome.status, item=_to_item(outcome.document, await _chunk_count(session, outcome.document.id)))


async def list_items(session:AsyncSession, limit:int, offset:int)->ItemsResponse:
    chunk_counts = (
        select(Chunk.document_id, func.count().label("n"))
        .where(Chunk.strategy == DEFAULT_STRATEGY)
        .group_by(Chunk.document_id)
        .subquery()
    )
    stmt = (
        select(Document, func.coalesce(chunk_counts.c.n, 0))
        .outerjoin(chunk_counts, chunk_counts.c.document_id == Document.id)
        .order_by(Document.created_at.desc(), Document.id.desc())
        .limit(limit).offset(offset)
    )
    rows = (await session.execute(stmt)).all()
    total = (await session.execute(select(func.count()).select_from(Document))).scalar_one()

    return ItemsResponse(items=[_to_item(doc, n) for doc, n in rows], total=total, limit=limit, offset=offset)


async def answer(session:AsyncSession, question:str, top_k:int)->QueryResponse:
    retrieved = await search(session, question, k=top_k)
    relevant = [c for c in retrieved.chunks if c.similarity >= MIN_SIMILARITY]

    if not relevant:
        log.info("query.no_match", extra={"fields": {"retrieved": len(retrieved.chunks), "top_similarity": retrieved.chunks[0].similarity if retrieved.chunks else None}})
        return QueryResponse(
            answer=NO_MATCH_ANSWER if retrieved.chunks else EMPTY_INBOX_ANSWER, sources=[],
            timings=QueryTimings(embed_ms=retrieved.embed_ms, search_ms=retrieved.search_ms, generate_ms=0),
        )

    generated = await generate_answer(question, relevant)

    sources = [
        SourceOut(
            n=n, cited=n in generated.cited, chunk_id=c.chunk_id, document_id=c.document_id,
            source_type=c.source_type, source=c.source, title=c.title, snippet=c.content.strip(),
            char_start=c.char_start, char_end=c.char_end, similarity=round(c.similarity, 4),
        )
        for n, c in enumerate(relevant, start=1)
    ]
    timings = QueryTimings(embed_ms=retrieved.embed_ms, search_ms=retrieved.search_ms, generate_ms=generated.generate_ms)

    log.info("query.done", extra={"fields": {
        "top_k": top_k, "retrieved": len(sources), "cited": sorted(generated.cited),
        "top_similarity": sources[0].similarity, **timings.model_dump(),
    }})
    return QueryResponse(answer=generated.text, sources=sources, timings=timings)
