"""Tests for CustomLLMProvider."""
import pytest
from unittest.mock import AsyncMock, patch

from ..llm.custom_provider import CustomLLMProvider


@pytest.mark.asyncio
async def test_complete_without_token():
    """Test that complete returns error without HF_TOKEN."""
    with patch('kai.config.HF_TOKEN', ''):
        provider = CustomLLMProvider()
        result = await provider.complete("test prompt")
        assert result == "HF_TOKEN not set"


@pytest.mark.asyncio
async def test_complete_with_mock_response():
    """Test complete with mocked HF API response."""
    with patch('kai.config.HF_TOKEN', 'fake_token'), \
         patch('kai.config.HF_MODEL_NORMAL', 'test/model'), \
         patch('aiohttp.ClientSession.post') as mock_post:

        # Mock response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = [{"generated_text": "test prompt generated response"}]
        mock_post.return_value.__aenter__.return_value = mock_response

        provider = CustomLLMProvider()
        result = await provider.complete("test prompt")

        assert "generated response" in result
        mock_post.assert_called_once()


@pytest.mark.asyncio
async def test_remaining():
    """Test remaining budget calculation."""
    provider = CustomLLMProvider()
    provider.daily_budget = 10.0
    provider.spent_today = 3.0
    assert provider.remaining() == 7.0


@pytest.mark.asyncio
async def test_aclose():
    """Test aclose method."""
    with patch('aiohttp.ClientSession') as mock_session:
        mock_session_instance = AsyncMock()
        mock_session_instance.closed = False
        mock_session.return_value = mock_session_instance

        provider = CustomLLMProvider()
        provider._session = mock_session_instance

        await provider.aclose()
        mock_session_instance.close.assert_awaited_once()