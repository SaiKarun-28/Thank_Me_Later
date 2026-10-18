"""
Pytest configuration, shared fixtures, and mocked providers.
"""
import pytest
from typing import AsyncGenerator
import httpx
from fastapi.testclient import TestClient

from app.main import app
from app.providers.base import LLMProvider


class MockLLMProvider(LLMProvider):
    """Predictable mock provider for deterministic testing."""
    def __init__(
        self,
        name: str = "mock",
        api_key: str = "mock-key",
        base_url: str = "http://localhost:8000",
        model: str = "mock-model",
        mock_response: str = '{"status": "ok"}',
    ):
        super().__init__(name=name, api_key=api_key, base_url=base_url, model=model)
        self.mock_response = mock_response
        self.call_count = 0

    async def test_connection(self):
        return {
            "success": True,
            "message": "Connected to mock provider",
            "model": self.model,
            "latency_ms": 12.5,
        }

    async def _raw_completion(self, prompt: str, system_prompt: str = None) -> str:
        self.call_count += 1
        return self.mock_response


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def sentinel_key():
    """Sentinel key for security redaction tests."""
    return "SENTINEL-KEY-987654321-ALPHA"
