"""
Test the full competitor analysis pipeline:
1. Google Places API → Discover competitors
2. Apify → Enrich with reviews & prices

Run from backend directory:
    cd backend
    python -m app.competitor_analysis.test_full_pipeline
"""

import asyncio
from dotenv import load_dotenv

# Load .env from project root
load_dotenv("../.env")

from app.competitor_analysis.models import SearchArea
from app.competitor_analysis.google_places import GooglePlacesClient
from app.competitor_analysis.apify_scraper import ApifyScraper


async def main():
    # Configuration
    restaurant_name = "Nice Day Chinese"
    address = "316 Elm St, New Haven, CT 06511"
    cuisine = ["chinese restaurant"]  # Custom cuisine keywords
    radius_meters = 2000
    max_competitors = 5  # Keep small for testing (Apify costs $)
    max_reviews_per_competitor = 10

    print("=" * 70)
    print("FULL COMPETITOR ANALYSIS PIPELINE")
    print("=" * 70)
    print(f"Target: {restaurant_name}")
    print(f"Location: {address}")
    print(f"Cuisine: {cuisine}")
    print(f"Radius: {radius_meters}m")
    print("=" * 70)

    async with GooglePlacesClient() as google, ApifyScraper() as apify:

        # ============================================================
        # STEP 1: Discover competitors via Google Places API
        # ============================================================
        print("\n[STEP 1] DISCOVERING COMPETITORS (Google Places API)")
        print("-" * 50)

        # First, geocode the address to get coordinates
        lat, lng = await google.geocode_address(address)
        print(f"Location: {lat}, {lng}")

        # Search for competitors
        all_competitors = []
        for keyword in cuisine:
            print(f"\nSearching for '{keyword}'...")
            search_area = SearchArea(
                latitude=lat,
                longitude=lng,
                radius_meters=radius_meters,
                keyword=keyword,
            )
            results = await google.search_nearby(search_area, max_results=max_competitors)

            # Filter out the target restaurant
            for place in results:
                if restaurant_name.lower() not in place.name.lower():
                    all_competitors.append(place)

            print(f"  Found {len(results)} results")

        # Dedupe by place_id
        seen = set()
        unique_competitors = []
        for c in all_competitors:
            if c.place_id not in seen:
                seen.add(c.place_id)
                unique_competitors.append(c)

        # Limit for testing
        basic_competitors = unique_competitors[:max_competitors]

        print(f"\nDiscovered {len(basic_competitors)} unique competitors")

        # Get Place Details for each (to get Google Maps URL)
        print("Fetching Place Details (for Google Maps URLs)...")
        competitors = []
        for c in basic_competitors:
            try:
                detailed = await google.get_place_details(c.place_id)
                competitors.append(detailed)
                print(f"  ✓ {detailed.name} - URL: {detailed.google_maps_url[:50] if detailed.google_maps_url else 'N/A'}...")
            except Exception as e:
                print(f"  ✗ {c.name} - Failed: {e}")
                competitors.append(c)  # Use basic info as fallback

        # ============================================================
        # STEP 2: Enrich with reviews via Apify
        # ============================================================
        print("\n" + "=" * 70)
        print("[STEP 2] ENRICHING WITH REVIEWS (Apify)")
        print("-" * 50)
        print(f"Scraping reviews for {len(competitors)} competitors...")
        print("(This may take a few minutes)\n")

        enriched_data = await apify.enrich_competitors_batch(
            competitors,
            max_reviews_per_place=max_reviews_per_competitor,
            max_concurrent=2,  # Don't overload Apify
        )

        # ============================================================
        # RESULTS
        # ============================================================
        print("\n" + "=" * 70)
        print("COMPETITOR ANALYSIS RESULTS")
        print("=" * 70)

        for competitor in competitors:
            reviews_data = enriched_data.get(competitor.place_id)

            print(f"\n{'─' * 50}")
            print(f"📍 {competitor.name}")
            print(f"   Address: {competitor.address}")

            # Google Places data
            rating = f"{competitor.rating}*" if competitor.rating else "N/A"
            reviews = competitor.user_ratings_total or 0
            price = competitor.price_level.value if competitor.price_level else "N/A"
            print(f"   Google: {rating} ({reviews} reviews) | Price: {price}")

            # Apify enriched data
            if reviews_data and reviews_data.reviews:
                print(f"   Scraped: {len(reviews_data.reviews)} reviews")

                # Show sample reviews
                print(f"\n   Sample reviews:")
                for review in reviews_data.reviews[:3]:
                    text = review.get("text", "")[:100]
                    stars = review.get("rating", "?")
                    author = review.get("author", "Anonymous")
                    print(f"   • \"{text}...\"")
                    print(f"     — {author}, {stars}*")
            else:
                print(f"   Scraped: No reviews found")

        # Summary
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)

        ratings = [c.rating for c in competitors if c.rating]
        if ratings:
            avg = sum(ratings) / len(ratings)
            print(f"Average competitor rating: {avg:.1f}*")

        total_reviews_scraped = sum(
            len(d.reviews) for d in enriched_data.values() if d
        )
        print(f"Total reviews scraped: {total_reviews_scraped}")


if __name__ == "__main__":
    asyncio.run(main())
