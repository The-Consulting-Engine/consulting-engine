"""
Competitor Analysis Module

This module provides restaurant/competitor analysis using:
- Google Places API for discovering competitors within a vicinity
- Apify platform for scraping detailed competitor data (reviews, menus, etc.)
- LLM-powered menu grouping and strategic analysis

Integrated into the main consulting engine pipeline via API routes.
"""

from .models import CompetitorProfile, SearchArea, AnalysisResult
from .google_places import GooglePlacesClient
from .apify_scraper import ApifyScraper
from .analyzer import CompetitorAnalyzer
from .pipeline import CompetitorAnalysisPipeline, PipelineConfig, PipelineResult
from .strategic_analyzer import (
    validate_premium_pricing,
    PricePositioning,
    PremiumValidation,
    MenuComplexity,
    CompetitiveGap,
)
from .price_analyzer import analyze_prices

__all__ = [
    # Models
    "CompetitorProfile",
    "SearchArea",
    "AnalysisResult",
    # Clients
    "GooglePlacesClient",
    "ApifyScraper",
    "CompetitorAnalyzer",
    # Pipeline
    "CompetitorAnalysisPipeline",
    "PipelineConfig",
    "PipelineResult",
    # Analysis
    "analyze_prices",
    "validate_premium_pricing",
    "PricePositioning",
    "PremiumValidation",
    "MenuComplexity",
    "CompetitiveGap",
]
