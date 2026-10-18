"""
Declarative Provider Registry and Factory.
Adding a new provider is a single registry entry.
"""
from dataclasses import dataclass
import re
from typing import Dict, List, Optional
from urllib.parse import urlparse

from app.providers.base import LLMProvider, LLMProviderError
from app.providers.gemini import GeminiProvider
from app.providers.openai_compat import OpenAICompatProvider
from app.schemas.settings import ProviderInfo

# Safe model name validation regex: alphanumeric, underscores, hyphens, periods, colons, slashes, up to 64 chars
SAFE_MODEL_REGEX = re.compile(r"^[a-zA-Z0-9_\-.:/]{1,64}$")


@dataclass(frozen=True)
class ProviderDescriptor:
    id: str
    name: str
    adapter: str  # "openai_compat" or "gemini"
    default_base_url: str
    default_model: str
    available_models: List[str]
    requires_key: bool = True
    allows_custom_url: bool = False


# Declarative registry: Adding a provider = one registry entry
PROVIDER_REGISTRY: Dict[str, ProviderDescriptor] = {
    "gemini": ProviderDescriptor(
        id="gemini",
        name="Google Gemini",
        adapter="gemini",
        default_base_url="https://generativelanguage.googleapis.com/v1beta",
        default_model="gemini-1.5-flash",
        available_models=["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash"],
        requires_key=True,
        allows_custom_url=False,
    ),
    "groq": ProviderDescriptor(
        id="groq",
        name="Groq",
        adapter="openai_compat",
        default_base_url="https://api.groq.com/openai/v1",
        default_model="llama-3.3-70b-versatile",
        available_models=[
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768",
        ],
        requires_key=True,
        allows_custom_url=False,
    ),
    "openrouter": ProviderDescriptor(
        id="openrouter",
        name="OpenRouter",
        adapter="openai_compat",
        default_base_url="https://openrouter.ai/api/v1",
        default_model="meta-llama/llama-3.3-70b-instruct",
        available_models=[
            "meta-llama/llama-3.3-70b-instruct",
            "google/gemini-2.0-flash-exp:free",
            "mistralai/mistral-7b-instruct:free",
            "anthropic/claude-3.5-haiku",
        ],
        requires_key=True,
        allows_custom_url=False,
    ),
    "nvidia": ProviderDescriptor(
        id="nvidia",
        name="NVIDIA NIM",
        adapter="openai_compat",
        default_base_url="https://integrate.api.nvidia.com/v1",
        default_model="meta/llama-3.1-70b-instruct",
        available_models=[
            "meta/llama-3.1-70b-instruct",
            "mistralai/mixtral-8x7b-instruct-v0.1",
            "nvidia/llama-3.1-nemotron-70b-instruct",
        ],
        requires_key=True,
        allows_custom_url=False,
    ),
    "cerebras": ProviderDescriptor(
        id="cerebras",
        name="Cerebras",
        adapter="openai_compat",
        default_base_url="https://api.cerebras.ai/v1",
        default_model="llama3.3-70b",
        available_models=["llama3.3-70b", "llama3.1-8b"],
        requires_key=True,
        allows_custom_url=False,
    ),
    "mistral": ProviderDescriptor(
        id="mistral",
        name="Mistral AI",
        adapter="openai_compat",
        default_base_url="https://api.mistral.ai/v1",
        default_model="mistral-small-latest",
        available_models=["mistral-small-latest", "mistral-large-latest", "open-mistral-7b"],
        requires_key=True,
        allows_custom_url=False,
    ),
    "ollama": ProviderDescriptor(
        id="ollama",
        name="Ollama (Local)",
        adapter="openai_compat",
        default_base_url="http://localhost:11434/v1",
        default_model="llama3.2",
        available_models=["llama3.2", "mistral", "qwen2.5", "llama3.1"],
        requires_key=False,
        allows_custom_url=True,
    ),
}


def validate_model_name(model: str) -> str:
    """Enforces strict regex safety on model names."""
    if not model or not isinstance(model, str):
        raise LLMProviderError("Model name cannot be empty.", status_code=400)
    cleaned = model.strip()
    if not SAFE_MODEL_REGEX.match(cleaned):
        raise LLMProviderError(
            f"Invalid model name '{cleaned}'. Must match pattern: ^[a-zA-Z0-9_\\-.:/]{{1,64}}$",
            status_code=400,
        )
    return cleaned


def validate_custom_url(provider_id: str, custom_url: Optional[str]) -> Optional[str]:
    """
    Validates custom base URLs.
    Custom URLs are strictly permitted ONLY for Ollama pointing to localhost or host.docker.internal.
    """
    if not custom_url:
        return None

    cleaned = custom_url.strip().rstrip("/")
    if provider_id != "ollama":
        raise LLMProviderError(
            f"Custom base URLs are not allowed for provider '{provider_id}'. Only 'ollama' supports custom URLs.",
            status_code=400,
        )

    parsed = urlparse(cleaned)
    if parsed.scheme not in ("http", "https"):
        raise LLMProviderError(
            "Custom URL must use http or https scheme.",
            status_code=400,
        )

    hostname = (parsed.hostname or "").lower()
    allowed_hosts = {"localhost", "127.0.0.1", "host.docker.internal"}
    if hostname not in allowed_hosts:
        raise LLMProviderError(
            f"Custom Ollama URL host '{hostname}' is not permitted. Only localhost, 127.0.0.1, or host.docker.internal are allowed.",
            status_code=400,
        )

    return cleaned


class ProviderRegistry:
    @staticmethod
    def list_providers() -> List[ProviderInfo]:
        """Returns metadata for all supported providers."""
        return [
            ProviderInfo(
                id=desc.id,
                name=desc.name,
                default_model=desc.default_model,
                available_models=desc.available_models,
                requires_key=desc.requires_key,
                allows_custom_url=desc.allows_custom_url,
                default_base_url=desc.default_base_url,
            )
            for desc in PROVIDER_REGISTRY.values()
        ]

    @staticmethod
    def get_descriptor(provider_id: str) -> ProviderDescriptor:
        provider_key = provider_id.lower().strip()
        if provider_key not in PROVIDER_REGISTRY:
            supported = ", ".join(PROVIDER_REGISTRY.keys())
            raise LLMProviderError(
                f"Unsupported provider '{provider_id}'. Supported providers are: {supported}",
                status_code=400,
            )
        return PROVIDER_REGISTRY[provider_key]


def get_provider(
    provider_id: str,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    custom_url: Optional[str] = None,
) -> LLMProvider:
    """
    Factory creating a configured LLMProvider instance.
    Validates model name and base URL safety.
    """
    desc = ProviderRegistry.get_descriptor(provider_id)
    
    # Validate and choose model
    selected_model = validate_model_name(model or desc.default_model)

    # Validate and choose base_url
    if custom_url:
        selected_url = validate_custom_url(desc.id, custom_url) or desc.default_base_url
    else:
        selected_url = desc.default_base_url

    # Check key requirement
    clean_key = (api_key or "").strip()
    if desc.requires_key and not clean_key:
        raise LLMProviderError(
            f"Provider '{desc.name}' requires an API key. Please supply your key via X-LLM-Key header.",
            status_code=401,
        )

    if desc.adapter == "gemini":
        return GeminiProvider(
            name=desc.name,
            api_key=clean_key,
            base_url=selected_url,
            model=selected_model,
        )
    else:
        return OpenAICompatProvider(
            name=desc.name,
            api_key=clean_key,
            base_url=selected_url,
            model=selected_model,
        )
