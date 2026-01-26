"""
Configuration for competitor analysis module.

Add these to your .env file:
    GOOGLE_PLACES_API_KEY=your_google_api_key
    APIFY_API_TOKEN=your_apify_token
"""

from pydantic_settings import BaseSettings
from typing import Optional


class CompetitorAnalysisSettings(BaseSettings):
    """Settings for competitor analysis module."""

    # Google Places API
    GOOGLE_PLACES_API_KEY: Optional[str] = None

    # Apify
    APIFY_API_TOKEN: Optional[str] = None

    # Default search parameters
    DEFAULT_SEARCH_RADIUS_METERS: int = 1500
    MAX_COMPETITORS_TO_ANALYZE: int = 20
    MAX_REVIEWS_PER_SOURCE: int = 100

    # Rate limiting (be nice to APIs)
    GOOGLE_REQUESTS_PER_SECOND: float = 10.0
    APIFY_CONCURRENT_ACTORS: int = 3

    # Caching (TODO: implement caching layer)
    CACHE_TTL_HOURS: int = 24  # How long to cache competitor data

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = CompetitorAnalysisSettings()
