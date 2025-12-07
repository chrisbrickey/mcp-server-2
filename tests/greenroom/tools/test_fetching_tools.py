"""Tests for fetching_tools.py."""

import httpx
import pytest
from pytest_httpx import HTTPXMock

from greenroom.tools.fetching_tools import fetch_genres


def test_fetch_genres_combines_media_types(monkeypatch, httpx_mock: HTTPXMock):
    """Test list_genres returns combined film and TV genres."""
    # Set up environment
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    # Mock TMDB API responses
    film_genres = {
        "genres": [
            {"id": 28, "name": "Action"},
            {"id": 18, "name": "Drama"},
        ]
    }

    tv_genres = {
        "genres": [
            {"id": 18, "name": "Drama"},
            {"id": 9648, "name": "Mystery"},
        ]
    }

    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/genre/movie/list?api_key=test_api_key",
        json=film_genres
    )
    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/genre/tv/list?api_key=test_api_key",
        json=tv_genres
    )

    # Call the function
    result = fetch_genres()

    # Expected result structure
    expected = {
        "Drama": {
            "id": 18,
            "has_films": True,
            "has_tv_shows": True
        },
        "Action": {
            "id": 28,
            "has_films": True,
            "has_tv_shows": False
        },
        "Mystery": {
            "id": 9648,
            "has_films": False,
            "has_tv_shows": True
        }
    }

    # Single assertion comparing entire structure
    assert result == expected


def test_fetch_genres_drops_incomplete_genre_data(monkeypatch, httpx_mock: HTTPXMock):
    """Test that genres with missing id or name fields are silently dropped."""
    # Set up environment
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    # Mock TMDB API responses with incomplete data
    film_genres = {
        "genres": [
            {"id": 28, "name": "Action"},  # Valid
            {"id": 18},  # Missing name - should be dropped
            {"name": "Comedy"},  # Missing id - should be dropped
            {"id": 12, "name": "Adventure"},  # Valid
        ]
    }

    tv_genres = {
        "genres": [
            {"id": 18, "name": "Drama"},  # Valid
            {},  # Missing both - should be dropped
            {"id": 9648, "name": "Mystery"},  # Valid
        ]
    }

    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/genre/movie/list?api_key=test_api_key",
        json=film_genres
    )
    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/genre/tv/list?api_key=test_api_key",
        json=tv_genres
    )

    # Call the function
    result = fetch_genres()

    # Expected result should only include valid genres
    expected = {
        "Action": {
            "id": 28,
            "has_films": True,
            "has_tv_shows": False
        },
        "Adventure": {
            "id": 12,
            "has_films": True,
            "has_tv_shows": False
        },
        "Drama": {
            "id": 18,
            "has_films": False,
            "has_tv_shows": True
        },
        "Mystery": {
            "id": 9648,
            "has_films": False,
            "has_tv_shows": True
        }
    }

    assert result == expected


def test_fetch_genres_raises_value_error_when_api_key_missing(monkeypatch):
    """Test that ValueError is raised when TMDB_API_KEY is not set."""
    # Ensure TMDB_API_KEY is not set
    monkeypatch.delenv("TMDB_API_KEY", raising=False)

    # Call the function and expect ValueError
    with pytest.raises(ValueError) as exc_info:
        fetch_genres()

    # Verify the error message mentions the API key
    assert "TMDB_API_KEY not configured" in str(exc_info.value)
    assert ".env file" in str(exc_info.value)


def test_fetch_genres_raises_runtime_error_on_http_error(monkeypatch, httpx_mock: HTTPXMock):
    """Test that RuntimeError is raised when TMDB API returns HTTP error."""
    # Set up environment
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    # Mock TMDB API to return 401 Unauthorized error
    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/genre/movie/list?api_key=test_api_key",
        status_code=401,
        text="Invalid API key"
    )

    # Call the function and expect RuntimeError
    with pytest.raises(RuntimeError) as exc_info:
        fetch_genres()

    # Verify the error message mentions the HTTP error
    assert "TMDB API error" in str(exc_info.value)
    assert "401" in str(exc_info.value)


def test_fetch_genres_raises_runtime_error_on_invalid_json(monkeypatch, httpx_mock: HTTPXMock):
    """Test that RuntimeError is raised when TMDB API returns invalid JSON."""
    # Set up environment
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    # Mock TMDB API to return invalid JSON for film endpoint
    # (Both endpoints need to be mocked since fetch_genres calls both)
    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/genre/movie/list?api_key=test_api_key",
        content=b"This is not valid JSON at all!"
    )

    httpx_mock.add_response(
        url="https://api.themoviedb.org/3/genre/tv/list?api_key=test_api_key",
        json={"genres": []}  # Valid response for TV endpoint
    )

    # Call the function and expect RuntimeError
    with pytest.raises(RuntimeError) as exc_info:
        fetch_genres()

    # Verify the error message mentions invalid JSON
    assert "invalid JSON" in str(exc_info.value)


def test_fetch_genres_raises_connection_error_on_request_failure(monkeypatch, httpx_mock: HTTPXMock):
    """Test that ConnectionError is raised when unable to connect to TMDB API."""
    # Set up environment
    monkeypatch.setenv("TMDB_API_KEY", "test_api_key")

    # Mock TMDB API to raise a connection error
    httpx_mock.add_exception(
        httpx.RequestError("Connection refused"),
        url="https://api.themoviedb.org/3/genre/movie/list?api_key=test_api_key"
    )

    # Call the function and expect ConnectionError
    with pytest.raises(ConnectionError) as exc_info:
        fetch_genres()

    # Verify the error message mentions connection failure
    assert "Failed to connect to TMDB API" in str(exc_info.value)
