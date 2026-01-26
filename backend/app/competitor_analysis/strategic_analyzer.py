"""
Strategic analytics for restaurant consulting.

Generates insights, visualizations, and initiative recommendations
based on competitive price analysis.

Key Frameworks:
1. Price Positioning Analysis - where does the restaurant sit in the market?
2. Menu Engineering - complexity, balance, optimization opportunities
3. Competitive Gaps - what's missing vs offered by competitors?
4. Initiative Generator - actionable recommendations with impact sizing

Usage:
    from app.competitor_analysis.strategic_analyzer import generate_strategic_analysis

    strategic = generate_strategic_analysis(
        price_analysis=price_analysis,
        grouped_data=grouped_data,
        restaurants_df=restaurants_df,
    )
"""

import io
import base64
from typing import Optional
from dataclasses import dataclass, field

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class PricePositioning:
    """Market positioning analysis results."""
    position: str  # "premium", "mid-market", "value", "inconsistent"
    confidence: float  # 0-1
    avg_percentile: float
    percentile_std: float
    premium_categories: list[str] = field(default_factory=list)
    value_categories: list[str] = field(default_factory=list)
    description: str = ""


@dataclass
class MenuComplexity:
    """Menu engineering metrics."""
    total_items: int
    unique_categories: int
    items_per_category: float
    redundancy_score: float  # 0-1, higher = more redundant
    complexity_rating: str  # "lean", "balanced", "complex", "bloated"
    redundant_groups: list[str] = field(default_factory=list)


@dataclass
class CompetitiveGap:
    """Gap analysis results."""
    gap_type: str  # "missing_item", "price_opportunity", "differentiation"
    group_name: str
    description: str
    competitor_count: int
    avg_competitor_price: Optional[float]
    opportunity_size: str  # "high", "medium", "low"


@dataclass
class Initiative:
    """Strategic initiative recommendation."""
    id: str
    title: str
    category: str  # "pricing", "menu", "positioning", "operations"
    priority: str  # "high", "medium", "low"
    hypothesis: str
    evidence: list[str]
    expected_impact: str
    implementation_complexity: str  # "easy", "medium", "hard"
    metrics_to_track: list[str]


@dataclass
class PremiumValidation:
    """
    Cross-check of pricing premium against rating/review evidence.

    Validates whether premium pricing is justified by customer perception.
    """
    is_premium_priced: bool  # Is target priced above market median?
    premium_pct: float  # How much above median (e.g., +18%)

    # Target's reputation metrics
    target_rating: Optional[float]
    target_review_count: Optional[int]
    target_confidence_score: float  # rating * log(reviews)

    # Competitor benchmark
    competitor_avg_rating: Optional[float]
    competitor_avg_review_count: Optional[float]
    competitor_avg_confidence: float

    # Validation result
    validation_status: str  # "justified", "misaligned", "insufficient_data", "value_leader"
    confidence_gap: float  # target confidence - competitor avg confidence

    # Detailed findings
    description: str
    risk_level: str  # "low", "medium", "high"
    recommendations: list[str] = field(default_factory=list)


# =============================================================================
# POSITIONING ANALYSIS
# =============================================================================

def analyze_price_positioning(
    price_analysis: dict,
) -> PricePositioning:
    """
    Determine market positioning based on price percentiles.

    Premium: avg percentile > 70
    Mid-market: avg percentile 30-70
    Value: avg percentile < 30
    Inconsistent: high std dev across categories
    """
    narrow = price_analysis.get('narrow_group_analysis')
    if narrow is None or narrow.empty:
        return PricePositioning(
            position="unknown",
            confidence=0,
            avg_percentile=0,
            percentile_std=0,
            description="Insufficient data for positioning analysis"
        )

    # Filter to groups with competitor comparison
    with_comps = narrow[
        (narrow['target_item_count'] > 0) &
        (narrow['target_percentile'].notna())
    ]

    if with_comps.empty:
        return PricePositioning(
            position="unknown",
            confidence=0,
            avg_percentile=0,
            percentile_std=0,
            description="No competitor comparisons available"
        )

    percentiles = with_comps['target_percentile']
    avg_pctl = percentiles.mean()
    std_pctl = percentiles.std()

    # Determine position
    if std_pctl > 25:
        position = "inconsistent"
        description = (
            f"Pricing is inconsistent across menu (std dev: {std_pctl:.0f}). "
            "Some items are premium-priced while others are value-positioned, "
            "which may confuse customers about brand positioning."
        )
    elif avg_pctl >= 70:
        position = "premium"
        description = (
            f"Premium positioning with average {avg_pctl:.0f}th percentile pricing. "
            "Prices are consistently above most competitors. "
            "This requires strong differentiation and perceived value to sustain."
        )
    elif avg_pctl >= 30:
        position = "mid-market"
        description = (
            f"Mid-market positioning at {avg_pctl:.0f}th percentile. "
            "Competitive pricing that balances value and margin. "
            "Consider selective premium pricing on differentiated items."
        )
    else:
        position = "value"
        description = (
            f"Value positioning at {avg_pctl:.0f}th percentile. "
            "Prices are below most competitors. "
            "May be leaving margin on table if quality/experience justifies higher prices."
        )

    # Find premium and value categories
    premium_cats = with_comps[with_comps['target_percentile'] >= 75]['narrow_group'].tolist()
    value_cats = with_comps[with_comps['target_percentile'] <= 25]['narrow_group'].tolist()

    # Confidence based on sample size and consistency
    n_groups = len(with_comps)
    confidence = min(1.0, n_groups / 10) * (1 - min(std_pctl / 50, 0.5))

    return PricePositioning(
        position=position,
        confidence=round(confidence, 2),
        avg_percentile=round(avg_pctl, 1),
        percentile_std=round(std_pctl, 1),
        premium_categories=premium_cats,
        value_categories=value_cats,
        description=description,
    )


# =============================================================================
# PREMIUM VALIDATION
# =============================================================================

def _calculate_confidence_score(rating: float, review_count: int) -> float:
    """
    Calculate confidence score: rating * log(review_count + 1).

    Duplicated from price_analyzer for independence.
    """
    import math

    if rating is None or review_count is None:
        return 0.0

    rating = float(rating) if rating else 0
    review_count = int(review_count) if review_count else 0

    rating = max(0, min(5, rating))
    review_count = max(0, review_count)

    log_reviews = math.log10(review_count + 1)
    return (rating + 1) * log_reviews if log_reviews > 0 else 0.0


def validate_premium_pricing(
    price_analysis: dict,
    restaurants_df: pd.DataFrame,
) -> PremiumValidation:
    """
    Cross-check pricing premium against rating/review evidence.

    Determines if premium pricing is justified by customer perception:
    - High price + high reviews = justified premium
    - High price + low reviews = misaligned premium (RED FLAG)
    - Low price + high reviews = value leader (margin opportunity)
    - Low price + low reviews = appropriate positioning

    Returns PremiumValidation with status, confidence gap, and recommendations.
    """
    # Get overall price gap
    overall = price_analysis.get('overall_metrics', {})
    avg_gap = overall.get('avg_price_gap', 0) or 0
    is_premium = avg_gap > 5  # More than 5% above median = premium

    # Get target restaurant metrics
    target_rating = None
    target_review_count = None
    target_confidence = 0.0

    if restaurants_df is not None and not restaurants_df.empty:
        target_row = restaurants_df[restaurants_df['is_target'] == True]
        if not target_row.empty:
            target_rating = target_row['rating'].iloc[0]
            target_review_count = target_row['review_count'].iloc[0]
            if pd.notna(target_rating) and pd.notna(target_review_count):
                target_confidence = _calculate_confidence_score(
                    float(target_rating),
                    int(target_review_count)
                )

    # Get competitor metrics
    competitor_rows = restaurants_df[restaurants_df['is_target'] == False] if restaurants_df is not None else pd.DataFrame()

    competitor_avg_rating = None
    competitor_avg_review_count = None
    competitor_avg_confidence = 0.0

    if not competitor_rows.empty:
        ratings = competitor_rows['rating'].dropna()
        reviews = competitor_rows['review_count'].dropna()

        if len(ratings) > 0:
            competitor_avg_rating = round(ratings.mean(), 2)
        if len(reviews) > 0:
            competitor_avg_review_count = round(reviews.mean(), 0)

        # Calculate average confidence
        confidences = []
        for _, row in competitor_rows.iterrows():
            r = row.get('rating')
            rc = row.get('review_count')
            if pd.notna(r) and pd.notna(rc):
                confidences.append(_calculate_confidence_score(float(r), int(rc)))

        if confidences:
            competitor_avg_confidence = sum(confidences) / len(confidences)

    # Calculate confidence gap
    confidence_gap = target_confidence - competitor_avg_confidence

    # Determine validation status
    has_data = target_rating is not None and target_review_count is not None

    if not has_data:
        validation_status = "insufficient_data"
        risk_level = "medium"
        description = (
            "Unable to validate pricing premium - target restaurant lacks rating/review data. "
            "Consider gathering customer feedback to justify current pricing."
        )
        recommendations = [
            "Encourage customer reviews on Google/Uber Eats",
            "Monitor review trends to validate pricing",
        ]
    elif is_premium and confidence_gap >= 0:
        # Premium priced AND has equal or better reputation
        validation_status = "justified"
        risk_level = "low"
        description = (
            f"Premium pricing (+{avg_gap:.0f}%) appears justified. "
            f"Target has {target_rating:.1f}★ with {target_review_count:,} reviews, "
            f"{'above' if confidence_gap > 0 else 'matching'} competitor average "
            f"({competitor_avg_rating:.1f}★, {competitor_avg_review_count:.0f} reviews). "
            "Strong customer perception supports higher prices."
        )
        recommendations = [
            "Maintain quality to preserve premium positioning",
            "Consider modest price increases on highest-rated items",
        ]
    elif is_premium and confidence_gap < 0:
        # Premium priced BUT lower reputation = MISALIGNED
        validation_status = "misaligned"
        risk_level = "high"
        gap_severity = "significantly" if confidence_gap < -2 else "somewhat"
        description = (
            f"⚠️ MISALIGNED PREMIUM: Pricing is +{avg_gap:.0f}% above market, "
            f"but reputation is {gap_severity} below competitors. "
            f"Target: {target_rating:.1f}★ ({target_review_count:,} reviews) vs "
            f"Competitor avg: {competitor_avg_rating:.1f}★ ({competitor_avg_review_count:.0f} reviews). "
            "Customers may perceive poor value, risking volume loss."
        )
        recommendations = [
            "Reduce prices on overpriced items to align with perceived value",
            "Invest in service/quality improvements to justify premium",
            "Focus on generating more positive reviews",
            "Consider promotional pricing to rebuild customer base",
        ]
    elif not is_premium and confidence_gap > 0:
        # Priced at or below market BUT better reputation = margin opportunity
        validation_status = "value_leader"
        risk_level = "low"
        description = (
            f"💰 VALUE LEADER: Priced {abs(avg_gap):.0f}% {'below' if avg_gap < 0 else 'at'} market, "
            f"but reputation exceeds competitors. "
            f"Target: {target_rating:.1f}★ ({target_review_count:,} reviews) vs "
            f"Competitor avg: {competitor_avg_rating:.1f}★ ({competitor_avg_review_count:.0f} reviews). "
            "Strong margin capture opportunity."
        )
        recommendations = [
            "Raise prices on items where target significantly outperforms market",
            "Premium pricing likely sustainable given customer satisfaction",
            "Test price increases on signature/unique items first",
        ]
    else:
        # Priced at or below market with average reputation
        validation_status = "appropriate"
        risk_level = "low"
        description = (
            f"Pricing appears appropriately aligned with reputation. "
            f"Target: {target_rating:.1f}★ ({target_review_count:,} reviews), "
            f"Competitor avg: {competitor_avg_rating:.1f}★ ({competitor_avg_review_count:.0f} reviews)."
        )
        recommendations = []

    return PremiumValidation(
        is_premium_priced=is_premium,
        premium_pct=round(avg_gap, 1),
        target_rating=target_rating,
        target_review_count=target_review_count,
        target_confidence_score=round(target_confidence, 2),
        competitor_avg_rating=competitor_avg_rating,
        competitor_avg_review_count=competitor_avg_review_count,
        competitor_avg_confidence=round(competitor_avg_confidence, 2),
        validation_status=validation_status,
        confidence_gap=round(confidence_gap, 2),
        description=description,
        risk_level=risk_level,
        recommendations=recommendations,
    )


# =============================================================================
# MENU ENGINEERING
# =============================================================================

def analyze_menu_complexity(
    grouped_data: dict,
    price_analysis: dict,
) -> MenuComplexity:
    """
    Analyze menu structure and identify complexity issues.
    """
    stats = grouped_data.get('stats', {})
    total_items = stats.get('target_items', 0)

    wide = price_analysis.get('wide_group_analysis')
    narrow = price_analysis.get('narrow_group_analysis')

    if wide is None or wide.empty:
        return MenuComplexity(
            total_items=total_items,
            unique_categories=0,
            items_per_category=0,
            redundancy_score=0,
            complexity_rating="unknown",
        )

    # Count categories with target items
    target_categories = wide[wide['target_item_count'] > 0]
    unique_cats = len(target_categories)

    items_per_cat = total_items / unique_cats if unique_cats > 0 else 0

    # Find redundant groups (3+ items in narrow group)
    redundant_groups = []
    if narrow is not None and not narrow.empty:
        redundant = narrow[narrow['target_item_count'] >= 3]
        redundant_groups = redundant['narrow_group'].tolist()

    # Redundancy score: ratio of items in redundant groups
    redundant_item_count = sum(
        narrow[narrow['narrow_group'] == g]['target_item_count'].iloc[0]
        for g in redundant_groups
    ) if redundant_groups and narrow is not None else 0

    redundancy_score = redundant_item_count / total_items if total_items > 0 else 0

    # Complexity rating
    if total_items <= 15:
        complexity_rating = "lean"
    elif total_items <= 30 and redundancy_score < 0.2:
        complexity_rating = "balanced"
    elif total_items <= 50 and redundancy_score < 0.3:
        complexity_rating = "complex"
    else:
        complexity_rating = "bloated"

    return MenuComplexity(
        total_items=total_items,
        unique_categories=unique_cats,
        items_per_category=round(items_per_cat, 1),
        redundancy_score=round(redundancy_score, 2),
        complexity_rating=complexity_rating,
        redundant_groups=redundant_groups,
    )


# =============================================================================
# GAP ANALYSIS
# =============================================================================

def identify_competitive_gaps(
    grouped_data: dict,
    price_analysis: dict,
) -> list[CompetitiveGap]:
    """
    Identify gaps and opportunities in menu coverage.
    """
    gaps = []
    narrow = price_analysis.get('narrow_group_analysis')

    if narrow is None or narrow.empty:
        return gaps

    # 1. Missing items (competitors have, target doesn't)
    missing = narrow[
        (narrow['target_item_count'] == 0) &
        (narrow['competitor_count'] >= 2)
    ]

    for _, row in missing.iterrows():
        opportunity = "high" if row['competitor_count'] >= 3 else "medium"
        gaps.append(CompetitiveGap(
            gap_type="missing_item",
            group_name=row['narrow_group'],
            description=f"{row['competitor_count']} competitors offer this, but it's missing from your menu",
            competitor_count=row['competitor_count'],
            avg_competitor_price=row['competitor_median_price'],
            opportunity_size=opportunity,
        ))

    # 2. Underpriced items (margin opportunity)
    underpriced = narrow[
        (narrow['target_item_count'] > 0) &
        (narrow['underpricing_flag'] == True)
    ]

    for _, row in underpriced.iterrows():
        gap_pct = abs(row['relative_price_gap'])
        opportunity = "high" if gap_pct > 20 else "medium" if gap_pct > 10 else "low"
        gaps.append(CompetitiveGap(
            gap_type="price_opportunity",
            group_name=row['narrow_group'],
            description=f"Priced {gap_pct:.0f}% below competitor median - potential margin opportunity",
            competitor_count=row['competitor_count'],
            avg_competitor_price=row['competitor_median_price'],
            opportunity_size=opportunity,
        ))

    # 3. Unique/differentiated items (no competitor comparison)
    unique = narrow[
        (narrow['target_item_count'] > 0) &
        (narrow['competitor_count'] == 0)
    ]

    for _, row in unique.iterrows():
        gaps.append(CompetitiveGap(
            gap_type="differentiation",
            group_name=row['narrow_group'],
            description="Unique item not offered by competitors - potential differentiator",
            competitor_count=0,
            avg_competitor_price=None,
            opportunity_size="medium",
        ))

    # Sort by opportunity size
    priority_order = {"high": 0, "medium": 1, "low": 2}
    gaps.sort(key=lambda x: priority_order.get(x.opportunity_size, 3))

    return gaps


# =============================================================================
# INITIATIVE GENERATOR
# =============================================================================

def generate_initiatives(
    positioning: PricePositioning,
    complexity: MenuComplexity,
    gaps: list[CompetitiveGap],
    price_analysis: dict,
    premium_validation: Optional[PremiumValidation] = None,
) -> list[Initiative]:
    """
    Generate strategic initiatives based on analysis findings.
    """
    initiatives = []
    narrow = price_analysis.get('narrow_group_analysis', pd.DataFrame())
    overall = price_analysis.get('overall_metrics', {})

    # Initiative 0: Address misaligned premium (highest priority if detected)
    if premium_validation and premium_validation.validation_status == "misaligned":
        initiatives.append(Initiative(
            id="PRICE-00",
            title="Address Price-Quality Misalignment",
            category="pricing",
            priority="high",
            hypothesis="Current premium pricing is not supported by customer perception; realigning will prevent volume loss and improve competitiveness",
            evidence=[
                f"Priced {premium_validation.premium_pct:+.0f}% above market median",
                f"Target rating: {premium_validation.target_rating:.1f}★ ({premium_validation.target_review_count:,} reviews)",
                f"Competitor avg: {premium_validation.competitor_avg_rating:.1f}★ ({premium_validation.competitor_avg_review_count:.0f} reviews)",
                f"Confidence gap: {premium_validation.confidence_gap:.2f} (negative = below competitors)",
            ],
            expected_impact="Prevent customer churn; improve perceived value; potential 10-20% volume recovery",
            implementation_complexity="medium",
            metrics_to_track=["Customer review scores", "Order volume trends", "Price perception", "Repeat customer rate"],
        ))

    # Initiative 0b: Capitalize on value leader position
    if premium_validation and premium_validation.validation_status == "value_leader":
        initiatives.append(Initiative(
            id="PRICE-00",
            title="Capture Margin from Strong Reputation",
            category="pricing",
            priority="high",
            hypothesis="Strong customer perception supports price increases without demand loss",
            evidence=[
                f"Currently priced {abs(premium_validation.premium_pct):.0f}% {'below' if premium_validation.premium_pct < 0 else 'at'} market",
                f"Target rating: {premium_validation.target_rating:.1f}★ ({premium_validation.target_review_count:,} reviews)",
                f"Competitor avg: {premium_validation.competitor_avg_rating:.1f}★ ({premium_validation.competitor_avg_review_count:.0f} reviews)",
                f"Confidence gap: +{premium_validation.confidence_gap:.2f} (above competitors)",
            ],
            expected_impact="5-15% margin improvement without volume loss; capitalize on customer loyalty",
            implementation_complexity="easy",
            metrics_to_track=["Margin per order", "Volume impact", "Customer satisfaction"],
        ))

    # Initiative 1: Price optimization
    overpriced_count = overall.get('overpriced_count', 0)
    if overpriced_count >= 3:
        # Find top overpriced items
        if not narrow.empty:
            top_overpriced = narrow[narrow['overpricing_flag']].nlargest(3, 'relative_price_gap')
            evidence = [
                f"'{row['narrow_group']}' is {row['relative_price_gap']:.0f}% above market"
                for _, row in top_overpriced.iterrows()
            ]
        else:
            evidence = [f"{overpriced_count} items priced above competitor 75th percentile"]

        initiatives.append(Initiative(
            id="PRICE-01",
            title="Selective Price Adjustment for High-Gap Items",
            category="pricing",
            priority="high",
            hypothesis="Reducing prices on items significantly above market will increase order volume without proportional margin loss",
            evidence=evidence,
            expected_impact="5-15% increase in orders for adjusted items; improved price perception",
            implementation_complexity="easy",
            metrics_to_track=["Item-level sales volume", "Basket size", "Price perception surveys"],
        ))

    # Initiative 2: Margin capture on underpriced items
    margin_gaps = [g for g in gaps if g.gap_type == "price_opportunity"]
    if margin_gaps:
        evidence = [f"'{g.group_name}': {g.description}" for g in margin_gaps[:3]]
        initiatives.append(Initiative(
            id="PRICE-02",
            title="Margin Capture on Underpriced Items",
            category="pricing",
            priority="medium",
            hypothesis="Raising prices on underpriced items to market median will capture margin without demand impact",
            evidence=evidence,
            expected_impact="Direct margin improvement of 10-20% on affected items",
            implementation_complexity="easy",
            metrics_to_track=["Item margin", "Sales volume change", "Customer complaints"],
        ))

    # Initiative 3: Menu rationalization
    if complexity.complexity_rating in ("complex", "bloated") or complexity.redundant_groups:
        evidence = [
            f"Menu has {complexity.total_items} items across {complexity.unique_categories} categories",
            f"Redundancy score: {complexity.redundancy_score:.0%}",
        ]
        if complexity.redundant_groups:
            evidence.append(f"Redundant groups: {', '.join(complexity.redundant_groups[:3])}")

        initiatives.append(Initiative(
            id="MENU-01",
            title="Menu Rationalization & Simplification",
            category="menu",
            priority="medium",
            hypothesis="Reducing menu complexity will lower operational costs, reduce decision fatigue, and improve kitchen efficiency",
            evidence=evidence,
            expected_impact="10-20% reduction in food waste; faster ticket times; reduced training costs",
            implementation_complexity="medium",
            metrics_to_track=["Food cost %", "Average ticket time", "Item sell-through rates"],
        ))

    # Initiative 4: Fill assortment gaps
    missing_items = [g for g in gaps if g.gap_type == "missing_item" and g.opportunity_size == "high"]
    if missing_items:
        evidence = [
            f"'{g.group_name}' offered by {g.competitor_count} competitors at ~${g.avg_competitor_price:.2f}"
            for g in missing_items[:3]
        ]
        initiatives.append(Initiative(
            id="MENU-02",
            title="Fill High-Demand Assortment Gaps",
            category="menu",
            priority="medium",
            hypothesis="Adding commonly-offered items will capture customers who currently go elsewhere for these items",
            evidence=evidence,
            expected_impact="Incremental sales from new items; improved competitive position",
            implementation_complexity="medium",
            metrics_to_track=["New item sales", "Customer acquisition", "Basket composition"],
        ))

    # Initiative 5: Positioning clarification
    if positioning.position == "inconsistent":
        initiatives.append(Initiative(
            id="POS-01",
            title="Clarify Price Positioning Strategy",
            category="positioning",
            priority="high",
            hypothesis="Consistent pricing signals improve brand perception and customer expectations",
            evidence=[
                f"Pricing std dev of {positioning.percentile_std:.0f} percentile points",
                f"Premium categories: {', '.join(positioning.premium_categories[:2]) or 'None'}",
                f"Value categories: {', '.join(positioning.value_categories[:2]) or 'None'}",
            ],
            expected_impact="Clearer brand identity; reduced customer confusion; improved loyalty",
            implementation_complexity="medium",
            metrics_to_track=["Brand perception scores", "Repeat customer rate", "Price complaints"],
        ))

    # Initiative 6: Leverage differentiation
    unique_items = [g for g in gaps if g.gap_type == "differentiation"]
    if len(unique_items) >= 2:
        initiatives.append(Initiative(
            id="POS-02",
            title="Amplify Unique Menu Differentiators",
            category="positioning",
            priority="low",
            hypothesis="Promoting unique items competitors don't offer will strengthen competitive moat",
            evidence=[f"Unique item: '{g.group_name}'" for g in unique_items[:3]],
            expected_impact="Increased awareness of differentiators; improved competitive position",
            implementation_complexity="easy",
            metrics_to_track=["Unique item sales %", "Customer mentions", "Social media engagement"],
        ))

    # Sort by priority
    priority_order = {"high": 0, "medium": 1, "low": 2}
    initiatives.sort(key=lambda x: priority_order.get(x.priority, 3))

    return initiatives


# =============================================================================
# VISUALIZATIONS
# =============================================================================

def create_price_positioning_chart(
    price_analysis: dict,
    figsize: tuple = (12, 6),
) -> str:
    """
    Create price positioning scatter plot.

    Returns base64 encoded PNG.
    """
    narrow = price_analysis.get('narrow_group_analysis')
    if narrow is None or narrow.empty:
        return None

    # Filter to items with comparisons
    data = narrow[
        (narrow['target_item_count'] > 0) &
        (narrow['competitor_median_price'].notna())
    ].copy()

    if data.empty:
        return None

    fig, ax = plt.subplots(figsize=figsize)

    # Plot items
    colors = []
    for _, row in data.iterrows():
        if row['overpricing_flag']:
            colors.append('#e74c3c')  # Red
        elif row['underpricing_flag']:
            colors.append('#27ae60')  # Green
        else:
            colors.append('#3498db')  # Blue

    scatter = ax.scatter(
        data['competitor_median_price'],
        data['target_median_price'],
        c=colors,
        s=100,
        alpha=0.7,
        edgecolors='white',
        linewidth=1,
    )

    # Add item labels
    for _, row in data.iterrows():
        ax.annotate(
            row['narrow_group'],
            (row['competitor_median_price'], row['target_median_price']),
            xytext=(5, 5),
            textcoords='offset points',
            fontsize=8,
            alpha=0.8,
        )

    # Add diagonal line (parity)
    max_price = max(data['target_median_price'].max(), data['competitor_median_price'].max())
    ax.plot([0, max_price * 1.1], [0, max_price * 1.1], 'k--', alpha=0.3, label='Price parity')

    # Labels
    ax.set_xlabel('Competitor Median Price ($)', fontsize=11)
    ax.set_ylabel('Target Price ($)', fontsize=11)
    ax.set_title('Price Positioning: Target vs Competitors', fontsize=13, fontweight='bold')

    # Legend
    legend_elements = [
        mpatches.Patch(color='#e74c3c', label='Overpriced (>p75)'),
        mpatches.Patch(color='#3498db', label='Competitive'),
        mpatches.Patch(color='#27ae60', label='Underpriced (<p25)'),
    ]
    ax.legend(handles=legend_elements, loc='upper left')

    ax.grid(True, alpha=0.3)
    plt.tight_layout()

    # Convert to base64
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
    buffer.seek(0)
    img_str = base64.b64encode(buffer.read()).decode()
    plt.close()

    return img_str


def create_category_comparison_chart(
    price_analysis: dict,
    figsize: tuple = (10, 6),
) -> str:
    """
    Create category-level price comparison bar chart.

    Returns base64 encoded PNG.
    """
    wide = price_analysis.get('wide_group_analysis')
    if wide is None or wide.empty:
        return None

    # Filter to categories with both target and competitor data
    data = wide[
        (wide['target_item_count'] > 0) &
        (wide['competitor_median_price'].notna())
    ].copy()

    if data.empty:
        return None

    fig, ax = plt.subplots(figsize=figsize)

    categories = data['wide_group'].tolist()
    x = np.arange(len(categories))
    width = 0.35

    target_prices = data['target_median_price'].tolist()
    comp_prices = data['competitor_median_price'].tolist()

    bars1 = ax.bar(x - width/2, target_prices, width, label='Target', color='#3498db')
    bars2 = ax.bar(x + width/2, comp_prices, width, label='Competitor Median', color='#95a5a6')

    # Add gap annotations
    for i, (t, c) in enumerate(zip(target_prices, comp_prices)):
        if c > 0:
            gap = (t - c) / c * 100
            color = '#e74c3c' if gap > 0 else '#27ae60'
            ax.annotate(
                f'{gap:+.0f}%',
                (i, max(t, c) + 0.5),
                ha='center',
                fontsize=9,
                color=color,
                fontweight='bold',
            )

    ax.set_xlabel('Category', fontsize=11)
    ax.set_ylabel('Median Price ($)', fontsize=11)
    ax.set_title('Price Comparison by Category', fontsize=13, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(categories, rotation=45, ha='right')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()

    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
    buffer.seek(0)
    img_str = base64.b64encode(buffer.read()).decode()
    plt.close()

    return img_str


def create_price_gap_waterfall(
    price_analysis: dict,
    figsize: tuple = (12, 6),
) -> str:
    """
    Create waterfall chart showing price gaps by item.

    Returns base64 encoded PNG.
    """
    narrow = price_analysis.get('narrow_group_analysis')
    if narrow is None or narrow.empty:
        return None

    # Get items with price gaps, sorted by gap
    data = narrow[
        (narrow['target_item_count'] > 0) &
        (narrow['relative_price_gap'].notna())
    ].sort_values('relative_price_gap', ascending=False).head(10)

    if data.empty:
        return None

    fig, ax = plt.subplots(figsize=figsize)

    items = data['narrow_group'].tolist()
    gaps = data['relative_price_gap'].tolist()

    colors = ['#e74c3c' if g > 0 else '#27ae60' for g in gaps]

    bars = ax.barh(items, gaps, color=colors, alpha=0.8)

    # Add value labels
    for bar, gap in zip(bars, gaps):
        width = bar.get_width()
        ax.annotate(
            f'{gap:+.1f}%',
            xy=(width, bar.get_y() + bar.get_height()/2),
            xytext=(5 if width >= 0 else -5, 0),
            textcoords='offset points',
            ha='left' if width >= 0 else 'right',
            va='center',
            fontsize=9,
        )

    ax.axvline(x=0, color='black', linewidth=0.5)
    ax.set_xlabel('Price Gap vs Competitor Median (%)', fontsize=11)
    ax.set_title('Price Gap Analysis by Item', fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='x')

    plt.tight_layout()

    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
    buffer.seek(0)
    img_str = base64.b64encode(buffer.read()).decode()
    plt.close()

    return img_str


def create_percentile_distribution(
    price_analysis: dict,
    figsize: tuple = (10, 5),
) -> str:
    """
    Create histogram of target's price percentiles.

    Returns base64 encoded PNG.
    """
    narrow = price_analysis.get('narrow_group_analysis')
    if narrow is None or narrow.empty:
        return None

    percentiles = narrow[
        (narrow['target_item_count'] > 0) &
        (narrow['target_percentile'].notna())
    ]['target_percentile']

    if percentiles.empty:
        return None

    fig, ax = plt.subplots(figsize=figsize)

    # Create histogram
    bins = [0, 25, 50, 75, 100]
    counts, _, patches = ax.hist(percentiles, bins=bins, edgecolor='white', linewidth=1)

    # Color by zone
    colors = ['#27ae60', '#f1c40f', '#e67e22', '#e74c3c']
    for patch, color in zip(patches, colors):
        patch.set_facecolor(color)

    ax.set_xlabel('Price Percentile vs Competitors', fontsize=11)
    ax.set_ylabel('Number of Items', fontsize=11)
    ax.set_title('Distribution of Price Percentiles', fontsize=13, fontweight='bold')
    ax.set_xticks([12.5, 37.5, 62.5, 87.5])
    ax.set_xticklabels(['Value\n(0-25)', 'Mid-Low\n(25-50)', 'Mid-High\n(50-75)', 'Premium\n(75-100)'])

    # Add count labels
    for i, count in enumerate(counts):
        if count > 0:
            ax.annotate(
                f'{int(count)}',
                (bins[i] + 12.5, count + 0.1),
                ha='center',
                fontsize=11,
                fontweight='bold',
            )

    plt.tight_layout()

    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
    buffer.seek(0)
    img_str = base64.b64encode(buffer.read()).decode()
    plt.close()

    return img_str


# =============================================================================
# MAIN ORCHESTRATOR
# =============================================================================

def generate_strategic_analysis(
    price_analysis: dict,
    grouped_data: dict,
    restaurants_df: pd.DataFrame,
) -> dict:
    """
    Generate complete strategic analysis with insights and visualizations.

    Args:
        price_analysis: Output from analyze_prices()
        grouped_data: Output from group_menus_for_analysis()
        restaurants_df: Restaurants DataFrame

    Returns:
        {
            "target_name": str,
            "positioning": PricePositioning,
            "premium_validation": PremiumValidation,
            "menu_complexity": MenuComplexity,
            "competitive_gaps": list[CompetitiveGap],
            "initiatives": list[Initiative],
            "visualizations": {
                "price_positioning": base64 PNG,
                "category_comparison": base64 PNG,
                "price_gap_waterfall": base64 PNG,
                "percentile_distribution": base64 PNG,
            },
            "executive_summary": str,
        }
    """
    # Get target name
    target_name = price_analysis.get('target_name', 'Target Restaurant')

    # Run analyses
    positioning = analyze_price_positioning(price_analysis)
    premium_validation = validate_premium_pricing(price_analysis, restaurants_df)
    complexity = analyze_menu_complexity(grouped_data, price_analysis)
    gaps = identify_competitive_gaps(grouped_data, price_analysis)
    initiatives = generate_initiatives(positioning, complexity, gaps, price_analysis, premium_validation)

    # Generate visualizations
    visualizations = {
        'price_positioning': create_price_positioning_chart(price_analysis),
        'category_comparison': create_category_comparison_chart(price_analysis),
        'price_gap_waterfall': create_price_gap_waterfall(price_analysis),
        'percentile_distribution': create_percentile_distribution(price_analysis),
    }

    # Generate executive summary
    overall = price_analysis.get('overall_metrics', {})
    exec_summary = _generate_executive_summary(
        target_name, positioning, premium_validation, complexity, gaps, initiatives, overall
    )

    return {
        'target_name': target_name,
        'positioning': positioning,
        'premium_validation': premium_validation,
        'menu_complexity': complexity,
        'competitive_gaps': gaps,
        'initiatives': initiatives,
        'visualizations': visualizations,
        'executive_summary': exec_summary,
    }


def _generate_executive_summary(
    target_name: str,
    positioning: PricePositioning,
    premium_validation: PremiumValidation,
    complexity: MenuComplexity,
    gaps: list[CompetitiveGap],
    initiatives: list[Initiative],
    overall: dict,
) -> str:
    """Generate executive summary text."""

    lines = [
        f"# Strategic Analysis: {target_name}",
        "",
        "## Market Positioning",
        positioning.description,
        "",
    ]

    # Add premium validation section if meaningful
    if premium_validation.validation_status != "insufficient_data":
        lines.extend([
            "## Premium Validation",
            premium_validation.description,
            "",
        ])
        if premium_validation.recommendations:
            lines.append("**Recommendations:**")
            for rec in premium_validation.recommendations[:3]:
                lines.append(f"- {rec}")
            lines.append("")

    lines.append("## Key Findings")

    # Pricing findings
    avg_gap = overall.get('avg_price_gap')
    if avg_gap:
        direction = "above" if avg_gap > 0 else "below"
        lines.append(f"- Prices average {abs(avg_gap):.0f}% {direction} competitor median")

    overpriced = overall.get('overpriced_count', 0)
    underpriced = overall.get('underpriced_count', 0)
    if overpriced:
        lines.append(f"- {overpriced} items flagged as overpriced (above competitor 75th percentile)")
    if underpriced:
        lines.append(f"- {underpriced} items potentially underpriced (margin opportunity)")

    # Menu findings
    lines.append(f"- Menu complexity: {complexity.complexity_rating} ({complexity.total_items} items)")
    if complexity.redundant_groups:
        lines.append(f"- Menu redundancy detected in: {', '.join(complexity.redundant_groups)}")

    # Gap findings
    missing = [g for g in gaps if g.gap_type == "missing_item"]
    if missing:
        lines.append(f"- {len(missing)} potential menu gaps vs competitors")

    # Initiatives
    lines.extend([
        "",
        "## Recommended Initiatives",
    ])
    for i, init in enumerate(initiatives[:5], 1):
        lines.append(f"{i}. [{init.priority.upper()}] {init.title}")

    return "\n".join(lines)


def print_strategic_analysis(analysis: dict) -> None:
    """Pretty print strategic analysis results."""

    print("=" * 70)
    print(f"STRATEGIC ANALYSIS: {analysis['target_name']}")
    print("=" * 70)

    # Positioning
    pos = analysis['positioning']
    print(f"\n--- MARKET POSITIONING: {pos.position.upper()} ---")
    print(f"  Average percentile: {pos.avg_percentile}th")
    print(f"  Confidence: {pos.confidence:.0%}")
    print(f"\n  {pos.description}")

    # Premium Validation
    pv = analysis.get('premium_validation')
    if pv:
        status_icons = {
            "justified": "✅",
            "misaligned": "⚠️",
            "value_leader": "💰",
            "appropriate": "✓",
            "insufficient_data": "❓",
        }
        icon = status_icons.get(pv.validation_status, "")
        print(f"\n--- PREMIUM VALIDATION: {icon} {pv.validation_status.upper()} ---")
        print(f"  Premium: {'+' if pv.premium_pct > 0 else ''}{pv.premium_pct}% vs market")
        if pv.target_rating:
            print(f"  Target: {pv.target_rating:.1f}★ ({pv.target_review_count:,} reviews)")
        if pv.competitor_avg_rating:
            print(f"  Competitors: {pv.competitor_avg_rating:.1f}★ avg ({pv.competitor_avg_review_count:.0f} reviews avg)")
        print(f"  Confidence gap: {pv.confidence_gap:+.2f}")
        print(f"  Risk level: {pv.risk_level}")
        print(f"\n  {pv.description}")
        if pv.recommendations:
            print("\n  Recommendations:")
            for rec in pv.recommendations:
                print(f"    • {rec}")

    # Menu complexity
    comp = analysis['menu_complexity']
    print(f"\n--- MENU COMPLEXITY: {comp.complexity_rating.upper()} ---")
    print(f"  Total items: {comp.total_items}")
    print(f"  Categories: {comp.unique_categories}")
    print(f"  Items per category: {comp.items_per_category}")
    print(f"  Redundancy score: {comp.redundancy_score:.0%}")
    if comp.redundant_groups:
        print(f"  Redundant groups: {', '.join(comp.redundant_groups)}")

    # Gaps
    gaps = analysis['competitive_gaps']
    print(f"\n--- COMPETITIVE GAPS ({len(gaps)}) ---")
    for gap in gaps[:5]:
        print(f"  [{gap.opportunity_size.upper()}] {gap.group_name}: {gap.description}")

    # Initiatives
    initiatives = analysis['initiatives']
    print(f"\n--- STRATEGIC INITIATIVES ({len(initiatives)}) ---")
    for init in initiatives:
        print(f"\n  [{init.priority.upper()}] {init.id}: {init.title}")
        print(f"    Category: {init.category}")
        print(f"    Hypothesis: {init.hypothesis}")
        print(f"    Evidence:")
        for e in init.evidence[:2]:
            print(f"      - {e}")
        print(f"    Expected Impact: {init.expected_impact}")
        print(f"    Complexity: {init.implementation_complexity}")

    # Executive summary
    print("\n" + "=" * 70)
    print("EXECUTIVE SUMMARY")
    print("=" * 70)
    print(analysis['executive_summary'])

    # Visualizations
    viz = analysis['visualizations']
    available = [k for k, v in viz.items() if v]
    print(f"\n--- VISUALIZATIONS GENERATED ---")
    print(f"  {', '.join(available)}")
    print(f"  (Access via analysis['visualizations']['<name>'] - base64 PNG)")
