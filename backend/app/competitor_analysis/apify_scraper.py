"""
Apify integration for scraping competitor details (reviews, prices).

This is used for ENRICHMENT after Google Places API discovers competitors.
Flow: Google Places (discovery) → Apify (enrichment with reviews/prices)

Apify docs: https://docs.apify.com/api/v2
"""

import asyncio
import os
from datetime import datetime
from typing import Optional
import httpx

from .models import ApifyScrapedData, GooglePlaceResult, PriceLevel


class ApifyScraper:
    """Client for Apify platform to scrape reviews and prices for competitors."""

    BASE_URL = "https://api.apify.com/v2"

    # Actor IDs from Apify store (use tilde for API calls)
    ACTORS = {
        "google_reviews": "compass~google-maps-reviews-scraper",
        "yelp": "yin~yelp-scraper",
        "tripadvisor": "maxcopell~tripadvisor-scraper",
        "uber_eats": "borderline~uber-eats-scraper-ppr",
    }

    def __init__(self, api_token: Optional[str] = None):
        """
        Initialize the Apify client.

        Args:
            api_token: Apify API token. If not provided, reads from APIFY_API_TOKEN env var.
        """
        self.api_token = api_token or os.getenv("APIFY_API_TOKEN")
        if not self.api_token:
            raise ValueError("Apify API token required. Set APIFY_API_TOKEN env var.")

        self._client = httpx.AsyncClient(timeout=300.0)

    async def scrape_reviews(
        self,
        place_name: str,
        address: str,
        max_reviews: int = 50,
    ) -> ApifyScrapedData:
        """
        Scrape Google reviews for a specific restaurant.

        Args:
            place_name: Name of the restaurant (e.g., "Nice Day Chinese")
            address: Address for disambiguation (e.g., "New Haven, CT")
            max_reviews: Maximum reviews to scrape

        Returns:
            ApifyScrapedData with reviews, ratings, and any available price info
        """
        # Build search query to find the specific place
        search_query = f"{place_name}, {address}"

        input_data = {
            "searchStringsArray": [search_query],
            "maxCrawledPlaces": 1,  # Just the one place
            "maxReviews": max_reviews,
            "language": "en",
        }

        print(f"  Scraping reviews for: {place_name}")
        results = await self._run_actor(self.ACTORS["google_reviews"], input_data)

        if not results:
            return ApifyScrapedData(
                source="google_reviews",
                reviews=[],
                review_count=0,
            )

        # This actor returns each review as a separate item
        return self._parse_reviews_list(results)

    async def scrape_reviews_by_url(
        self,
        google_maps_url: str,
        max_reviews: int = 50,
    ) -> ApifyScrapedData:
        """
        Scrape reviews using a direct Google Maps URL (most reliable method).

        Args:
            google_maps_url: Full Google Maps URL from Place Details API
            max_reviews: Maximum reviews to scrape

        Returns:
            ApifyScrapedData with reviews and ratings
        """
        input_data = {
            "startUrls": [{"url": google_maps_url}],
            "maxReviews": max_reviews,
            "language": "en",
        }

        print(f"  Scraping reviews via URL: {google_maps_url[:60]}...")
        results = await self._run_actor(self.ACTORS["google_reviews"], input_data)

        if not results:
            return ApifyScrapedData(
                source="google_reviews",
                reviews=[],
                review_count=0,
            )

        # This actor returns each review as a separate item in results
        # So results IS the list of reviews, not results[0].reviews
        return self._parse_reviews_list(results)

    async def scrape_reviews_by_place_id(
        self,
        place_id: str,
        max_reviews: int = 50,
    ) -> ApifyScrapedData:
        """
        Scrape reviews using Google Place ID (more accurate than name search).

        Args:
            place_id: Google Place ID from Places API
            max_reviews: Maximum reviews to scrape

        Returns:
            ApifyScrapedData with reviews and ratings
        """
        # Construct Google Maps URL from place ID
        google_maps_url = f"https://www.google.com/maps/place/?q=place_id:{place_id}"

        input_data = {
            "startUrls": [{"url": google_maps_url}],
            "maxReviews": max_reviews,
            "language": "en",
        }

        print(f"  Scraping reviews for place_id: {place_id}")
        results = await self._run_actor(self.ACTORS["google_reviews"], input_data)

        if not results:
            return ApifyScrapedData(
                source="google_reviews",
                reviews=[],
                review_count=0,
            )

        # This actor returns each review as a separate item
        return self._parse_reviews_list(results)

    async def enrich_competitor(
        self,
        competitor: GooglePlaceResult,
        max_reviews: int = 30,
    ) -> ApifyScrapedData:
        """
        Enrich a competitor (from Google Places) with scraped reviews and prices.

        Args:
            competitor: GooglePlaceResult from Places API discovery
            max_reviews: Maximum reviews to scrape

        Returns:
            ApifyScrapedData with reviews, ratings, prices
        """
        # Use Google Maps URL if available (most accurate)
        if competitor.google_maps_url:
            return await self.scrape_reviews_by_url(
                google_maps_url=competitor.google_maps_url,
                max_reviews=max_reviews,
            )

        # Fallback to name + address search
        return await self.scrape_reviews(
            place_name=competitor.name,
            address=competitor.address,
            max_reviews=max_reviews,
        )

    async def enrich_competitors_batch(
        self,
        competitors: list[GooglePlaceResult],
        max_reviews_per_place: int = 20,
        max_concurrent: int = 3,
    ) -> dict[str, ApifyScrapedData]:
        """
        Enrich multiple competitors with reviews (with concurrency limit).

        Args:
            competitors: List of GooglePlaceResults from discovery
            max_reviews_per_place: Max reviews to scrape per competitor
            max_concurrent: Max concurrent Apify jobs

        Returns:
            Dict mapping place_id to ApifyScrapedData
        """
        results = {}
        semaphore = asyncio.Semaphore(max_concurrent)

        async def enrich_one(competitor: GooglePlaceResult):
            async with semaphore:
                try:
                    data = await self.enrich_competitor(
                        competitor,
                        max_reviews=max_reviews_per_place
                    )
                    results[competitor.place_id] = data
                except Exception as e:
                    print(f"  Failed to enrich {competitor.name}: {e}")
                    results[competitor.place_id] = ApifyScrapedData(
                        source="google_reviews",
                        reviews=[],
                        review_count=0,
                    )

        # Run all enrichments with concurrency limit
        await asyncio.gather(*[enrich_one(c) for c in competitors])

        return results

    async def scrape_ubereats_menu(
        self,
        restaurant_name: str,
        address: str,
    ) -> dict:
        """
        Scrape Uber Eats menu and pricing data for a restaurant.

        Args:
            restaurant_name: Name of the restaurant
            address: Full address or city/state for location context

        Returns:
            Dict with menu items, prices, and restaurant info from Uber Eats
        """
        # Input format for borderline~uber-eats-scraper-ppr
        input_data = {
            "query": restaurant_name,
            "address": address,
            "locale": "en-US",
            "maxRows": 1,  # Just need the one restaurant
        }

        print(f"  Scraping Uber Eats for: {restaurant_name}")
        results = await self._run_actor(self.ACTORS["uber_eats"], input_data)

        if not results:
            return {
                "source": "uber_eats",
                "found": False,
                "restaurant_name": restaurant_name,
                "menu_items": [],
                "price_range": None,
            }

        # Parse the first result (the matched restaurant)
        return self._parse_ubereats_result(results[0] if results else {}, restaurant_name)

    async def scrape_ubereats_batch(
        self,
        competitors: list[GooglePlaceResult],
        max_concurrent: int = 3,
    ) -> dict[str, dict]:
        """
        Scrape Uber Eats menu data for multiple competitors.

        Args:
            competitors: List of GooglePlaceResults from discovery
            max_concurrent: Max concurrent Apify jobs

        Returns:
            Dict mapping place_id to Uber Eats menu data
        """
        results = {}
        semaphore = asyncio.Semaphore(max_concurrent)

        async def scrape_one(competitor: GooglePlaceResult):
            async with semaphore:
                try:
                    data = await self.scrape_ubereats_menu(
                        restaurant_name=competitor.name,
                        address=competitor.address,
                    )
                    results[competitor.place_id] = data
                except Exception as e:
                    print(f"  Failed to scrape Uber Eats for {competitor.name}: {e}")
                    results[competitor.place_id] = {
                        "source": "uber_eats",
                        "found": False,
                        "restaurant_name": competitor.name,
                        "error": str(e),
                    }

        await asyncio.gather(*[scrape_one(c) for c in competitors])
        return results

    def _parse_ubereats_result(self, item: dict, restaurant_name: str) -> dict:
        """Parse Uber Eats scraper result into structured menu data."""
        # Extract menu items with prices
        # Menu structure: list of categories, each with catalogItems
        menu_items = []
        raw_menu = item.get("menu") or []

        for category in raw_menu:
            category_name = category.get("catalogName") or "Other"
            catalog_items = category.get("catalogItems") or []

            for menu_item in catalog_items:
                # Price is in cents, priceTagline is formatted (e.g., "$11.69")
                price = menu_item.get("priceTagline") or menu_item.get("price")
                if isinstance(price, int):
                    price = f"${price / 100:.2f}"

                parsed_item = {
                    "name": menu_item.get("title") or menu_item.get("titleBadge") or "",
                    "description": menu_item.get("itemDescription") or "",
                    "price": price,
                    "category": category_name,
                    "image_url": menu_item.get("imageUrl"),
                    "is_available": menu_item.get("isAvailable", True),
                }
                if parsed_item["name"]:
                    menu_items.append(parsed_item)

        # Parse rating - can be a dict like {'ratingValue': 4.7, 'reviewCount': '700+'}
        rating_data = item.get("rating") or {}
        if isinstance(rating_data, dict):
            rating = rating_data.get("ratingValue")
            rating_count = rating_data.get("reviewCount")
        else:
            rating = rating_data
            rating_count = None

        # Parse delivery time from etaRange
        eta_range = item.get("etaRange") or {}
        if isinstance(eta_range, dict):
            delivery_time = eta_range.get("text") or f"{eta_range.get('min', '?')}-{eta_range.get('max', '?')} min"
        else:
            delivery_time = eta_range

        # Parse fare/delivery fee from fareBadge
        fare_badge = item.get("fareBadge") or {}
        delivery_fee = fare_badge.get("text") if isinstance(fare_badge, dict) else None

        return {
            "source": "uber_eats",
            "found": True,
            "restaurant_name": item.get("title") or restaurant_name,
            "ubereats_url": item.get("url"),
            "phone_number": item.get("phoneNumber"),
            "rating": rating,
            "rating_count": rating_count,
            "price_range": item.get("priceRange"),
            "delivery_fee": delivery_fee,
            "delivery_time": delivery_time,
            "categories": item.get("cuisineList") or item.get("categories") or [],
            "location": item.get("location"),
            "is_open": item.get("isOpen"),
            "hours": item.get("hours"),
            "menu_items": menu_items,
            "menu_item_count": len(menu_items),
            "raw_data": item,
        }

    def _parse_reviews_list(self, results: list[dict]) -> ApifyScrapedData:
        """
        Parse results where each item IS a review (compass~google-maps-reviews-scraper format).

        This actor returns:
        [
            {"name": "Reviewer1", "text": "Great food...", "stars": 5, ...},
            {"name": "Reviewer2", "text": "Okay place...", "stars": 3, ...},
        ]
        """
        reviews = []
        total_stars = 0
        rated_count = 0

        for r in results:
            # Parse each review item
            stars = r.get("stars") or r.get("rating") or r.get("reviewRating")
            review = {
                "text": r.get("text") or r.get("reviewText") or "",
                "rating": stars,
                "author": r.get("name") or r.get("reviewerName") or "Anonymous",
                "date": r.get("publishAt") or r.get("publishedAt") or r.get("date"),
                "likes": r.get("likesCount") or r.get("likes") or 0,
                "reviewer_url": r.get("reviewerUrl"),
                "is_local_guide": r.get("isLocalGuide", False),
            }
            reviews.append(review)

            if stars:
                total_stars += stars
                rated_count += 1

        avg_rating = total_stars / rated_count if rated_count > 0 else None

        return ApifyScrapedData(
            source="google_reviews",
            scraped_at=datetime.utcnow(),
            reviews=reviews,
            review_count=len(reviews),
            average_rating=avg_rating,
            categories=[],
            price_range=None,
            menu_items=[],
            popular_dishes=[],
            raw_data={"reviews": results},  # Store raw for debugging
        )

    def _parse_scraped_data(self, item: dict) -> ApifyScrapedData:
        """Parse Apify scraper result into ApifyScrapedData."""
        # Try multiple possible field names for reviews
        raw_reviews = (
            item.get("reviews") or
            item.get("reviewsData") or
            item.get("userReviews") or
            []
        )

        # Parse reviews - try multiple field name variations
        reviews = []
        for r in raw_reviews:
            review = {
                "text": r.get("text") or r.get("reviewText") or r.get("snippet") or "",
                "rating": r.get("stars") or r.get("rating") or r.get("reviewRating"),
                "author": r.get("name") or r.get("author") or r.get("reviewerName") or r.get("userName"),
                "date": r.get("publishedAtDate") or r.get("date") or r.get("reviewDate"),
                "likes": r.get("likesCount") or r.get("likes") or 0,
            }
            reviews.append(review)

        # Extract price info - try multiple field names
        price_range = item.get("price") or item.get("priceRange") or item.get("priceLevel")

        # Extract popular dishes/menu items if available
        popular_dishes = []
        menu_items = []

        if "menu" in item:
            menu_items = item.get("menu", [])
        if "popularTimesHistogram" in item:
            pass

        # Try multiple field names for review count and rating
        review_count = (
            item.get("reviewsCount") or
            item.get("totalReviews") or
            item.get("reviewCount") or
            len(raw_reviews)
        )

        avg_rating = (
            item.get("totalScore") or
            item.get("rating") or
            item.get("averageRating") or
            item.get("stars")
        )

        return ApifyScrapedData(
            source="google_reviews",
            scraped_at=datetime.utcnow(),
            reviews=reviews,
            review_count=review_count,
            average_rating=avg_rating,
            categories=item.get("categories") or item.get("category") or [],
            price_range=price_range,
            menu_items=menu_items,
            popular_dishes=popular_dishes,
            raw_data=item,
        )

    async def _run_actor(
        self,
        actor_id: str,
        input_data: dict,
        timeout_secs: int = 300,
        poll_interval: int = 5,
    ) -> list[dict]:
        """
        Run an Apify actor and return results.

        Args:
            actor_id: The actor ID (e.g., "compass~google-maps-reviews-scraper")
            input_data: Input configuration for the actor
            timeout_secs: Max wait time in seconds
            poll_interval: Seconds between status checks

        Returns:
            List of result items from the actor's dataset
        """
        # 1. Start the actor run
        start_url = f"{self.BASE_URL}/acts/{actor_id}/runs"
        headers = {"Authorization": f"Bearer {self.api_token}"}

        response = await self._client.post(
            start_url,
            json=input_data,
            headers=headers,
        )
        response.raise_for_status()
        run_data = response.json()

        run_id = run_data["data"]["id"]
        print(f"    Actor run started: {run_id}")

        # 2. Poll for completion
        status_url = f"{self.BASE_URL}/actor-runs/{run_id}"
        elapsed = 0

        while elapsed < timeout_secs:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

            response = await self._client.get(status_url, headers=headers)
            response.raise_for_status()
            status_data = response.json()

            status = status_data["data"]["status"]
            print(f"    Status: {status} ({elapsed}s)")

            if status == "SUCCEEDED":
                break
            elif status in ("FAILED", "ABORTED", "TIMED-OUT"):
                raise Exception(f"Actor run failed with status: {status}")

        if elapsed >= timeout_secs:
            raise Exception(f"Actor run timed out after {timeout_secs}s")

        # 3. Fetch results from dataset
        dataset_id = status_data["data"]["defaultDatasetId"]
        dataset_url = f"{self.BASE_URL}/datasets/{dataset_id}/items"

        response = await self._client.get(dataset_url, headers=headers)
        response.raise_for_status()

        results = response.json()
        print(f"    Got {len(results)} results")

        return results

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
