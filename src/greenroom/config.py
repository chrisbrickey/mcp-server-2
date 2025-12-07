"""Configuration constants for the greenroom MCP server.

This module contains all configurable constants for genre categorization
and mood mapping. Modify these values to customize genre categorization behavior.
"""

from enum import Enum
from typing import Dict, List

# =============================================================================
# Genre Property Keys
# =============================================================================

GENRE_ID = "id"
"""Key for the TMDB genre ID in the genre properties dictionary."""

HAS_FILMS = "has_films"
"""Key indicating whether a genre is available for films."""

HAS_TV_SHOWS = "has_tv_shows"
"""Key indicating whether a genre is available for TV shows."""


# =============================================================================
# Mood Category Enum
# =============================================================================

class Mood(str, Enum):
    """Mood categories for classification.

    Inherits from str to ensure values are JSON-serializable while
    maintaining type safety and IDE autocomplete support.
    """
    DARK = "Dark"
    """Mood category for suspenseful, scary, intense topics."""

    LIGHT = "Light"
    """Mood category for uplifting, cheerful, entertaining topics."""

    SERIOUS = "Serious"
    """Mood category for educational, thought-provoking, heavy topics."""

    FUN = "Fun"
    """Mood category for exciting, adventurous, escapist topics."""

    OTHER = "Other"
    """Fallback mood category for genres that don't fit other categories."""


# =============================================================================
# Genre-to-Mood Mappings
# =============================================================================
# Hardcoded mappings for known genres. Unknown genres will be categorized
# using LLM sampling when available.

GENRE_MOOD_MAP = {
    # Dark moods - suspenseful, scary, intense
    "Horror": Mood.DARK,
    "Thriller": Mood.DARK,
    "Crime": Mood.DARK,
    "Mystery": Mood.DARK,

    # Light moods - uplifting, cheerful, entertaining
    "Comedy": Mood.LIGHT,
    "Family": Mood.LIGHT,
    "Kids": Mood.LIGHT,
    "Animation": Mood.LIGHT,
    "Romance": Mood.LIGHT,

    # Serious moods - educational, thought-provoking, heavy topics
    "Documentary": Mood.SERIOUS,
    "History": Mood.SERIOUS,
    "War": Mood.SERIOUS,
    "Drama": Mood.SERIOUS,
    "News": Mood.SERIOUS,
    "War & Politics": Mood.SERIOUS,

    # Fun moods - exciting, adventurous, escapist
    "Action": Mood.FUN,
    "Adventure": Mood.FUN,
    "Action & Adventure": Mood.FUN,
    "Fantasy": Mood.FUN,
    "Science Fiction": Mood.FUN,
    "Sci-Fi & Fantasy": Mood.FUN,
    "Music": Mood.FUN,
}

# =============================================================================
# Ollama Agent Configuration
# =============================================================================

OLLAMA_BASE_URL = "http://localhost:11434"
"""Base URL for Ollama API server."""

OLLAMA_DEFAULT_MODEL = "llama3.2:latest"
"""Default Ollama model to use for agent comparisons."""

OLLAMA_TIMEOUT = 30.0
"""Timeout in seconds for Ollama API requests."""