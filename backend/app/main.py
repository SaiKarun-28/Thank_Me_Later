"""
FastAPI application entry point for Thank Me Later.
Stateless, BYOK architecture with strict secret redaction and CORS lock.
Organized into section-wise modules.
"""
import os
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.section1_foundation_and_providers.routers.settings import router as settings_router
from app.section1_foundation_and_providers.security.exceptions import (
    generic_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.section1_foundation_and_providers.security.security import (
    active_secrets,
    configure_secure_logging,
    register_secret,
)
from app.section2_parsing_and_upload.routers.upload import router as upload_router
from app.section4_ranking_and_search.routers.jobs import router as jobs_router


# Simple in-memory per-IP rate limiter
_rate_limit_storage: defaultdict[str, list] = defaultdict(list)
_RATE_LIMIT_MAX = 60  # 60 requests per window
_RATE_LIMIT_WINDOW = 60  # seconds


def _check_rate_limit(client_ip: str) -> bool:
    """Check if client IP is within rate limits. Returns True if allowed."""
    now = time.time()
    window_start = now - _RATE_LIMIT_WINDOW

    # Remove timestamps outside the current window
    _rate_limit_storage[client_ip] = [
        ts for ts in _rate_limit_storage[client_ip] if ts > window_start
    ]

    if len(_rate_limit_storage[client_ip]) >= _RATE_LIMIT_MAX:
        return False

    _rate_limit_storage[client_ip].append(now)
    return True


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Configure project-wide secure logging with secret redaction
    configure_secure_logging()
    yield


app = FastAPI(
    title="Thank Me Later — Resume-to-Job Matcher",
    description="Stateless BYOK Resume Matching Backend",
    version="0.1.0",
    lifespan=lifespan,
)


# Secret Registration Middleware: Auto-registers header secrets into ContextVar
@app.middleware("http")
async def secret_redaction_middleware(request: Request, call_next):
    # Initialize a new isolated set for this request's context
    active_secrets.set(set())

    # Register X-LLM-Key if present
    x_llm_key = request.headers.get("X-LLM-Key")
    if x_llm_key:
        register_secret(x_llm_key)

    # Rate limit check
    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(client_ip):
        return Response(
            content={"detail": "Rate limit exceeded. Please slow down."},
            status_code=429,
            headers={"Retry-After": "60"},
        )

    response = await call_next(request)
    return response


# CORS Configuration: Strictly locked to frontend origin
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:3001")
allowed_origins = [orig.strip() for orig in allowed_origins_env.split(",") if orig.strip()]

cors_regex = os.getenv("CORS_ORIGIN_REGEX", r"^https://(thank-me-later|thankmelater)(-[a-z0-9-]+)?\.vercel\.app$")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=cors_regex,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# Exception handlers ensuring zero secret or input leakage
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)


# Register section routers
app.include_router(settings_router)
app.include_router(upload_router)
app.include_router(jobs_router)


@app.get("/", tags=["system"])
async def root():
    """Root landing endpoint providing service metadata."""
    return {
        "name": "Thank Me Later API",
        "version": "0.1.0",
        "status": "online",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", tags=["system"])
async def health_check():
    """Health status verifying stateless in-memory operation."""
    return {"status": "ok", "persistence": "none", "version": "0.1.0"}