"""
Demo script for competitor analysis MVP.

Run with:
    cd backend
    python -m app.competitor_analysis.demo

Before running, set environment variables:
    export GOOGLE_PLACES_API_KEY=your_key
    export APIFY_API_TOKEN=your_token
"""

import asyncio
from .models import SearchArea
from .analyzer import CompetitorAnalyzer


async def main():
    """Demo: Analyze restaurant competition near a location."""

    # Example 1: Search by address
    search_area = SearchArea(
        address="Union Square, San Francisco, CA",
        radius_meters=500,
        keyword="pizza",  # Filter to pizza restaurants
        min_rating=4.0,   # Only 4+ star places
    )

    # Example 2: Search by coordinates
    # search_area = SearchArea(
    #     latitude=37.7879,
    #     longitude=-122.4074,
    #     radius_meters=1000,
    #     keyword="thai food",
    # )

    print(f"Searching for competitors near: {search_area.address or f'{search_area.latitude}, {search_area.longitude}'}")
    print(f"Radius: {search_area.radius_meters}m")
    print(f"Keyword filter: {search_area.keyword or 'None'}")
    print("-" * 50)

    async with CompetitorAnalyzer() as analyzer:
        # Option A: Quick discovery (Google Places only)
        # competitors = await analyzer.discover_competitors(search_area)
        # print(f"Found {len(competitors)} competitors")
        # for c in competitors[:5]:
        #     print(f"  - {c.name} ({c.rating}*) - {c.address}")

        # Option B: Full analysis with enrichment
        result = await analyzer.analyze(
            search_area=search_area,
            enrich_sources=["google_reviews"],  # Add "yelp", "tripadvisor" for more data
            max_competitors=10,
        )

        print(f"\n=== ANALYSIS RESULTS ===")
        print(f"Total competitors found: {result.total_found}")
        print(f"Analyzed in detail: {len(result.competitors)}")

        if result.market_summary:
            print(f"\nMarket Summary:\n{result.market_summary}")

        print(f"\n=== TOP COMPETITORS ===")
        for i, competitor in enumerate(result.competitors[:5], 1):
            print(f"\n{i}. {competitor.name}")
            print(f"   Address: {competitor.address}")
            print(f"   Rating: {competitor.google_rating}* ({competitor.google_review_count} reviews)")
            print(f"   Price: {competitor.price_level.value if competitor.price_level else 'Unknown'}")
            if competitor.website:
                print(f"   Website: {competitor.website}")
            if competitor.strengths:
                print(f"   Strengths: {', '.join(competitor.strengths)}")
            if competitor.weaknesses:
                print(f"   Weaknesses: {', '.join(competitor.weaknesses)}")

        if result.opportunities:
            print(f"\n=== MARKET OPPORTUNITIES ===")
            for opp in result.opportunities:
                print(f"  - {opp}")

        if result.threats:
            print(f"\n=== COMPETITIVE THREATS ===")
            for threat in result.threats:
                print(f"  - {threat}")


if __name__ == "__main__":
    asyncio.run(main())
