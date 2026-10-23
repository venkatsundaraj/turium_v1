from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.lib.connections import get_db
from app.schemas import IngestRequest, IngestResponse, ItemsResponse, QueryRequest, QueryResponse
from app.services import inbox

router = APIRouter()

Session = Annotated[AsyncSession, Depends(get_db)]


@router.post(
    "/ingest",
    response_model=IngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save a note or a URL",
    responses={200: {"description": "Item already existed (unchanged/updated/rechunked)"}},
)
async def ingest(session:Session, response:Response, body:Annotated[IngestRequest, Body()]):
    result = await inbox.ingest(session, body)
    if result.status != "created":
        response.status_code = status.HTTP_200_OK
    return result


@router.get("/items", response_model=ItemsResponse, summary="List saved items, newest first")
async def list_items(
    session:Session,
    limit:Annotated[int, Query(ge=1, le=100)] = 50,
    offset:Annotated[int, Query(ge=0)] = 0,
):
    return await inbox.list_items(session, limit, offset)


@router.post("/query", response_model=QueryResponse, summary="Ask a question over saved content")
async def query(session:Session, body:QueryRequest):
    return await inbox.answer(session, body.question, body.top_k)
