"""
Custom FastAPI exception handlers enforcing zero secret leakage.
Drops "input" fields to prevent reflection of sensitive headers or body payloads.
"""
from typing import Any, Dict, List
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.section1_foundation_and_providers.security.security import redact_text


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Overrides standard FastAPI 422 handler.
    Strictly removes the 'input' field from all error items to prevent reflection
    of client-provided keys or raw resume data, and redacts error messages.
    """
    sanitized_errors: List[Dict[str, Any]] = []
    
    for err in exc.errors():
        error_copy = dict(err)
        # Drop raw user input to ensure secrets / PII are never reflected
        error_copy.pop("input", None)
        
        # Redact any messages or location strings that might contain registered secrets
        if "msg" in error_copy and isinstance(error_copy["msg"], str):
            error_copy["msg"] = redact_text(error_copy["msg"])
            
        sanitized_errors.append(error_copy)

    return JSONResponse(
        status_code=422,
        content={"detail": sanitized_errors},
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """
    Sanitizes standard HTTP exceptions, ensuring detail messages never leak active secrets.
    """
    detail = exc.detail
    if isinstance(detail, str):
        detail = redact_text(detail)
    elif isinstance(detail, dict):
        detail = {k: redact_text(str(v)) if isinstance(v, str) else v for k, v in detail.items()}
    elif isinstance(detail, list):
        detail = [redact_text(str(x)) if isinstance(x, str) else x for x in detail]

    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": detail},
        headers=exc.headers,
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Fallback 500 handler ensuring uncaught exception traces never leak active secrets.
    """
    message = redact_text(str(exc))
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred.", "message": message},
    )
