"""
Google Gemini API Provider.
Strictly sends API Key via 'x-goog-api-key' header, never in URL parameters.
"""
import time
from typing import Any, Dict, Optional
import httpx

from app.providers.base import LLMProvider, LLMProviderError


class GeminiProvider(LLMProvider):
    """
    Adapter for Google Gemini REST API.
    """

    def __init__(
        self,
        name: str = "gemini",
        api_key: Optional[str] = None,
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        model: str = "gemini-1.5-flash",
        timeout: float = 30.0,
    ):
        super().__init__(name=name, api_key=api_key, base_url=base_url, model=model, timeout=timeout)

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "ThankMeLater/0.1.0",
        }
        if self.api_key:
            headers["x-goog-api-key"] = self.api_key.strip()
        return headers

    async def _raw_completion(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        # Note: Model name is in the path, NEVER the API key in the URL
        url = f"{self.base_url}/models/{self.model}:generateContent"

        payload: Dict[str, Any] = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json",
            },
        }

        if system_prompt:
            payload["systemInstruction"] = {
                "parts": [{"text": system_prompt}],
            }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(url, json=payload, headers=self._get_headers())
                response.raise_for_status()
                data = response.json()
                
                candidates = data.get("candidates", [])
                if not candidates:
                    raise LLMProviderError(
                        message=f"No candidates returned by Gemini ({self.model}).",
                        status_code=502,
                    )
                
                parts = candidates[0].get("content", {}).get("parts", [])
                if not parts:
                    raise LLMProviderError(
                        message=f"No text parts returned in candidate by Gemini ({self.model}).",
                        status_code=502,
                    )
                return parts[0].get("text", "")
            except Exception as e:
                raise self._normalize_error(e)

    async def test_connection(self) -> Dict[str, Any]:
        """Verify Gemini API key via generateContent ping."""
        url = f"{self.base_url}/models/{self.model}:generateContent"
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": "respond with 'pong' only"}],
                }
            ],
            "generationConfig": {
                "maxOutputTokens": 10,
            },
        }

        start = time.perf_counter()
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                response = await client.post(url, json=payload, headers=self._get_headers())
                response.raise_for_status()
                elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
                return {
                    "success": True,
                    "message": f"Successfully connected to Google Gemini ({self.model}).",
                    "model": self.model,
                    "latency_ms": elapsed_ms,
                }
            except Exception as e:
                raise self._normalize_error(e)
