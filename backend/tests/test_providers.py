"""
LLM Provider Registry and Adapter Tests.
"""
import pytest
import httpx

from app.providers.base import LLMProviderError, extract_json_object
from app.providers.gemini import GeminiProvider
from app.providers.openai_compat import OpenAICompatProvider
from app.providers.registry import (
    ProviderRegistry,
    get_provider,
    validate_model_name,
    validate_custom_url,
)


def test_provider_registry_contains_all_seven_providers():
    """Verify that all 7 required BYOK providers are registered."""
    providers = ProviderRegistry.list_providers()
    provider_ids = {p.id for p in providers}
    expected = {"gemini", "groq", "openrouter", "nvidia", "cerebras", "mistral", "ollama"}
    assert expected.issubset(provider_ids), f"Missing providers: {expected - provider_ids}"


def test_model_name_regex_validation():
    """Verify safe model name regex enforcement."""
    # Valid model names
    assert validate_model_name("llama-3.3-70b-versatile") == "llama-3.3-70b-versatile"
    assert validate_model_name("gemini-1.5-flash") == "gemini-1.5-flash"
    assert validate_model_name("meta/llama-3.1-70b-instruct") == "meta/llama-3.1-70b-instruct"
    assert validate_model_name("google/gemini-2.0-flash-exp:free") == "google/gemini-2.0-flash-exp:free"
    assert validate_model_name("mistral.small.latest") == "mistral.small.latest"

    # Invalid model names
    with pytest.raises(LLMProviderError) as exc_info:
        validate_model_name("llama 3.3 versatile")  # contains space
    assert exc_info.value.status_code == 400

    with pytest.raises(LLMProviderError) as exc_info:
        validate_model_name("<script>alert(1)</script>")  # special characters
    assert exc_info.value.status_code == 400

    with pytest.raises(LLMProviderError) as exc_info:
        validate_model_name("a" * 65)  # exceeds 64 chars
    assert exc_info.value.status_code == 400


def test_custom_url_restrictions():
    """Verify that custom URLs are only permitted for Ollama on localhost or host.docker.internal."""
    # Ollama on localhost / host.docker.internal -> valid
    assert validate_custom_url("ollama", "http://localhost:11434/v1") == "http://localhost:11434/v1"
    assert validate_custom_url("ollama", "http://127.0.0.1:11434/v1") == "http://127.0.0.1:11434/v1"
    assert validate_custom_url("ollama", "http://host.docker.internal:11434/v1") == "http://host.docker.internal:11434/v1"

    # Ollama on external untrusted host -> invalid
    with pytest.raises(LLMProviderError) as exc:
        validate_custom_url("ollama", "http://api.malicious.com:11434/v1")
    assert exc.value.status_code == 400

    # Non-Ollama provider (Groq) with custom URL -> invalid
    with pytest.raises(LLMProviderError) as exc:
        validate_custom_url("groq", "http://localhost:8000/v1")
    assert exc.value.status_code == 400


def test_gemini_header_key_security():
    """
    Verify that Google Gemini adapter puts the API key strictly in the
    'x-goog-api-key' header and never in the URL.
    """
    key = "TEST-GEMINI-KEY-999"
    provider = get_provider("gemini", api_key=key, model="gemini-1.5-flash")
    
    assert isinstance(provider, GeminiProvider)
    headers = provider._get_headers()
    assert headers.get("x-goog-api-key") == key
    assert key not in provider.base_url


def test_openai_compat_authorization_header():
    """Verify that OpenAI-compatible adapter formats Authorization Bearer header correctly."""
    key = "gsk_testkey12345"
    provider = get_provider("groq", api_key=key, model="llama-3.3-70b-versatile")
    
    assert isinstance(provider, OpenAICompatProvider)
    headers = provider._get_headers()
    assert headers.get("Authorization") == f"Bearer {key}"


def test_extract_json_object_variations():
    """Verify robust extraction of JSON from raw model strings."""
    # Direct JSON
    assert extract_json_object('{"name": "Alice"}') == {"name": "Alice"}

    # Markdown code fences
    fence_input = "```json\n{\n  \"skills\": [\"Python\", \"FastAPI\"]\n}\n```"
    assert extract_json_object(fence_input) == {"skills": ["Python", "FastAPI"]}

    # Preceding and trailing chatter
    chatter_input = "Sure, here is your parsed profile:\n{\"years_experience\": 5.5}\nHope this helps!"
    assert extract_json_object(chatter_input) == {"years_experience": 5.5}

    # Invalid JSON raises ValueError
    with pytest.raises(ValueError):
        extract_json_object("Not a json at all.")


@pytest.mark.asyncio
async def test_provider_error_normalization():
    """Verify that upstream HTTP errors are translated into friendly user messages."""
    provider = get_provider("groq", api_key="test-key")

    # 401 Unauthorized
    req = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    resp_401 = httpx.Response(401, request=req, text="Unauthorized: Invalid API key")
    err_401 = provider._normalize_error(httpx.HTTPStatusError("401", request=req, response=resp_401))
    assert err_401.status_code == 401
    assert "The provided API key is invalid" in err_401.message

    # 429 Rate Limit
    resp_429 = httpx.Response(429, request=req, text="Rate limit reached")
    err_429 = provider._normalize_error(httpx.HTTPStatusError("429", request=req, response=resp_429))
    assert err_429.status_code == 429
    assert "Rate limit or quota exceeded" in err_429.message

    # Timeout
    err_timeout = provider._normalize_error(httpx.ReadTimeout("timed out", request=req))
    assert err_timeout.status_code == 504
    assert "timed out" in err_timeout.message
