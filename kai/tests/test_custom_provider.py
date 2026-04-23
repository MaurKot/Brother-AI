"""Tests for CustomLLMProvider."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

from ..llm.custom_provider import CustomLLMProvider


def test_complete_without_token():
    with patch("kai.config.HF_TOKEN", ""):
        provider = CustomLLMProvider()
        result = asyncio.run(provider.complete("test prompt"))
        assert result == "HF_TOKEN not set"


def test_complete_with_mock_response():
    with patch("kai.config.HF_TOKEN", "fake_token"), patch(
        "kai.config.HF_MODEL_NORMAL", "test/model"
    ):
        provider = CustomLLMProvider()
        provider._client = Mock(return_value=Mock())
        provider._generate = Mock(return_value="generated response")

        result = asyncio.run(provider.complete("test prompt"))

        assert result == "generated response"
        provider._client.assert_called_once_with("test/model")


def test_complete_fallback_on_error():
    with patch("kai.config.HF_TOKEN", "fake_token"):
        provider = CustomLLMProvider()
        provider._client = Mock(side_effect=RuntimeError("boom"))

        result = asyncio.run(provider.complete("test prompt"))

        assert result == provider.FALLBACK_REPLY


def test_remaining():
    provider = CustomLLMProvider()
    provider.daily_budget = 10.0
    provider.spent_today = 3.0
    assert provider.remaining() == 7.0


def test_aclose():
    provider = CustomLLMProvider()
    asyncio.run(provider.aclose())
