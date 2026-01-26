"""
Data models for competitor analysis.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class PriceLevel(str, Enum):
    """Google Places price level mapping."""
    FREE = "FREE"
    INEXPENSIVE = "$"
    MODERATE = "$$"
    EXPENSIVE = "$$$"
    VERY_EXPENSIVE = "$$$$"


class SearchArea(BaseModel):
    """Defines the geographic search area for competitor discovery."""

    # Option 1: Center point + radius
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius_meters: int = Field(default=1500, description="Search radius in meters (max 50000)")

    # Option 2: Address-based (will be geocoded)
    address: Optional[str] = None

    # Search filters
    keyword: Optional[str] = Field(default=None, description="e.g., 'pizza', 'thai food', 'fine dining'")
    min_rating: Optional[float] = Field(default=None, ge=0, le=5)
    open_now: bool = False


class GooglePlaceResult(BaseModel):
    """Raw result from Google Places API."""

    place_id: str
    name: str
    address: str
    latitude: float
    longitude: float
    rating: Optional[float] = None
    user_ratings_total: Optional[int] = None
    price_level: Optional[PriceLevel] = None
    types: list[str] = Field(default_factory=list)
    business_status: Optional[str] = None

    # From Place Details (optional enrichment)
    phone_number: Optional[str] = None
    website: Optional[str] = None
    opening_hours: Optional[dict] = None
    reviews: Optional[list[dict]] = None
    google_maps_url: Optional[str] = None  # Direct Google Maps URL for Apify

    # Uber Eats menu/pricing link
    ubereats_search_url: Optional[str] = None  # Uber Eats search URL for menu pricing
    ubereats_data: Optional["UberEatsData"] = None  # Scraped menu/pricing data from Uber Eats


class UberEatsMenuItem(BaseModel):
    """A single menu item from Uber Eats."""
    name: str
    description: Optional[str] = None
    price: Optional[str] = None  # e.g., "$12.99"
    category: Optional[str] = None  # e.g., "Appetizers", "Main Courses"


class UberEatsData(BaseModel):
    """Menu and pricing data scraped from Uber Eats."""
    source: str = "uber_eats"
    found: bool = False
    restaurant_name: str
    ubereats_url: Optional[str] = None
    rating: Optional[float] = None
    rating_count: Optional[int] = None
    price_range: Optional[str] = None  # e.g., "$$"
    delivery_fee: Optional[str] = None
    delivery_time: Optional[str] = None  # e.g., "25-35 min"
    categories: list[str] = Field(default_factory=list)
    menu_items: list[UberEatsMenuItem] = Field(default_factory=list)
    menu_item_count: int = 0
    raw_data: Optional[dict] = None


class ApifyScrapedData(BaseModel):
    """Data scraped via Apify (e.g., from Yelp, TripAdvisor, Google reviews)."""

    source: str  # e.g., "yelp", "tripadvisor", "google_reviews"
    scraped_at: datetime = Field(default_factory=datetime.utcnow)

    # Review data
    reviews: list[dict] = Field(default_factory=list)
    review_count: Optional[int] = None
    average_rating: Optional[float] = None

    # Menu/pricing data (if available)
    menu_items: list[dict] = Field(default_factory=list)
    price_range: Optional[str] = None

    # Additional metadata
    photos: list[str] = Field(default_factory=list)
    popular_dishes: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)

    # Raw response for debugging
    raw_data: Optional[dict] = None


class CompetitorProfile(BaseModel):
    """Complete competitor profile combining all data sources."""

    # Core identity
    id: str  # Internal ID
    place_id: str  # Google Place ID
    name: str
    address: str

    # Location
    latitude: float
    longitude: float
    distance_meters: Optional[float] = None  # From search center

    # Google Places data
    google_rating: Optional[float] = None
    google_review_count: Optional[int] = None
    price_level: Optional[PriceLevel] = None
    website: Optional[str] = None
    phone: Optional[str] = None

    # Enriched data from Apify
    apify_data: list[ApifyScrapedData] = Field(default_factory=list)

    # Computed/analyzed fields (populated by analyzer)
    sentiment_score: Optional[float] = None
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class AnalysisResult(BaseModel):
    """Final analysis output for the competitor landscape."""

    # Search context
    search_area: SearchArea
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)

    # Discovered competitors
    competitors: list[CompetitorProfile] = Field(default_factory=list)
    total_found: int = 0

    # Market insights (populated by analyzer)
    market_summary: Optional[str] = None
    average_rating: Optional[float] = None
    price_distribution: dict[str, int] = Field(default_factory=dict)

    # Competitive positioning insights
    market_gaps: list[str] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)
    threats: list[str] = Field(default_factory=list)

    # Raw data for debugging
    raw_google_response: Optional[dict] = None
