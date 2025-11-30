"""Agent comparison tools for the greenroom MCP server."""

import asyncio
import os
from typing import Dict, Any, Optional

import httpx
from fastmcp import FastMCP, Context

from greenroom.config import OLLAMA_BASE_URL, OLLAMA_DEFAULT_MODEL, OLLAMA_TIMEOUT


def register_agent_tools(mcp: FastMCP) -> None:
    """Register agent comparison tools with the MCP server."""

    @mcp.tool()
    async def compare_llm_responses(
        ctx: Context,
        prompt: str,
        llm_model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 500
    ) -> Dict[str, Any]:
        """
        Compare how Claude and a second agent (defaults to Ollama) respond to the same prompt.

        Sends the same prompt to both Claude (via ctx.sample) and the second agent in parallel,
        returning a structured comparison of their responses.

        Args:
            prompt: The prompt to send to both LLMs
            llm_model: Which second model to use (default: llama3.2:latest)
            temperature: Temperature for both LLMs (default: 0.7)
            max_tokens: Maximum tokens for responses (default: 500)

        Returns:
            Dictionary containing:
            {
                "prompt": "original prompt text",
                "claude_response": {
                    "text": "Claude's response...",
                    "model": "claude-sonnet-4-5",
                    "error": None
                },
                "alternative_response": {
                    "text": "Ollama's response...",
                    "model": "llama3.2:latest",
                    "error": None
                },
                "comparison": {
                    "claude_length": 150,
                    "alternative_length": 142,
                    "both_succeeded": true
                }
            }

        Raises:
            ValueError: If prompt is empty or invalid parameters provided
        """
        # Delegate to helper function to enable unit testing without FastMCP server setup
        return await compare_llms(ctx, prompt, llm_model, temperature, max_tokens)


async def compare_llms(
    ctx: Context,
    prompt: str,
    alternative_model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 500
) -> Dict[str, Any]:
    """
    Encapsulates the LLM comparison logic.
    See compare_llm_responses() for detailed documentation.
    The current state of this method is hard-coded to compare Claude and Ollama.
    """
    # Validate inputs
    if not prompt or not prompt.strip():
        raise ValueError("Prompt cannot be empty")

    if temperature < 0 or temperature > 2:
        raise ValueError("Temperature must be between 0 and 2")

    if max_tokens < 1 or max_tokens > 4000:
        raise ValueError("Max tokens must be between 1 and 4000")

    # Use default model if not specified
    model = alternative_model or OLLAMA_DEFAULT_MODEL

    # Call both LLMs in parallel
    claude_result, alternative_result = await asyncio.gather(
        _call_claude(ctx, prompt, temperature, max_tokens),
        _call_ollama(prompt, model, temperature, max_tokens),
        return_exceptions=True
    )

    # Format responses
    claude_response = _format_response(claude_result, "claude-sonnet-4-5")
    alternative_response = _format_response(alternative_result, model)

    # Build comparison
    both_succeeded = (
        claude_response["error"] is None and
        alternative_response["error"] is None
    )

    return {
        "prompt": prompt,
        "claude_response": claude_response,
        "alternative_response": alternative_response,
        "comparison": {
            "claude_length": len(claude_response["text"]) if claude_response["text"] else 0,
            "alternative_length": len(alternative_response["text"]) if alternative_response["text"] else 0,
            "both_succeeded": both_succeeded
        }
    }


async def _call_claude(
    ctx: Context,
    prompt: str,
    temperature: float,
    max_tokens: int
) -> str:
    """
    Call Claude via ctx.sample().

    Args:
        ctx: FastMCP context for LLM sampling
        prompt: The prompt to send
        temperature: Temperature setting
        max_tokens: Maximum tokens to generate

    Returns:
        Claude's response text

    Raises:
        Exception: Any error from ctx.sample()
    """
    try:
        response = await ctx.sample(
            messages=prompt,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.text
    except Exception as e:
        # Re-raise to be caught by asyncio.gather
        raise RuntimeError(f"Claude API error: {str(e)}") from e


async def _call_ollama(
    prompt: str,
    model: str,
    temperature: float,
    max_tokens: int
) -> str:
    """
    Call Ollama via httpx.

    Args:
        prompt: The prompt to send
        model: Ollama model name
        temperature: Temperature setting
        max_tokens: Maximum tokens to generate

    Returns:
        Ollama's response text

    Raises:
        Exception: Any error from Ollama API
    """
    base_url = os.getenv("OLLAMA_BASE_URL", OLLAMA_BASE_URL)

    try:
        async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
            response = await client.post(
                f"{base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens
                    }
                }
            )
            response.raise_for_status()

            data = response.json()
            return data.get("response", "")

    except httpx.HTTPStatusError as e:
        raise RuntimeError(
            f"Ollama API error: {e.response.status_code} - {e.response.text}"
        ) from e
    except httpx.RequestError as e:
        raise ConnectionError(
            f"Failed to connect to Ollama API at {base_url}. "
            f"Is the Ollama server running? Error: {str(e)}"
        ) from e
    except Exception as e:
        raise RuntimeError(f"Ollama error: {str(e)}") from e


def _format_response(result: Any, model: str) -> Dict[str, Any]:
    """
    Format LLM response or error into structured output.

    Args:
        result: Either a string response or an exception
        model: The model name

    Returns:
        Formatted response dict with text, model, and error fields
    """
    if isinstance(result, Exception):
        return {
            "text": None,
            "model": model,
            "error": str(result)
        }
    else:
        return {
            "text": result,
            "model": model,
            "error": None
        }