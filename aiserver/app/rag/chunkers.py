"""Strategy registry. Chunks are stored with their strategy label, so strategies can coexist and be compared."""

from app.rag.chunking import FIXED_STRATEGY_LABEL, chunk_text
from app.rag.recursive_chunking import RECURSIVE_STRATEGY_LABEL, chunk_recursive

CHUNKERS = {
    FIXED_STRATEGY_LABEL: chunk_text,
    RECURSIVE_STRATEGY_LABEL: chunk_recursive,
}

# Used by both ingestion and retrieval: query-time search only sees chunks of this strategy.
DEFAULT_STRATEGY = RECURSIVE_STRATEGY_LABEL
