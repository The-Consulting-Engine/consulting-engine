"""
Industry benchmarks for different verticals.

Sources should be documented. When no source available, mark as ASSUMPTION.
"""
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class Benchmark:
    """A single benchmark value with source."""
    value: float
    unit: str
    source: str                    # "NRA 2023", "industry_survey", "ASSUMPTION"
    confidence: float              # 0-1, how reliable is this benchmark
    applicable_to: str             # e.g., "full_service_restaurant", "qsr", "all"
    notes: Optional[str] = None


# Restaurant industry benchmarks
RESTAURANT_BENCHMARKS: Dict[str, Benchmark] = {
    # Labor benchmarks
    "labor_pct": Benchmark(
        value=28.0,
        unit="percentage",
        source="National Restaurant Association 2023 State of the Industry",
        confidence=0.85,
        applicable_to="full_service_restaurant",
        notes="Full-service restaurants typically range 28-35%. QSR is lower (25-30%)."
    ),
    "labor_pct_qsr": Benchmark(
        value=25.0,
        unit="percentage",
        source="National Restaurant Association 2023",
        confidence=0.85,
        applicable_to="qsr",
        notes="Quick-service restaurants have lower labor % due to operational efficiency."
    ),

    # COGS benchmarks
    "cogs_pct": Benchmark(
        value=30.0,
        unit="percentage",
        source="Restaurant industry standard",
        confidence=0.80,
        applicable_to="full_service_restaurant",
        notes="Food cost typically 28-35% for full service. Varies by cuisine type."
    ),
    "cogs_pct_qsr": Benchmark(
        value=32.0,
        unit="percentage",
        source="QSR industry reports",
        confidence=0.75,
        applicable_to="qsr",
        notes="QSR tends slightly higher food cost, offset by lower labor."
    ),

    # Margin benchmarks
    "gross_margin_pct": Benchmark(
        value=70.0,
        unit="percentage",
        source="Derived from COGS benchmark",
        confidence=0.80,
        applicable_to="full_service_restaurant",
        notes="100% - COGS%. Healthy restaurants maintain 65-75%."
    ),
    "net_margin_pct": Benchmark(
        value=5.0,
        unit="percentage",
        source="National Restaurant Association",
        confidence=0.75,
        applicable_to="all",
        notes="Restaurant net margins are notoriously thin. 3-9% is typical."
    ),

    # Rent benchmarks
    "rent_pct": Benchmark(
        value=6.0,
        unit="percentage",
        source="Industry rule of thumb",
        confidence=0.70,
        applicable_to="all",
        notes="Rent should ideally be 5-8% of revenue. Above 10% is concerning."
    ),

    # Prime cost (labor + COGS)
    "prime_cost_pct": Benchmark(
        value=60.0,
        unit="percentage",
        source="Restaurant industry standard",
        confidence=0.85,
        applicable_to="full_service_restaurant",
        notes="Prime cost (labor + food) should be under 65%. Under 60% is excellent."
    ),

    # Revenue per square foot (ASSUMPTION - highly variable)
    "revenue_per_sqft_annual": Benchmark(
        value=500.0,
        unit="currency_per_sqft",
        source="ASSUMPTION - varies widely by location and concept",
        confidence=0.50,
        applicable_to="full_service_restaurant",
        notes="Highly variable. $300-$800 is typical range."
    ),

    # Volatility benchmarks
    "revenue_volatility_cv": Benchmark(
        value=0.15,
        unit="coefficient_of_variation",
        source="ASSUMPTION - based on typical monthly variance",
        confidence=0.60,
        applicable_to="all",
        notes="CV < 0.15 is stable. > 0.25 indicates high volatility."
    ),
    "labor_volatility_cv": Benchmark(
        value=0.10,
        unit="coefficient_of_variation",
        source="ASSUMPTION - labor should be more stable than revenue",
        confidence=0.60,
        applicable_to="all",
        notes="Labor should track revenue but with lower variance."
    ),

    # Trend benchmarks
    "revenue_growth_monthly": Benchmark(
        value=0.5,
        unit="pct_per_month",
        source="ASSUMPTION - healthy growth expectation",
        confidence=0.50,
        applicable_to="all",
        notes="0.5% monthly = ~6% annual. Varies by maturity and market."
    ),

    # Correlation benchmarks
    "labor_revenue_correlation": Benchmark(
        value=0.80,
        unit="correlation",
        source="ASSUMPTION - well-managed operations",
        confidence=0.65,
        applicable_to="all",
        notes="Labor should track revenue. r < 0.7 suggests scheduling issues."
    ),

    # Discount benchmarks
    "discount_rate_pct": Benchmark(
        value=3.0,
        unit="percentage",
        source="ASSUMPTION - healthy discount level",
        confidence=0.55,
        applicable_to="all",
        notes="Discounts > 5% of revenue may indicate over-reliance on promotions."
    ),
}


# General business benchmarks (non-restaurant)
GENERAL_BENCHMARKS: Dict[str, Benchmark] = {
    "labor_pct": Benchmark(
        value=30.0,
        unit="percentage",
        source="ASSUMPTION - varies widely by industry",
        confidence=0.40,
        applicable_to="general",
        notes="Service businesses typically 25-40%. Manufacturing lower."
    ),
    "gross_margin_pct": Benchmark(
        value=50.0,
        unit="percentage",
        source="ASSUMPTION - median across industries",
        confidence=0.40,
        applicable_to="general",
        notes="Highly variable. 30-70% depending on industry."
    ),
}


def get_benchmarks_for_vertical(vertical_id: str) -> Dict[str, float]:
    """
    Get benchmark values for a vertical.

    Returns dict of {metric_id: benchmark_value} for use in analytics.
    """
    if vertical_id.startswith("restaurant"):
        benchmarks = RESTAURANT_BENCHMARKS
    else:
        benchmarks = GENERAL_BENCHMARKS

    return {
        metric_id: bm.value
        for metric_id, bm in benchmarks.items()
    }


def get_benchmark_details(vertical_id: str) -> Dict[str, Dict[str, Any]]:
    """
    Get full benchmark details for a vertical.

    Returns dict with full benchmark objects for transparency.
    """
    if vertical_id.startswith("restaurant"):
        benchmarks = RESTAURANT_BENCHMARKS
    else:
        benchmarks = GENERAL_BENCHMARKS

    return {
        metric_id: {
            "value": bm.value,
            "unit": bm.unit,
            "source": bm.source,
            "confidence": bm.confidence,
            "applicable_to": bm.applicable_to,
            "notes": bm.notes,
            "is_assumption": "ASSUMPTION" in bm.source
        }
        for metric_id, bm in benchmarks.items()
    }
