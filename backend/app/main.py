from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine
from sqlalchemy.exc import DBAPIError
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.api.jobs import router as jobs_router
from app.api.sse import router as sse_router
from app.config import settings
from app.database import Base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    import app.models  # noqa: F401

    sync_engine = create_engine(settings.sync_database_url, pool_pre_ping=True)
    Base.metadata.create_all(sync_engine)
    sync_engine.dispose()
    yield


app = FastAPI(title="DocFlow API", version="1.0.0", lifespan=lifespan)

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs_router)
app.include_router(sse_router)


@app.exception_handler(DBAPIError)
async def database_error(request: Request, exc: DBAPIError) -> JSONResponse:
    logger.exception("Database error on %s", request.url.path)
    msg = str(getattr(exc, "orig", None) or exc)
    return JSONResponse(
        status_code=503,
        content={
            "detail": (
                "Database unavailable. Ensure PostgreSQL is running and the `docflow` database exists "
                f"(see backend/.env.example). Raw error: {msg}"
            )
        },
    )


@app.exception_handler(Exception)
async def unhandled_error(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        return await http_exception_handler(request, exc)
    if isinstance(exc, RequestValidationError):
        return await request_validation_exception_handler(request, exc)
    logger.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": f"{type(exc).__name__}: {exc!s}"},
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
