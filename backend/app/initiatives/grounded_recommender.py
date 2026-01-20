"""
Grounded Recommender - Produces fully-traceable, data-grounded recommendations.

This is the main orchestrator that:
1. Runs enhanced analytics
2. Scores initiatives with evidence
3. Produces final recommendations with full traceability

Output format meets hard requirements:
- Data-grounded: every claim includes computed evidence
- Ranked: impact_range, confidence_0to1, effort_SML, priority_score
- No hallucinated numbers: assumptions are labeled
- No generic advice: references specific data points
"""
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import pandas as pd

from app.analytics.enhanced_engine import EnhancedAnalyticsEngine
from app.analytics.benchmarks import get_benchmarks_for_vertical, get_benchmark_details
from app.initiatives.evidence_scorer import EvidenceBasedScorer, ScoredInitiative
from app.core.vertical_config import VerticalConfig
from app.llm.client import LLMClient


@dataclass
class GroundedRecommendation:
    """
    A single recommendation with full traceability.

    Meets all hard requirements:
    1. Data-grounded: evidence_chain shows dataset + columns + filters + numbers
    2. Ranked: has impact_range, confidence, effort, priority_score
    3. No hallucinated numbers: is_assumption flag, assumptions list
    4. No generic advice: data_specifics has actual categories/time windows
    """
    # Identity
    rank: int
    initiative_id: str
    title: str
    category: str

    # The recommendation (specific, not generic)
    recommendation_text: str          # One-liner
    detailed_rationale: str           # Full explanation with evidence citations

    # Ranking components (all required)
    impact_range: Dict[str, float]    # {low, mid, high}
    confidence: float                 # 0-1
    effort: str                       # "S", "M", "L"
    priority_score: float             # Composite score

    # Evidence chain (full traceability)
    evidence_chain: List[Dict[str, Any]]  # [{dataset, columns, filters, computation, result}]

    # Assumptions (explicit)
    assumptions: List[str]
    is_assumption_based: bool         # True if impact is assumption-based

    # Sensitivity analysis (if not assumption-based)
    sensitivity: Optional[Dict[str, float]]

    # Data specifics (no generic advice)
    data_specifics: Dict[str, Any]    # Actual categories, vendors, time windows

    # What would improve this
    data_gaps: List[str]

    # Scoring breakdown (transparency)
    scoring_breakdown: Dict[str, float]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class GroundedRecommender:
    """
    Main orchestrator for producing grounded recommendations.

    Usage:
        recommender = GroundedRecommender(vertical_config)
        results = recommender.generate_recommendations(
            normalized_data,
            run_context
        )
    """

    def __init__(
        self,
        vertical_config: VerticalConfig,
        llm_client: Optional[LLMClient] = None
    ):
        """
        Initialize recommender.

        Args:
            vertical_config: Vertical configuration with initiatives
            llm_client: Optional LLM client for explanation writing (NOT for selection)
        """
        self.config = vertical_config
        self.llm_client = llm_client

        # Get benchmarks for this vertical
        self.benchmarks = get_benchmarks_for_vertical(vertical_config.vertical_id)
        self.benchmark_details = get_benchmark_details(vertical_config.vertical_id)

    def generate_recommendations(
        self,
        normalized_data: Dict[str, pd.DataFrame],
        run_context: Optional[Dict[str, Any]] = None,
        max_recommendations: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate fully-grounded recommendations.

        Args:
            normalized_data: {pack_type: DataFrame} with canonical columns
            run_context: Optional context from intake questions
            max_recommendations: Max recommendations to return (None = all)

        Returns:
            {
                "mode_info": {...},
                "analytics_summary": {...},
                "recommendations": [GroundedRecommendation, ...],
                "benchmarks_used": {...},
                "data_quality_summary": {...}
            }
        """
        run_context = run_context or {}

        # =====================================================================
        # STEP 1: Run enhanced analytics
        # =====================================================================
        analytics_engine = EnhancedAnalyticsEngine(benchmarks=self.benchmarks)
        analytics_results = analytics_engine.analyze(normalized_data)

        mode_info = analytics_results['mode_info']

        # Determine max recommendations based on mode
        if max_recommendations is None:
            mode = mode_info.get('mode', 'DIRECTIONAL_MODE')
            if mode == 'PNL_MODE':
                max_recommendations = 7
            elif mode == 'OPS_MODE':
                max_recommendations = 5
            else:
                max_recommendations = 3

        # =====================================================================
        # STEP 2: Score initiatives with evidence
        # =====================================================================
        constraints = run_context.get('constraints', {})
        blacklist = run_context.get('derived', {}).get('initiative_blacklist', [])

        scorer = EvidenceBasedScorer(
            analytics_results=analytics_results,
            benchmarks=self.benchmarks,
            constraints=constraints
        )

        # Get initiative definitions from playbook
        initiative_defs = [
            {
                'id': init.id,
                'title': init.title,
                'category': init.category,
                'description': init.description,
                'type': getattr(init, 'type', init.category),
                'sizing_method': init.sizing_method,
                'sizing_params': init.sizing_params,
                'priority_weight': init.priority_weight
            }
            for init in self.config.initiatives
        ]

        scored_initiatives = scorer.score_all(initiative_defs, blacklist=blacklist)

        # Limit to max recommendations
        scored_initiatives = scored_initiatives[:max_recommendations]

        # =====================================================================
        # STEP 3: Build grounded recommendations
        # =====================================================================
        recommendations = []

        for scored in scored_initiatives:
            rec = self._build_recommendation(scored, analytics_results)
            recommendations.append(rec)

        # =====================================================================
        # STEP 4: Optionally enhance with LLM explanations
        # =====================================================================
        if self.llm_client and self.llm_client.available:
            recommendations = self._enhance_with_llm(recommendations, analytics_results)

        # =====================================================================
        # STEP 5: Build final output
        # =====================================================================
        return {
            "mode_info": mode_info,
            "analytics_summary": self._build_analytics_summary(analytics_results),
            "recommendations": [r.to_dict() for r in recommendations],
            "benchmarks_used": self.benchmark_details,
            "data_quality_summary": analytics_results.get('data_quality', {}),
            "patterns_detected": analytics_results.get('patterns', []),
            "anomalies_detected": analytics_results.get('anomalies', [])
        }

    def _build_recommendation(
        self,
        scored: ScoredInitiative,
        analytics_results: Dict[str, Any]
    ) -> GroundedRecommendation:
        """Build a grounded recommendation from a scored initiative."""

        # Build evidence chain from scoring evidence
        evidence_chain = []
        for se in scored.scoring_evidence:
            evidence_chain.append({
                "component": se.component,
                "computation": se.computation,
                "result": se.normalized_score,
                "supporting_metrics": se.supporting_metrics,
                "confidence": se.confidence
            })

        # Add impact evidence
        if scored.impact.base_metric:
            evidence_chain.append({
                "component": "impact_calculation",
                "computation": f"Based on {scored.impact.base_metric}={scored.impact.base_value}, method={scored.impact.method}",
                "result": scored.impact.mid,
                "supporting_metrics": [scored.impact.base_metric],
                "confidence": 0.7 if not scored.impact.is_assumption else 0.4
            })

        # Build recommendation text (specific, not generic)
        rec_text = self._build_recommendation_text(scored)

        # Build detailed rationale
        rationale = self._build_rationale(scored, analytics_results)

        return GroundedRecommendation(
            rank=scored.rank,
            initiative_id=scored.initiative_id,
            title=scored.title,
            category=scored.category,
            recommendation_text=rec_text,
            detailed_rationale=rationale,
            impact_range={
                "low": scored.impact.low,
                "mid": scored.impact.mid,
                "high": scored.impact.high
            },
            confidence=scored.confidence,
            effort=scored.effort.value,
            priority_score=scored.priority_score,
            evidence_chain=evidence_chain,
            assumptions=scored.assumptions,
            is_assumption_based=scored.impact.is_assumption,
            sensitivity=scored.impact.sensitivity,
            data_specifics=scored.data_specifics,
            data_gaps=scored.data_gaps,
            scoring_breakdown={
                "evidence_strength": scored.evidence_strength,
                "gap_magnitude": scored.gap_magnitude,
                "confidence": scored.confidence,
                "effort_score": scored.effort_score
            }
        )

    def _build_recommendation_text(self, scored: ScoredInitiative) -> str:
        """Build a specific, data-grounded recommendation one-liner."""
        specifics = scored.data_specifics

        # Get gap info from scoring evidence
        gap_evidence = next(
            (se for se in scored.scoring_evidence if se.component == "gap_magnitude"),
            None
        )

        parts = [scored.title]

        # Add specific data references
        if gap_evidence and gap_evidence.raw_value > 0:
            parts.append(f"({gap_evidence.raw_value:.1f}pp gap to benchmark)")

        if specifics.get('peak_labor_month'):
            parts.append(f"Focus on {specifics['peak_labor_month']}")
        elif specifics.get('trough_revenue_month'):
            parts.append(f"Address {specifics['trough_revenue_month']} trough")
        elif specifics.get('best_day'):
            parts.append(f"Leverage {specifics['best_day']} patterns")

        # Add time period
        if specifics.get('analysis_period'):
            parts.append(f"[Based on {specifics['analysis_period']}]")

        return " - ".join(parts)

    def _build_rationale(
        self,
        scored: ScoredInitiative,
        analytics_results: Dict[str, Any]
    ) -> str:
        """Build detailed rationale with evidence citations."""
        lines = []

        # Opening with priority score
        lines.append(f"Priority Score: {scored.priority_score:.2f}/1.00")
        lines.append("")

        # Evidence summary
        lines.append("EVIDENCE:")
        for se in scored.scoring_evidence:
            lines.append(f"  • {se.component}: {se.normalized_score:.2f} ({se.computation})")
        lines.append("")

        # Gap analysis
        gap_evidence = next(
            (se for se in scored.scoring_evidence if se.component == "gap_magnitude"),
            None
        )
        if gap_evidence and gap_evidence.raw_value > 0:
            lines.append("GAP ANALYSIS:")
            lines.append(f"  {gap_evidence.computation}")
            lines.append("")

        # Impact calculation
        lines.append("IMPACT CALCULATION:")
        if scored.impact.is_assumption:
            lines.append("  ⚠️ ASSUMPTION-BASED (limited data)")
        lines.append(f"  Method: {scored.impact.method}")
        if scored.impact.base_metric:
            lines.append(f"  Base: {scored.impact.base_metric} = ${scored.impact.base_value:,.0f}/month")
        lines.append(f"  Range: ${scored.impact.low:,.0f} - ${scored.impact.high:,.0f}")
        if scored.impact.sensitivity:
            lines.append("  Sensitivity:")
            for k, v in scored.impact.sensitivity.items():
                lines.append(f"    • {k}: ${v:,.0f}")
        lines.append("")

        # Data specifics
        if scored.data_specifics:
            lines.append("DATA SPECIFICS:")
            for k, v in scored.data_specifics.items():
                if not isinstance(v, (list, dict)):
                    lines.append(f"  • {k}: {v}")
                elif isinstance(v, list) and len(v) > 0 and len(v) <= 5:
                    lines.append(f"  • {k}: {v}")
            lines.append("")

        # Assumptions
        if scored.assumptions:
            lines.append("ASSUMPTIONS:")
            for assumption in scored.assumptions:
                lines.append(f"  • {assumption}")
            lines.append("")

        # Data gaps
        if scored.data_gaps:
            lines.append("WOULD IMPROVE WITH:")
            for gap in scored.data_gaps[:3]:
                lines.append(f"  • {gap}")

        return "\n".join(lines)

    def _build_analytics_summary(self, analytics_results: Dict[str, Any]) -> Dict[str, Any]:
        """Build a summary of key analytics for the output."""
        metrics = analytics_results.get('metrics', [])

        # Extract key metrics
        key_metrics = {}
        key_ids = [
            'revenue_avg_monthly', 'labor_avg_monthly', 'cogs_avg_monthly',
            'labor_pct', 'cogs_pct', 'gross_margin_pct',
            'revenue_trend', 'labor_volatility'
        ]

        for m in metrics:
            if m['metric_id'] in key_ids:
                key_metrics[m['metric_id']] = {
                    'value': m['value'],
                    'unit': m['unit'],
                    'confidence': m['confidence'],
                    'benchmark': m.get('benchmark'),
                    'gap_to_benchmark': m.get('gap_to_benchmark'),
                    'gap_direction': m.get('gap_direction')
                }

        return {
            "key_metrics": key_metrics,
            "total_metrics_computed": len(metrics),
            "patterns_found": len(analytics_results.get('patterns', [])),
            "anomalies_found": len(analytics_results.get('anomalies', []))
        }

    def _enhance_with_llm(
        self,
        recommendations: List[GroundedRecommendation],
        analytics_results: Dict[str, Any]
    ) -> List[GroundedRecommendation]:
        """
        Optionally enhance recommendations with LLM-written explanations.

        NOTE: LLM is used ONLY for writing prose, NOT for selection or scoring.
        All numbers and rankings are already computed deterministically.
        """
        if not self.llm_client or not self.llm_client.available:
            return recommendations

        # Build context for LLM
        metrics_summary = []
        for m in analytics_results.get('metrics', [])[:20]:
            metrics_summary.append(f"- {m['metric_id']}: {m['value']} {m['unit']}")

        metrics_text = "\n".join(metrics_summary)

        for rec in recommendations:
            prompt = f"""You are writing a brief, specific explanation for a business recommendation.

RECOMMENDATION: {rec.title}
RANK: #{rec.rank}
PRIORITY SCORE: {rec.priority_score:.2f}

EVIDENCE:
{rec.detailed_rationale}

KEY METRICS:
{metrics_text}

Write a 2-3 sentence explanation that:
1. States the specific opportunity (cite actual numbers from evidence)
2. Explains why this is prioritized (reference the gap or pattern)
3. Is actionable and specific (no generic advice)

Keep it under 100 words. Do not make up any numbers not in the evidence."""

            try:
                response = self.llm_client.generate(prompt, temperature=0.3)
                # Append LLM explanation to rationale
                rec.detailed_rationale += f"\n\nSUMMARY:\n{response}"
            except Exception:
                # LLM failure is OK - we already have the full rationale
                pass

        return recommendations


# Convenience function for direct usage
def generate_grounded_recommendations(
    normalized_data: Dict[str, pd.DataFrame],
    vertical_config: VerticalConfig,
    run_context: Optional[Dict[str, Any]] = None,
    llm_client: Optional[LLMClient] = None,
    max_recommendations: Optional[int] = None
) -> Dict[str, Any]:
    """
    Convenience function to generate grounded recommendations.

    Args:
        normalized_data: {pack_type: DataFrame} with canonical columns
        vertical_config: Vertical configuration
        run_context: Optional context from intake questions
        llm_client: Optional LLM for explanation writing
        max_recommendations: Max recommendations to return

    Returns:
        Full recommendation output with analytics and evidence chains
    """
    recommender = GroundedRecommender(vertical_config, llm_client)
    return recommender.generate_recommendations(
        normalized_data,
        run_context,
        max_recommendations
    )
