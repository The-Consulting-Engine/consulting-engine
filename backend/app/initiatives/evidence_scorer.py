"""
Evidence-Based Initiative Scorer

Replaces LLM-based selection with deterministic, traceable scoring.

Principles:
1. Every score is computed, not guessed
2. Every score component has an evidence chain
3. LLM is only used for writing explanations AFTER scoring
4. No recommendation without supporting evidence
"""
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum


class EffortLevel(Enum):
    SMALL = "S"
    MEDIUM = "M"
    LARGE = "L"


@dataclass
class ScoringEvidence:
    """Evidence chain for a scoring component."""
    component: str                    # "evidence_strength", "gap_magnitude", etc.
    raw_value: float                  # The raw computed value
    normalized_score: float           # 0-1 normalized score
    computation: str                  # How we computed this
    supporting_metrics: List[str]     # Which metrics support this score
    confidence: float                 # Confidence in this score component


@dataclass
class ImpactEstimate:
    """Fully-traced impact estimate."""
    low: float
    mid: float
    high: float
    method: str                       # How we computed this
    base_metric: Optional[str]        # Which metric we used as base
    base_value: Optional[float]       # The base value
    assumptions: List[str]            # Assumptions made
    is_assumption: bool               # True if impact is assumption-based (no data)
    sensitivity: Optional[Dict[str, float]] = None  # How impact changes with assumptions


@dataclass
class ScoredInitiative:
    """A fully-scored initiative with evidence chains."""
    initiative_id: str
    title: str
    category: str

    # Scoring breakdown (all components add up to priority_score)
    evidence_strength: float          # 0-1: How much data supports this?
    gap_magnitude: float              # 0-1: How big is the opportunity?
    confidence: float                 # 0-1: How reliable is our analysis?
    effort: EffortLevel               # S/M/L: Implementation difficulty
    effort_score: float               # 0-1: Inverted effort (higher = easier)

    # Final score
    priority_score: float             # Weighted combination

    # Impact with full traceability
    impact: ImpactEstimate

    # Evidence chains for transparency
    scoring_evidence: List[ScoringEvidence]

    # Specifics from data (no generic advice)
    data_specifics: Dict[str, Any]    # Actual categories, time periods, line items

    # What we're assuming (explicit)
    assumptions: List[str]

    # What would make this more confident
    data_gaps: List[str]

    # Rank (assigned after sorting)
    rank: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['effort'] = self.effort.value
        return d


class EvidenceBasedScorer:
    """
    Score initiatives based purely on computed evidence.

    No LLM selection - deterministic scoring with full traceability.
    """

    # Scoring weights (configurable)
    WEIGHTS = {
        "evidence_strength": 0.25,
        "gap_magnitude": 0.35,
        "confidence": 0.20,
        "effort_score": 0.20
    }

    def __init__(
        self,
        analytics_results: Dict[str, Any],
        benchmarks: Dict[str, float],
        constraints: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize scorer with analytics results.

        Args:
            analytics_results: Output from EnhancedAnalyticsEngine.analyze()
            benchmarks: Industry benchmarks {metric_id: value}
            constraints: Operator constraints from intake questions
        """
        self.analytics = analytics_results
        self.benchmarks = benchmarks
        self.constraints = constraints or {}

        # Index metrics by ID for quick lookup
        self.metrics_by_id = {
            m['metric_id']: m
            for m in analytics_results.get('metrics', [])
        }

        # Index patterns for quick lookup
        self.patterns = analytics_results.get('patterns', [])

        # Index anomalies
        self.anomalies = analytics_results.get('anomalies', [])

        # Index breakdowns
        self.breakdowns = {
            b['category_field']: b
            for b in analytics_results.get('breakdowns', [])
        }

    def score_all(
        self,
        initiative_definitions: List[Dict[str, Any]],
        blacklist: Optional[List[str]] = None
    ) -> List[ScoredInitiative]:
        """
        Score all initiatives and return sorted by priority.

        Args:
            initiative_definitions: List of initiative configs from playbook
            blacklist: Initiative IDs to skip (from intake questions)

        Returns:
            List of ScoredInitiative, sorted by priority_score descending
        """
        blacklist = blacklist or []
        scored = []

        for init_def in initiative_definitions:
            init_id = init_def.get('id')

            # Skip blacklisted
            if init_id in blacklist:
                continue

            # Score this initiative
            scored_init = self._score_initiative(init_def)

            if scored_init is not None:
                scored.append(scored_init)

        # Sort by priority score
        scored.sort(key=lambda x: x.priority_score, reverse=True)

        # Assign ranks
        for i, init in enumerate(scored):
            init.rank = i + 1

        return scored

    def _score_initiative(
        self,
        init_def: Dict[str, Any]
    ) -> Optional[ScoredInitiative]:
        """Score a single initiative based on available evidence."""

        init_id = init_def.get('id', '')
        init_type = init_def.get('type', init_def.get('category', ''))
        title = init_def.get('title', '')
        category = init_def.get('category', '')

        scoring_evidence = []
        data_specifics = {}
        assumptions = []
        data_gaps = []

        # =====================================================================
        # 1. EVIDENCE STRENGTH: How much data supports this initiative?
        # =====================================================================
        evidence_strength, evidence_detail = self._compute_evidence_strength(init_def)
        scoring_evidence.append(evidence_detail)

        # If no evidence at all, skip this initiative
        if evidence_strength == 0:
            return None

        # =====================================================================
        # 2. GAP MAGNITUDE: How big is the opportunity?
        # =====================================================================
        gap_magnitude, gap_detail, gap_specifics = self._compute_gap_magnitude(init_def)
        scoring_evidence.append(gap_detail)
        data_specifics.update(gap_specifics)

        # =====================================================================
        # 3. CONFIDENCE: How reliable is our analysis?
        # =====================================================================
        confidence, confidence_detail = self._compute_confidence(init_def, evidence_strength)
        scoring_evidence.append(confidence_detail)

        # =====================================================================
        # 4. EFFORT: How hard is implementation?
        # =====================================================================
        effort, effort_score, effort_detail = self._compute_effort(init_def)
        scoring_evidence.append(effort_detail)

        # =====================================================================
        # 5. COMPUTE PRIORITY SCORE
        # =====================================================================
        priority_score = (
            self.WEIGHTS["evidence_strength"] * evidence_strength +
            self.WEIGHTS["gap_magnitude"] * gap_magnitude +
            self.WEIGHTS["confidence"] * confidence +
            self.WEIGHTS["effort_score"] * effort_score
        )

        # =====================================================================
        # 6. COMPUTE IMPACT (gap-based, not arbitrary %)
        # =====================================================================
        impact, impact_assumptions = self._compute_impact(init_def, gap_specifics)
        assumptions.extend(impact_assumptions)

        # =====================================================================
        # 7. IDENTIFY DATA GAPS
        # =====================================================================
        data_gaps = self._identify_data_gaps(init_def, evidence_strength)

        # =====================================================================
        # 8. ADD DATA-SPECIFIC DETAILS (no generic advice)
        # =====================================================================
        data_specifics.update(self._get_data_specifics(init_def))

        return ScoredInitiative(
            initiative_id=init_id,
            title=title,
            category=category,
            evidence_strength=round(evidence_strength, 3),
            gap_magnitude=round(gap_magnitude, 3),
            confidence=round(confidence, 3),
            effort=effort,
            effort_score=round(effort_score, 3),
            priority_score=round(priority_score, 3),
            impact=impact,
            scoring_evidence=scoring_evidence,
            data_specifics=data_specifics,
            assumptions=assumptions,
            data_gaps=data_gaps
        )

    # =========================================================================
    # SCORING COMPONENTS
    # =========================================================================

    def _compute_evidence_strength(
        self,
        init_def: Dict[str, Any]
    ) -> Tuple[float, ScoringEvidence]:
        """
        Compute evidence strength: how much data supports this initiative?

        Returns (score, evidence_detail)
        """
        init_type = init_def.get('type', init_def.get('category', ''))
        supporting_metrics = []
        score = 0.0

        # Map initiative types to relevant metrics
        metric_requirements = {
            "LABOR_OPTIMIZATION": ["labor_pct", "labor_avg_monthly", "labor_volatility", "labor_revenue_correlation"],
            "PRICING": ["revenue_avg_monthly", "cogs_pct", "gross_margin_pct"],
            "COST_REDUCTION": ["cogs_avg_monthly", "rent_avg_monthly", "utilities_avg_monthly"],
            "THROUGHPUT": ["revenue_avg_monthly", "revenue_peak_month", "revenue_trough_month"],
            "DISCOUNT_CONTROL": ["revenue_avg_monthly"],  # Would need discount data
            "WASTE_REDUCTION": ["cogs_pct", "cogs_avg_monthly"],
            "MARKETING": ["revenue_avg_monthly", "revenue_trend"],
            "Revenue Optimization": ["revenue_avg_monthly", "cogs_pct", "gross_margin_pct"],
            "Labor Efficiency": ["labor_pct", "labor_avg_monthly", "labor_volatility"],
            "Cost Control": ["cogs_pct", "rent_avg_monthly"],
            "Operations": ["revenue_avg_monthly", "revenue_trend"],
        }

        required_metrics = metric_requirements.get(init_type, ["revenue_avg_monthly"])

        # Count how many required metrics we have
        found_count = 0
        for metric_id in required_metrics:
            if metric_id in self.metrics_by_id:
                found_count += 1
                supporting_metrics.append(metric_id)

        # Evidence score = proportion of required metrics found
        if len(required_metrics) > 0:
            base_score = found_count / len(required_metrics)
        else:
            base_score = 0.5  # Default if no specific requirements

        # Bonus for patterns that support this initiative
        pattern_bonus = 0
        for pattern in self.patterns:
            if self._pattern_supports_initiative(pattern, init_def):
                pattern_bonus += 0.1
                supporting_metrics.append(f"pattern:{pattern['pattern_id']}")

        score = min(1.0, base_score + pattern_bonus)

        evidence = ScoringEvidence(
            component="evidence_strength",
            raw_value=found_count,
            normalized_score=round(score, 3),
            computation=f"Found {found_count}/{len(required_metrics)} required metrics + {int(pattern_bonus*10)} supporting patterns",
            supporting_metrics=supporting_metrics,
            confidence=0.9  # High confidence in this calculation
        )

        return score, evidence

    def _compute_gap_magnitude(
        self,
        init_def: Dict[str, Any]
    ) -> Tuple[float, ScoringEvidence, Dict[str, Any]]:
        """
        Compute gap magnitude: how big is the opportunity?

        Uses benchmark comparison when available.
        """
        init_type = init_def.get('type', init_def.get('category', ''))
        specifics = {}
        score = 0.0
        supporting_metrics = []

        # Type-specific gap calculation
        if init_type in ["LABOR_OPTIMIZATION", "Labor Efficiency"]:
            score, specifics = self._compute_labor_gap()
            supporting_metrics = ["labor_pct", "labor_avg_monthly"]

        elif init_type in ["PRICING", "Revenue Optimization"]:
            score, specifics = self._compute_pricing_gap()
            supporting_metrics = ["cogs_pct", "gross_margin_pct"]

        elif init_type in ["COST_REDUCTION", "Cost Control"]:
            score, specifics = self._compute_cost_gap()
            supporting_metrics = ["cogs_pct"]

        elif init_type == "THROUGHPUT":
            score, specifics = self._compute_throughput_gap()
            supporting_metrics = ["revenue_volatility", "revenue_trend"]

        elif init_type == "WASTE_REDUCTION":
            score, specifics = self._compute_waste_gap()
            supporting_metrics = ["cogs_pct"]

        else:
            # Default: moderate gap assumption
            score = 0.3
            specifics = {"gap_type": "assumed", "gap_value": None}

        evidence = ScoringEvidence(
            component="gap_magnitude",
            raw_value=specifics.get('gap_value', 0) or 0,
            normalized_score=round(score, 3),
            computation=specifics.get('computation', 'default_assumption'),
            supporting_metrics=supporting_metrics,
            confidence=specifics.get('confidence', 0.5)
        )

        return score, evidence, specifics

    def _compute_labor_gap(self) -> Tuple[float, Dict[str, Any]]:
        """Compute labor efficiency gap."""
        labor_pct_metric = self.metrics_by_id.get('labor_pct')

        if labor_pct_metric is None:
            return 0.2, {"gap_type": "no_data", "gap_value": None, "confidence": 0.3}

        current_labor_pct = labor_pct_metric['value']
        benchmark = self.benchmarks.get('labor_pct', 28.0)

        gap = current_labor_pct - benchmark  # Positive = above benchmark (bad)

        # Normalize: 0 gap = 0 score, 10+ point gap = 1.0 score
        normalized = min(1.0, max(0, gap / 10))

        return normalized, {
            "gap_type": "benchmark_comparison",
            "current_value": current_labor_pct,
            "benchmark_value": benchmark,
            "gap_value": round(gap, 2),
            "gap_direction": "above" if gap > 0 else "below",
            "computation": f"current({current_labor_pct:.1f}%) - benchmark({benchmark:.1f}%) = {gap:.1f}pp gap",
            "confidence": 0.85
        }

    def _compute_pricing_gap(self) -> Tuple[float, Dict[str, Any]]:
        """Compute pricing/margin gap."""
        gross_margin = self.metrics_by_id.get('gross_margin_pct')
        cogs_pct = self.metrics_by_id.get('cogs_pct')

        if cogs_pct is None and gross_margin is None:
            return 0.2, {"gap_type": "no_data", "gap_value": None, "confidence": 0.3}

        if cogs_pct:
            current = cogs_pct['value']
            benchmark = self.benchmarks.get('cogs_pct', 30.0)
            gap = current - benchmark  # Positive = above benchmark (bad)
            normalized = min(1.0, max(0, gap / 10))

            return normalized, {
                "gap_type": "cogs_benchmark",
                "current_value": current,
                "benchmark_value": benchmark,
                "gap_value": round(gap, 2),
                "gap_direction": "above" if gap > 0 else "below",
                "computation": f"COGS current({current:.1f}%) - benchmark({benchmark:.1f}%) = {gap:.1f}pp gap",
                "confidence": 0.80
            }

        # Fallback to gross margin
        current = gross_margin['value']
        benchmark = self.benchmarks.get('gross_margin_pct', 70.0)
        gap = benchmark - current  # Positive = below benchmark (bad)
        normalized = min(1.0, max(0, gap / 15))

        return normalized, {
            "gap_type": "margin_benchmark",
            "current_value": current,
            "benchmark_value": benchmark,
            "gap_value": round(gap, 2),
            "gap_direction": "below" if gap > 0 else "above",
            "computation": f"Margin benchmark({benchmark:.1f}%) - current({current:.1f}%) = {gap:.1f}pp gap",
            "confidence": 0.75
        }

    def _compute_cost_gap(self) -> Tuple[float, Dict[str, Any]]:
        """Compute cost reduction gap."""
        cogs_pct = self.metrics_by_id.get('cogs_pct')

        if cogs_pct:
            current = cogs_pct['value']
            benchmark = self.benchmarks.get('cogs_pct', 30.0)
            gap = current - benchmark
            normalized = min(1.0, max(0, gap / 10))

            return normalized, {
                "gap_type": "cogs_benchmark",
                "current_value": current,
                "benchmark_value": benchmark,
                "gap_value": round(gap, 2),
                "computation": f"COGS {current:.1f}% vs benchmark {benchmark:.1f}%",
                "confidence": 0.75
            }

        return 0.3, {"gap_type": "assumed", "gap_value": None, "confidence": 0.4}

    def _compute_throughput_gap(self) -> Tuple[float, Dict[str, Any]]:
        """Compute throughput/capacity gap."""
        # Look for volatility patterns - high volatility suggests capacity underutilization
        revenue_vol = self.metrics_by_id.get('revenue_total_volatility')
        revenue_range = self.metrics_by_id.get('revenue_range')

        if revenue_vol:
            cv = revenue_vol['value']
            # High volatility = potential to capture more in low periods
            normalized = min(1.0, cv * 2)  # CV of 0.5 = score of 1.0

            return normalized, {
                "gap_type": "volatility_based",
                "current_value": cv,
                "computation": f"Revenue CV = {cv:.2f}, suggests {normalized*100:.0f}% capacity opportunity",
                "confidence": 0.6
            }

        return 0.3, {"gap_type": "assumed", "gap_value": None, "confidence": 0.4}

    def _compute_waste_gap(self) -> Tuple[float, Dict[str, Any]]:
        """Compute waste reduction gap."""
        cogs_pct = self.metrics_by_id.get('cogs_pct')

        if cogs_pct:
            current = cogs_pct['value']
            benchmark = self.benchmarks.get('cogs_pct', 30.0)
            gap = current - benchmark

            if gap > 0:
                # Assume 20-30% of excess COGS could be waste
                waste_potential = gap * 0.25
                normalized = min(1.0, waste_potential / 5)

                return normalized, {
                    "gap_type": "cogs_derived",
                    "current_value": current,
                    "benchmark_value": benchmark,
                    "gap_value": round(gap, 2),
                    "waste_potential_pct": round(waste_potential, 2),
                    "computation": f"COGS gap ({gap:.1f}pp) × 25% waste factor = {waste_potential:.1f}pp potential",
                    "confidence": 0.55
                }

        return 0.2, {"gap_type": "assumed", "gap_value": None, "confidence": 0.35}

    def _compute_confidence(
        self,
        init_def: Dict[str, Any],
        evidence_strength: float
    ) -> Tuple[float, ScoringEvidence]:
        """Compute overall confidence in this recommendation."""
        mode_confidence = self.analytics.get('mode_info', {}).get('confidence', 0.5)
        data_quality = self.analytics.get('data_quality', {}).get('overall_completeness', 0.5)
        months = self.analytics.get('time_coverage', {}).get('months', 0)

        # Confidence factors
        factors = []

        # Mode confidence contributes 40%
        mode_contrib = mode_confidence * 0.4
        factors.append(f"mode_confidence({mode_confidence:.2f})×0.4")

        # Data completeness contributes 30%
        completeness_contrib = data_quality * 0.3
        factors.append(f"data_completeness({data_quality:.2f})×0.3")

        # Evidence strength contributes 30%
        evidence_contrib = evidence_strength * 0.3
        factors.append(f"evidence_strength({evidence_strength:.2f})×0.3")

        # Bonus for more months
        month_bonus = min(0.1, months * 0.01)

        score = mode_contrib + completeness_contrib + evidence_contrib + month_bonus
        score = min(1.0, score)

        evidence = ScoringEvidence(
            component="confidence",
            raw_value=score,
            normalized_score=round(score, 3),
            computation=" + ".join(factors) + f" + month_bonus({month_bonus:.2f})",
            supporting_metrics=["mode_info", "data_quality", "time_coverage"],
            confidence=0.95
        )

        return score, evidence

    def _compute_effort(
        self,
        init_def: Dict[str, Any]
    ) -> Tuple[EffortLevel, float, ScoringEvidence]:
        """Compute implementation effort."""
        init_type = init_def.get('type', init_def.get('category', ''))

        # Effort mapping (can be made configurable)
        effort_map = {
            "LABOR_OPTIMIZATION": (EffortLevel.MEDIUM, 0.5),
            "Labor Efficiency": (EffortLevel.MEDIUM, 0.5),
            "PRICING": (EffortLevel.SMALL, 0.8),
            "Revenue Optimization": (EffortLevel.SMALL, 0.7),
            "COST_REDUCTION": (EffortLevel.MEDIUM, 0.5),
            "Cost Control": (EffortLevel.MEDIUM, 0.5),
            "THROUGHPUT": (EffortLevel.LARGE, 0.3),
            "Operations": (EffortLevel.MEDIUM, 0.5),
            "DISCOUNT_CONTROL": (EffortLevel.SMALL, 0.8),
            "WASTE_REDUCTION": (EffortLevel.MEDIUM, 0.5),
            "MARKETING": (EffortLevel.MEDIUM, 0.5),
            "Marketing": (EffortLevel.MEDIUM, 0.5),
        }

        effort, effort_score = effort_map.get(init_type, (EffortLevel.MEDIUM, 0.5))

        # Adjust based on constraints
        if self.constraints.get('pricing_control') == 'no_control':
            if init_type in ["PRICING", "Revenue Optimization"]:
                effort = EffortLevel.LARGE
                effort_score = 0.2

        evidence = ScoringEvidence(
            component="effort_score",
            raw_value=effort_score,
            normalized_score=round(effort_score, 3),
            computation=f"effort_level={effort.value}, inverted_score={effort_score}",
            supporting_metrics=[],
            confidence=0.7
        )

        return effort, effort_score, evidence

    # =========================================================================
    # IMPACT COMPUTATION
    # =========================================================================

    def _compute_impact(
        self,
        init_def: Dict[str, Any],
        gap_specifics: Dict[str, Any]
    ) -> Tuple[ImpactEstimate, List[str]]:
        """
        Compute impact estimate based on gaps, not arbitrary percentages.
        """
        init_type = init_def.get('type', init_def.get('category', ''))
        assumptions = []

        # Get base values
        revenue_avg = self.metrics_by_id.get('revenue_avg_monthly', {}).get('value')
        labor_avg = self.metrics_by_id.get('labor_avg_monthly', {}).get('value')
        cogs_avg = self.metrics_by_id.get('cogs_avg_monthly', {}).get('value')

        gap_value = gap_specifics.get('gap_value')
        gap_type = gap_specifics.get('gap_type')

        # Capture rates - conservative, mid, optimistic
        capture_rates = {"low": 0.25, "mid": 0.50, "high": 0.75}

        # Type-specific impact calculation
        if init_type in ["LABOR_OPTIMIZATION", "Labor Efficiency"] and labor_avg and gap_value and gap_value > 0:
            # Gap is in percentage points
            # Impact = annual_labor × (gap_pct / 100) × capture_rate
            annual_labor = labor_avg * 12
            gap_fraction = gap_value / 100

            low = annual_labor * gap_fraction * capture_rates["low"]
            mid = annual_labor * gap_fraction * capture_rates["mid"]
            high = annual_labor * gap_fraction * capture_rates["high"]

            assumptions.append(f"Labor gap of {gap_value:.1f}pp can be partially captured")
            assumptions.append(f"Capture rates: {capture_rates['low']*100:.0f}%-{capture_rates['high']*100:.0f}% of gap")

            return ImpactEstimate(
                low=round(low, 2),
                mid=round(mid, 2),
                high=round(high, 2),
                method="gap_based",
                base_metric="labor_avg_monthly",
                base_value=labor_avg,
                assumptions=assumptions,
                is_assumption=False,
                sensitivity={
                    "if_gap_1pp_smaller": round(mid - (annual_labor * 0.01 * capture_rates["mid"]), 2),
                    "if_capture_rate_halved": round(mid * 0.5, 2)
                }
            ), assumptions

        elif init_type in ["PRICING", "Revenue Optimization"] and revenue_avg and gap_value and gap_value > 0:
            annual_revenue = revenue_avg * 12
            gap_fraction = gap_value / 100

            low = annual_revenue * gap_fraction * capture_rates["low"]
            mid = annual_revenue * gap_fraction * capture_rates["mid"]
            high = annual_revenue * gap_fraction * capture_rates["high"]

            assumptions.append(f"Margin gap of {gap_value:.1f}pp can be partially captured through pricing")
            assumptions.append(f"Assumes price elasticity allows {capture_rates['mid']*100:.0f}% gap capture")

            return ImpactEstimate(
                low=round(low, 2),
                mid=round(mid, 2),
                high=round(high, 2),
                method="gap_based",
                base_metric="revenue_avg_monthly",
                base_value=revenue_avg,
                assumptions=assumptions,
                is_assumption=False,
                sensitivity={
                    "if_gap_1pp_smaller": round(mid - (annual_revenue * 0.01 * capture_rates["mid"]), 2),
                    "if_price_elasticity_high": round(mid * 0.5, 2)
                }
            ), assumptions

        elif init_type in ["COST_REDUCTION", "Cost Control", "WASTE_REDUCTION"] and cogs_avg and gap_value and gap_value > 0:
            annual_cogs = cogs_avg * 12
            gap_fraction = gap_value / 100

            low = annual_cogs * gap_fraction * capture_rates["low"]
            mid = annual_cogs * gap_fraction * capture_rates["mid"]
            high = annual_cogs * gap_fraction * capture_rates["high"]

            assumptions.append(f"COGS gap of {gap_value:.1f}pp partially addressable")

            return ImpactEstimate(
                low=round(low, 2),
                mid=round(mid, 2),
                high=round(high, 2),
                method="gap_based",
                base_metric="cogs_avg_monthly",
                base_value=cogs_avg,
                assumptions=assumptions,
                is_assumption=False,
                sensitivity=None
            ), assumptions

        # Fallback: assumption-based with conservative estimates
        if revenue_avg:
            annual_revenue = revenue_avg * 12
            # Very conservative: 1-3% of revenue
            low = annual_revenue * 0.01
            mid = annual_revenue * 0.02
            high = annual_revenue * 0.03

            assumptions.append("ASSUMPTION: No specific gap data available")
            assumptions.append("Using conservative 1-3% of annual revenue as estimate")
            assumptions.append("Actual impact requires more detailed data")

            return ImpactEstimate(
                low=round(low, 2),
                mid=round(mid, 2),
                high=round(high, 2),
                method="assumption_based",
                base_metric="revenue_avg_monthly",
                base_value=revenue_avg,
                assumptions=assumptions,
                is_assumption=True,
                sensitivity=None
            ), assumptions

        # Last resort: fixed conservative range
        assumptions.append("ASSUMPTION: Insufficient data for impact calculation")
        assumptions.append("Using industry-typical ranges")

        return ImpactEstimate(
            low=5000,
            mid=15000,
            high=30000,
            method="assumption_fixed",
            base_metric=None,
            base_value=None,
            assumptions=assumptions,
            is_assumption=True,
            sensitivity=None
        ), assumptions

    # =========================================================================
    # DATA SPECIFICS
    # =========================================================================

    def _get_data_specifics(self, init_def: Dict[str, Any]) -> Dict[str, Any]:
        """Extract data-specific details (no generic advice)."""
        specifics = {}
        init_type = init_def.get('type', init_def.get('category', ''))

        # Time specifics
        time_coverage = self.analytics.get('time_coverage', {})
        if time_coverage.get('start') and time_coverage.get('end'):
            specifics['analysis_period'] = f"{time_coverage['start']} to {time_coverage['end']}"
            specifics['months_analyzed'] = time_coverage.get('months', 0)

        # Peak/trough months (for labor and revenue initiatives)
        if init_type in ["LABOR_OPTIMIZATION", "Labor Efficiency"]:
            labor_peak = self.metrics_by_id.get('labor_peak_month')
            if labor_peak:
                specifics['peak_labor_month'] = labor_peak['evidence'].get('filters', {}).get('month')
                specifics['peak_labor_value'] = labor_peak['value']

            # Add correlation insight
            corr = self.metrics_by_id.get('labor_revenue_correlation')
            if corr:
                specifics['labor_revenue_correlation'] = corr['value']
                if corr['value'] < 0.7:
                    specifics['correlation_insight'] = "Low correlation suggests labor doesn't track revenue well"

        if init_type in ["PRICING", "Revenue Optimization", "THROUGHPUT"]:
            rev_peak = self.metrics_by_id.get('revenue_peak_month')
            rev_trough = self.metrics_by_id.get('revenue_trough_month')
            if rev_peak:
                specifics['peak_revenue_month'] = rev_peak['evidence'].get('filters', {}).get('month')
                specifics['peak_revenue_value'] = rev_peak['value']
            if rev_trough:
                specifics['trough_revenue_month'] = rev_trough['evidence'].get('filters', {}).get('month')
                specifics['trough_revenue_value'] = rev_trough['value']

        # Category breakdowns
        if 'category' in self.breakdowns:
            cat_breakdown = self.breakdowns['category']
            specifics['revenue_categories'] = cat_breakdown['breakdown'][:5]  # Top 5
            specifics['top_category'] = cat_breakdown['top_contributor']
            specifics['category_concentration'] = cat_breakdown['concentration']

        # Day of week patterns
        if 'day_of_week' in self.breakdowns:
            dow_breakdown = self.breakdowns['day_of_week']
            specifics['day_of_week_breakdown'] = dow_breakdown['breakdown']
            specifics['best_day'] = dow_breakdown['top_contributor']

        # Seasonality
        for pattern in self.patterns:
            if pattern['pattern_type'] == 'seasonality':
                specifics['seasonality'] = pattern['specifics']

        return specifics

    def _identify_data_gaps(
        self,
        init_def: Dict[str, Any],
        evidence_strength: float
    ) -> List[str]:
        """Identify what data would improve this recommendation."""
        gaps = []
        init_type = init_def.get('type', init_def.get('category', ''))

        if evidence_strength < 0.5:
            gaps.append("Limited supporting data - more months of history would improve confidence")

        # Type-specific gaps
        if init_type in ["LABOR_OPTIMIZATION", "Labor Efficiency"]:
            if 'labor_pct' not in self.metrics_by_id:
                gaps.append("Labor as % of revenue not available - need both labor and revenue data")
            if 'labor_revenue_correlation' not in self.metrics_by_id:
                gaps.append("Labor-revenue correlation not computed - need more data points")
            gaps.append("Hourly labor data would enable shift-level optimization")
            gaps.append("Role/position breakdown would identify specific overstaffing")

        elif init_type in ["PRICING", "Revenue Optimization"]:
            if 'gross_margin_pct' not in self.metrics_by_id:
                gaps.append("Gross margin not available - need COGS data")
            gaps.append("Item-level pricing data would enable SKU-specific recommendations")
            gaps.append("Competitor pricing would validate pricing power")

        elif init_type in ["COST_REDUCTION", "Cost Control", "WASTE_REDUCTION"]:
            gaps.append("Vendor-level cost breakdown would identify specific negotiation targets")
            gaps.append("Waste tracking data would quantify reduction opportunity")

        return gaps

    def _pattern_supports_initiative(
        self,
        pattern: Dict[str, Any],
        init_def: Dict[str, Any]
    ) -> bool:
        """Check if a detected pattern supports this initiative."""
        init_type = init_def.get('type', init_def.get('category', ''))
        pattern_type = pattern.get('pattern_type', '')
        pattern_id = pattern.get('pattern_id', '')

        # Mapping of patterns to supported initiatives
        if pattern_type == 'volatility' and 'labor' in pattern_id:
            return init_type in ["LABOR_OPTIMIZATION", "Labor Efficiency"]

        if pattern_type == 'correlation' and 'labor_revenue' in pattern_id:
            return init_type in ["LABOR_OPTIMIZATION", "Labor Efficiency"]

        if pattern_type == 'trend' and 'revenue' in pattern_id:
            return init_type in ["PRICING", "Revenue Optimization", "THROUGHPUT"]

        if pattern_type == 'seasonality':
            return init_type in ["LABOR_OPTIMIZATION", "THROUGHPUT", "PRICING"]

        if pattern_type == 'cycle' and 'day_of_week' in pattern_id:
            return init_type in ["LABOR_OPTIMIZATION", "THROUGHPUT"]

        return False
