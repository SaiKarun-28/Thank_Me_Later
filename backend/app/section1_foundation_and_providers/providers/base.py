"""
Abstract Base Class for LLM Providers.
"""
from abc import ABC, abstractmethod
import asyncio
import json
import logging
import re
from typing import Any, Dict, Optional

from app.section1_foundation_and_providers.security.security import redact_text

logger = logging.getLogger(__name__)


class LLMProviderError(Exception):
    """Normalized provider exception with friendly user-facing messages and status codes."""
    def __init__(self, message: str, status_code: int = 500, raw_error: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.raw_error = raw_error


def extract_json_object(raw_text: str) -> Dict[str, Any]:
    """
    Extracts a JSON object from text that may contain markdown code fences,
    preceding conversational chatter, or trailing content.
    """
    cleaned = raw_text.strip()
    
    # Strip markdown ```json ... ``` code blocks if present
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned).strip()

    # Direct JSON parse attempt
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    # Regex search for first outer {...} bracket pair
    match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group(1))
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not parse valid JSON object from LLM response: {raw_text[:200]}...")


class LLMProvider(ABC):
    """
    Base contract for all BYOK LLM Provider integrations.
    """
    def __init__(
        self,
        name: str,
        api_key: Optional[str],
        base_url: str,
        model: str,
        timeout: float = 30.0,
    ):
        self.name = name
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    @abstractmethod
    async def test_connection(self) -> Dict[str, Any]:
        """
        Validates connectivity and credentials with a minimal ping prompt.
        Returns a dict: {"success": bool, "message": str, "model": str, "latency_ms": float}.
        """
        pass

    @abstractmethod
    async def _raw_completion(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Execute raw model completion."""
        pass

    async def json_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_retries: int = 1,
    ) -> Dict[str, Any]:
        """
        Executes completion and parses JSON output.
        Automatically retries once on JSON decode errors with an explicit correction hint.
        """
        current_prompt = prompt
        last_error: Optional[Exception] = None

        for attempt in range(max_retries + 1):
            try:
                raw_response = await self._raw_completion(current_prompt, system_prompt=system_prompt)
                return extract_json_object(raw_response)
            except (ValueError, json.JSONDecodeError) as e:
                last_error = e
                if attempt < max_retries:
                    logger.warning(
                        "LLM returned invalid JSON on attempt %d for provider %s. Retrying with format reminder.",
                        attempt + 1,
                        self.name,
                    )
                    await asyncio.sleep(1.0)
                    current_prompt = (
                        f"{prompt}\n\nIMPORTANT: Your previous response was not valid JSON. "
                        f"Respond strictly with a valid JSON object only. No markdown formatting, no explanation."
                    )
                else:
                    raise LLMProviderError(
                        message=f"Model {self.model} returned invalid JSON format after {max_retries + 1} attempts.",
                        status_code=502,
                        raw_error=str(last_error),
                    )
            except LLMProviderError:
                raise
            except Exception as e:
                raise self._normalize_error(e)

        raise LLMProviderError(
            message=f"Failed to generate valid JSON from model {self.model}.",
            status_code=502,
            raw_error=str(last_error),
        )

    def _normalize_error(self, exc: Exception) -> LLMProviderError:
        """Normalizes upstream HTTP and connection errors into friendly messages."""
        import httpx

        if isinstance(exc, LLMProviderError):
            return exc

        if isinstance(exc, httpx.HTTPStatusError):
            code = exc.response.status_code
            safe_text = redact_text(exc.response.text)
            if code == 401 or code == 403:
                return LLMProviderError(
                    message=f"Authentication failed: The provided API key is invalid or unauthorized for provider '{self.name}'.",
                    status_code=401,
                    raw_error=safe_text,
                )
            if code == 429:
                return LLMProviderError(
                    message=f"Rate limit or quota exceeded for provider '{self.name}'. Please check your plan or try again shortly.",
                    status_code=429,
                    raw_error=safe_text,
                )
            if code == 404:
                return LLMProviderError(
                    message=f"Model '{self.model}' not found on provider '{self.name}'. Please verify the model name.",
                    status_code=404,
                    raw_error=safe_text,
                )
            return LLMProviderError(
                message=redact_text(f"Provider '{self.name}' returned HTTP {code}: {exc.response.text[:200]}"),
                status_code=code,
                raw_error=safe_text,
            )

        if isinstance(exc, (httpx.TimeoutException, asyncio.TimeoutError)):
            return LLMProviderError(
                message=f"Request to provider '{self.name}' timed out after {self.timeout}s.",
                status_code=504,
                raw_error=redact_text(str(exc)),
            )

        if isinstance(exc, httpx.RequestError):
            return LLMProviderError(
                message=f"Could not connect to provider '{self.name}' at {self.base_url}. Please check the URL or host.",
                status_code=502,
                raw_error=redact_text(str(exc)),
            )

        safe_exc_str = redact_text(str(exc))
        return LLMProviderError(
            message=f"Unexpected error communicating with provider '{self.name}': {safe_exc_str}",
            status_code=500,
            raw_error=safe_exc_str,
        )
