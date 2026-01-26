"""
Competitor Analysis Pipeline - Master Orchestrator

A complete end-to-end pipeline for restaurant competitive analysis.
Integrates all modules: discovery, scraping, cleaning, grouping, pricing, and strategy.

Usage:
    from app.competitor_analysis.pipeline import CompetitorAnalysisPipeline

    # Initialize
    pipeline = CompetitorAnalysisPipeline()

    # Run full analysis
    results = await pipeline.analyze(
        restaurant_name="Noa by September in Bangkok",
        address="200 Crown St, New Haven, CT 06510",
    )

    # Access results
    print(results.executive_summary)
    print(results.initiatives)
    results.save_outputs("./output")
"""

import os
import base64
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, Any

import pandas as pd

# Internal modules
from .analyzer import CompetitorAnalyzer
from .apify_scraper import ApifyScraper
from .data_cleaner import build_all_tables, print_data_quality_report
from .menu_grouper import group_menus_for_analysis
from .price_analyzer import analyze_prices
from .strategic_analyzer import (
    generate_strategic_analysis,
    PricePositioning,
    MenuComplexity,
    CompetitiveGap,
    Initiative,
)


# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass
class PipelineConfig:
    """Configuration for the analysis pipeline."""

    # Search parameters
    search_radius_meters: int = 2000
    max_competitors: int = 8

    # Cuisine search (None = auto-detect from Google Places)
    cuisine_override: Optional[list[str]] = None

    # Scraping options
    scrape_ubereats: bool = True
    max_menu_items_per_restaurant: int = 100  # Limit to control costs

    # LLM options
    openai_model: str = "gpt-4o-mini"

    # Output options
    save_raw_data: bool = True
    generate_visualizations: bool = True


# =============================================================================
# PIPELINE RESULT
# =============================================================================

@dataclass
class PipelineResult:
    """Complete results from the analysis pipeline."""

    # Metadata
    target_name: str
    target_address: str
    analysis_timestamp: str
    config: PipelineConfig

    # Raw data
    restaurants_df: pd.DataFrame
    menu_items_df: pd.DataFrame
    grouped_data: dict

    # Analysis results
    price_analysis: dict
    positioning: PricePositioning
    menu_complexity: MenuComplexity
    competitive_gaps: list[CompetitiveGap]
    initiatives: list[Initiative]

    # Outputs
    visualizations: dict[str, str]  # name -> base64 PNG
    executive_summary: str

    # Diagnostics
    steps_completed: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def save_outputs(self, output_dir: str) -> None:
        """Save all outputs to a directory."""
        os.makedirs(output_dir, exist_ok=True)

        # Save CSVs
        self.restaurants_df.to_csv(f"{output_dir}/restaurants.csv", index=False)
        self.menu_items_df.to_csv(f"{output_dir}/menu_items.csv", index=False)

        # Save price analysis
        if 'narrow_group_analysis' in self.price_analysis:
            self.price_analysis['narrow_group_analysis'].to_csv(
                f"{output_dir}/price_analysis_narrow.csv", index=False
            )
        if 'wide_group_analysis' in self.price_analysis:
            self.price_analysis['wide_group_analysis'].to_csv(
                f"{output_dir}/price_analysis_wide.csv", index=False
            )

        # Save visualizations
        for name, b64_data in self.visualizations.items():
            if b64_data:
                with open(f"{output_dir}/{name}.png", "wb") as f:
                    f.write(base64.b64decode(b64_data))

        # Save executive summary
        with open(f"{output_dir}/executive_summary.md", "w") as f:
            f.write(self.executive_summary)

        # Save initiatives as JSON
        initiatives_data = [
            {
                "id": i.id,
                "title": i.title,
                "category": i.category,
                "priority": i.priority,
                "hypothesis": i.hypothesis,
                "evidence": i.evidence,
                "expected_impact": i.expected_impact,
                "implementation_complexity": i.implementation_complexity,
                "metrics_to_track": i.metrics_to_track,
            }
            for i in self.initiatives
        ]
        with open(f"{output_dir}/initiatives.json", "w") as f:
            json.dump(initiatives_data, f, indent=2)

        # Save full results metadata
        metadata = {
            "target_name": self.target_name,
            "target_address": self.target_address,
            "analysis_timestamp": self.analysis_timestamp,
            "restaurants_count": len(self.restaurants_df),
            "menu_items_count": len(self.menu_items_df),
            "narrow_groups_count": self.grouped_data.get("stats", {}).get("narrow_group_count", 0),
            "positioning": self.positioning.position,
            "avg_price_gap": self.price_analysis.get("overall_metrics", {}).get("avg_price_gap"),
            "initiatives_count": len(self.initiatives),
            "steps_completed": self.steps_completed,
            "warnings": self.warnings,
            "errors": self.errors,
        }
        with open(f"{output_dir}/metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)

        print(f"✓ Saved outputs to {output_dir}/")

    def to_dict(self) -> dict:
        """Convert results to a dictionary (for API responses)."""
        return {
            "target_name": self.target_name,
            "target_address": self.target_address,
            "analysis_timestamp": self.analysis_timestamp,
            "summary": {
                "restaurants_analyzed": len(self.restaurants_df),
                "menu_items_analyzed": len(self.menu_items_df),
                "positioning": self.positioning.position,
                "positioning_confidence": self.positioning.confidence,
                "avg_price_gap_pct": self.price_analysis.get("overall_metrics", {}).get("avg_price_gap"),
                "overpriced_items": self.price_analysis.get("overall_metrics", {}).get("overpriced_count", 0),
                "underpriced_items": self.price_analysis.get("overall_metrics", {}).get("underpriced_count", 0),
                "menu_complexity": self.menu_complexity.complexity_rating,
                "competitive_gaps_count": len(self.competitive_gaps),
            },
            "initiatives": [
                {
                    "id": i.id,
                    "title": i.title,
                    "priority": i.priority,
                    "category": i.category,
                    "hypothesis": i.hypothesis,
                    "expected_impact": i.expected_impact,
                }
                for i in self.initiatives
            ],
            "executive_summary": self.executive_summary,
            "visualizations_available": list(k for k, v in self.visualizations.items() if v),
            "warnings": self.warnings,
            "errors": self.errors,
        }


# =============================================================================
# MAIN PIPELINE
# =============================================================================

class CompetitorAnalysisPipeline:
    """
    End-to-end competitor analysis pipeline.

    Orchestrates:
    1. Competitor discovery (Google Places API)
    2. Menu data scraping (Uber Eats via Apify)
    3. Data cleaning and normalization
    4. Menu grouping (OpenAI LLM)
    5. Price analysis
    6. Strategic analysis and recommendations
    """

    def __init__(
        self,
        google_api_key: Optional[str] = None,
        apify_token: Optional[str] = None,
        openai_api_key: Optional[str] = None,
    ):
        """
        Initialize the pipeline.

        API keys can be provided directly or via environment variables:
        - GOOGLE_PLACES_API_KEY
        - APIFY_API_TOKEN
        - OPENAI_API_KEY
        """
        self.google_api_key = google_api_key
        self.apify_token = apify_token
        self.openai_api_key = openai_api_key

    async def analyze(
        self,
        restaurant_name: str,
        address: str,
        config: Optional[PipelineConfig] = None,
        progress_callback: Optional[callable] = None,
    ) -> PipelineResult:
        """
        Run the complete analysis pipeline.

        Args:
            restaurant_name: Name of the target restaurant
            address: Full address of the target restaurant
            config: Pipeline configuration (uses defaults if not provided)
            progress_callback: Optional callback for progress updates
                              Signature: callback(step: str, message: str)

        Returns:
            PipelineResult with all analysis outputs
        """
        config = config or PipelineConfig()
        steps_completed = []
        warnings = []
        errors = []

        def log(step: str, message: str):
            print(f"[{step}] {message}")
            if progress_callback:
                progress_callback(step, message)

        log("INIT", f"Starting analysis for: {restaurant_name}")
        log("INIT", f"Address: {address}")

        # ---------------------------------------------------------------------
        # STEP 1: Discover competitors
        # ---------------------------------------------------------------------
        log("STEP 1", "Discovering competitors via Google Places API...")

        try:
            async with CompetitorAnalyzer(
                google_api_key=self.google_api_key,
                apify_token=self.apify_token,
            ) as analyzer:
                discovery_result = await analyzer.find_cuisine_competitors(
                    name=restaurant_name,
                    address=address,
                    radius_meters=config.search_radius_meters,
                    max_competitors=config.max_competitors,
                    cuisine_override=config.cuisine_override,
                    enrich_ubereats=False,
                )

            target_info = discovery_result["target"]
            competitors = discovery_result["competitors"]

            log("STEP 1", f"Found target: {target_info['name']}")
            log("STEP 1", f"Found {len(competitors)} competitors")
            steps_completed.append("competitor_discovery")

        except Exception as e:
            errors.append(f"Competitor discovery failed: {str(e)}")
            raise RuntimeError(f"Pipeline failed at Step 1: {e}")

        # ---------------------------------------------------------------------
        # STEP 2: Scrape Uber Eats menus
        # ---------------------------------------------------------------------
        all_menu_items = []
        restaurants_raw = []

        if config.scrape_ubereats:
            log("STEP 2", "Scraping Uber Eats for menu data...")

            try:
                async with ApifyScraper(api_token=self.apify_token) as scraper:
                    # Scrape target
                    log("STEP 2", f"Scraping target: {target_info['name']}")
                    target_ue = await scraper.scrape_ubereats_menu(
                        restaurant_name=target_info['name'],
                        address=address,
                    )

                    if target_ue.get("found"):
                        menu_count = len(target_ue.get("menu_items", []))
                        log("STEP 2", f"  ✓ Found {menu_count} menu items")
                        restaurants_raw.append({
                            "restaurant_id": target_info["place_id"],
                            "name": target_info["name"],
                            "address": target_info["address"],
                            "rating": target_ue.get("rating") or target_info["rating"],
                            "review_count": target_ue.get("rating_count") or target_info["review_count"],
                            "cuisines": target_info.get("cuisines", []),
                            "source": "uber_eats",
                        })
                        for item in target_ue.get("menu_items", [])[:config.max_menu_items_per_restaurant]:
                            all_menu_items.append({
                                "restaurant_id": target_info["place_id"],
                                "item_name": item.get("name"),
                                "category": item.get("category"),
                                "description": item.get("description"),
                                "price": item.get("price"),
                                "source": "uber_eats",
                            })
                    else:
                        warnings.append(f"Target restaurant not found on Uber Eats")
                        log("STEP 2", f"  ✗ Not found on Uber Eats")
                        restaurants_raw.append({
                            "restaurant_id": target_info["place_id"],
                            "name": target_info["name"],
                            "address": target_info["address"],
                            "rating": target_info["rating"],
                            "review_count": target_info["review_count"],
                            "cuisines": target_info.get("cuisines", []),
                            "source": "google_places",
                        })

                    # Scrape competitors
                    for comp in competitors:
                        log("STEP 2", f"Scraping: {comp.name}")
                        try:
                            comp_ue = await scraper.scrape_ubereats_menu(
                                restaurant_name=comp.name,
                                address=comp.address,
                            )

                            if comp_ue.get("found"):
                                menu_count = len(comp_ue.get("menu_items", []))
                                log("STEP 2", f"  ✓ Found {menu_count} menu items")
                                restaurants_raw.append({
                                    "restaurant_id": comp.place_id,
                                    "name": comp.name,
                                    "address": comp.address,
                                    "rating": comp_ue.get("rating") or comp.rating,
                                    "review_count": comp_ue.get("rating_count") or comp.user_ratings_total,
                                    "source": "uber_eats",
                                })
                                for item in comp_ue.get("menu_items", [])[:config.max_menu_items_per_restaurant]:
                                    all_menu_items.append({
                                        "restaurant_id": comp.place_id,
                                        "item_name": item.get("name"),
                                        "category": item.get("category"),
                                        "description": item.get("description"),
                                        "price": item.get("price"),
                                        "source": "uber_eats",
                                    })
                            else:
                                log("STEP 2", f"  ✗ Not found on Uber Eats (skipped)")
                        except Exception as e:
                            warnings.append(f"Failed to scrape {comp.name}: {str(e)}")
                            log("STEP 2", f"  ✗ Error: {e}")

                log("STEP 2", f"Total menu items collected: {len(all_menu_items)}")
                steps_completed.append("ubereats_scraping")

            except Exception as e:
                errors.append(f"Uber Eats scraping failed: {str(e)}")
                warnings.append("Continuing without Uber Eats data")
        else:
            log("STEP 2", "Skipping Uber Eats scraping (disabled in config)")
            # Add restaurants from Google data only
            restaurants_raw.append({
                "restaurant_id": target_info["place_id"],
                "name": target_info["name"],
                "address": target_info["address"],
                "rating": target_info["rating"],
                "review_count": target_info["review_count"],
                "source": "google_places",
            })
            for comp in competitors:
                restaurants_raw.append({
                    "restaurant_id": comp.place_id,
                    "name": comp.name,
                    "address": comp.address,
                    "rating": comp.rating,
                    "review_count": comp.user_ratings_total,
                    "source": "google_places",
                })

        # Check if we have enough data
        if len(all_menu_items) < 5:
            warnings.append("Insufficient menu data for meaningful analysis")

        # ---------------------------------------------------------------------
        # STEP 3: Clean data
        # ---------------------------------------------------------------------
        log("STEP 3", "Cleaning and normalizing data...")

        tables = build_all_tables(
            restaurants_raw=restaurants_raw,
            menus_raw=all_menu_items,
            reviews_raw=[],
            competitors_raw=[],
            target_restaurant_id=target_info["place_id"],
        )

        restaurants_df = tables["restaurants"]
        menu_items_df = tables["menu_items"]

        log("STEP 3", f"Restaurants: {len(restaurants_df)}")
        log("STEP 3", f"Menu items: {len(menu_items_df)}")
        steps_completed.append("data_cleaning")

        # ---------------------------------------------------------------------
        # STEP 4: Group menus with LLM
        # ---------------------------------------------------------------------
        log("STEP 4", "Grouping menus with LLM...")

        if len(menu_items_df) > 0:
            try:
                grouped_data = await group_menus_for_analysis(
                    menu_items_df=menu_items_df,
                    restaurants_df=restaurants_df,
                    api_key=self.openai_api_key,
                    model=config.openai_model,
                )
                log("STEP 4", f"Created {grouped_data['stats']['narrow_group_count']} narrow groups")
                steps_completed.append("menu_grouping")
            except Exception as e:
                errors.append(f"Menu grouping failed: {str(e)}")
                grouped_data = {"narrow_groups": {}, "wide_groups": {}, "items": [], "stats": {}}
        else:
            warnings.append("No menu items to group")
            grouped_data = {"narrow_groups": {}, "wide_groups": {}, "items": [], "stats": {}}

        # ---------------------------------------------------------------------
        # STEP 5: Price analysis
        # ---------------------------------------------------------------------
        log("STEP 5", "Analyzing prices...")

        price_analysis = analyze_prices(grouped_data, restaurants_df)
        overall = price_analysis.get("overall_metrics", {})
        log("STEP 5", f"Average price gap: {overall.get('avg_price_gap')}%")
        steps_completed.append("price_analysis")

        # ---------------------------------------------------------------------
        # STEP 6: Strategic analysis
        # ---------------------------------------------------------------------
        log("STEP 6", "Generating strategic insights...")

        strategic = generate_strategic_analysis(
            price_analysis=price_analysis,
            grouped_data=grouped_data,
            restaurants_df=restaurants_df,
        )
        log("STEP 6", f"Generated {len(strategic['initiatives'])} initiatives")
        steps_completed.append("strategic_analysis")

        # ---------------------------------------------------------------------
        # Build result
        # ---------------------------------------------------------------------
        log("DONE", "Pipeline complete!")

        return PipelineResult(
            target_name=target_info["name"],
            target_address=address,
            analysis_timestamp=datetime.now().isoformat(),
            config=config,
            restaurants_df=restaurants_df,
            menu_items_df=menu_items_df,
            grouped_data=grouped_data,
            price_analysis=price_analysis,
            positioning=strategic["positioning"],
            menu_complexity=strategic["menu_complexity"],
            competitive_gaps=strategic["competitive_gaps"],
            initiatives=strategic["initiatives"],
            visualizations=strategic["visualizations"] if config.generate_visualizations else {},
            executive_summary=strategic["executive_summary"],
            steps_completed=steps_completed,
            warnings=warnings,
            errors=errors,
        )


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

async def run_analysis(
    restaurant_name: str,
    address: str,
    output_dir: Optional[str] = None,
    **config_kwargs,
) -> PipelineResult:
    """
    Convenience function to run analysis with minimal setup.

    Args:
        restaurant_name: Name of the target restaurant
        address: Full address
        output_dir: Directory to save outputs (optional)
        **config_kwargs: Override default config options

    Returns:
        PipelineResult
    """
    config = PipelineConfig(**config_kwargs)
    pipeline = CompetitorAnalysisPipeline()

    result = await pipeline.analyze(
        restaurant_name=restaurant_name,
        address=address,
        config=config,
    )

    if output_dir:
        result.save_outputs(output_dir)

    return result


def print_results_summary(result: PipelineResult) -> None:
    """Print a formatted summary of pipeline results."""

    print("\n" + "=" * 70)
    print(f"ANALYSIS COMPLETE: {result.target_name}")
    print("=" * 70)

    print(f"\nTimestamp: {result.analysis_timestamp}")
    print(f"Steps completed: {', '.join(result.steps_completed)}")

    if result.warnings:
        print(f"\n⚠️  Warnings ({len(result.warnings)}):")
        for w in result.warnings:
            print(f"   - {w}")

    if result.errors:
        print(f"\n❌ Errors ({len(result.errors)}):")
        for e in result.errors:
            print(f"   - {e}")

    print(f"\n--- DATA SUMMARY ---")
    print(f"  Restaurants analyzed: {len(result.restaurants_df)}")
    print(f"  Menu items analyzed: {len(result.menu_items_df)}")
    print(f"  Narrow groups created: {result.grouped_data.get('stats', {}).get('narrow_group_count', 0)}")

    print(f"\n--- POSITIONING ---")
    print(f"  Market position: {result.positioning.position.upper()}")
    print(f"  Confidence: {result.positioning.confidence:.0%}")
    print(f"  Average percentile: {result.positioning.avg_percentile}th")

    print(f"\n--- MENU ---")
    print(f"  Complexity: {result.menu_complexity.complexity_rating}")
    print(f"  Total items: {result.menu_complexity.total_items}")
    print(f"  Categories: {result.menu_complexity.unique_categories}")

    overall = result.price_analysis.get("overall_metrics", {})
    print(f"\n--- PRICING ---")
    print(f"  Avg price gap: {overall.get('avg_price_gap')}%")
    print(f"  Overpriced items: {overall.get('overpriced_count', 0)}")
    print(f"  Underpriced items: {overall.get('underpriced_count', 0)}")

    print(f"\n--- INITIATIVES ({len(result.initiatives)}) ---")
    for init in result.initiatives[:5]:
        print(f"  [{init.priority.upper()}] {init.title}")

    print(f"\n--- EXECUTIVE SUMMARY ---")
    print(result.executive_summary)

    print("\n" + "=" * 70)
