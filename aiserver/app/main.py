import logging
import time
import uuid
from contextlib import asynccontextmanager

import openai
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.routes import router
from app.config import settings
from app.errors import AppError
from app.lib.connections import engine
from app.lib.logging import configure_logging, request_id_var

configure_logging(settings.LOG_LEVEL)
log = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app:FastAPI):
    async with engine.connect() as conn:
        await conn.execute(text('SELECT 1'))
    log.info("startup.db_connected")

    yield

    await engine.dispose()
    log.info("shutdown.engine_disposed")


app = FastAPI(description="Save notes and URLs, then ask questions over them (RAG).", title=settings.APP_NAME, lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_methods=["GET", "POST"], allow_headers=["*"], expose_headers=["X-Request-ID"])


@app.middleware("http")
async def request_context(request:Request, call_next):
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
    token = request_id_var.set(request_id)
    t0 = time.perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        log.info("http.request", extra={"fields": {
            "method": request.method, "path": request.url.path, "status": status_code,
            "duration_ms": int((time.perf_counter() - t0) * 1000),
        }})
        request_id_var.reset(token)


def _error(status_code:int, code:str, message:str, **extra)->JSONResponse:
    body = {"error": {"code": code, "message": message, "request_id": request_id_var.get(), **extra}}
    return JSONResponse(status_code=status_code, content=body)


@app.exception_handler(AppError)
async def app_error_handler(request:Request, exc:AppError):
    log.warning("request.failed", extra={"fields": {"code": exc.code, "error": exc.message}})
    return _error(exc.status_code, exc.code, exc.message)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request:Request, exc:RequestValidationError):
    details = [{"field": ".".join(str(p) for p in e["loc"][1:]), "message": e["msg"]} for e in exc.errors()]
    message = "; ".join(f"{d['field'] or 'body'}: {d['message']}" for d in details)
    return _error(422, "validation_error", message, details=details)


@app.exception_handler(openai.APIError)
async def llm_error_handler(request:Request, exc:openai.APIError):
    log.error("llm.failed", extra={"fields": {"error": str(exc), "type": exc.__class__.__name__}})
    return _error(502, "llm_unavailable", "The AI provider failed to respond. Please try again.")


@app.exception_handler(Exception)
async def unhandled_error_handler(request:Request, exc:Exception):
    log.exception("request.unhandled")
    return _error(500, "internal_error", "Something went wrong on our side.")


app.include_router(router)


@app.get('/health', tags=["ops"])
async def health():
    return {"status": "ok"}
