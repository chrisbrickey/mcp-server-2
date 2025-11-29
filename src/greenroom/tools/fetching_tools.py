"""Genre fetching tools for the greenroom MCP server."""

import json
import os
from typing import Dict, List, Any

import httpx
from fastmcp import FastMCP
from pydantic import BaseModel, ValidationError

from greenroom.config import GENRE_ID, HAS_MOVIES, HAS_TV_SHOWS


# Pydantic model for TMDB genre validation
class TMDBGenre(BaseModel):
    """TMDB API genre structure."""
    id: int
    name: str


def register_fetching_tools(mcp: FastMCP) -> None:
    """Register genre fetching tools with the MCP server."""

    @mcp.tool()
    def list_genres() -> Dict[str, Any]:
        """
        List all available entertainment genres across media types.

        Fetches genre lists from TMDB API for movies and TV shows, combining them into
        a unified map showing which media types support each genre.

        Returns:
            Dictionary mapping genre names to their properties:
            {
                "Documentary": {
                    "id": 99,
                    "has_movies": true,
                    "has_tv_shows": true
                },
                "Action": {
                    "id": 28,
                    "has_movies": true,
                    "has_tv_shows": false
                },
                ...
            }

        Raises:
            ValueError: If TMDB_API_KEY is not configured in environment
            RuntimeError: If TMDB API returns an HTTP error status or invalid JSON
            ConnectionError: If unable to connect to TMDB API
        """

        # Delegate to helper function to enable unit testing without FastMCP server setup
        return fetch_genres()


def fetch_genres() -> Dict[str, Any]:
    """
    Encapsulates the genre fetching logic. See list_genres() for detailed documentation of return value and exceptions.
    """
    api_key = os.getenv("TMDB_API_KEY")
    if not api_key:
        raise ValueError(
            "TMDB_API_KEY not configured. "
            "Set TMDB_API_KEY in .env file. "
            "Get your key from https://www.themoviedb.org/settings/api"
        )

    base_url = "https://api.themoviedb.org/3"
    headers = {"accept": "application/json"}

    try:
        # Fetch genres for both movies and TV shows
        with httpx.Client(timeout=10.0) as client:
            movie_response = client.get(
                f"{base_url}/genre/movie/list",
                params={"api_key": api_key},
                headers=headers
            )
            movie_response.raise_for_status()

            tv_response = client.get(
                f"{base_url}/genre/tv/list",
                params={"api_key": api_key},
                headers=headers
            )
            tv_response.raise_for_status()


        movie_data = movie_response.json().get("genres", [])
        tv_data = tv_response.json().get("genres", [])

        # Filter out genres with incomplete data (e.g. missing id or name field)
        # This helps to prevent a KeyError when the final data structure is built.
        movie_genres = _exclude_incomplete_genres(movie_data)
        tv_genres = _exclude_incomplete_genres(tv_data)

        return _combine_genre_lists(movie_genres, tv_genres)

    except httpx.HTTPStatusError as e:
        raise RuntimeError(
            f"TMDB API error: {e.response.status_code} - {e.response.text}"
        ) from e
    except httpx.RequestError as e:
        raise ConnectionError(
            f"Failed to connect to TMDB API: {str(e)}"
        ) from e
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"TMDB API returned invalid JSON: {str(e)}"
        ) from e

def _exclude_incomplete_genres(genres_data: List[Dict[str, Any]]) -> List[TMDBGenre]:
    """
    Validate genre data, skipping invalid entries.

    Args:
        genres_data: Raw genre data from TMDB API

    Returns:
        List of validated TMDBGenre models (invalid entries are silently skipped)
    """
    valid_genres = []
    for genre in genres_data:
        try:
            valid_genres.append(TMDBGenre(**genre))
        except ValidationError:
            # Skip invalid genre entries
            pass
    return valid_genres


def _combine_genre_lists(movie_genres: List[TMDBGenre], tv_genres: List[TMDBGenre]) -> Dict[str, Any]:
    """
    Combine movie and TV genre lists into a unified map.

    Args:
        movie_genres: List of validated TMDBGenre models for movies
        tv_genres: List of validated TMDBGenre models for TV shows

    Returns:
        Dictionary mapping genre names to their properties (id, has_movies, has_tv_shows)
    """
    genres_map = {
        genre.name: {
            GENRE_ID: genre.id,
            HAS_MOVIES: True,
            HAS_TV_SHOWS: False
        }
        for genre in movie_genres
    }

    for genre in tv_genres:
        if genre.name in genres_map:
            genres_map[genre.name][HAS_TV_SHOWS] = True
        else:
            genres_map[genre.name] = {
                GENRE_ID: genre.id,
                HAS_MOVIES: False,
                HAS_TV_SHOWS: True
            }

    return genres_map
