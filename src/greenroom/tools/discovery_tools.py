"""Media discovery tools for the greenroom MCP server."""

from typing import Dict, Any, Optional
from fastmcp import FastMCP

from greenroom.services.tmdb.service import TMDBService
from greenroom.models.media import MediaList


def register_discovery_tools(mcp: FastMCP) -> None:
    """Register media discovery tools with the MCP server."""

    # Initialize service (could be dependency injected in the future)
    media_service = TMDBService()

    @mcp.tool()
    def discover_media(
        media_type: str,
        genre_id: Optional[int] = None,
        year: Optional[int] = None,
        language: Optional[str] = None,
        sort_by: str = "popularity.desc",
        page: int = 1,
        max_results: int = 20
    ) -> Dict[str, Any]:
        """
        Discover media of any type.

        Generic discovery tool that works with films, TV shows, or any other
        media type supported by the underlying service.

        Args:
            media_type: Type of media ("film", "tv", etc.)
            genre_id: Optional TMDB genre ID to filter by (use list_genres to find IDs)
            year: Optional year to filter by (release year for films, first air year for TV)
            language: Optional ISO 639-1 language code (e.g., "en", "es", "fr")
            sort_by: Sort order - options: "popularity.desc", "popularity.asc",
                     "vote_average.desc", "vote_average.asc", "date.desc", "date.asc"
                     (default: "popularity.desc")
            page: Page number for pagination, 1-indexed (default: 1)
            max_results: Maximum number of results to return (default: 20, max: 100)

        Returns:
            Dictionary containing:
            {
                "results": [
                    {
                        "id": str,
                        "media_type": str,
                        "title": str,
                        "date": str (YYYY-MM-DD format, may be None),
                        "rating": float (0-10 scale, may be None),
                        "description": str (may be None),
                        "genre_ids": List[int]
                    }
                ],
                "total_results": int,
                "page": int,
                "total_pages": int,
                "provider": str
            }

        Raises:
            ValueError: If invalid parameters provided
            RuntimeError: If service returns an error
            ConnectionError: If unable to connect to service
        """
        # Validate parameters
        _validate_discovery_params_internal(media_type, year, page, max_results, language, sort_by)

        # Call service
        media_list = media_service.discover(
            media_type=media_type,
            genre_id=genre_id,
            year=year,
            language=language,
            sort_by=sort_by,
            page=page,
            max_results=max_results
        )

        # Format for Claude
        return _format_media_list(media_list, media_service)

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
        Discover films.

        Convenience wrapper around discover_media for films. Discovers films based on
        optional filters like genre, release year, language, and sorting preferences.

        Args:
            genre_id: Optional TMDB genre ID to filter by (use list_genres to find IDs)
            year: Optional release year to filter by (e.g., 2024)
            language: Optional ISO 639-1 language code (e.g., "en", "es", "fr")
            sort_by: Sort order - options: "popularity.desc", "popularity.asc",
                     "vote_average.desc", "vote_average.asc", "date.desc", "date.asc"
                     (default: "popularity.desc")
            page: Page number for pagination, 1-indexed (default: 1)
            max_results: Maximum number of results to return (default: 20, max: 100)

        Returns:
            Dictionary with results and pagination metadata

        Raises:
            ValueError: If invalid parameters provided
            RuntimeError: If service returns an error
            ConnectionError: If unable to connect to service
        """
        return discover_media(
            media_type="film",
            genre_id=genre_id,
            year=year,
            language=language,
            sort_by=sort_by,
            page=page,
            max_results=max_results
        )

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
        Discover TV shows.

        Convenience wrapper around discover_media for TV shows. Discovers TV shows based on
        optional filters like genre, first air year, language, and sorting preferences.

        Args:
            genre_id: Optional TMDB genre ID to filter by (use list_genres to find IDs)
            year: Optional first air year to filter by (e.g., 2024)
            language: Optional ISO 639-1 language code (e.g., "en", "es", "fr")
            sort_by: Sort order - options: "popularity.desc", "popularity.asc",
                     "vote_average.desc", "vote_average.asc", "date.desc", "date.asc"
                     (default: "popularity.desc")
            page: Page number for pagination, 1-indexed (default: 1)
            max_results: Maximum number of results to return (default: 20, max: 100)

        Returns:
            Dictionary with results and pagination metadata

        Raises:
            ValueError: If invalid parameters provided
            RuntimeError: If service returns an error
            ConnectionError: If unable to connect to service
        """
        return discover_media(
            media_type="tv",
            genre_id=genre_id,
            year=year,
            language=language,
            sort_by=sort_by,
            page=page,
            max_results=max_results
        )


def _validate_discovery_params_internal(
    media_type: str,
    year: Optional[int],
    page: int,
    max_results: int,
    language: Optional[str],
    sort_by: str
) -> None:
    """Validate discovery parameters (internal version).

    Args:
        media_type: Type of media
        year: Optional year filter
        page: Page number
        max_results: Maximum results
        language: Optional language code
        sort_by: Sort order

    Raises:
        ValueError: If any parameter is invalid
    """
    if media_type not in ["film", "tv"]:
        raise ValueError(f"media_type must be 'film' or 'tv', got '{media_type}'")

    if year is not None and year < 1900:
        raise ValueError("year must be 1900 or later")

    if page < 1:
        raise ValueError("page must be 1 or greater")

    if max_results < 1 or max_results > 100:
        raise ValueError("max_results must be between 1 and 100")

    if language is not None:
        if not isinstance(language, str) or len(language) != 2 or not language.isalpha():
            raise ValueError("language must be a 2-character ISO 639-1 code (e.g., 'en', 'es', 'fr')")

    valid_sort_options = [
        "popularity.desc", "popularity.asc",
        "vote_average.desc", "vote_average.asc",
        "date.desc", "date.asc"
    ]
    if sort_by not in valid_sort_options:
        raise ValueError(f"sort_by must be one of: {', '.join(valid_sort_options)}")


def _format_media_list(media_list: MediaList, media_service: TMDBService) -> Dict[str, Any]:
    """Format MediaList for Claude/agent consumption.

    Args:
        media_list: MediaList from service
        media_service: Media service instance for getting provider name

    Returns:
        Dictionary formatted for Claude
    """
    return {
        "results": [
            {
                "id": media.id,
                "media_type": media.media_type,
                "title": media.title,
                "date": media.date.isoformat() if media.date else None,
                "rating": media.rating,
                "description": media.description,
                "genre_ids": media.genre_ids
            }
            for media in media_list.results
        ],
        "total_results": media_list.total_results,
        "page": media_list.page,
        "total_pages": media_list.total_pages,
        "provider": media_service.get_provider_name()
    }


# ============================================================================
# Backwards-compatible test wrappers and exports
# ============================================================================
# The following functions and exports are provided for backwards compatibility
# with existing tests. New code should use the MCP tools registered above.

from greenroom.services.tmdb.models import TMDBFilm, TMDBTVShow
from greenroom.services.tmdb.config import (
    TMDBMediaConfig as FilmTmdbConfig,  # Alias for backwards compatibility
    TMDBMediaConfig as TvTmdbConfig,    # Alias for backwards compatibility
    TMDB_FILM_CONFIG as FILM_CONFIG,
    TMDB_TV_CONFIG as TV_CONFIG
)


def discover_films_from_tmdb(
    genre_id: Optional[int] = None,
    year: Optional[int] = None,
    language: Optional[str] = None,
    sort_by: str = "popularity.desc",
    page: int = 1,
    max_results: int = 20
) -> Dict[str, Any]:
    """Backwards-compatible wrapper for discover_films.

    This function is provided for testing purposes. New code should use
    the MCP tool registered via register_discovery_tools().
    """
    service = TMDBService()
    media_list = service.discover(
        media_type="film",
        genre_id=genre_id,
        year=year,
        language=language,
        sort_by=sort_by,
        page=page,
        max_results=max_results
    )
    # Return old TMDB-specific format for backwards compatibility
    return {
        "results": [
            {
                "id": int(media.id),
                "title": media.title if media.title else None,
                "release_date": media.date.isoformat() if media.date else None,
                "vote_average": media.rating,
                "overview": media.description if media.description else None,
                "genre_ids": media.genre_ids
            }
            for media in media_list.results
        ],
        "total_results": media_list.total_results,
        "page": media_list.page,
        "total_pages": media_list.total_pages
    }


def discover_tv_shows_from_tmdb(
    genre_id: Optional[int] = None,
    year: Optional[int] = None,
    language: Optional[str] = None,
    sort_by: str = "popularity.desc",
    page: int = 1,
    max_results: int = 20
) -> Dict[str, Any]:
    """Backwards-compatible wrapper for discover_tv_shows.

    This function is provided for testing purposes. New code should use
    the MCP tool registered via register_discovery_tools().
    """
    service = TMDBService()
    media_list = service.discover(
        media_type="tv",
        genre_id=genre_id,
        year=year,
        language=language,
        sort_by=sort_by,
        page=page,
        max_results=max_results
    )
    # Return old TMDB-specific format for backwards compatibility
    return {
        "results": [
            {
                "id": int(media.id),
                "name": media.title if media.title else None,
                "first_air_date": media.date.isoformat() if media.date else None,
                "vote_average": media.rating,
                "overview": media.description if media.description else None,
                "genre_ids": media.genre_ids
            }
            for media in media_list.results
        ],
        "total_results": media_list.total_results,
        "page": media_list.page,
        "total_pages": media_list.total_pages
    }


# Backwards-compatible helper function exports for testing
def _validate_discovery_params(
    genre_id: Optional[int],
    year: Optional[int],
    language: Optional[str],
    sort_by: str,
    page: int,
    max_results: int,
    media_config
) -> None:
    """Backwards-compatible wrapper for parameter validation.

    This function is provided for testing purposes only.

    Args:
        genre_id: Optional genre filter
        year: Optional year filter
        language: Optional language code
        sort_by: Sort order
        page: Page number
        max_results: Maximum results
        media_config: Media configuration object

    Raises:
        ValueError: If any parameter is invalid
    """
    if year is not None and year < 1900:
        raise ValueError("Year must be 1900 or later")

    if page < 1:
        raise ValueError("Page must be 1 or greater")

    if max_results < 1 or max_results > 100:
        raise ValueError("max_results must be between 1 and 100")

    if language is not None:
        if not isinstance(language, str) or len(language) != 2 or not language.isalpha():
            raise ValueError("language must be a 2-character ISO 639-1 code (e.g., 'en', 'es', 'fr')")

    # Build valid sort options based on media config
    valid_sort_options = [
        "popularity.desc", "popularity.asc",
        "vote_average.desc", "vote_average.asc",
    ]

    # Add media-type-specific date sort options
    if hasattr(media_config, 'date_sort_prefix'):
        valid_sort_options.extend([
            f"{media_config.date_sort_prefix}.desc",
            f"{media_config.date_sort_prefix}.asc"
        ])

    if sort_by not in valid_sort_options:
        raise ValueError(f"sort_by must be one of: {', '.join(valid_sort_options)}")


def _build_discovery_params(
    api_key: str,
    genre_id: Optional[int],
    year: Optional[int],
    language: Optional[str],
    sort_by: str,
    page: int,
    media_config
) -> Dict[str, Any]:
    """Backwards-compatible wrapper for building discovery parameters.

    This function is provided for testing purposes only.
    """
    params = {
        "api_key": api_key,
        "sort_by": sort_by,
        "page": page,
        "include_adult": False,
        "include_video": False
    }

    if genre_id is not None:
        params["with_genres"] = genre_id

    if year is not None:
        params[media_config.year_param] = year

    if language is not None:
        params["with_original_language"] = language

    return params


def _filter_incomplete_media(media_data: list, model_class):
    """Backwards-compatible wrapper for filtering incomplete media.

    This function is provided for testing purposes only.
    """
    from pydantic import ValidationError

    valid_items = []
    for item in media_data:
        try:
            valid_items.append(model_class(**item))
        except ValidationError:
            pass
    return valid_items


def _format_discovery_response(
    media_items: list,
    raw_data: Dict[str, Any],
    page: int,
    media_config
) -> Dict[str, Any]:
    """Backwards-compatible wrapper for formatting discovery responses.

    This function is provided for testing purposes only.
    """
    results = []
    for item in media_items:
        result_dict = {"id": item.id}

        # Add media-type-specific fields
        if hasattr(item, 'title'):  # Film
            result_dict["title"] = item.title
            result_dict["release_date"] = item.release_date
        elif hasattr(item, 'name'):  # TV Show
            result_dict["name"] = item.name
            result_dict["first_air_date"] = item.first_air_date

        # Add common fields
        result_dict["vote_average"] = item.vote_average
        result_dict["overview"] = item.overview
        result_dict["genre_ids"] = item.genre_ids if item.genre_ids else []

        results.append(result_dict)

    return {
        "page": page,
        "total_results": raw_data.get("total_results", 0),
        "total_pages": raw_data.get("total_pages", 0),
        "results": results
    }
