"""
Competitor analysis engine.

Orchestrates the competitor discovery and analysis pipeline:
1. Discover competitors via Google Places API
2. Enrich with detailed data via Apify scrapers
3. Analyze and generate insights
"""

from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote_plus
import uuid

from .models import (
    SearchArea,
    CompetitorProfile,
    AnalysisResult,
    GooglePlaceResult,
)
from .google_places import GooglePlacesClient
from .apify_scraper import ApifyScraper


# Common cuisine/category mappings for search keywords
CUISINE_KEYWORDS = {
    # Cuisine types (from Google Places types)
    "italian_restaurant": "italian restaurant",
    "chinese_restaurant": "chinese restaurant",
    "japanese_restaurant": "japanese restaurant",
    "thai_restaurant": "thai restaurant",
    "indian_restaurant": "indian restaurant",
    "mexican_restaurant": "mexican restaurant",
    "vietnamese_restaurant": "vietnamese restaurant",
    "korean_restaurant": "korean restaurant",
    "french_restaurant": "french restaurant",
    "mediterranean_restaurant": "mediterranean restaurant",
    "greek_restaurant": "greek restaurant",
    "american_restaurant": "american restaurant",
    "seafood_restaurant": "seafood restaurant",
    "steakhouse": "steakhouse",
    "sushi_restaurant": "sushi restaurant",
    "pizza_restaurant": "pizza",
    "burger_restaurant": "burger restaurant",
    "barbecue_restaurant": "bbq restaurant",
    "vegetarian_restaurant": "vegetarian restaurant",
    "vegan_restaurant": "vegan restaurant",

    # Service styles
    "fast_food_restaurant": "fast food",
    "cafe": "cafe",
    "coffee_shop": "coffee shop",
    "bakery": "bakery",
    "bar": "bar",
    "pub": "pub",
    "brunch_restaurant": "brunch",
    "breakfast_restaurant": "breakfast restaurant",

    # Generic fallbacks
    "restaurant": "restaurant",
    "food": "restaurant",
    "meal_delivery": "restaurant",
    "meal_takeaway": "restaurant",
}

# Categories that indicate service style (can combine with cuisine)
SERVICE_STYLE_TYPES = {
    "fast_food_restaurant",
    "cafe",
    "coffee_shop",
    "bakery",
    "bar",
    "pub",
    "meal_delivery",
    "meal_takeaway",
}


def generate_ubereats_search_url(name: str, address: Optional[str] = None) -> str:
    """
    Generate an Uber Eats search URL for a restaurant.

    Args:
        name: Restaurant name.
        address: Full address (used to extract location for better search results).

    Returns:
        Uber Eats search URL in format: https://www.ubereats.com/search?q=<name>+<city>+<state>
    """
    # Build query: restaurant name + location
    query_parts = [name]

    # Extract city and state from address
    # Typical formats: "123 Main St, City, ST 12345" or "123 Main St, City, State"
    if address:
        parts = [p.strip() for p in address.split(",")]
        if len(parts) >= 3:
            # Format: "Street, City, State ZIP"
            city = parts[1]
            # State might have ZIP attached, extract just the state
            state_part = parts[2].split()[0] if parts[2] else ""
            query_parts.append(f"{city} {state_part}".strip())
        elif len(parts) == 2:
            # Format: "Street, City" - just append city
            query_parts.append(parts[1])

    query = " ".join(query_parts)
    encoded_query = quote_plus(query)

    return f"https://www.ubereats.com/search?q={encoded_query}"


@dataclass
class RestaurantIdentity:
    """Identified restaurant with its cuisine and style."""
    place: GooglePlaceResult
    cuisines: list[str]  # e.g., ["italian", "pizza"]
    service_styles: list[str]  # e.g., ["fast_food", "casual"]
    search_keywords: list[str]  # Keywords to use for competitor search


class CompetitorAnalyzer:
    """
    Main orchestrator for competitor analysis.

    Usage:
        async with CompetitorAnalyzer() as analyzer:
            # Option 1: General search
            result = await analyzer.analyze(
                SearchArea(address="123 Main St, San Francisco, CA", radius_meters=1000)
            )

            # Option 2: Cuisine-specific competitor search
            result = await analyzer.find_cuisine_competitors(
                address="316 Elm St, New Haven, CT",
                radius_meters=2000
            )
    """

    def __init__(
        self,
        google_api_key: Optional[str] = None,
        apify_token: Optional[str] = None,
    ):
        """
        Initialize the analyzer with API credentials.

        Args:
            google_api_key: Google Places API key (or set GOOGLE_PLACES_API_KEY env var)
            apify_token: Apify API token (or set APIFY_API_TOKEN env var)
        """
        self.google_client = GooglePlacesClient(api_key=google_api_key)
        self.apify_scraper = ApifyScraper(api_token=apify_token)

    async def identify_restaurant(
        self,
        name: Optional[str] = None,
        address: Optional[str] = None,
    ) -> RestaurantIdentity:
        """
        Identify a restaurant by name and/or address, then extract its cuisine/style.

        Args:
            name: Restaurant name (primary identifier).
            address: Street address (used for location context).

        Returns:
            RestaurantIdentity with cuisine types and search keywords.
        """
        if not name and not address:
            raise ValueError("Either name or address must be provided")

        # Build search query - name takes priority
        if name and address:
            # Search by name near the address location
            search_area = SearchArea(
                address=address,
                radius_meters=500,  # Wider radius since we'll match by name
                keyword=name,
            )
        elif name:
            # Name only - search more broadly
            search_area = SearchArea(
                address=name,  # Use name as address to geocode general area
                radius_meters=100,
                keyword=name,
            )
        else:
            # Address only - small radius
            search_area = SearchArea(
                address=address,
                radius_meters=50,
            )

        results = await self.google_client.search_nearby(search_area, max_results=10)

        if not results:
            raise Exception(f"No restaurant found for: {name or address}")

        # If name provided, find best match by name similarity
        if name:
            place = self._find_best_name_match(results, name)
        else:
            place = results[0]

        # Get detailed info to ensure we have all types
        detailed = await self.google_client.get_place_details(place.place_id)

        # Extract cuisines and service styles from place types
        cuisines = []
        service_styles = []
        search_keywords = []

        for place_type in detailed.types:
            if place_type in CUISINE_KEYWORDS:
                keyword = CUISINE_KEYWORDS[place_type]
                search_keywords.append(keyword)

                if place_type in SERVICE_STYLE_TYPES:
                    service_styles.append(place_type.replace("_restaurant", "").replace("_", " "))
                else:
                    # Extract cuisine name from type
                    cuisine = place_type.replace("_restaurant", "").replace("_", " ")
                    if cuisine not in ["restaurant", "food", "meal delivery", "meal takeaway"]:
                        cuisines.append(cuisine)

        # Deduplicate while preserving order
        search_keywords = list(dict.fromkeys(search_keywords))
        cuisines = list(dict.fromkeys(cuisines))

        # If no specific cuisine found, use generic
        if not search_keywords:
            search_keywords = ["restaurant"]

        return RestaurantIdentity(
            place=detailed,
            cuisines=cuisines,
            service_styles=service_styles,
            search_keywords=search_keywords,
        )

    def _find_best_name_match(
        self,
        results: list[GooglePlaceResult],
        target_name: str,
    ) -> GooglePlaceResult:
        """Find the result that best matches the target name."""
        target_lower = target_name.lower().strip()

        # Score each result by name similarity
        scored = []
        for place in results:
            place_name_lower = place.name.lower().strip()

            # Exact match
            if place_name_lower == target_lower:
                return place

            # Calculate simple similarity score
            score = 0

            # Check if target name is contained in place name or vice versa
            if target_lower in place_name_lower:
                score += 50
            if place_name_lower in target_lower:
                score += 50

            # Check word overlap
            target_words = set(target_lower.split())
            place_words = set(place_name_lower.split())
            common_words = target_words & place_words
            if common_words:
                score += len(common_words) * 20

            # Penalize if no overlap at all
            if score == 0:
                # Check if any word starts with same letters
                for tw in target_words:
                    for pw in place_words:
                        if tw[:3] == pw[:3] and len(tw) >= 3:
                            score += 10

            scored.append((score, place))

        # Sort by score descending, return best match
        scored.sort(key=lambda x: x[0], reverse=True)

        if scored and scored[0][0] > 0:
            return scored[0][1]

        # Fallback to first result if no good match
        return results[0]

    async def find_cuisine_competitors(
        self,
        name: Optional[str] = None,
        address: Optional[str] = None,
        radius_meters: int = 2000,
        max_competitors: int = 20,
        include_all_cuisines: bool = True,
        cuisine_override: Optional[list[str]] = None,
        enrich_ubereats: bool = False,
    ) -> dict:
        """
        Find competitors that serve the same cuisine/style as the target restaurant.

        This is a multi-step process:
        1. Identify the target restaurant and its cuisine type
        2. Search for nearby competitors in the same cuisine category
        3. Generate Uber Eats search URLs
        4. (Optional) Scrape Uber Eats for menu/pricing data

        Args:
            name: Restaurant name (primary identifier - use this!).
            address: Address for location context.
            radius_meters: Search radius for competitors.
            max_competitors: Max competitors to return.
            include_all_cuisines: If True, search for all cuisine types found.
                                  If False, only use the primary cuisine.
            cuisine_override: Custom list of cuisines/keywords to search for.
                              Examples: ["chinese restaurant", "asian food"]
                              If provided, skips auto-detection from Google.
            enrich_ubereats: If True, scrape Uber Eats for menu/pricing data.

        Returns:
            Dict with target restaurant info and list of competitors.
        """
        # Step 1: Identify the target restaurant
        search_desc = name or address
        print(f"[1] Identifying restaurant: {search_desc}")
        identity = await self.identify_restaurant(name=name, address=address)

        print(f"    Found: {identity.place.name}")
        print(f"    Cuisines: {identity.cuisines or ['General']}")
        print(f"    Service styles: {identity.service_styles or ['N/A']}")
        print(f"    Auto-detected keywords: {identity.search_keywords}")

        # Step 2: Search for competitors using cuisine keywords
        all_competitors = []
        seen_place_ids = {identity.place.place_id}  # Exclude the target restaurant

        # Use custom cuisine override if provided, otherwise use auto-detected
        if cuisine_override:
            keywords_to_search = cuisine_override
            print(f"    Using CUSTOM keywords: {keywords_to_search}")
        else:
            keywords_to_search = identity.search_keywords if include_all_cuisines else identity.search_keywords[:1]

        for keyword in keywords_to_search:
            print(f"\n[2] Searching for '{keyword}' within {radius_meters}m...")

            search_area = SearchArea(
                latitude=identity.place.latitude,
                longitude=identity.place.longitude,
                radius_meters=radius_meters,
                keyword=keyword,
            )

            results = await self.google_client.search_nearby(
                search_area,
                max_results=max_competitors
            )

            # Add unique competitors
            for place in results:
                if place.place_id not in seen_place_ids:
                    seen_place_ids.add(place.place_id)
                    all_competitors.append(place)

            print(f"    Found {len(results)} results, {len(all_competitors)} unique competitors total")

        # Sort by rating (highest first), then by review count
        all_competitors.sort(
            key=lambda p: (p.rating or 0, p.user_ratings_total or 0),
            reverse=True
        )

        # Limit to max_competitors
        all_competitors = all_competitors[:max_competitors]

        # Generate Uber Eats search URLs for menu pricing lookup
        print(f"\n[3] Generating Uber Eats search URLs for {len(all_competitors)} competitors...")
        for competitor in all_competitors:
            competitor.ubereats_search_url = generate_ubereats_search_url(
                name=competitor.name,
                address=competitor.address
            )

        # Also generate for the target restaurant
        target_ubereats_url = generate_ubereats_search_url(
            name=identity.place.name,
            address=identity.place.address
        )

        # Optional: Enrich with Uber Eats menu/pricing data
        target_ubereats_data = None
        if enrich_ubereats:
            await self.enrich_with_ubereats(all_competitors)
            # Also scrape target restaurant
            print(f"\n[5] Scraping Uber Eats for target: {identity.place.name}")
            target_ubereats_data = await self.apify_scraper.scrape_ubereats_menu(
                restaurant_name=identity.place.name,
                address=identity.place.address,
            )

        return {
            "target": {
                "name": identity.place.name,
                "address": identity.place.address,
                "place_id": identity.place.place_id,
                "rating": identity.place.rating,
                "review_count": identity.place.user_ratings_total,
                "price_level": identity.place.price_level.value if identity.place.price_level else None,
                "cuisines": identity.cuisines,
                "service_styles": identity.service_styles,
                "website": identity.place.website,
                "phone": identity.place.phone_number,
                "ubereats_search_url": target_ubereats_url,
                "ubereats_data": target_ubereats_data,
            },
            "search_criteria": {
                "keywords": keywords_to_search,
                "radius_meters": radius_meters,
            },
            "competitors": all_competitors,
            "total_found": len(all_competitors),
        }

    async def enrich_with_ubereats(
        self,
        competitors: list[GooglePlaceResult],
        max_concurrent: int = 3,
    ) -> list[GooglePlaceResult]:
        """
        Enrich competitors with Uber Eats menu and pricing data.

        Args:
            competitors: List of competitors to enrich
            max_concurrent: Max concurrent Apify jobs

        Returns:
            Same list of competitors with ubereats_data populated
        """
        print(f"\n[4] Enriching {len(competitors)} competitors with Uber Eats data...")

        ubereats_results = await self.apify_scraper.scrape_ubereats_batch(
            competitors=competitors,
            max_concurrent=max_concurrent,
        )

        # Attach Uber Eats data to each competitor
        for competitor in competitors:
            if competitor.place_id in ubereats_results:
                ue_data = ubereats_results[competitor.place_id]
                competitor.ubereats_data = ue_data
                if ue_data.get("found"):
                    print(f"    ✓ {competitor.name}: {ue_data.get('menu_item_count', 0)} menu items")
                else:
                    print(f"    ✗ {competitor.name}: Not found on Uber Eats")

        return competitors

    async def analyze(
        self,
        search_area: SearchArea,
        enrich_sources: list[str] = ["google_reviews"],
        max_competitors: int = 20,
    ) -> AnalysisResult:
        """
        Run full competitor analysis for an area (general search).

        Args:
            search_area: Geographic area to search.
            enrich_sources: Data sources for enrichment ("google_reviews", "yelp", "tripadvisor")
            max_competitors: Maximum competitors to analyze in detail.

        Returns:
            AnalysisResult with competitors and market insights.
        """
        # Step 1: Discover competitors
        google_results = await self.google_client.search_nearby(search_area)

        # Step 2: Build basic competitor profiles
        competitors = []
        for place in google_results[:max_competitors]:
            profile = CompetitorProfile(
                id=str(uuid.uuid4()),
                place_id=place.place_id,
                name=place.name,
                address=place.address,
                latitude=place.latitude,
                longitude=place.longitude,
                google_rating=place.rating,
                google_review_count=place.user_ratings_total,
                price_level=place.price_level,
            )
            competitors.append(profile)

        # Step 3: Build result
        result = AnalysisResult(
            search_area=search_area,
            competitors=competitors,
            total_found=len(google_results),
        )

        # Calculate basic stats
        ratings = [c.google_rating for c in competitors if c.google_rating]
        if ratings:
            result.average_rating = sum(ratings) / len(ratings)

        # Price distribution
        for c in competitors:
            if c.price_level:
                price_key = c.price_level.value
                result.price_distribution[price_key] = result.price_distribution.get(price_key, 0) + 1

        return result

    async def discover_competitors(
        self,
        search_area: SearchArea
    ) -> list[GooglePlaceResult]:
        """
        Discover competitors in the area using Google Places.

        Returns basic info (name, rating, location) without detailed enrichment.
        """
        return await self.google_client.search_nearby(search_area)

    async def close(self):
        """Clean up resources."""
        await self.google_client.close()
        await self.apify_scraper.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
