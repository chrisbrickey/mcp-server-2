"""Tests for discovery_tools.py."""

import httpx
import pytest
from pytest_httpx import HTTPXMock
from unittest.mock import patch

from greenroom.tools.discovery_tools import (
    discover_films_from_tmdb,
    discover_tv_shows_from_tmdb,
    _validate_discovery_params,
    _build_discovery_params,
    _filter_incomplete_media,
    _format_discovery_response,
    TMDBFilm,
    TMDBTVShow,
    FilmTmdbConfig,
    TvTmdbConfig,
    FILM_CONFIG,
    TV_CONFIG,
)


def test_discover_films_returns_formatted_results(monkeypatch, httpx_mock: HTTPXMock):
    """Test discover_films returns properly formatted film data."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    mock_response = {
        "page": 1,
        "total_results": 100,
        "total_pages": 5,
        "results": [
            {
                "id": 550,
                "title": "Fight Club",
                "release_date": "1999-10-15",
                "vote_average": 8.4,
                "overview": "A ticking-time-bomb insomniac and a slippery soap salesman channel primal male aggression.",
                "genre_ids": [18, 53],
                "poster_path": "/path.jpg"
            },
            {
                "id": 680,
                "title": "Pulp Fiction",
                "release_date": "1994-09-10",
                "vote_average": 8.5,
                "overview": "A burger-loving hit man, his philosophical partner, and a drug-addled gangster's moll.",
                "genre_ids": [80, 18],
                "popularity": 65.3
            }
        ]
    }

    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/discover/movie?api_key=test_api_key&sort_by=popularity.desc&page=1&include_adult=false&include_video=false&with_genres=18&primary_release_year=1999",
        json=mock_response
    )

    result = discover_films_from_tmdb(genre_id=18, year=1999, page=1)

    assert result["page"] == 1
    assert result["total_results"] == 100
    assert result["total_pages"] == 5
    assert len(result["results"]) == 2
    assert result["results"][0]["title"] == "Fight Club"
    assert result["results"][0]["vote_average"] == 8.4
    assert result["results"][0]["genre_ids"] == [18, 53]
    assert result["results"][1]["title"] == "Pulp Fiction"


def test_discover_films_handles_incomplete_data(monkeypatch, httpx_mock: HTTPXMock):
    """Test that films with missing optional fields are handled gracefully."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    mock_response = {
        "page": 1,
        "total_results": 4,
        "total_pages": 1,
        "results": [
            {"id": 1, "title": "Complete Film", "release_date": "2024-01-01", "vote_average": 7.5, "overview": "Full details", "genre_ids": [28]},
            {"id": 2, "title": "Missing Date"},  # No release_date
            {"id": 3, "vote_average": 6.0},  # No title
            {"id": 4},  # Only ID
            {"title": "No ID"},  # Missing ID - should be filtered out
        ]
    }

    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/discover/movie?api_key=test_api_key&sort_by=popularity.desc&page=1&include_adult=false&include_video=false",
        json=mock_response
    )

    result = discover_films_from_tmdb()

    # Should return 4 films (all with IDs), not 5
    assert len(result["results"]) == 4

    # Check first film has all data
    assert result["results"][0]["title"] == "Complete Film"
    assert result["results"][0]["release_date"] == "2024-01-01"
    assert result["results"][0]["vote_average"] == 7.5
    assert result["results"][0]["overview"] == "Full details"
    assert result["results"][0]["genre_ids"] == [28]

    # Check that missing fields are None
    assert result["results"][1]["title"] == "Missing Date"
    assert result["results"][1]["release_date"] is None
    assert result["results"][1]["overview"] is None

    assert result["results"][2]["title"] is None
    assert result["results"][2]["vote_average"] == 6.0

    # Check film with only ID
    assert result["results"][3]["id"] == 4
    assert result["results"][3]["title"] is None
    assert result["results"][3]["genre_ids"] == []


def test_discover_films_handles_empty_results(monkeypatch, httpx_mock: HTTPXMock):
    """Test discover_films handles empty results gracefully."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    mock_response = {
        "page": 1,
        "total_results": 0,
        "total_pages": 0,
        "results": []
    }

    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/discover/movie?api_key=test_api_key&sort_by=popularity.desc&page=1&include_adult=false&include_video=false",
        json=mock_response
    )

    result = discover_films_from_tmdb()

    assert result["results"] == []
    assert result["total_results"] == 0
    assert result["page"] == 1
    assert result["total_pages"] == 0


def test_discover_films_respects_max_results(monkeypatch, httpx_mock: HTTPXMock):
    """Test that max_results parameter limits returned films."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    # Mock response with 20 films
    mock_results = [{"id": i, "title": f"Film {i}"} for i in range(20)]
    mock_response = {
        "page": 1,
        "total_results": 100,
        "total_pages": 5,
        "results": mock_results
    }

    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/discover/movie?api_key=test_api_key&sort_by=popularity.desc&page=1&include_adult=false&include_video=false",
        json=mock_response
    )

    result = discover_films_from_tmdb(max_results=5)

    assert len(result["results"]) == 5
    assert result["results"][0]["id"] == 0
    assert result["results"][4]["id"] == 4


def test_discover_films_uses_default_parameters(monkeypatch, httpx_mock: HTTPXMock):
    """Test that discover_films applies correct default parameters."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    mock_response = {
        "page": 1,
        "total_results": 0,
        "total_pages": 0,
        "results": []
    }

    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/discover/movie?api_key=test_api_key&sort_by=popularity.desc&page=1&include_adult=false&include_video=false",
        json=mock_response
    )

    discover_films_from_tmdb()

    # Verify the mock was called with correct default URL
    assert len(httpx_mock.get_requests()) == 1
    request = httpx_mock.get_requests()[0]
    assert "sort_by=popularity.desc" in str(request.url)
    assert "page=1" in str(request.url)
    assert "include_adult=false" in str(request.url)


def test_discover_films_filters_by_language(monkeypatch, httpx_mock: HTTPXMock):
    """Test language parameter filters films correctly."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    mock_response = {
        "page": 1,
        "total_results": 1,
        "total_pages": 1,
        "results": [
            {"id": 123, "title": "Spanish Film", "original_language": "es"}
        ]
    }

    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/discover/movie?api_key=test_api_key&sort_by=popularity.desc&page=1&include_adult=false&include_video=false&with_original_language=es",
        json=mock_response
    )

    result = discover_films_from_tmdb(language="es")

    assert len(result["results"]) == 1
    assert result["results"][0]["title"] == "Spanish Film"

    # Verify the URL included the language parameter
    request = httpx_mock.get_requests()[0]
    assert "with_original_language=es" in str(request.url)


def test_validate_discovery_params_rejects_invalid_year():
    """Test parameter validation rejects invalid year."""
    with pytest.raises(ValueError, match="Year must be 1900 or later"):
        _validate_discovery_params(None, 1899, None, "popularity.desc", 1, 20, FILM_CONFIG)


def test_validate_discovery_params_rejects_invalid_page():
    """Test parameter validation rejects invalid page."""
    with pytest.raises(ValueError, match="Page must be 1 or greater"):
        _validate_discovery_params(None, None, None, "popularity.desc", 0, 20, FILM_CONFIG)


def test_validate_discovery_params_rejects_invalid_max_results():
    """Test parameter validation rejects invalid max_results."""
    with pytest.raises(ValueError, match="max_results must be between 1 and 100"):
        _validate_discovery_params(None, None, None, "popularity.desc", 1, 150, FILM_CONFIG)

    with pytest.raises(ValueError, match="max_results must be between 1 and 100"):
        _validate_discovery_params(None, None, None, "popularity.desc", 1, 0, FILM_CONFIG)


def test_validate_discovery_params_rejects_invalid_sort_by():
    """Test parameter validation rejects invalid sort_by."""
    with pytest.raises(ValueError, match="sort_by must be one of"):
        _validate_discovery_params(None, None, None, "invalid.sort", 1, 20, FILM_CONFIG)


def test_validate_discovery_params_rejects_invalid_language():
    """Test parameter validation rejects invalid language code."""
    # Too long
    with pytest.raises(ValueError, match="language must be a 2-character ISO 639-1 code"):
        _validate_discovery_params(None, None, "eng", "popularity.desc", 1, 20, FILM_CONFIG)

    # Too short
    with pytest.raises(ValueError, match="language must be a 2-character ISO 639-1 code"):
        _validate_discovery_params(None, None, "e", "popularity.desc", 1, 20, FILM_CONFIG)

    # Contains numbers
    with pytest.raises(ValueError, match="language must be a 2-character ISO 639-1 code"):
        _validate_discovery_params(None, None, "e1", "popularity.desc", 1, 20, FILM_CONFIG)

    # Not a string
    with pytest.raises(ValueError, match="language must be a 2-character ISO 639-1 code"):
        _validate_discovery_params(None, None, 12, "popularity.desc", 1, 20, FILM_CONFIG)


def test_validate_discovery_params_accepts_valid_inputs():
    """Test parameter validation accepts valid inputs."""
    # Should not raise any exceptions
    _validate_discovery_params(28, 2024, "en", "popularity.desc", 1, 20, FILM_CONFIG)
    _validate_discovery_params(None, None, None, "vote_average.desc", 2, 50, FILM_CONFIG)
    _validate_discovery_params(18, 1900, "fr", "release_date.asc", 10, 100, FILM_CONFIG)


def test_discover_films_raises_value_error_when_api_key_missing(monkeypatch):
    """Test that ValueError is raised when TMDB_API_KEY is not set."""
    monkeypatch.delenv("TMDB_API_KEY", raising=False)

    with pytest.raises(ValueError) as exc_info:
        discover_films_from_tmdb()

    assert "TMDB_API_KEY not configured" in str(exc_info.value)
    assert ".env file" in str(exc_info.value)


def test_discover_films_raises_runtime_error_on_http_error(monkeypatch, httpx_mock: HTTPXMock):
    """Test that RuntimeError is raised when TMDB API returns HTTP error."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/discover/movie?api_key=test_api_key&sort_by=popularity.desc&page=1&include_adult=false&include_video=false",
        status_code=401,
        text="Invalid API key"
    )

    with pytest.raises(RuntimeError) as exc_info:
        discover_films_from_tmdb()

    assert "TMDB API error" in str(exc_info.value)
    assert "401" in str(exc_info.value)


def test_discover_films_raises_runtime_error_on_invalid_json(monkeypatch, httpx_mock: HTTPXMock):
    """Test that RuntimeError is raised when TMDB API returns invalid JSON."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/discover/movie?api_key=test_api_key&sort_by=popularity.desc&page=1&include_adult=false&include_video=false",
        content=b"Not valid JSON!"
    )

    with pytest.raises(RuntimeError) as exc_info:
        discover_films_from_tmdb()

    assert "invalid JSON" in str(exc_info.value)


def test_discover_films_raises_connection_error_on_request_failure(monkeypatch, httpx_mock: HTTPXMock):
    """Test that ConnectionError is raised when unable to connect to TMDB API."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    httpx_mock.add_exception(
        httpx.RequestError("Connection refused"),
        url="https://api.themoviedb.org/3/discover/movie?api_key=test_api_key&sort_by=popularity.desc&page=1&include_adult=false&include_video=false"
    )

    with pytest.raises(ConnectionError) as exc_info:
        discover_films_from_tmdb()

    assert "Failed to connect to TMDB API" in str(exc_info.value)


def test_build_discovery_params():
    """Test that _build_discovery_params creates correct parameter dict."""
    params = _build_discovery_params(
        api_key="test_key",
        genre_id=28,
        year=2024,
        language="en",
        sort_by="vote_average.desc",
        page=2,
        media_config=FILM_CONFIG
    )

    assert params["api_key"] == "test_key"
    assert params["with_genres"] == 28
    assert params["primary_release_year"] == 2024
    assert params["with_original_language"] == "en"
    assert params["sort_by"] == "vote_average.desc"
    assert params["page"] == 2
    assert params["include_adult"] is False
    assert params["include_video"] is False


def test_build_discovery_params_with_optional_none():
    """Test that _build_discovery_params handles None optional parameters."""
    params = _build_discovery_params(
        api_key="test_key",
        genre_id=None,
        year=None,
        language=None,
        sort_by="popularity.desc",
        page=1,
        media_config=FILM_CONFIG
    )

    assert "with_genres" not in params
    assert "primary_release_year" not in params
    assert "with_original_language" not in params
    assert params["api_key"] == "test_key"
    assert params["sort_by"] == "popularity.desc"


def test_filter_incomplete_films():
    """Test that _filter_incomplete_media validates and filters film data."""
    films_data = [
        {"id": 1, "title": "Valid Film"},
        {"id": 2},  # Valid - only id required
        {"title": "No ID"},  # Invalid - missing id
        {},  # Invalid - missing id
        {"id": 3, "vote_average": 8.5, "genre_ids": [28, 12]},  # Valid
    ]

    result = _filter_incomplete_media(films_data, TMDBFilm)

    assert len(result) == 3
    assert all(isinstance(film, TMDBFilm) for film in result)
    assert result[0].id == 1
    assert result[0].title == "Valid Film"
    assert result[1].id == 2
    assert result[1].title is None
    assert result[2].id == 3
    assert result[2].vote_average == 8.5


def test_format_discovery_response():
    """Test that _format_discovery_response creates correct output structure."""
    films = [
        TMDBFilm(id=1, title="Film 1", vote_average=8.0, genre_ids=[28]),
        TMDBFilm(id=2, title="Film 2"),
    ]

    raw_data = {
        "total_results": 50,
        "total_pages": 3
    }

    result = _format_discovery_response(films, raw_data, page=1, media_config=FILM_CONFIG)

    assert result["page"] == 1
    assert result["total_results"] == 50
    assert result["total_pages"] == 3
    assert len(result["results"]) == 2
    assert result["results"][0]["id"] == 1
    assert result["results"][0]["title"] == "Film 1"
    assert result["results"][0]["vote_average"] == 8.0
    assert result["results"][0]["genre_ids"] == [28]
    assert result["results"][1]["id"] == 2
    assert result["results"][1]["title"] == "Film 2"
    assert result["results"][1]["genre_ids"] == []

# TV Show Discovery Tests

def test_discover_tv_shows_returns_formatted_results(monkeypatch, httpx_mock: HTTPXMock):
    """Test discover_tv_shows returns properly formatted TV show data."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    mock_response = {
        "page": 1,
        "total_results": 100,
        "total_pages": 5,
        "results": [
            {
                "id": 1396,
                "name": "Breaking Bad",
                "first_air_date": "2008-01-20",
                "vote_average": 8.9,
                "overview": "A high school chemistry teacher turned meth manufacturer.",
                "genre_ids": [18, 80],
                "poster_path": "/path.jpg"
            },
            {
                "id": 1399,
                "name": "Game of Thrones",
                "first_air_date": "2011-04-17",
                "vote_average": 8.3,
                "overview": "Nine noble families fight for control.",
                "genre_ids": [10765, 18],
                "popularity": 369.5
            }
        ]
    }

    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/discover/tv?api_key=test_api_key&sort_by=popularity.desc&page=1&include_adult=false&include_video=false&with_genres=18&first_air_date_year=2008",
        json=mock_response
    )

    result = discover_tv_shows_from_tmdb(genre_id=18, year=2008, page=1)

    assert result["page"] == 1
    assert result["total_results"] == 100
    assert result["total_pages"] == 5
    assert len(result["results"]) == 2
    assert result["results"][0]["name"] == "Breaking Bad"
    assert result["results"][0]["first_air_date"] == "2008-01-20"
    assert result["results"][0]["vote_average"] == 8.9
    assert result["results"][0]["genre_ids"] == [18, 80]
    assert result["results"][1]["name"] == "Game of Thrones"


def test_discover_tv_shows_handles_incomplete_data(monkeypatch, httpx_mock: HTTPXMock):
    """Test that TV shows with missing optional fields are handled gracefully."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    mock_response = {
        "page": 1,
        "total_results": 3,
        "total_pages": 1,
        "results": [
            {"id": 1, "name": "Complete Show", "first_air_date": "2024-01-01", "vote_average": 7.5, "overview": "Full details", "genre_ids": [35]},
            {"id": 2, "name": "Missing Date"},  # No first_air_date
            {"id": 3},  # Only ID
        ]
    }

    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/discover/tv?api_key=test_api_key&sort_by=popularity.desc&page=1&include_adult=false&include_video=false",
        json=mock_response
    )

    result = discover_tv_shows_from_tmdb()

    assert len(result["results"]) == 3
    assert result["results"][0]["name"] == "Complete Show"
    assert result["results"][1]["name"] == "Missing Date"
    assert result["results"][1]["first_air_date"] is None
    assert result["results"][2]["id"] == 3
    assert result["results"][2]["name"] is None


def test_build_discovery_params_with_tv_config():
    """Test that _build_discovery_params uses first_air_date_year for TV shows."""
    params = _build_discovery_params(
        api_key="test_key",
        genre_id=18,
        year=2020,
        language="en",
        sort_by="vote_average.desc",
        page=1,
        media_config=TV_CONFIG
    )

    assert params["api_key"] == "test_key"
    assert params["with_genres"] == 18
    assert params["first_air_date_year"] == 2020  # TV-specific parameter
    assert "primary_release_year" not in params
    assert params["with_original_language"] == "en"


def test_filter_incomplete_media_with_tv_shows():
    """Test that _filter_incomplete_media works with TV show model."""
    tv_data = [
        {"id": 1, "name": "Valid Show"},
        {"id": 2},  # Valid - only id required
        {"name": "No ID"},  # Invalid - missing id
        {"id": 3, "vote_average": 8.5, "genre_ids": [35, 10765]},  # Valid
    ]

    result = _filter_incomplete_media(tv_data, TMDBTVShow)

    assert len(result) == 3
    assert all(isinstance(show, TMDBTVShow) for show in result)
    assert result[0].id == 1
    assert result[0].name == "Valid Show"
    assert result[1].id == 2
    assert result[1].name is None
    assert result[2].id == 3
    assert result[2].vote_average == 8.5


def test_format_discovery_response_with_tv_config():
    """Test that _format_discovery_response formats TV show data correctly."""
    shows = [
        TMDBTVShow(id=1, name="Show 1", first_air_date="2020-01-01", vote_average=8.0, genre_ids=[35]),
        TMDBTVShow(id=2, name="Show 2"),
    ]

    raw_data = {
        "total_results": 50,
        "total_pages": 3
    }

    result = _format_discovery_response(shows, raw_data, page=1, media_config=TV_CONFIG)

    assert result["page"] == 1
    assert result["total_results"] == 50
    assert len(result["results"]) == 2
    assert result["results"][0]["name"] == "Show 1"  # TV-specific field
    assert result["results"][0]["first_air_date"] == "2020-01-01"  # TV-specific field
    assert "title" not in result["results"][0]
    assert "release_date" not in result["results"][0]


def test_discover_tv_shows_handles_empty_results(monkeypatch, httpx_mock: HTTPXMock):
    """Test discover_tv_shows handles empty results gracefully."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    mock_response = {
        "page": 1,
        "total_results": 0,
        "total_pages": 0,
        "results": []
    }

    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/discover/tv?api_key=test_api_key&sort_by=popularity.desc&page=1&include_adult=false&include_video=false",
        json=mock_response
    )

    result = discover_tv_shows_from_tmdb()

    assert result["results"] == []
    assert result["total_results"] == 0
    assert result["page"] == 1
    assert result["total_pages"] == 0


def test_discover_tv_shows_respects_max_results(monkeypatch, httpx_mock: HTTPXMock):
    """Test that max_results parameter limits returned TV shows."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    # Mock response with 20 TV shows
    mock_results = [{"id": i, "name": f"Show {i}"} for i in range(20)]
    mock_response = {
        "page": 1,
        "total_results": 100,
        "total_pages": 5,
        "results": mock_results
    }

    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/discover/tv?api_key=test_api_key&sort_by=popularity.desc&page=1&include_adult=false&include_video=false",
        json=mock_response
    )

    result = discover_tv_shows_from_tmdb(max_results=5)

    assert len(result["results"]) == 5
    assert result["results"][0]["id"] == 0
    assert result["results"][4]["id"] == 4


def test_discover_tv_shows_uses_default_parameters(monkeypatch, httpx_mock: HTTPXMock):
    """Test that discover_tv_shows applies correct default parameters."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    mock_response = {
        "page": 1,
        "total_results": 0,
        "total_pages": 0,
        "results": []
    }

    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/discover/tv?api_key=test_api_key&sort_by=popularity.desc&page=1&include_adult=false&include_video=false",
        json=mock_response
    )

    discover_tv_shows_from_tmdb()

    # Verify the mock was called with correct default URL
    assert len(httpx_mock.get_requests()) == 1
    request = httpx_mock.get_requests()[0]
    assert "sort_by=popularity.desc" in str(request.url)
    assert "page=1" in str(request.url)
    assert "include_adult=false" in str(request.url)


def test_discover_tv_shows_filters_by_language(monkeypatch, httpx_mock: HTTPXMock):
    """Test language parameter filters TV shows correctly."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    mock_response = {
        "page": 1,
        "total_results": 1,
        "total_pages": 1,
        "results": [
            {"id": 456, "name": "Korean Drama", "original_language": "ko"}
        ]
    }

    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/discover/tv?api_key=test_api_key&sort_by=popularity.desc&page=1&include_adult=false&include_video=false&with_original_language=ko",
        json=mock_response
    )

    result = discover_tv_shows_from_tmdb(language="ko")

    assert len(result["results"]) == 1
    assert result["results"][0]["name"] == "Korean Drama"

    # Verify the URL included the language parameter
    request = httpx_mock.get_requests()[0]
    assert "with_original_language=ko" in str(request.url)


def test_discover_tv_shows_uses_first_air_date_year(monkeypatch, httpx_mock: HTTPXMock):
    """Test that discover_tv_shows uses first_air_date_year parameter."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    mock_response = {
        "page": 1,
        "total_results": 1,
        "total_pages": 1,
        "results": [
            {"id": 789, "name": "2020 Show", "first_air_date": "2020-05-15"}
        ]
    }

    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/discover/tv?api_key=test_api_key&sort_by=popularity.desc&page=1&include_adult=false&include_video=false&first_air_date_year=2020",
        json=mock_response
    )

    result = discover_tv_shows_from_tmdb(year=2020)

    assert len(result["results"]) == 1

    # Verify the URL used first_air_date_year, not primary_release_year
    request = httpx_mock.get_requests()[0]
    assert "first_air_date_year=2020" in str(request.url)
    assert "primary_release_year" not in str(request.url)


def test_validate_discovery_params_with_tv_config_rejects_invalid_sort_by():
    """Test parameter validation rejects invalid sort_by for TV shows."""
    # Film-specific sort option should be rejected for TV config
    with pytest.raises(ValueError, match="sort_by must be one of"):
        _validate_discovery_params(None, None, None, "release_date.desc", 1, 20, TV_CONFIG)


def test_validate_discovery_params_accepts_tv_sort_options():
    """Test parameter validation accepts TV-specific sort options."""
    # Should not raise any exceptions
    _validate_discovery_params(18, 2024, "en", "first_air_date.desc", 1, 20, TV_CONFIG)
    _validate_discovery_params(None, None, None, "first_air_date.asc", 2, 50, TV_CONFIG)
    _validate_discovery_params(35, 2020, "ko", "popularity.desc", 10, 100, TV_CONFIG)


def test_discover_tv_shows_raises_value_error_when_api_key_missing(monkeypatch):
    """Test that ValueError is raised when TMDB_API_KEY is not set."""
    monkeypatch.delenv("TMDB_API_KEY", raising=False)

    with pytest.raises(ValueError) as exc_info:
        discover_tv_shows_from_tmdb()

    assert "TMDB_API_KEY not configured" in str(exc_info.value)
    assert ".env file" in str(exc_info.value)


def test_discover_tv_shows_raises_runtime_error_on_http_error(monkeypatch, httpx_mock: HTTPXMock):
    """Test that RuntimeError is raised when TMDB API returns HTTP error."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/discover/tv?api_key=test_api_key&sort_by=popularity.desc&page=1&include_adult=false&include_video=false",
        status_code=401,
        text="Invalid API key"
    )

    with pytest.raises(RuntimeError) as exc_info:
        discover_tv_shows_from_tmdb()

    assert "TMDB API error" in str(exc_info.value)
    assert "401" in str(exc_info.value)


def test_discover_tv_shows_raises_runtime_error_on_invalid_json(monkeypatch, httpx_mock: HTTPXMock):
    """Test that RuntimeError is raised when TMDB API returns invalid JSON."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/discover/tv?api_key=test_api_key&sort_by=popularity.desc&page=1&include_adult=false&include_video=false",
        content=b"Not valid JSON!"
    )

    with pytest.raises(RuntimeError) as exc_info:
        discover_tv_shows_from_tmdb()

    assert "invalid JSON" in str(exc_info.value)


def test_discover_tv_shows_raises_connection_error_on_request_failure(monkeypatch, httpx_mock: HTTPXMock):
    """Test that ConnectionError is raised when unable to connect to TMDB API."""
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    httpx_mock.add_exception(
        httpx.RequestError("Connection refused"),
        url="https://api.themoviedb.org/3/discover/tv?api_key=test_api_key&sort_by=popularity.desc&page=1&include_adult=false&include_video=false"
    )

    with pytest.raises(ConnectionError) as exc_info:
        discover_tv_shows_from_tmdb()

    assert "Failed to connect to TMDB API" in str(exc_info.value)
