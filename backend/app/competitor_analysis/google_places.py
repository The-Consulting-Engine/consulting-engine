"""
Google Places API client for competitor discovery.

Documentation: https://developers.google.com/maps/documentation/places/web-service/overview
"""

import asyncio
import os
from typing import Optional
import httpx

from .models import SearchArea, GooglePlaceResult, PriceLevel


class GooglePlacesClient:
    """Client for Google Places API to discover nearby competitors."""

    BASE_URL = "https://maps.googleapis.com/maps/api/place"
    GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"

    # Map Google's price_level (0-4) to our PriceLevel enum
    PRICE_LEVEL_MAP = {
        0: PriceLevel.FREE,
        1: PriceLevel.INEXPENSIVE,
        2: PriceLevel.MODERATE,
        3: PriceLevel.EXPENSIVE,
        4: PriceLevel.VERY_EXPENSIVE,
    }

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Google Places client.

        Args:
            api_key: Google Maps API key. If not provided, reads from GOOGLE_PLACES_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("GOOGLE_PLACES_API_KEY")
        if not self.api_key:
            raise ValueError("Google Places API key required. Set GOOGLE_PLACES_API_KEY env var.")

        self._client = httpx.AsyncClient(timeout=30.0)

    async def search_nearby(
        self,
        search_area: SearchArea,
        max_results: int = 60
    ) -> list[GooglePlaceResult]:
        """
        Search for restaurants/competitors near a location.

        Uses the Nearby Search endpoint:
        https://developers.google.com/maps/documentation/places/web-service/search-nearby

        Args:
            search_area: Search parameters including location and filters.
            max_results: Maximum results to return (up to 60, Google's limit).

        Returns:
            List of GooglePlaceResult objects.
        """
        # Geocode address if lat/lng not provided
        if search_area.latitude is None or search_area.longitude is None:
            if not search_area.address:
                raise ValueError("Either lat/lng or address must be provided")
            lat, lng = await self.geocode_address(search_area.address)
        else:
            lat, lng = search_area.latitude, search_area.longitude

        # Build request params
        params = {
            "location": f"{lat},{lng}",
            "radius": search_area.radius_meters,
            "type": "restaurant",
            "key": self.api_key,
        }
        if search_area.keyword:
            params["keyword"] = search_area.keyword
        if search_area.open_now:
            params["opennow"] = "true"

        # Fetch results (with pagination)
        all_results = []
        url = f"{self.BASE_URL}/nearbysearch/json"

        while len(all_results) < max_results:
            response = await self._client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            if data.get("status") not in ("OK", "ZERO_RESULTS"):
                error_msg = data.get("error_message", data.get("status", "Unknown error"))
                raise Exception(f"Google Places API error: {error_msg}")

            # Parse results
            for place in data.get("results", []):
                parsed = self._parse_place(place, center_lat=lat, center_lng=lng)

                # Apply min_rating filter if specified
                if search_area.min_rating and parsed.rating:
                    if parsed.rating < search_area.min_rating:
                        continue

                all_results.append(parsed)

            # Check for more pages
            next_page_token = data.get("next_page_token")
            if not next_page_token or len(all_results) >= max_results:
                break

            # Google requires a short delay before using next_page_token
            await asyncio.sleep(2)
            params = {"pagetoken": next_page_token, "key": self.api_key}

        return all_results[:max_results]

    async def get_place_details(self, place_id: str) -> GooglePlaceResult:
        """
        Get detailed information about a specific place.

        Uses the Place Details endpoint:
        https://developers.google.com/maps/documentation/places/web-service/details

        Args:
            place_id: Google Place ID.

        Returns:
            Enriched GooglePlaceResult with additional details.
        """
        fields = [
            "place_id",
            "name",
            "formatted_address",
            "geometry",
            "rating",
            "user_ratings_total",
            "price_level",
            "types",
            "formatted_phone_number",
            "website",
            "opening_hours",
            "reviews",
            "business_status",
            "url",  # Google Maps URL for Apify scraping
        ]

        params = {
            "place_id": place_id,
            "fields": ",".join(fields),
            "key": self.api_key,
        }

        url = f"{self.BASE_URL}/details/json"
        response = await self._client.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if data.get("status") != "OK":
            error_msg = data.get("error_message", data.get("status", "Unknown error"))
            raise Exception(f"Google Places API error: {error_msg}")

        result = data.get("result", {})

        # Parse location
        geometry = result.get("geometry", {})
        location = geometry.get("location", {})

        # Parse price level
        price_level = None
        if "price_level" in result:
            price_level = self.PRICE_LEVEL_MAP.get(result["price_level"])

        return GooglePlaceResult(
            place_id=result.get("place_id", place_id),
            name=result.get("name", "Unknown"),
            address=result.get("formatted_address", ""),
            latitude=location.get("lat", 0),
            longitude=location.get("lng", 0),
            rating=result.get("rating"),
            user_ratings_total=result.get("user_ratings_total"),
            price_level=price_level,
            types=result.get("types", []),
            business_status=result.get("business_status"),
            phone_number=result.get("formatted_phone_number"),
            website=result.get("website"),
            opening_hours=result.get("opening_hours"),
            reviews=result.get("reviews"),
            google_maps_url=result.get("url"),  # Direct Google Maps URL
        )

    async def geocode_address(self, address: str) -> tuple[float, float]:
        """
        Convert an address to latitude/longitude coordinates.

        Args:
            address: Human-readable address string.

        Returns:
            Tuple of (latitude, longitude).
        """
        params = {"address": address, "key": self.api_key}
        response = await self._client.get(self.GEOCODE_URL, params=params)
        response.raise_for_status()
        data = response.json()

        if data.get("status") != "OK":
            error_msg = data.get("error_message", data.get("status", "Unknown error"))
            raise Exception(f"Geocoding error for '{address}': {error_msg}")

        results = data.get("results", [])
        if not results:
            raise Exception(f"No geocoding results for '{address}'")

        location = results[0]["geometry"]["location"]
        return location["lat"], location["lng"]

    def _parse_place(
        self,
        raw_place: dict,
        center_lat: Optional[float] = None,
        center_lng: Optional[float] = None,
    ) -> GooglePlaceResult:
        """Parse raw Google Places API response into structured model."""
        geometry = raw_place.get("geometry", {})
        location = geometry.get("location", {})

        # Parse price level
        price_level = None
        if "price_level" in raw_place:
            price_level = self.PRICE_LEVEL_MAP.get(raw_place["price_level"])

        result = GooglePlaceResult(
            place_id=raw_place.get("place_id", ""),
            name=raw_place.get("name", "Unknown"),
            address=raw_place.get("vicinity", raw_place.get("formatted_address", "")),
            latitude=location.get("lat", 0),
            longitude=location.get("lng", 0),
            rating=raw_place.get("rating"),
            user_ratings_total=raw_place.get("user_ratings_total"),
            price_level=price_level,
            types=raw_place.get("types", []),
            business_status=raw_place.get("business_status"),
        )

        return result

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
