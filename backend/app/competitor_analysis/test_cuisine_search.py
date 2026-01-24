"""
Test script for cuisine-specific competitor search.

This identifies what type of restaurant is at an address, then finds
competitors in the same cuisine category.

Run from backend directory:
    cd backend
    python -m app.competitor_analysis.test_cuisine_search
"""

import asyncio
from dotenv import load_dotenv

# Load .env from project root
load_dotenv("../.env")

from app.competitor_analysis.analyzer import CompetitorAnalyzer


async def main():
    # Your restaurant - NAME is the primary identifier
    restaurant_name = "Nice Day Chinese"  # <-- CHANGE THIS
    address = "316 Elm St, New Haven, CT 06511"    # For location context
    radius_meters = 2000  # 2km search radius

    # OPTIONAL: Override the auto-detected cuisine with your own keywords
    # Set to None to use auto-detection, or specify custom keywords:
    custom_cuisine = ["chinese restaurant", "asian food", "takeout"]    # Auto-detect from Google
    # custom_cuisine = ["chinese restaurant"]  # Single cuisine
    # custom_cuisine = ["chinese restaurant", "asian food", "takeout"]  # Multiple

    print("=" * 70)
    print("CUISINE-SPECIFIC COMPETITOR SEARCH")
    print("=" * 70)
    print(f"Target name: {restaurant_name}")
    print(f"Target address: {address}")
    print(f"Search radius: {radius_meters}m")
    print(f"Custom cuisine: {custom_cuisine or 'Auto-detect'}")
    print("-" * 70)

    async with CompetitorAnalyzer() as analyzer:
        # Find cuisine-specific competitors
        # Name takes priority, address is for location context
        result = await analyzer.find_cuisine_competitors(
            name=restaurant_name,
            address=address,
            radius_meters=radius_meters,
            max_competitors=15,
            include_all_cuisines=True,  # Search all cuisine types found
            cuisine_override=custom_cuisine,  # Set custom keywords or None for auto
        )

        # Display target restaurant info
        target = result["target"]
        print("\n" + "=" * 70)
        print("TARGET RESTAURANT")
        print("=" * 70)
        print(f"Name: {target['name']}")
        print(f"Address: {target['address']}")
        print(f"Rating: {target['rating']}* ({target['review_count']} reviews)")
        print(f"Price: {target['price_level'] or 'N/A'}")
        print(f"Cuisines: {', '.join(target['cuisines']) or 'General'}")
        print(f"Service styles: {', '.join(target['service_styles']) or 'N/A'}")
        print(f"Website: {target['website'] or 'N/A'}")
        print(f"Phone: {target['phone'] or 'N/A'}")

        # Display search criteria
        criteria = result["search_criteria"]
        print(f"\nSearch keywords used: {criteria['keywords']}")

        # Display competitors
        competitors = result["competitors"]
        print("\n" + "=" * 70)
        print(f"COMPETITORS IN SAME CUISINE ({result['total_found']} found)")
        print("=" * 70)

        for i, place in enumerate(competitors, 1):
            rating_str = f"{place.rating}*" if place.rating else "N/A"
            reviews_str = f"({place.user_ratings_total} reviews)" if place.user_ratings_total else ""
            price_str = place.price_level.value if place.price_level else ""

            print(f"\n{i}. {place.name}")
            print(f"   Address: {place.address}")
            print(f"   Rating: {rating_str} {reviews_str}  Price: {price_str}")

            # Show categories if available
            if place.types:
                # Filter to meaningful types
                meaningful_types = [
                    t for t in place.types
                    if t not in ["restaurant", "food", "point_of_interest", "establishment"]
                ][:3]
                if meaningful_types:
                    print(f"   Types: {', '.join(meaningful_types)}")

        # Summary comparison
        print("\n" + "=" * 70)
        print("COMPETITIVE SUMMARY")
        print("=" * 70)

        if competitors:
            ratings = [p.rating for p in competitors if p.rating]
            if ratings:
                avg_competitor_rating = sum(ratings) / len(ratings)
                print(f"Average competitor rating: {avg_competitor_rating:.1f}*")

                if target["rating"]:
                    diff = target["rating"] - avg_competitor_rating
                    if diff > 0:
                        print(f"Your rating is {diff:.1f} points ABOVE average")
                    elif diff < 0:
                        print(f"Your rating is {abs(diff):.1f} points BELOW average")
                    else:
                        print("Your rating matches the average")

            # Price distribution
            price_counts = {}
            for p in competitors:
                if p.price_level:
                    price_counts[p.price_level.value] = price_counts.get(p.price_level.value, 0) + 1

            if price_counts:
                print(f"Competitor price distribution: {price_counts}")

            # Top-rated competitors
            top_rated = sorted(
                [p for p in competitors if p.rating],
                key=lambda p: (p.rating, p.user_ratings_total or 0),
                reverse=True
            )[:3]

            if top_rated:
                print("\nTop-rated competitors to watch:")
                for p in top_rated:
                    print(f"  - {p.name}: {p.rating}* ({p.user_ratings_total} reviews)")


if __name__ == "__main__":
    asyncio.run(main())
