"""
OpenAI-Compatible Provider Implementation for Section 1.
Supports Groq, OpenRouter, NVIDIA NIM, Cerebras, Mistral, and local Ollama.
"""
import os
import time
from typing import Any, Dict, List, Optional
import httpx

from app.section1_foundation_and_providers.providers.base import LLMProvider, LLMProviderError


class OpenAICompatProvider(LLMProvider):
    """
    Adapter for any provider offering the standard /chat/completions endpoint.
    """

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "ThankMeLater/0.1.0",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key.strip()}"
        if "openrouter.ai" in self.base_url:
            headers["HTTP-Referer"] = os.getenv("FRONTEND_URL", "http://localhost:3000")
            headers["X-Title"] = "Thank Me Later"
        return headers

    async def _raw_completion(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        messages: List[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
        }

        # Attempt JSON mode if standard provider (Groq, OpenRouter, Mistral, Cerebras, etc.)
        if "ollama" not in self.name.lower():
            payload["response_format"] = {"type": "json_object"}

        url = f"{self.base_url}/chat/completions"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(url, json=payload, headers=self._get_headers())
                response.raise_for_status()
                data = response.json()
                choices = data.get("choices", [])
                if not choices:
                    raise LLMProviderError(
                        message=f"No completion choices returned by {self.name}.",
                        status_code=502,
                    )
                content = choices[0].get("message", {}).get("content", "")
                return content
            except Exception as e:
                raise self._normalize_error(e)

    async def test_connection(self) -> Dict[str, Any]:
        """Test API connectivity and key validity."""
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": "respond with 'pong' only"}],
            "max_tokens": 10,
        }

        start = time.perf_counter()
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                response = await client.post(url, json=payload, headers=self._get_headers())
                response.raise_for_status()
                elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
                return {
                    "success": True,
                    "message": f"Successfully connected to {self.name} ({self.model}).",
                    "model": self.model,
                    "latency_ms": elapsed_ms,
                }
            except Exception as e:
                raise self._normalize_error(e)
