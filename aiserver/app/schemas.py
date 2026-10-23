"""HTTP request/response contracts. Kept separate from ORM models so the DB can change without breaking clients."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class _In(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


# ---- POST /ingest ---------------------------------------------------------

class NoteIngest(_In):
    type:Literal["note"]
    content:str = Field(min_length=1, max_length=50_000)
    title:str | None = Field(default=None, max_length=255)


class UrlIngest(_In):
    type:Literal["url"]
    url:HttpUrl


IngestRequest = Annotated[NoteIngest | UrlIngest, Field(discriminator="type")]


class ItemOut(BaseModel):
    id:int
    source_type:Literal["note", "url", "file"]
    source:str
    title:str | None
    preview:str
    chunk_count:int
    created_at:datetime


class IngestResponse(BaseModel):
    status:Literal["created", "updated", "unchanged", "rechunked"]
    item:ItemOut


# ---- GET /items -----------------------------------------------------------

class ItemsResponse(BaseModel):
    items:list[ItemOut]
    total:int
    limit:int
    offset:int


# ---- POST /query ----------------------------------------------------------

class QueryRequest(_In):
    question:str = Field(min_length=3, max_length=2_000)
    top_k:int = Field(default=5, ge=1, le=10)


class SourceOut(BaseModel):
    n:int = Field(description="The number the answer cites as [n]")
    cited:bool
    chunk_id:int
    document_id:int
    source_type:str
    source:str
    title:str | None
    snippet:str
    char_start:int
    char_end:int
    similarity:float


class QueryTimings(BaseModel):
    embed_ms:int
    search_ms:int
    generate_ms:int


class QueryResponse(BaseModel):
    answer:str
    sources:list[SourceOut]
    timings:QueryTimings
