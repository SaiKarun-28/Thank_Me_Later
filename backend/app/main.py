"""
FastAPI application entry point for Thank Me Later.
Stateless, BYOK architecture with strict secret redaction and CORS lock.
"""
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.routers import settings
from app.utils.exceptions import (
    generic_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.utils.security import (
    active_secrets,
    configure_secure_logging,
    register_secret,
)


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

    response = await call_next(request)
    return response


# CORS Configuration: Strictly locked to frontend origin
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
allowed_origins = [orig.strip() for orig in allowed_origins_env.split(",") if orig.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-LLM-Key", "Authorization", "Accept"],
)

# Exception handlers ensuring zero secret or input leakage
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Register routers
app.include_router(settings.router)


@app.get("/health", tags=["system"])
async def health_check():
    """Health status verifying stateless in-memory operation."""
    return {"status": "ok", "persistence": "none", "version": "0.1.0"}
