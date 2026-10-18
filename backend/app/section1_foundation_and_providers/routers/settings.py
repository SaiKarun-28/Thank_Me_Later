"""
Settings router: Test connection and metadata for Section 1.
"""
from typing import List, Optional
from fastapi import APIRouter, Header, HTTPException, status
import logging

from app.section1_foundation_and_providers.providers.base import LLMProviderError
from app.section1_foundation_and_providers.providers.registry import ProviderRegistry, get_provider
from app.section1_foundation_and_providers.schemas.settings import (
    ProviderInfo,
    TestSettingsRequest,
    TestSettingsResponse,
)
from app.section1_foundation_and_providers.security.security import register_secret

router = APIRouter(prefix="/settings", tags=["settings"])
logger = logging.getLogger(__name__)


@router.get("/providers", response_model=List[ProviderInfo])
async def list_providers() -> List[ProviderInfo]:
    """Returns the list of supported LLM providers and default models."""
    return ProviderRegistry.list_providers()


@router.get("/sources")
async def list_sources():
    """Returns metadata schemas and credential field definitions for all 7 job sources."""
    from app.section3_job_sources.registry import get_all_source_meta
    return get_all_source_meta()


@router.post("/test", response_model=TestSettingsResponse)
async def test_llm_connection(
    request: TestSettingsRequest,
    x_llm_key: Optional[str] = Header(None, alias="X-LLM-Key"),
) -> TestSettingsResponse:
    """
    Validates LLM credentials and connectivity without persisting any keys.
    Key is provided via X-LLM-Key header (or body api_key fallback).
    Secrets are immediately registered in ContextVar for logging redaction.
    """
    effective_key = x_llm_key or request.api_key
    if effective_key:
        register_secret(effective_key)

    try:
        provider = get_provider(
            provider_id=request.provider,
            api_key=effective_key,
            model=request.model,
            custom_url=request.base_url,
        )
        result = await provider.test_connection()
        return TestSettingsResponse(
            success=result.get("success", True),
            message=result.get("message", "Connection verified successfully."),
            model=result.get("model", request.model),
            latency_ms=result.get("latency_ms"),
        )
    except LLMProviderError as e:
        logger.warning("Provider test failed for %s: %s", request.provider, e.message)
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message,
        )
    except Exception as e:
        logger.error("Unexpected error during provider test for %s: %s", request.provider, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete connection test.",
        )
