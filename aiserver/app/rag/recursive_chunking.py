"""Structure-aware chunking: split on the coarsest boundary that fits, then pack.

Why this over fixed-size windows: notes and extracted web articles are already
organised into paragraphs. Cutting on paragraph -> line -> sentence -> word
boundaries keeps each chunk a coherent unit of meaning, which embeds better and
reads better as a cited snippet. Fixed windows cut mid-sentence.

Offsets are tracked against the original text throughout, so every chunk is an
exact slice: text[char_start:char_end] == content. That is what lets the UI
highlight a citation inside the stored document.
"""

from app.rag.chunking import TextChunk, count_tokens

RECURSIVE_CHUNK_SIZE = 1000   # chars (~250 tokens): one or two paragraphs
RECURSIVE_CHUNK_OVERLAP = 150  # carried over at an atom boundary, never mid-word
RECURSIVE_STRATEGY_LABEL = f"recursive_c{RECURSIVE_CHUNK_SIZE}_o{RECURSIVE_CHUNK_OVERLAP}"

# Coarsest first. "" means hard cut, the last resort for e.g. a giant URL or token blob.
SEPARATORS = ("\n\n", "\n", ". ", "? ", "! ", "; ", ", ", " ", "")

Span = tuple[int, int]


def _split(text:str, start:int, end:int, size:int, separators:tuple[str, ...])->list[Span]:
    """Break text[start:end] into contiguous spans that are each <= size."""
    if end - start <= size:
        return [(start, end)]

    sep, rest = separators[0], separators[1:]

    if sep == "":
        return [(s, min(s + size, end)) for s in range(start, end, size)]

    # Cut points sit just after each separator, so the separator stays with the text before it.
    cuts, pos = [], text.find(sep, start, end)
    while pos != -1:
        cuts.append(pos + len(sep))
        pos = text.find(sep, pos + len(sep), end)

    if not cuts:
        return _split(text, start, end, size, rest)

    spans:list[Span] = []
    piece_start = start
    for cut in [*cuts, end]:
        if cut > piece_start:
            spans.extend(_split(text, piece_start, cut, size, rest))
            piece_start = cut
    return spans


def chunk_recursive(text:str, size:int = RECURSIVE_CHUNK_SIZE, overlap:int = RECURSIVE_CHUNK_OVERLAP)->list[TextChunk]:
    if size <= 0:
        raise ValueError(f"size must be positive, got {size}")
    if not 0 <= overlap < size:
        raise ValueError(f"overlap must be in [0, size), got {overlap}")
    if not text:
        return []

    atoms = _split(text, 0, len(text), size, SEPARATORS)

    # Greedily pack adjacent atoms into chunks of at most `size` chars.
    result:list[TextChunk] = []
    i = 0
    while i < len(atoms):
        chunk_start = atoms[i][0]
        j = i
        while j < len(atoms) and atoms[j][1] - chunk_start <= size:
            j += 1
        chunk_end = atoms[j - 1][1]

        content = text[chunk_start:chunk_end]
        if content.strip():
            result.append(TextChunk(
                index=len(result),
                content=content,
                char_start=chunk_start,
                char_end=chunk_end,
                token_count=count_tokens(content),
            ))

        if j == len(atoms):
            break

        # Start the next chunk at the first atom inside the overlap window (always > i, so we progress).
        i = next((k for k in range(i + 1, j) if atoms[k][0] >= chunk_end - overlap), j)

    return result
