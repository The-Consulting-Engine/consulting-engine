"""
Test script for Apify Google Maps scraper.

Run from backend directory:
    cd backend
    python -m app.competitor_analysis.test_apify

This completely bypasses the Google Places API - Apify scrapes Google Maps directly.
"""

import asyncio
from dotenv import load_dotenv

# Load .env from project root
load_dotenv("../.env")

from app.competitor_analysis.apify_scraper import ApifyScraper


async def main():
    # Your test parameters
    location = "316 Elm St, New Haven, CT 06511"
    keyword = "restaurants"
    max_results = 10  # Keep small for testing (Apify charges per result)

    print("=" * 60)
    print("APIFY GOOGLE MAPS SCRAPER TEST")
    print("=" * 60)
    print(f"Location: {location}")
    print(f"Keyword: {keyword}")
    print(f"Max results: {max_results}")
    print("-" * 60)

    async with ApifyScraper() as scraper:
        # Search for restaurants
        print("\n[1] Searching for restaurants via Apify...")
        print("    (This may take 1-3 minutes as Apify scrapes Google Maps)\n")

        places = await scraper.search_restaurants(
            location=location,
            keyword=keyword,
            max_results=max_results,
            scrape_reviews=True,
            max_reviews=5,  # Just a few reviews per place for testing
        )

        print(f"\n[2] Found {len(places)} restaurants\n")

        # Display results
        print("=" * 60)
        print("COMPETITORS FOUND")
        print("=" * 60)

        for i, place in enumerate(places, 1):
            rating_str = f"{place.rating}*" if place.rating else "N/A"
            reviews_str = f"({place.user_ratings_total} reviews)" if place.user_ratings_total else ""
            price_str = place.price_level.value if place.price_level else ""

            print(f"\n{i}. {place.name}")
            print(f"   Address: {place.address}")
            print(f"   Rating: {rating_str} {reviews_str}  Price: {price_str}")
            print(f"   Phone: {place.phone_number or 'N/A'}")
            print(f"   Website: {place.website or 'N/A'}")
            print(f"   Categories: {', '.join(place.types[:3]) if place.types else 'N/A'}")

            # Show sample review if available
            if place.reviews:
                review = place.reviews[0]
                text = review.get("text", "")[:150]
                print(f"   Sample review: \"{text}...\"")
                print(f"                  - {review.get('author_name')}, {review.get('rating')}*")

        # Summary stats
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)

        ratings = [p.rating for p in places if p.rating]
        if ratings:
            avg_rating = sum(ratings) / len(ratings)
            print(f"Average rating: {avg_rating:.1f}*")

        price_counts = {}
        for p in places:
            if p.price_level:
                price_counts[p.price_level.value] = price_counts.get(p.price_level.value, 0) + 1
        if price_counts:
            print(f"Price distribution: {price_counts}")


if __name__ == "__main__":
    asyncio.run(main())
