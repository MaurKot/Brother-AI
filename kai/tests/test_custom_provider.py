"""Tests for CustomLLMProvider."""
codex/analyze-and-fix-errors-tcgfls


main
import asyncio
from unittest.mock import AsyncMock, Mock, patch

from ..llm.custom_provider import CustomLLMProvider


def test_complete_without_token():
codex/analyze-and-fix-errors-tcgfls
    with patch("kai.config.HF_TOKEN", ""):

    """Test that complete returns error without HF_TOKEN."""
    with patch('kai.config.HF_TOKEN', ''):
main
        provider = CustomLLMProvider()
        result = asyncio.run(provider.complete("test prompt"))
        assert result == "HF_TOKEN not set"


def test_complete_with_mock_response():
codex/analyze-and-fix-errors-tcgfls
    with patch("kai.config.HF_TOKEN", "fake_token"), patch(
        "kai.config.HF_MODEL_NORMAL", "test/model"
    ):
        provider = CustomLLMProvider()
        provider._client = Mock(return_value=Mock())
        provider._generate = Mock(return_value="generated response")

        result = asyncio.run(provider.complete("test prompt"))

        assert result == "generated response"
        provider._client.assert_called_once_with("test/model")

    """Test complete with mocked HF API response."""
    with patch('kai.config.HF_TOKEN', 'fake_token'), \
         patch('kai.config.HF_MODEL_NORMAL', 'test/model'):

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = [{"generated_text": "test prompt generated response"}]

        mock_post_cm = AsyncMock()
        mock_post_cm.__aenter__.return_value = mock_response

        mock_session = Mock()
        mock_session.post.return_value = mock_post_cm
 main


def test_complete_fallback_on_error():
    with patch("kai.config.HF_TOKEN", "fake_token"):
        provider = CustomLLMProvider()
codex/analyze-and-fix-errors-tcgfls
        provider._client = Mock(side_effect=RuntimeError("boom"))

        result = asyncio.run(provider.complete("test prompt"))

        assert result == provider.FALLBACK_REPLY


def test_remaining():

        provider._session_get = AsyncMock(return_value=mock_session)

        result = asyncio.run(provider.complete("test prompt"))

        assert "generated response" in result
        mock_session.post.assert_called_once()


def test_remaining():
    """Test remaining budget calculation."""
main
    provider = CustomLLMProvider()
    provider.daily_budget = 10.0
    provider.spent_today = 3.0
    assert provider.remaining() == 7.0


def test_aclose():
 codex/analyze-and-fix-errors-tcgfls
    provider = CustomLLMProvider()
    asyncio.run(provider.aclose())

    """Test aclose method."""
    mock_session_instance = AsyncMock()
    mock_session_instance.closed = False

    provider = CustomLLMProvider()
    provider._session = mock_session_instance

    asyncio.run(provider.aclose())
    mock_session_instance.close.assert_awaited_once()
main
