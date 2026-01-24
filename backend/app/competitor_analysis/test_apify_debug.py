"""
Debug test for Apify - compare this input with your manual run.

Run:
    cd backend
    python -m app.competitor_analysis.test_apify_debug
"""

import asyncio
import json
from dotenv import load_dotenv

load_dotenv("../.env")

from app.competitor_analysis.apify_scraper import ApifyScraper


async def main():
    # Test with a single known Google Maps URL
    # REPLACE THIS with a URL you tested manually on Apify
    test_url = "https://www.google.com/maps/place/China+King/@41.3066607,-72.927537,17z/data=!3m1!4b1!4m6!3m5!1s0x89e7d9b4b28b02e1:0x27b895e5fb7b21bc!8m2!3d41.3066607!4d-72.927537!16s%2Fg%2F1v3lq_55?entry=ttu&g_ep=EgoyMDI2MDEyMS4wIKXMDSoASAFQAw%3D%3D"

    print("=" * 70)
    print("APIFY DEBUG TEST")
    print("=" * 70)
    print(f"\nTest URL: {test_url}")
    print("\nCompare the DEBUG output below with your manual Apify input!\n")

    async with ApifyScraper() as scraper:
        # What we're sending to Apify
        input_data = {
            "startUrls": [{"url": test_url}],
            "maxReviews": 10,
            "language": "en",
        }

        print("INPUT WE'RE SENDING:")
        print(json.dumps(input_data, indent=2))
        print("\n" + "-" * 70)

        # Make the actual call
        print("\nCalling Apify...\n")
        result = await scraper.scrape_reviews_by_url(test_url, max_reviews=10)

        print("\n" + "=" * 70)
        print("RESULTS")
        print("=" * 70)
        print(f"Reviews found: {len(result.reviews)}")
        print(f"Review count: {result.review_count}")
        print(f"Average rating: {result.average_rating}")

        if result.reviews:
            print("\nFirst review:")
            print(json.dumps(result.reviews[0], indent=2, default=str))

        if result.raw_data:
            print("\n" + "-" * 70)
            print("RAW DATA KEYS:")
            print(list(result.raw_data.keys()))


if __name__ == "__main__":
    asyncio.run(main())
