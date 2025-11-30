"""Tests for agent_tools.py."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from greenroom.tools.agent_tools import (
    compare_llms,
    _call_claude,
    _call_ollama,
    _format_response,
)


@pytest.mark.asyncio
@patch("greenroom.tools.agent_tools.httpx.AsyncClient")
async def test_compare_llms_both_succeed(mock_async_client_class):
    """Test that compare_llms correctly calls both LLMs and formats responses."""
    # Setup mock Claude response
    mock_ctx = MagicMock()
    mock_claude_response = MagicMock()
    mock_claude_response.text = "Claude says: The sky is blue due to Rayleigh scattering."
    mock_ctx.sample = AsyncMock(return_value=mock_claude_response)

    # Setup mock Ollama response
    mock_client = MagicMock()
    mock_ollama_response = MagicMock()
    mock_ollama_response.json.return_value = {
        "response": "Ollama says: Light scattering causes the blue sky.",
        "done": True
    }
    mock_ollama_response.raise_for_status = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_ollama_response)
    mock_async_client_class.return_value.__aenter__.return_value = mock_client

    # Call the function
    result = await compare_llms(
        ctx=mock_ctx,
        prompt="Why is the sky blue?",
        alternative_model="llama3.2:latest",
        temperature=0.7,
        max_tokens=100
    )

    # Verify structure
    assert "prompt" in result
    assert "claude_response" in result
    assert "alternative_response" in result
    assert "comparison" in result

    # Verify prompt
    assert result["prompt"] == "Why is the sky blue?"

    # Verify Claude response
    assert result["claude_response"]["text"] == "Claude says: The sky is blue due to Rayleigh scattering."
    assert result["claude_response"]["model"] == "claude-sonnet-4-5"
    assert result["claude_response"]["error"] is None

    # Verify alternative response
    assert result["alternative_response"]["text"] == "Ollama says: Light scattering causes the blue sky."
    assert result["alternative_response"]["model"] == "llama3.2:latest"
    assert result["alternative_response"]["error"] is None

    # Verify comparison
    assert result["comparison"]["claude_length"] == len("Claude says: The sky is blue due to Rayleigh scattering.")
    assert result["comparison"]["alternative_length"] == len("Ollama says: Light scattering causes the blue sky.")
    assert result["comparison"]["both_succeeded"] is True

    # Verify Claude was called with correct parameters
    mock_ctx.sample.assert_called_once_with(
        messages="Why is the sky blue?",
        temperature=0.7,
        max_tokens=100
    )

    # Verify Ollama was called with correct parameters
    mock_client.post.assert_called_once()
    call_args = mock_client.post.call_args
    assert "http://localhost:11434/api/generate" in call_args[0][0]
    assert call_args[1]["json"]["model"] == "llama3.2:latest"
    assert call_args[1]["json"]["prompt"] == "Why is the sky blue?"
    assert call_args[1]["json"]["options"]["temperature"] == 0.7
    assert call_args[1]["json"]["options"]["num_predict"] == 100


@pytest.mark.asyncio
@patch("greenroom.tools.agent_tools.httpx.AsyncClient")
async def test_compare_llms_claude_fails_ollama_succeeds(mock_async_client_class):
    """Test graceful degradation when Claude fails but Ollama succeeds."""
    # Setup mock Claude to fail
    mock_ctx = MagicMock()
    mock_ctx.sample = AsyncMock(side_effect=RuntimeError("Claude API error"))

    # Setup mock Ollama to succeed
    mock_client = MagicMock()
    mock_ollama_response = MagicMock()
    mock_ollama_response.json.return_value = {"response": "Ollama response"}
    mock_ollama_response.raise_for_status = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_ollama_response)
    mock_async_client_class.return_value.__aenter__.return_value = mock_client

    # Call the function
    result = await compare_llms(mock_ctx, "Test prompt")

    # Verify Claude error is captured
    assert result["claude_response"]["text"] is None
    assert result["claude_response"]["error"] is not None
    assert "Claude API error" in result["claude_response"]["error"]

    # Verify Ollama succeeded
    assert result["alternative_response"]["text"] == "Ollama response"
    assert result["alternative_response"]["error"] is None

    # Verify comparison shows failure
    assert result["comparison"]["both_succeeded"] is False


@pytest.mark.asyncio
@patch("greenroom.tools.agent_tools.httpx.AsyncClient")
async def test_compare_llms_ollama_fails_claude_succeeds(mock_async_client_class):
    """Test graceful degradation when Ollama fails but Claude succeeds."""
    # Setup mock Claude to succeed
    mock_ctx = MagicMock()
    mock_claude_response = MagicMock()
    mock_claude_response.text = "Claude response"
    mock_ctx.sample = AsyncMock(return_value=mock_claude_response)

    # Setup mock Ollama to fail
    mock_client = MagicMock()
    mock_error_response = MagicMock()
    mock_error_response.status_code = 500
    mock_error_response.text = "Internal server error"
    mock_client.post = AsyncMock(
        side_effect=httpx.HTTPStatusError("500 Error", request=MagicMock(), response=mock_error_response)
    )
    mock_async_client_class.return_value.__aenter__.return_value = mock_client

    # Call the function
    result = await compare_llms(mock_ctx, "Test prompt")

    # Verify Claude succeeded
    assert result["claude_response"]["text"] == "Claude response"
    assert result["claude_response"]["error"] is None

    # Verify Ollama error is captured
    assert result["alternative_response"]["text"] is None
    assert result["alternative_response"]["error"] is not None
    assert "Ollama API error" in result["alternative_response"]["error"]

    # Verify comparison shows failure
    assert result["comparison"]["both_succeeded"] is False


@pytest.mark.asyncio
@patch("greenroom.tools.agent_tools.httpx.AsyncClient")
async def test_compare_llms_both_fail(mock_async_client_class):
    """Test that both errors are captured when both LLMs fail."""
    # Setup mock Claude to fail
    mock_ctx = MagicMock()
    mock_ctx.sample = AsyncMock(side_effect=RuntimeError("Claude error"))

    # Setup mock Ollama to fail
    mock_client = MagicMock()
    mock_client.post = AsyncMock(side_effect=ConnectionError("Ollama connection error"))
    mock_async_client_class.return_value.__aenter__.return_value = mock_client

    # Call the function
    result = await compare_llms(mock_ctx, "Test prompt")

    # Verify both errors are captured
    assert result["claude_response"]["text"] is None
    assert result["claude_response"]["error"] is not None
    assert "Claude error" in result["claude_response"]["error"]

    assert result["alternative_response"]["text"] is None
    assert result["alternative_response"]["error"] is not None

    # Verify comparison shows both failed
    assert result["comparison"]["both_succeeded"] is False


@pytest.mark.asyncio
@patch("greenroom.tools.agent_tools.httpx.AsyncClient")
async def test_compare_llms_uses_default_model(mock_async_client_class):
    """Test that default model is used when alternative_model is not specified."""
    # Setup mocks
    mock_ctx = MagicMock()
    mock_claude_response = MagicMock()
    mock_claude_response.text = "Claude response"
    mock_ctx.sample = AsyncMock(return_value=mock_claude_response)

    mock_client = MagicMock()
    mock_ollama_response = MagicMock()
    mock_ollama_response.json.return_value = {"response": "Ollama response"}
    mock_ollama_response.raise_for_status = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_ollama_response)
    mock_async_client_class.return_value.__aenter__.return_value = mock_client

    # Call without specifying model
    result = await compare_llms(mock_ctx, "Test prompt")

    # Verify default model was used
    assert result["alternative_response"]["model"] == "llama3.2:latest"

    # Verify Ollama was called with default model
    call_args = mock_client.post.call_args
    assert call_args[1]["json"]["model"] == "llama3.2:latest"


@pytest.mark.asyncio
async def test_compare_llms_validates_empty_prompt():
    """Test that empty prompt raises ValueError."""
    mock_ctx = MagicMock()

    with pytest.raises(ValueError, match="Prompt cannot be empty"):
        await compare_llms(mock_ctx, "")

    with pytest.raises(ValueError, match="Prompt cannot be empty"):
        await compare_llms(mock_ctx, "   ")


@pytest.mark.asyncio
async def test_compare_llms_validates_temperature():
    """Test that invalid temperature raises ValueError."""
    mock_ctx = MagicMock()

    with pytest.raises(ValueError, match="Temperature must be between 0 and 2"):
        await compare_llms(mock_ctx, "Test", temperature=-0.1)

    with pytest.raises(ValueError, match="Temperature must be between 0 and 2"):
        await compare_llms(mock_ctx, "Test", temperature=2.1)


@pytest.mark.asyncio
async def test_compare_llms_validates_max_tokens():
    """Test that invalid max_tokens raises ValueError."""
    mock_ctx = MagicMock()

    with pytest.raises(ValueError, match="Max tokens must be between 1 and 4000"):
        await compare_llms(mock_ctx, "Test", max_tokens=0)

    with pytest.raises(ValueError, match="Max tokens must be between 1 and 4000"):
        await compare_llms(mock_ctx, "Test", max_tokens=4001)


@pytest.mark.asyncio
async def test_call_claude_success():
    """Test _call_claude successfully calls ctx.sample."""
    mock_ctx = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Claude's response"
    mock_ctx.sample = AsyncMock(return_value=mock_response)

    result = await _call_claude(mock_ctx, "Test prompt", 0.5, 200)

    assert result == "Claude's response"
    mock_ctx.sample.assert_called_once_with(
        messages="Test prompt",
        temperature=0.5,
        max_tokens=200
    )


@pytest.mark.asyncio
async def test_call_claude_handles_errors():
    """Test _call_claude wraps errors in RuntimeError."""
    mock_ctx = MagicMock()
    mock_ctx.sample = AsyncMock(side_effect=Exception("Sample failed"))

    with pytest.raises(RuntimeError, match="Claude API error: Sample failed"):
        await _call_claude(mock_ctx, "Test", 0.7, 100)


@pytest.mark.asyncio
@patch("greenroom.tools.agent_tools.httpx.AsyncClient")
async def test_call_ollama_success(mock_async_client_class):
    """Test _call_ollama successfully calls Ollama API."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {"response": "Ollama's response", "done": True}
    mock_response.raise_for_status = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_async_client_class.return_value.__aenter__.return_value = mock_client

    result = await _call_ollama("Test prompt", "llama3.2:latest", 0.5, 200)

    assert result == "Ollama's response"

    # Verify API call
    mock_client.post.assert_called_once()
    call_args = mock_client.post.call_args
    assert call_args[1]["json"]["model"] == "llama3.2:latest"
    assert call_args[1]["json"]["prompt"] == "Test prompt"
    assert call_args[1]["json"]["stream"] is False
    assert call_args[1]["json"]["options"]["temperature"] == 0.5
    assert call_args[1]["json"]["options"]["num_predict"] == 200


@pytest.mark.asyncio
@patch("greenroom.tools.agent_tools.httpx.AsyncClient")
async def test_call_ollama_handles_http_errors(mock_async_client_class):
    """Test _call_ollama handles HTTP status errors."""
    mock_client = MagicMock()
    mock_error_response = MagicMock()
    mock_error_response.status_code = 404
    mock_error_response.text = "Model not found"
    mock_client.post = AsyncMock(
        side_effect=httpx.HTTPStatusError("404", request=MagicMock(), response=mock_error_response)
    )
    mock_async_client_class.return_value.__aenter__.return_value = mock_client

    with pytest.raises(RuntimeError, match="Ollama API error: 404 - Model not found"):
        await _call_ollama("Test", "unknown-model", 0.7, 100)


@pytest.mark.asyncio
@patch("greenroom.tools.agent_tools.httpx.AsyncClient")
async def test_call_ollama_handles_connection_errors(mock_async_client_class):
    """Test _call_ollama handles connection errors."""
    mock_client = MagicMock()
    mock_client.post = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
    mock_async_client_class.return_value.__aenter__.return_value = mock_client

    with pytest.raises(ConnectionError, match="Failed to connect to Ollama API"):
        await _call_ollama("Test", "llama3.2:latest", 0.7, 100)


@pytest.mark.asyncio
@patch("greenroom.tools.agent_tools.httpx.AsyncClient")
@patch.dict("os.environ", {"OLLAMA_BASE_URL": "http://custom:8080"})
async def test_call_ollama_uses_env_var(mock_async_client_class):
    """Test _call_ollama uses OLLAMA_BASE_URL from environment."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {"response": "Response"}
    mock_response.raise_for_status = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_async_client_class.return_value.__aenter__.return_value = mock_client

    await _call_ollama("Test", "llama3.2:latest", 0.7, 100)

    # Verify custom URL was used
    call_args = mock_client.post.call_args
    assert "http://custom:8080/api/generate" in call_args[0][0]


def test_format_response_with_success():
    """Test _format_response formats successful response."""
    result = _format_response("Test response text", "test-model")

    assert result["text"] == "Test response text"
    assert result["model"] == "test-model"
    assert result["error"] is None


def test_format_response_with_exception():
    """Test _format_response formats exception."""
    error = RuntimeError("Test error message")
    result = _format_response(error, "test-model")

    assert result["text"] is None
    assert result["model"] == "test-model"
    assert result["error"] == "Test error message"


def test_format_response_with_different_exception_types():
    """Test _format_response handles different exception types."""
    # ConnectionError
    error1 = ConnectionError("Connection failed")
    result1 = _format_response(error1, "model1")
    assert "Connection failed" in result1["error"]

    # ValueError
    error2 = ValueError("Invalid value")
    result2 = _format_response(error2, "model2")
    assert "Invalid value" in result2["error"]

    # Generic Exception
    error3 = Exception("Generic error")
    result3 = _format_response(error3, "model3")
    assert "Generic error" in result3["error"]
