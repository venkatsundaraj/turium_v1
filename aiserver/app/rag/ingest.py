from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal
from app.rag.loader import load_corpus, LoadedDocument
from app.lib.connections import SessionLocal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Select, delete, update
from app.rag.embedding import embed_text
from app.models.document import Document, Chunk
from app.lib.connections import engine
from app.rag.chunkers import CHUNKERS, DEFAULT_STRATEGY
import asyncio


EMBED_DB_BATCH = 100

IngestStatus = Literal["created", "updated", "unchanged", "rechunked"]


@dataclass(slots=True)
class IngestOutcome:
    document:Document
    status:IngestStatus
    new_chunks:list[Chunk] = field(default_factory=list)  # added this call, not yet embedded


async def _ingest_chunk(session:AsyncSession, doc_id:int, content:str, strategy:str)->list[Chunk]:

    chunker = CHUNKERS[strategy]

    chunks = [
        Chunk(content = c.content, document_id = doc_id, strategy = strategy, char_start=c.char_start, char_end=c.char_end, token_count=c.token_count, chunk_index = c.index, embedding = None)
        for c in chunker(content)
    ]
    session.add_all(chunks)

    return chunks



async def ingest_one(session:AsyncSession, loaded:LoadedDocument, strategy:str = DEFAULT_STRATEGY)->IngestOutcome:
    """Upsert a document by `source` and (re)chunk it. Flushes but never commits: the caller owns the transaction."""

    doc = (await session.execute(Select(Document).where(Document.source == loaded.source))).scalar_one_or_none()

    if doc is None:

        doc = Document(title = loaded.title, meta=loaded.meta, source = loaded.source, source_type = loaded.source_type.value, content_hash=loaded.content_hash, content=loaded.content)

        session.add(doc)
        await session.flush()

        return IngestOutcome(doc, "created", await _ingest_chunk(session, doc.id, loaded.content, strategy))

    if doc.content_hash == loaded.content_hash:

        exists = (await session.execute(Select(Chunk.id).where(Chunk.document_id == doc.id, Chunk.strategy == strategy).limit(1))).scalar_one_or_none()

        if exists is not None:
            return IngestOutcome(doc, "unchanged")
        return IngestOutcome(doc, "rechunked", await _ingest_chunk(session, doc.id, loaded.content, strategy))

    doc.title = loaded.title
    doc.meta = loaded.meta
    doc.content = loaded.content
    doc.content_hash = loaded.content_hash

    # Content changed: chunks of every strategy are stale.
    await session.execute(delete(Chunk).where(Chunk.document_id == doc.id))

    return IngestOutcome(doc, "updated", await _ingest_chunk(session, doc.id, loaded.content, strategy))


async def embed_chunks(chunks:list[Chunk])->None:
    """Embed in-session chunk objects in place (one API call per 100 chunks)."""
    vectors = await embed_text([c.content for c in chunks])
    for chunk, vec in zip(chunks, vectors):
        chunk.embedding = vec


async def _fill_embeddings(session:AsyncSession):
    """Backfill every chunk still missing an embedding (used by the corpus CLI)."""

    filled = 0
    while True:
        rows = (await session.execute(Select(Chunk.id, Chunk.content).where(Chunk.embedding.is_(None)).order_by(Chunk.id).limit(EMBED_DB_BATCH))).all()

        if not rows:
            return filled

        vectors = await embed_text([content for _, content in rows])

        for (chunk_id, _), vec in zip(rows, vectors):
            await session.execute(update(Chunk).where(Chunk.id == chunk_id).values(embedding = vec))

        await session.commit()
        filled += len(rows)
        print(f"  embedded {filled} chunks...")



async def ingest_corpus(corpus_dir:Path, strategy:str = DEFAULT_STRATEGY):
    docs = load_corpus(corpus_dir=corpus_dir)

    if not docs:
        return []

    async with SessionLocal() as session:
        for d in docs:
            outcome = await ingest_one(session, d, strategy)
            await session.commit()
            print(f"  {d.source}: {outcome.status} ({len(outcome.new_chunks)} new chunks)")

        print("Phase B: filling embeddings")
        await _fill_embeddings(session)

    return "embedded is completed"



BASE_DIR = Path(__file__).resolve().parent.parent.parent
FILE_PATH = BASE_DIR / "data" / "corpus"

async def main():
    import sys
    strategy = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_STRATEGY
    try:
        await ingest_corpus(FILE_PATH, strategy=strategy)
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
