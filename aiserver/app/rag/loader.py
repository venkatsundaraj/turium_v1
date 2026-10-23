"""Turn raw inputs (a note, a fetched web page, corpus files) into one normalised LoadedDocument."""

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.models.document import SourceType
from app.rag.web import FetchedPage

TITLE_MAX = 255
CORPUS_SUFFIXES = {".md", ".txt"}
# Footnote markers like [12] or [citation needed]: noise for embeddings, and they collide with our [n] citations.
_FOOTNOTE = re.compile(r"\[(?:\d+|[a-z]|citation needed)\]")


@dataclass(frozen=True, slots=True)
class LoadedDocument:
    source:str          # unique identity: the URL, the file path, or "note:<hash>"
    source_type:SourceType
    title:str | None
    content:str
    content_hash:str
    meta:dict[str, Any] = field(default_factory=dict)


def _sha256(text:str)->str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize_text(text:str)->str:
    """Unify newlines, strip trailing spaces, collapse 3+ blank lines. Keeps paragraph breaks for the chunker."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _first_line_title(text:str, limit:int = 80)->str:
    line = text.split("\n", 1)[0].strip()
    return line if len(line) <= limit else line[: limit - 1].rstrip() + "…"


def load_note(content:str, title:str | None = None)->LoadedDocument:
    text = normalize_text(content)
    digest = _sha256(text)
    return LoadedDocument(
        # Identical notes dedupe to one document; edited text is a new note.
        source=f"note:{digest}",
        source_type=SourceType.NOTE,
        title=(title or _first_line_title(text))[:TITLE_MAX],
        content=text,
        content_hash=digest,
    )


def load_web_page(page:FetchedPage)->LoadedDocument:
    text = normalize_text(_FOOTNOTE.sub("", page.text))
    return LoadedDocument(
        source=page.final_url,
        source_type=SourceType.URL,
        title=(page.title or page.final_url)[:TITLE_MAX],
        content=text,
        content_hash=_sha256(text),
        meta={"requested_url": page.requested_url, "content_type": page.content_type},
    )


def load_corpus(corpus_dir:Path)->list[LoadedDocument]:
    docs = []
    for path in sorted(corpus_dir.rglob("*")):
        if path.suffix not in CORPUS_SUFFIXES or not path.is_file():
            continue
        text = normalize_text(path.read_text(encoding="utf-8"))
        if not text:
            continue
        docs.append(LoadedDocument(
            source=str(path.relative_to(corpus_dir)),
            source_type=SourceType.FILE,
            title=path.stem[:TITLE_MAX],
            content=text,
            content_hash=_sha256(text),
        ))
    return docs
