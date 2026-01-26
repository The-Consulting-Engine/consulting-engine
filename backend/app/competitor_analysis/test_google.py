"""
Quick test script for Google Places API.

Run from backend directory:
    cd backend
    python -m app.competitor_analysis.test_google
"""

import asyncio
from dotenv import load_dotenv

# Load .env from project root
load_dotenv("../.env")

from app.competitor_analysis.models import SearchArea
from app.competitor_analysis.google_places import GooglePlacesClient


async def main():
    # Your test parameters
    search_area = SearchArea(
        address="316 Elm St, New Haven, CT 06511",
        radius_meters=2000,  # 2km
        # keyword=None,  # General restaurants
    )

    print(f"Searching for restaurants near: {search_area.address}")
    print(f"Radius: {search_area.radius_meters}m")
    print("-" * 60)

    async with GooglePlacesClient() as client:
        # Step 1: Test geocoding
        print("\n[1] Testing geocode...")
        lat, lng = await client.geocode_address(search_area.address)
        print(f"    Coordinates: {lat}, {lng}")

        # Step 2: Search for nearby restaurants
        print("\n[2] Searching for nearby restaurants...")
        results = await client.search_nearby(search_area, max_results=20)
        print(f"    Found {len(results)} restaurants\n")

        # Step 3: Display results
        print("=" * 60)
        print("TOP COMPETITORS")
        print("=" * 60)

        for i, place in enumerate(results[:15], 1):
            rating_str = f"{place.rating}*" if place.rating else "N/A"
            reviews_str = f"({place.user_ratings_total} reviews)" if place.user_ratings_total else ""
            price_str = place.price_level.value if place.price_level else ""

            print(f"\n{i}. {place.name}")
            print(f"   {place.address}")
            print(f"   Rating: {rating_str} {reviews_str}  Price: {price_str}")
            print(f"   Place ID: {place.place_id}")

        # Step 4: Get details for top result
        if results:
            print("\n" + "=" * 60)
            print("DETAILED VIEW: #1 Result")
            print("=" * 60)

            details = await client.get_place_details(results[0].place_id)
            print(f"\nName: {details.name}")
            print(f"Address: {details.address}")
            print(f"Phone: {details.phone_number or 'N/A'}")
            print(f"Website: {details.website or 'N/A'}")
            print(f"Rating: {details.rating} ({details.user_ratings_total} reviews)")

            if details.opening_hours:
                print(f"Open now: {details.opening_hours.get('open_now', 'Unknown')}")

            if details.reviews:
                print(f"\nSample review:")
                review = details.reviews[0]
                print(f"  \"{review.get('text', '')[:200]}...\"")
                print(f"  - {review.get('author_name')}, {review.get('rating')}*")


if __name__ == "__main__":
    asyncio.run(main())
