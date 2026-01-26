"""
Price analysis module for competitor benchmarking.

Calculates pricing indicators to understand competitive positioning:
- Target vs competitor price gaps
- Overpricing/underpricing flags
- Percentile rankings
- Menu redundancy analysis

Usage:
    from app.competitor_analysis.price_analyzer import analyze_prices

    analysis = analyze_prices(grouped_data, restaurants_df)
    print(analysis['narrow_group_analysis'])
    print(analysis['wide_group_analysis'])
    print(analysis['summary'])
"""

from typing import Optional
import pandas as pd
import numpy as np
import math


def _calculate_confidence_score(rating: float, review_count: int) -> float:
    """
    Calculate a confidence score for a restaurant based on rating and review volume.

    Formula: rating * log(review_count + 1)

    This weights restaurants with more reviews more heavily, while still
    considering rating quality. A 4.8★ restaurant with 2000 reviews will
    have much more influence than a 4.9★ with 12 reviews.

    Returns a score (higher = more confident/reliable).
    """
    if rating is None or review_count is None:
        return 1.0  # Default weight

    rating = float(rating) if rating else 0
    review_count = int(review_count) if review_count else 0

    # Ensure non-negative values
    rating = max(0, min(5, rating))
    review_count = max(0, review_count)

    # log(1) = 0, so add 1 to ensure positive weight even with 0 reviews
    # Use log base 10 for more intuitive scaling
    log_reviews = math.log10(review_count + 1)

    # Multiply by rating to weight higher-rated restaurants more
    # Add 1 to avoid zero-weight for 0-rated restaurants
    return (rating + 1) * log_reviews if log_reviews > 0 else 1.0


def _weighted_median(values: list[float], weights: list[float]) -> float:
    """
    Calculate weighted median of a list of values.

    For price benchmarking, this gives more influence to competitors
    with higher confidence scores (better ratings + more reviews).
    """
    if not values or not weights:
        return None

    # Filter out None values
    valid = [(v, w) for v, w in zip(values, weights) if v is not None and w is not None]
    if not valid:
        return None

    values, weights = zip(*valid)

    # Sort by values
    sorted_pairs = sorted(zip(values, weights), key=lambda x: x[0])
    values, weights = zip(*sorted_pairs)

    # Calculate cumulative weights
    total_weight = sum(weights)
    if total_weight == 0:
        return np.median(values)

    cumsum = 0
    for v, w in zip(values, weights):
        cumsum += w
        if cumsum >= total_weight / 2:
            return v

    return values[-1]


def _calculate_percentile(value: float, values: list[float]) -> float:
    """
    Calculate what percentile a value falls at within a distribution.

    Returns 0-100 percentile rank.
    """
    if not values or value is None:
        return None

    values = [v for v in values if v is not None]
    if not values:
        return None

    below = sum(1 for v in values if v < value)
    equal = sum(1 for v in values if v == value)

    # Percentile rank formula: (below + 0.5 * equal) / total * 100
    percentile = (below + 0.5 * equal) / len(values) * 100
    return round(percentile, 1)


def _get_competitor_ids(restaurants_df: pd.DataFrame) -> set:
    """Get set of competitor restaurant IDs."""
    if restaurants_df is None or restaurants_df.empty:
        return set()
    return set(restaurants_df[~restaurants_df['is_target']]['restaurant_id'].tolist())


def analyze_narrow_groups(
    grouped_data: dict,
    restaurants_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Analyze pricing for narrow groups (specific item types).

    Returns DataFrame with columns:
        - narrow_group: Group name (e.g., "general tso chicken")
        - wide_group: Parent category
        - target_item_count: Number of target items in group (menu redundancy)
        - target_median_price: Median price of target items (p50)
        - target_min_price: Min target price
        - target_max_price: Max target price
        - competitor_count: Number of competitors with items in group
        - total_competitors: Total number of competitors
        - competitor_item_count: Total competitor items in group
        - competitor_median_price: Median of all competitor prices
        - competitor_weighted_median: Confidence-weighted median (by rating * log(reviews))
        - competitor_p25: 25th percentile of competitor prices
        - competitor_p75: 75th percentile of competitor prices
        - competitor_min_price: Min competitor price
        - competitor_max_price: Max competitor price
        - relative_price_gap: % difference (target - competitor) / competitor
        - weighted_price_gap: % difference using confidence-weighted median
        - target_percentile: Where target median falls among competitors (0-100)
        - overpricing_flag: Target > competitor p75
        - underpricing_flag: Target < competitor p25
        - group_presence_gap: % of competitors NOT offering this item
        - menu_redundancy_flag: Target has 3+ items in group
    """
    if not grouped_data.get('narrow_groups'):
        return pd.DataFrame()

    competitor_ids = _get_competitor_ids(restaurants_df)
    total_competitors = len(competitor_ids)

    # Build restaurant confidence lookup
    restaurant_confidence = {}
    if restaurants_df is not None and not restaurants_df.empty:
        for _, row in restaurants_df.iterrows():
            rid = row.get('restaurant_id')
            if rid:
                restaurant_confidence[rid] = _calculate_confidence_score(
                    row.get('rating'),
                    row.get('review_count')
                )

    rows = []
    for group_name, items in grouped_data['narrow_groups'].items():
        target_items = [i for i in items if i['is_target'] and i['price'] is not None]
        competitor_items = [i for i in items if not i['is_target'] and i['price'] is not None]

        # Get prices
        target_prices = [i['price'] for i in target_items]
        competitor_prices = [i['price'] for i in competitor_items]

        # Find which wide group this belongs to
        wide_group = None
        for item in items:
            if 'narrow_group' in item:
                # Look up in items list
                for full_item in grouped_data.get('items', []):
                    if full_item.get('narrow_group') == group_name:
                        wide_group = full_item.get('wide_group')
                        break
            break

        # Calculate target metrics
        target_median = np.median(target_prices) if target_prices else None
        target_min = min(target_prices) if target_prices else None
        target_max = max(target_prices) if target_prices else None
        target_item_count = len(target_items)

        # Calculate competitor metrics
        competitor_median = np.median(competitor_prices) if competitor_prices else None
        competitor_p25 = np.percentile(competitor_prices, 25) if competitor_prices else None
        competitor_p75 = np.percentile(competitor_prices, 75) if competitor_prices else None
        competitor_min = min(competitor_prices) if competitor_prices else None
        competitor_max = max(competitor_prices) if competitor_prices else None

        # Calculate confidence-weighted median
        competitor_weighted_median = None
        if competitor_items:
            weights = [
                restaurant_confidence.get(i['restaurant_id'], 1.0)
                for i in competitor_items if i['price'] is not None
            ]
            competitor_weighted_median = _weighted_median(competitor_prices, weights)

        # Count unique competitors in this group
        competitors_in_group = set(i['restaurant_id'] for i in competitor_items)
        competitor_count = len(competitors_in_group)

        # Calculate indicators
        relative_price_gap = None
        if target_median is not None and competitor_median is not None and competitor_median > 0:
            relative_price_gap = round((target_median - competitor_median) / competitor_median * 100, 1)

        # Calculate weighted price gap (using confidence-weighted median)
        weighted_price_gap = None
        if target_median is not None and competitor_weighted_median is not None and competitor_weighted_median > 0:
            weighted_price_gap = round((target_median - competitor_weighted_median) / competitor_weighted_median * 100, 1)

        # Target percentile among competitors
        target_percentile = None
        if target_median is not None and competitor_prices:
            target_percentile = _calculate_percentile(target_median, competitor_prices)

        # Flags
        overpricing_flag = False
        underpricing_flag = False
        if target_median is not None:
            if competitor_p75 is not None and target_median > competitor_p75:
                overpricing_flag = True
            if competitor_p25 is not None and target_median < competitor_p25:
                underpricing_flag = True

        # Group presence gap: what % of competitors DON'T have this item
        group_presence_gap = None
        if total_competitors > 0:
            group_presence_gap = round((1 - competitor_count / total_competitors) * 100, 1)

        # Menu redundancy flag
        menu_redundancy_flag = target_item_count >= 3

        rows.append({
            'narrow_group': group_name,
            'wide_group': wide_group,
            'target_item_count': target_item_count,
            'target_median_price': round(target_median, 2) if target_median else None,
            'target_min_price': target_min,
            'target_max_price': target_max,
            'competitor_count': competitor_count,
            'total_competitors': total_competitors,
            'competitor_item_count': len(competitor_items),
            'competitor_median_price': round(competitor_median, 2) if competitor_median else None,
            'competitor_weighted_median': round(competitor_weighted_median, 2) if competitor_weighted_median else None,
            'competitor_p25': round(competitor_p25, 2) if competitor_p25 else None,
            'competitor_p75': round(competitor_p75, 2) if competitor_p75 else None,
            'competitor_min_price': competitor_min,
            'competitor_max_price': competitor_max,
            'relative_price_gap': relative_price_gap,
            'weighted_price_gap': weighted_price_gap,
            'target_percentile': target_percentile,
            'overpricing_flag': overpricing_flag,
            'underpricing_flag': underpricing_flag,
            'group_presence_gap': group_presence_gap,
            'menu_redundancy_flag': menu_redundancy_flag,
        })

    df = pd.DataFrame(rows)

    # Sort by relative price gap (most overpriced first)
    if not df.empty and 'relative_price_gap' in df.columns:
        df = df.sort_values('relative_price_gap', ascending=False, na_position='last')

    return df


def analyze_wide_groups(
    grouped_data: dict,
    restaurants_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Analyze pricing for wide groups (categories like mains, appetizers).

    Returns DataFrame with category-level metrics.
    """
    if not grouped_data.get('wide_groups'):
        return pd.DataFrame()

    competitor_ids = _get_competitor_ids(restaurants_df)
    total_competitors = len(competitor_ids)

    # Build restaurant confidence lookup
    restaurant_confidence = {}
    if restaurants_df is not None and not restaurants_df.empty:
        for _, row in restaurants_df.iterrows():
            rid = row.get('restaurant_id')
            if rid:
                restaurant_confidence[rid] = _calculate_confidence_score(
                    row.get('rating'),
                    row.get('review_count')
                )

    rows = []
    for category, items in grouped_data['wide_groups'].items():
        target_items = [i for i in items if i['is_target'] and i['price'] is not None]
        competitor_items = [i for i in items if not i['is_target'] and i['price'] is not None]

        target_prices = [i['price'] for i in target_items]
        competitor_prices = [i['price'] for i in competitor_items]

        # Target metrics
        target_median = np.median(target_prices) if target_prices else None
        target_mean = np.mean(target_prices) if target_prices else None
        target_min = min(target_prices) if target_prices else None
        target_max = max(target_prices) if target_prices else None

        # Competitor metrics
        competitor_median = np.median(competitor_prices) if competitor_prices else None
        competitor_mean = np.mean(competitor_prices) if competitor_prices else None
        competitor_p25 = np.percentile(competitor_prices, 25) if competitor_prices else None
        competitor_p75 = np.percentile(competitor_prices, 75) if competitor_prices else None

        # Calculate confidence-weighted median
        competitor_weighted_median = None
        if competitor_items:
            weights = [
                restaurant_confidence.get(i['restaurant_id'], 1.0)
                for i in competitor_items if i['price'] is not None
            ]
            competitor_weighted_median = _weighted_median(competitor_prices, weights)

        # Competitors in category
        competitors_in_category = set(i['restaurant_id'] for i in competitor_items)
        competitor_count = len(competitors_in_category)

        # Price gap
        relative_price_gap = None
        if target_median is not None and competitor_median is not None and competitor_median > 0:
            relative_price_gap = round((target_median - competitor_median) / competitor_median * 100, 1)

        # Weighted price gap
        weighted_price_gap = None
        if target_median is not None and competitor_weighted_median is not None and competitor_weighted_median > 0:
            weighted_price_gap = round((target_median - competitor_weighted_median) / competitor_weighted_median * 100, 1)

        # Target percentile
        target_percentile = None
        if target_median is not None and competitor_prices:
            target_percentile = _calculate_percentile(target_median, competitor_prices)

        # Presence gap
        presence_gap = None
        if total_competitors > 0:
            presence_gap = round((1 - competitor_count / total_competitors) * 100, 1)

        rows.append({
            'wide_group': category,
            'target_item_count': len(target_items),
            'target_median_price': round(target_median, 2) if target_median else None,
            'target_mean_price': round(target_mean, 2) if target_mean else None,
            'target_price_range': f"${target_min:.2f}-${target_max:.2f}" if target_min and target_max else None,
            'competitor_count': competitor_count,
            'competitor_item_count': len(competitor_items),
            'competitor_median_price': round(competitor_median, 2) if competitor_median else None,
            'competitor_weighted_median': round(competitor_weighted_median, 2) if competitor_weighted_median else None,
            'competitor_mean_price': round(competitor_mean, 2) if competitor_mean else None,
            'competitor_p25': round(competitor_p25, 2) if competitor_p25 else None,
            'competitor_p75': round(competitor_p75, 2) if competitor_p75 else None,
            'relative_price_gap': relative_price_gap,
            'weighted_price_gap': weighted_price_gap,
            'target_percentile': target_percentile,
            'presence_gap': presence_gap,
        })

    df = pd.DataFrame(rows)

    if not df.empty:
        df = df.sort_values('target_item_count', ascending=False)

    return df


def calculate_overall_metrics(
    narrow_analysis: pd.DataFrame,
    wide_analysis: pd.DataFrame,
    grouped_data: dict,
) -> dict:
    """
    Calculate overall pricing metrics and summary statistics.
    """
    metrics = {
        'total_target_items': 0,
        'total_competitor_items': 0,
        'avg_price_gap': None,
        'median_price_gap': None,
        'overpriced_count': 0,
        'underpriced_count': 0,
        'competitive_count': 0,
        'avg_target_percentile': None,
        'menu_redundancy_groups': 0,
        'assortment_gaps': [],
    }

    if grouped_data.get('stats'):
        metrics['total_target_items'] = grouped_data['stats'].get('target_items', 0)
        metrics['total_competitor_items'] = grouped_data['stats'].get('competitor_items', 0)

    if not narrow_analysis.empty:
        # Filter to groups where target has items
        target_groups = narrow_analysis[narrow_analysis['target_item_count'] > 0]

        if not target_groups.empty:
            gaps = target_groups['relative_price_gap'].dropna()
            if len(gaps) > 0:
                metrics['avg_price_gap'] = round(gaps.mean(), 1)
                metrics['median_price_gap'] = round(gaps.median(), 1)

            metrics['overpriced_count'] = int(target_groups['overpricing_flag'].sum())
            metrics['underpriced_count'] = int(target_groups['underpricing_flag'].sum())
            metrics['competitive_count'] = int(
                ((~target_groups['overpricing_flag']) & (~target_groups['underpricing_flag'])).sum()
            )

            percentiles = target_groups['target_percentile'].dropna()
            if len(percentiles) > 0:
                metrics['avg_target_percentile'] = round(percentiles.mean(), 1)

            metrics['menu_redundancy_groups'] = int(target_groups['menu_redundancy_flag'].sum())

        # Find assortment gaps (groups where competitors have items but target doesn't)
        competitor_only = narrow_analysis[
            (narrow_analysis['target_item_count'] == 0) &
            (narrow_analysis['competitor_count'] > 0)
        ]
        metrics['assortment_gaps'] = competitor_only['narrow_group'].tolist()

    return metrics


def generate_pricing_insights(
    narrow_analysis: pd.DataFrame,
    wide_analysis: pd.DataFrame,
    overall_metrics: dict,
) -> list[dict]:
    """
    Generate actionable pricing insights from the analysis.

    Returns list of insight dicts with:
        - type: "overpriced" | "underpriced" | "gap" | "redundancy" | "opportunity"
        - severity: "high" | "medium" | "low"
        - group: affected group name
        - message: human-readable insight
        - data: supporting metrics
    """
    insights = []

    if narrow_analysis.empty:
        return insights

    # Overpriced items (sorted by gap)
    overpriced = narrow_analysis[
        (narrow_analysis['overpricing_flag']) &
        (narrow_analysis['target_item_count'] > 0)
    ].sort_values('relative_price_gap', ascending=False)

    for _, row in overpriced.iterrows():
        severity = "high" if row['relative_price_gap'] > 30 else "medium" if row['relative_price_gap'] > 15 else "low"
        insights.append({
            'type': 'overpriced',
            'severity': severity,
            'group': row['narrow_group'],
            'message': f"'{row['narrow_group']}' is {row['relative_price_gap']:.0f}% above competitor median "
                      f"(${row['target_median_price']:.2f} vs ${row['competitor_median_price']:.2f})",
            'data': {
                'target_price': row['target_median_price'],
                'competitor_median': row['competitor_median_price'],
                'competitor_p75': row['competitor_p75'],
                'gap_pct': row['relative_price_gap'],
                'percentile': row['target_percentile'],
            }
        })

    # Underpriced items (potential margin opportunity)
    underpriced = narrow_analysis[
        (narrow_analysis['underpricing_flag']) &
        (narrow_analysis['target_item_count'] > 0)
    ].sort_values('relative_price_gap', ascending=True)

    for _, row in underpriced.iterrows():
        gap = abs(row['relative_price_gap'])
        severity = "high" if gap > 20 else "medium" if gap > 10 else "low"
        insights.append({
            'type': 'underpriced',
            'severity': severity,
            'group': row['narrow_group'],
            'message': f"'{row['narrow_group']}' is {gap:.0f}% below competitor median - potential margin opportunity "
                      f"(${row['target_median_price']:.2f} vs ${row['competitor_median_price']:.2f})",
            'data': {
                'target_price': row['target_median_price'],
                'competitor_median': row['competitor_median_price'],
                'competitor_p25': row['competitor_p25'],
                'gap_pct': row['relative_price_gap'],
                'percentile': row['target_percentile'],
            }
        })

    # Assortment gaps (competitors have, target doesn't)
    for group in overall_metrics.get('assortment_gaps', []):
        row = narrow_analysis[narrow_analysis['narrow_group'] == group].iloc[0]
        if row['competitor_count'] >= 2:  # Only flag if multiple competitors have it
            insights.append({
                'type': 'gap',
                'severity': 'medium',
                'group': group,
                'message': f"'{group}' offered by {row['competitor_count']} competitors but missing from target menu",
                'data': {
                    'competitor_count': row['competitor_count'],
                    'competitor_median_price': row['competitor_median_price'],
                }
            })

    # Menu redundancy
    redundant = narrow_analysis[
        (narrow_analysis['menu_redundancy_flag']) &
        (narrow_analysis['target_item_count'] > 0)
    ]

    for _, row in redundant.iterrows():
        insights.append({
            'type': 'redundancy',
            'severity': 'low',
            'group': row['narrow_group'],
            'message': f"'{row['narrow_group']}' has {row['target_item_count']} items on target menu - "
                      "consider consolidating",
            'data': {
                'item_count': row['target_item_count'],
                'price_range': f"${row['target_min_price']:.2f}-${row['target_max_price']:.2f}"
                              if row['target_min_price'] and row['target_max_price'] else None,
            }
        })

    # Sort by severity
    severity_order = {'high': 0, 'medium': 1, 'low': 2}
    insights.sort(key=lambda x: severity_order.get(x['severity'], 3))

    return insights


def analyze_prices(
    grouped_data: dict,
    restaurants_df: pd.DataFrame,
) -> dict:
    """
    Run complete price analysis on grouped menu data.

    Args:
        grouped_data: Output from group_menus_for_analysis()
        restaurants_df: Restaurants DataFrame with is_target flag

    Returns:
        {
            "narrow_group_analysis": pd.DataFrame with detailed metrics per item group,
            "wide_group_analysis": pd.DataFrame with category-level metrics,
            "overall_metrics": dict with summary statistics,
            "insights": list of actionable insights,
            "target_name": name of target restaurant,
        }
    """
    # Get target name
    target_name = None
    if restaurants_df is not None and not restaurants_df.empty:
        target_row = restaurants_df[restaurants_df['is_target'] == True]
        if not target_row.empty:
            target_name = target_row['name'].iloc[0]

    # Run analyses
    narrow_analysis = analyze_narrow_groups(grouped_data, restaurants_df)
    wide_analysis = analyze_wide_groups(grouped_data, restaurants_df)
    overall_metrics = calculate_overall_metrics(narrow_analysis, wide_analysis, grouped_data)
    insights = generate_pricing_insights(narrow_analysis, wide_analysis, overall_metrics)

    return {
        'narrow_group_analysis': narrow_analysis,
        'wide_group_analysis': wide_analysis,
        'overall_metrics': overall_metrics,
        'insights': insights,
        'target_name': target_name,
    }


def print_price_analysis(analysis: dict) -> None:
    """Pretty print the price analysis results."""

    print("=" * 70)
    print(f"PRICE ANALYSIS: {analysis['target_name'] or 'Target Restaurant'}")
    print("=" * 70)

    # Overall metrics
    metrics = analysis['overall_metrics']
    print("\n--- OVERALL METRICS ---")
    print(f"  Target items: {metrics['total_target_items']}")
    print(f"  Competitor items: {metrics['total_competitor_items']}")
    print(f"  Avg price gap: {metrics['avg_price_gap']}%" if metrics['avg_price_gap'] else "  Avg price gap: N/A")
    print(f"  Median price gap: {metrics['median_price_gap']}%" if metrics['median_price_gap'] else "  Median price gap: N/A")
    print(f"  Avg target percentile: {metrics['avg_target_percentile']}th" if metrics['avg_target_percentile'] else "  Avg target percentile: N/A")
    print(f"\n  Pricing position breakdown:")
    print(f"    Overpriced items: {metrics['overpriced_count']}")
    print(f"    Underpriced items: {metrics['underpriced_count']}")
    print(f"    Competitive items: {metrics['competitive_count']}")
    print(f"    Menu redundancy groups: {metrics['menu_redundancy_groups']}")
    print(f"    Assortment gaps: {len(metrics['assortment_gaps'])}")

    # Narrow group analysis
    narrow = analysis['narrow_group_analysis']
    if not narrow.empty:
        print("\n--- NARROW GROUP ANALYSIS ---")
        display_cols = [
            'narrow_group', 'target_median_price', 'competitor_median_price',
            'relative_price_gap', 'target_percentile', 'overpricing_flag', 'underpricing_flag'
        ]
        display_df = narrow[narrow['target_item_count'] > 0][display_cols].copy()
        display_df.columns = ['Group', 'Target $', 'Comp $', 'Gap %', 'Pctl', 'Over?', 'Under?']
        print(display_df.to_string(index=False))

    # Wide group analysis
    wide = analysis['wide_group_analysis']
    if not wide.empty:
        print("\n--- CATEGORY ANALYSIS ---")
        display_cols = [
            'wide_group', 'target_item_count', 'target_median_price',
            'competitor_median_price', 'relative_price_gap', 'target_percentile'
        ]
        display_df = wide[display_cols].copy()
        display_df.columns = ['Category', 'Items', 'Target $', 'Comp $', 'Gap %', 'Pctl']
        print(display_df.to_string(index=False))

    # Insights
    insights = analysis['insights']
    if insights:
        print("\n--- INSIGHTS ---")
        for i, insight in enumerate(insights, 1):
            severity_icon = "🔴" if insight['severity'] == 'high' else "🟡" if insight['severity'] == 'medium' else "🟢"
            print(f"  {i}. [{severity_icon} {insight['type'].upper()}] {insight['message']}")

    print("\n" + "=" * 70)
