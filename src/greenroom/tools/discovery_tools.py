"""Film discovery tools for the greenroom MCP server."""

import json
import os
from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Protocol

import httpx
from fastmcp import FastMCP
from pydantic import BaseModel, Field, ValidationError


class TmdbConfig(Protocol):
    """Protocol defining the interface for TMDB media type configurations.

    This protocol allows different media types (films, TV shows, etc.) to define
    their own configuration classes while ensuring they all implement the same interface.
    """
    endpoint: str
    year_param: str
    title_field: str
    date_field: str
    date_sort_prefix: str


@dataclass
class FilmTmdbConfig:
    """Configuration for TMDB film discovery API.

    Defines film-specific TMDB API parameters and response field names.
    """
    endpoint: str = "movie"
    year_param: str = "primary_release_year"
    title_field: str = "title"
    date_field: str = "release_date"
    date_sort_prefix: str = "release_date"


@dataclass
class TvTmdbConfig:
    """Configuration for TMDB TV show discovery API.

    Defines TV show-specific TMDB API parameters and response field names.
    """
    endpoint: str = "tv"
    year_param: str = "first_air_date_year"
    title_field: str = "name"
    date_field: str = "first_air_date"
    date_sort_prefix: str = "first_air_date"


# Create singleton instances
FILM_CONFIG = FilmTmdbConfig()
TV_CONFIG = TvTmdbConfig()


# Pydantic model for TMDB film validation
class TMDBFilm(BaseModel):
    """TMDB API film structure with flexible field handling.

    Only 'id' is required - all other fields optional to handle:
    - Incomplete TMDB data
    - API changes/additions
    - Regional variations in data availability
    """
    id: int
    title: Optional[str] = None
    release_date: Optional[str] = None
    vote_average: Optional[float] = None
    overview: Optional[str] = None
    genre_ids: Optional[List[int]] = Field(default_factory=list)


# Pydantic model for TMDB TV show validation
class TMDBTVShow(BaseModel):
    """TMDB API TV show structure with flexible field handling.

    Only 'id' is required - all other fields optional to handle:
    - Incomplete TMDB data
    - API changes/additions
    - Regional variations in data availability
    """
    id: int
    name: Optional[str] = None
    first_air_date: Optional[str] = None
    vote_average: Optional[float] = None
    overview: Optional[str] = None
    genre_ids: Optional[List[int]] = Field(default_factory=list)


def register_discovery_tools(mcp: FastMCP) -> None:
    """Register film discovery tools with the MCP server."""

    @mcp.tool()
    def discover_films(
        genre_id: Optional[int] = None,
        year: Optional[int] = None,
        language: Optional[str] = None,
        sort_by: str = "popularity.desc",
        page: int = 1,
        max_results: int = 20
    ) -> Dict[str, Any]:
        """
        Retrieve films based on discovery criteria.

        Discovers films from TMDB based on optional filters like genre, release year,
        language, and sorting preferences. Returns essential metadata for each film
        including title, release date, ratings, and overview.

        Args:
            genre_id: Optional TMDB genre ID to filter by (use list_genres to find IDs)
            year: Optional release year to filter by (e.g., 2024)
            language: Optional ISO 639-1 language code (e.g., "en", "es", "fr")
            sort_by: Sort order - options: "popularity.desc", "popularity.asc",
                     "vote_average.desc", "vote_average.asc", "release_date.desc",
                     "release_date.asc" (default: "popularity.desc")
            page: Page number for pagination, 1-indexed (default: 1)
            max_results: Maximum number of results to return (default: 20, max: 100)

        Returns:
            Dictionary containing:
            {
                "results": [
                    {
                        "id": int,
                        "title": str (may be None),
                        "release_date": str in YYYY-MM-DD format (may be None),
                        "vote_average": float (may be None),
                        "overview": str (may be None),
                        "genre_ids": List[int] (may be empty)
                    }
                ],
                "total_results": int,
                "page": int,
                "total_pages": int
            }

        Raises:
            ValueError: If TMDB_API_KEY is not configured in environment, or if
                       invalid parameters provided (year < 1900, page < 1, etc.)
            RuntimeError: If TMDB API returns an HTTP error status or invalid JSON
            ConnectionError: If unable to connect to TMDB API
        """
        # Delegate to helper function to enable unit testing without FastMCP server setup
        return discover_films_from_tmdb(genre_id, year, language, sort_by, page, max_results)

    @mcp.tool()
    def discover_tv_shows(
        genre_id: Optional[int] = None,
        year: Optional[int] = None,
        language: Optional[str] = None,
        sort_by: str = "popularity.desc",
        page: int = 1,
        max_results: int = 20
    ) -> Dict[str, Any]:
        """
        Retrieve TV shows based on discovery criteria.

        Discovers TV shows from TMDB based on optional filters like genre, first air year,
        language, and sorting preferences. Returns essential metadata for each show
        including name, first air date, ratings, and overview.

        Args:
            genre_id: Optional TMDB genre ID to filter by (use list_genres to find IDs)
            year: Optional first air year to filter by (e.g., 2024)
            language: Optional ISO 639-1 language code (e.g., "en", "es", "fr")
            sort_by: Sort order - options: "popularity.desc", "popularity.asc",
                     "vote_average.desc", "vote_average.asc", "first_air_date.desc",
                     "first_air_date.asc" (default: "popularity.desc")
            page: Page number for pagination, 1-indexed (default: 1)
            max_results: Maximum number of results to return (default: 20, max: 100)

        Returns:
            Dictionary containing:
            {
                "results": [
                    {
                        "id": int,
                        "name": str (may be None),
                        "first_air_date": str in YYYY-MM-DD format (may be None),
                        "vote_average": float (may be None),
                        "overview": str (may be None),
                        "genre_ids": List[int] (may be empty)
                    }
                ],
                "total_results": int,
                "page": int,
                "total_pages": int
            }

        Raises:
            ValueError: If TMDB_API_KEY is not configured in environment, or if
                       invalid parameters provided (year < 1900, page < 1, etc.)
            RuntimeError: If TMDB API returns an HTTP error status or invalid JSON
            ConnectionError: If unable to connect to TMDB API
        """
        # Delegate to helper function to enable unit testing without FastMCP server setup
        return discover_tv_shows_from_tmdb(genre_id, year, language, sort_by, page, max_results)


def _discover_media_from_tmdb(
    media_config: TmdbConfig,
    model_class: type[BaseModel],
    genre_id: Optional[int] = None,
    year: Optional[int] = None,
    language: Optional[str] = None,
    sort_by: str = "popularity.desc",
    page: int = 1,
    max_results: int = 20
) -> Dict[str, Any]:
    """Generic media discovery logic for any TMDB media type.

    Args:
        media_config: Media type configuration (FILM_CONFIG or TV_CONFIG)
        model_class: Pydantic model class (TMDBFilm or TMDBTVShow)
        genre_id: Optional TMDB genre ID to filter by
        year: Optional release/air year to filter by
        language: Optional ISO 639-1 language code
        sort_by: Sort order
        page: Page number for pagination
        max_results: Maximum number of results to return

    Returns:
        Formatted discovery response dictionary
    """
    # Validate inputs
    _validate_discovery_params(genre_id, year, language, sort_by, page, max_results, media_config)

    # Get API key
    api_key = os.getenv("TMDB_API_KEY")
    if not api_key:
        raise ValueError(
            "TMDB_API_KEY not configured. "
            "Set TMDB_API_KEY in .env file. "
            "Get your key from https://www.themoviedb.org/settings/api"
        )

    # Build query parameters
    params = _build_discovery_params(api_key, genre_id, year, language, sort_by, page, media_config)

    # Call TMDB API
    base_url = "https://api.themoviedb.org/3"
    headers = {"accept": "application/json"}

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                f"{base_url}/discover/{media_config.endpoint}",
                params=params,
                headers=headers
            )
            response.raise_for_status()

        data = response.json()

        # Extract and validate media data
        raw_results = data.get("results", [])
        validated_media = _filter_incomplete_media(raw_results, model_class)

        # Apply max_results limit
        limited_media = validated_media[:max_results]

        # Format response
        return _format_discovery_response(limited_media, data, page, media_config)

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


def discover_films_from_tmdb(
    genre_id: Optional[int] = None,
    year: Optional[int] = None,
    language: Optional[str] = None,
    sort_by: str = "popularity.desc",
    page: int = 1,
    max_results: int = 20
) -> Dict[str, Any]:
    """Encapsulates film discovery logic. See discover_films() for detailed documentation."""
    return _discover_media_from_tmdb(
        FILM_CONFIG, TMDBFilm, genre_id, year, language, sort_by, page, max_results
    )


def discover_tv_shows_from_tmdb(
    genre_id: Optional[int] = None,
    year: Optional[int] = None,
    language: Optional[str] = None,
    sort_by: str = "popularity.desc",
    page: int = 1,
    max_results: int = 20
) -> Dict[str, Any]:
    """Encapsulates TV show discovery logic. See discover_tv_shows() for detailed documentation."""
    return _discover_media_from_tmdb(
        TV_CONFIG, TMDBTVShow, genre_id, year, language, sort_by, page, max_results
    )


def _validate_discovery_params(
    genre_id: Optional[int],
    year: Optional[int],
    language: Optional[str],
    sort_by: str,
    page: int,
    max_results: int,
    media_config: TmdbConfig
) -> None:
    """Validate discovery parameters for any media type.

    Args:
        genre_id: TMDB genre ID (optional)
        year: Release/air year (optional)
        language: ISO 639-1 language code (optional)
        sort_by: Sort order string
        page: Page number for pagination
        max_results: Maximum number of results to return
        media_config: Media type configuration defining valid sort options

    Raises:
        ValueError: If any parameter is invalid
    """
    if year is not None and year < 1900:
        raise ValueError("Year must be 1900 or later")

    if page < 1:
        raise ValueError("Page must be 1 or greater")

    if max_results < 1 or max_results > 100:
        raise ValueError("max_results must be between 1 and 100")

    # Build valid sort options using media type configuration
    valid_sort_options = [
        "popularity.desc", "popularity.asc",
        "vote_average.desc", "vote_average.asc",
        f"{media_config.date_sort_prefix}.desc",
        f"{media_config.date_sort_prefix}.asc"
    ]
    if sort_by not in valid_sort_options:
        raise ValueError(f"sort_by must be one of: {', '.join(valid_sort_options)}")

    # Validate language code format (must be 2-character ISO 639-1 code)
    if language is not None:
        if not isinstance(language, str) or len(language) != 2 or not language.isalpha():
            raise ValueError("language must be a 2-character ISO 639-1 code (e.g., 'en', 'es', 'fr')")


def _build_discovery_params(
    api_key: str,
    genre_id: Optional[int],
    year: Optional[int],
    language: Optional[str],
    sort_by: str,
    page: int,
    media_config: TmdbConfig
) -> Dict[str, Any]:
    """Build TMDB API query parameters for any media type.

    Args:
        api_key: TMDB API key
        genre_id: TMDB genre ID (optional)
        year: Release/air year (optional)
        language: ISO 639-1 language code (optional)
        sort_by: Sort order string
        page: Page number for pagination
        media_config: Media type configuration

    Returns:
        Dictionary of query parameters for TMDB API
    """
    params = {
        "api_key": api_key,
        "sort_by": sort_by,
        "page": page,
        "include_adult": False,  # Exclude pornographic content
        "include_video": False   # Exclude video-only content
    }

    if genre_id is not None:
        params["with_genres"] = genre_id

    if year is not None:
        params[media_config.year_param] = year

    if language is not None:
        params["with_original_language"] = language

    return params


def _filter_incomplete_media(
    media_data: List[Dict[str, Any]],
    model_class: type[BaseModel]
) -> List[BaseModel]:
    """Validate media data using a Pydantic model, skipping invalid entries.

    Only media items with at least an 'id' field will be kept.

    Args:
        media_data: Raw media data from TMDB API
        model_class: Pydantic model class to validate against (TMDBFilm or TMDBTVShow)

    Returns:
        List of validated model instances (invalid entries are silently skipped)
    """
    valid_media = []
    for item in media_data:
        try:
            valid_media.append(model_class(**item))
        except ValidationError:
            # Skip items without even an 'id' field
            pass
    return valid_media


def _format_discovery_response(
    media_items: List[BaseModel],
    raw_data: Dict[str, Any],
    page: int,
    media_config: TmdbConfig
) -> Dict[str, Any]:
    """Format discovery response for return to user.

    Args:
        media_items: List of validated media models (TMDBFilm or TMDBTVShow)
        raw_data: Raw response data from TMDB API
        page: Current page number
        media_config: Media type configuration

    Returns:
        Formatted response dictionary with results and pagination metadata
    """
    return {
        "results": [
            {
                "id": item.id,
                media_config.title_field: getattr(item, media_config.title_field),
                media_config.date_field: getattr(item, media_config.date_field),
                "vote_average": item.vote_average,
                "overview": item.overview,
                "genre_ids": item.genre_ids or []
            }
            for item in media_items
        ],
        "total_results": raw_data.get("total_results", 0),
        "page": page,
        "total_pages": raw_data.get("total_pages", 0)
    }
