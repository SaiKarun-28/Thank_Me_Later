"""
Settings and Provider Schemas.
"""
from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field


class TestSettingsRequest(BaseModel):
    """Payload to test an LLM connection."""
    provider: str
    model: str
    base_url: Optional[str] = None
    # Key can be sent in body or header (header preferred: X-LLM-Key)
    api_key: Optional[str] = None


class TestSettingsResponse(BaseModel):
    success: bool
    message: str
    model: str
    latency_ms: Optional[float] = None


class ProviderInfo(BaseModel):
    id: str
    name: str
    default_model: str
    available_models: List[str]
    requires_key: bool
    allows_custom_url: bool
    default_base_url: Optional[str] = None


class SourceFieldSchema(BaseModel):
    key: str
    label: str
    type: Literal["text", "password", "select", "list"]
    required: bool = False
    default: Any = None
    options: Optional[List[str]] = None
    description: Optional[str] = None


class SourceMetaSchema(BaseModel):
    id: str
    name: str
    is_keyless: bool
    fields: List[SourceFieldSchema]
    attribution: Optional[str] = None
    terms_url: Optional[str] = None
