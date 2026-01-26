"""
Competitor Analysis Module (MVP Prototype)

This module provides restaurant/competitor analysis using:
- Google Places API for discovering competitors within a vicinity
- Apify platform for scraping detailed competitor data (reviews, menus, etc.)

This is a standalone MVP prototype - not yet integrated into the main pipeline.
"""

from .models import CompetitorProfile, SearchArea, AnalysisResult
from .google_places import GooglePlacesClient
from .apify_scraper import ApifyScraper
from .analyzer import CompetitorAnalyzer

__all__ = [
    "CompetitorProfile",
    "SearchArea",
    "AnalysisResult",
    "GooglePlacesClient",
    "ApifyScraper",
    "CompetitorAnalyzer",
]
