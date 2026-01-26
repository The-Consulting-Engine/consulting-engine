#!/usr/bin/env python3
"""
Run the competitor analysis pipeline.

Usage:
    cd backend
    python -m app.competitor_analysis.run_pipeline

Or with custom parameters:
    python -m app.competitor_analysis.run_pipeline \
        --name "Restaurant Name" \
        --address "123 Main St, City, ST" \
        --radius 3000 \
        --output ./my_output
"""

import asyncio
import argparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv("../.env")

from app.competitor_analysis.pipeline import (
    CompetitorAnalysisPipeline,
    PipelineConfig,
    print_results_summary,
)


# =============================================================================
# DEFAULT CONFIGURATION - EDIT THESE FOR YOUR ANALYSIS
# =============================================================================

DEFAULT_RESTAURANT = "Noa by September in Bangkok"
DEFAULT_ADDRESS = "200 Crown St, New Haven, CT 06510"
DEFAULT_OUTPUT_DIR = "pipeline_output"

# =============================================================================


async def main(
    restaurant_name: str,
    address: str,
    output_dir: str,
    radius: int = 2000,
    max_competitors: int = 8,
    cuisine_override: list[str] = None,
):
    """Run the analysis pipeline."""

    print("=" * 70)
    print("COMPETITOR ANALYSIS PIPELINE")
    print("=" * 70)
    print(f"\nTarget: {restaurant_name}")
    print(f"Address: {address}")
    print(f"Search radius: {radius}m")
    print(f"Max competitors: {max_competitors}")
    if cuisine_override:
        print(f"Cuisine filter: {cuisine_override}")
    print(f"Output directory: {output_dir}")
    print("\n" + "-" * 70)

    # Configure pipeline
    config = PipelineConfig(
        search_radius_meters=radius,
        max_competitors=max_competitors,
        cuisine_override=cuisine_override,
        scrape_ubereats=True,
        max_menu_items_per_restaurant=100,
        openai_model="gpt-4o-mini",
        generate_visualizations=True,
    )

    # Initialize and run pipeline
    pipeline = CompetitorAnalysisPipeline()

    result = await pipeline.analyze(
        restaurant_name=restaurant_name,
        address=address,
        config=config,
    )

    # Print summary
    print_results_summary(result)

    # Save outputs
    result.save_outputs(output_dir)

    # Also print file locations
    print(f"\n📁 Output files saved to: {output_dir}/")
    print(f"   - restaurants.csv")
    print(f"   - menu_items.csv")
    print(f"   - price_analysis_narrow.csv")
    print(f"   - price_analysis_wide.csv")
    print(f"   - initiatives.json")
    print(f"   - executive_summary.md")
    print(f"   - metadata.json")
    print(f"   - *.png (visualizations)")

    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run competitor analysis pipeline for a restaurant"
    )
    parser.add_argument(
        "--name", "-n",
        default=DEFAULT_RESTAURANT,
        help=f"Restaurant name (default: {DEFAULT_RESTAURANT})"
    )
    parser.add_argument(
        "--address", "-a",
        default=DEFAULT_ADDRESS,
        help=f"Restaurant address (default: {DEFAULT_ADDRESS})"
    )
    parser.add_argument(
        "--output", "-o",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})"
    )
    parser.add_argument(
        "--radius", "-r",
        type=int,
        default=2000,
        help="Search radius in meters (default: 2000)"
    )
    parser.add_argument(
        "--max-competitors", "-m",
        type=int,
        default=8,
        help="Maximum competitors to analyze (default: 8)"
    )
    parser.add_argument(
        "--cuisine",
        nargs="+",
        default=None,
        help="Filter by cuisine (e.g., --cuisine 'thai restaurant' 'asian restaurant')"
    )

    args = parser.parse_args()

    asyncio.run(main(
        restaurant_name=args.name,
        address=args.address,
        output_dir=args.output,
        radius=args.radius,
        max_competitors=args.max_competitors,
        cuisine_override=args.cuisine,
    ))
