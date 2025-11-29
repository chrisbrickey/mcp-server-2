"""Genre operations tools for the greenroom MCP server."""

from typing import Dict, List, Any

from fastmcp import FastMCP, Context

from greenroom.config import Mood, GENRE_MOOD_MAP
from greenroom.utils import create_empty_categorized_dict
from greenroom.tools.fetching_tools import fetch_genres


def register_operations_tools(mcp: FastMCP) -> None:
    """Register genre operations tools with the MCP server."""

    @mcp.tool()
    async def list_genres_simplified(ctx: Context) -> str:
        """
        Get a simplified list of available genre names.

        Uses LLM sampling to extract just the genre names from the full genre data,
        returning a clean, formatted list without IDs or media type flags.
        Falls back to direct extraction if sampling is not supported.

        Returns:
            A formatted string containing the sorted list of genre names.

        Raises:
            Sampling errors are logged and result in fallback to direct key extraction.
        """
        # Delegate to helper function to enable unit testing without FastMCP server setup
        return await simplify_genres(ctx)

    @mcp.tool()
    async def categorize_genres(ctx: Context) -> Dict[str, List[str]]:
        """
        Categorize all available genres by mood/tone.

        Groups entertainment genres into mood categories (Dark, Light, Serious, Fun)
        using a hybrid approach: hardcoded mappings for common genres with LLM-based
        categorization for edge cases and unknown genres.

        Returns:
            Dictionary mapping mood categories to lists of genre names:
            {
                "Dark": ["Horror", "Thriller", "Crime", "Mystery"],
                "Light": ["Comedy", "Family", "Kids", "Animation", "Romance"],
                "Serious": ["Documentary", "History", "War", "Drama"],
                "Fun": ["Action", "Adventure", "Fantasy", "Science Fiction"],
                "Other": ["Western", "Film Noir"]
            }

        Raises:
            ValueError: If TMDB_API_KEY is not configured in environment
            RuntimeError: If TMDB API returns an HTTP error status or invalid JSON
            ConnectionError: If unable to connect to TMDB API
        """
        # Delegate to helper function to enable unit testing without FastMCP server setup
        return await categorize_all_genres(ctx)


async def simplify_genres(ctx: Context) -> str:
    """
    Encapsulates the genre simplification logic. See list_genres_simplified() for detailed documentation.
    """
    # Fetch the full genre data
    genres = fetch_genres()

    try:
        # Use LLM sampling to format the response
        # Calls the agent again with new prompt to reformat the response before returning it to the user
        response = await ctx.sample(
            messages=f"Extract just the genre names from this data and return as a simple sorted comma-separated list:\n{genres}",
            system_prompt="You are a data formatter. Return only a clean, sorted list of genre names, nothing else.",
            temperature=0.0,  # Deterministic output
            max_tokens=500
        )
        return response.text
    except Exception as e:
        # Catch broad exception because we don't know the specific exception type
        # raised when sampling is not supported by the client
        await ctx.warning(f"Sampling failed ({type(e).__name__}: {e}), using fallback")
        return ", ".join(sorted(genres.keys()))

async def categorize_all_genres(ctx: Context) -> Dict[str, List[str]]:
    """
    Encapsulates the genre categorization logic. See categorize_genres() for detailed documentation.
    """
    # Fetch all genres
    genres = fetch_genres()

    # Initialize category buckets using helper function
    categorized = create_empty_categorized_dict()

    # Categorize each genre
    for genre_name in sorted(genres.keys()):
        mood = await _categorize_single_genre(genre_name, ctx)
        if mood in categorized:
            categorized[mood].append(genre_name)

    return categorized

async def _categorize_single_genre(genre_name: str, ctx: Context) -> str:
    """
    Categorize a single genre using hybrid approach.

    First checks hardcoded mappings, then falls back to LLM sampling for unknown genres.

    Args:
        genre_name: The name of the genre to categorize
        ctx: FastMCP context for LLM sampling

    Returns:
        Mood category string (MOOD_DARK, MOOD_LIGHT, MOOD_SERIOUS, or MOOD_FUN)
    """
    # Check hardcoded mapping first
    if genre_name in GENRE_MOOD_MAP:
        return GENRE_MOOD_MAP[genre_name]

    # Fall back to LLM sampling for unknown genres
    try:
        response = await ctx.sample(
            messages=f"Categorize the genre '{genre_name}' into exactly one of these moods: Dark, Light, Serious, or Fun. Respond with only the single mood word, nothing else.",
            system_prompt="You are a genre categorization system. Classify genres by mood/tone:\n- Dark: suspenseful, scary, intense\n- Light: uplifting, cheerful, entertaining\n- Serious: educational, thought-provoking, heavy topics\n- Fun: exciting, adventurous, escapist\nRespond with only one word.",
            temperature=0.0,
            max_tokens=10
        )
        # Normalize and validate the response
        mood = response.text.strip()
        if mood in [m.value for m in Mood]:
            return mood
    except Exception as e:
        # Log warning if sampling fails
        await ctx.warning(f"LLM categorization failed for '{genre_name}' ({type(e).__name__}: {e})")

    # Default fallback: categorize as "Other" if we can't determine
    return Mood.OTHER.value
