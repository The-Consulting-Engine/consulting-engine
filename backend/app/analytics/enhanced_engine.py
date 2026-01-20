"""
Enhanced Analytics Engine - Deep, evidence-grounded analysis.

Principles:
1. Compute EVERYTHING possible from the data
2. Every metric includes full evidence chain (dataset, columns, filters, computation)
3. Detect patterns, anomalies, correlations - not just averages
4. No hallucination - if we can't compute it, we don't claim it
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from scipy import stats
import warnings

warnings.filterwarnings('ignore')


@dataclass
class EvidenceChain:
    """Full traceability for any computed value."""
    dataset: str                          # e.g., "PNL", "REVENUE", "LABOR"
    columns: List[str]                    # Columns used
    filters: Optional[Dict[str, Any]]     # Any filters applied
    computation: str                      # Human-readable computation description
    sample_size: int                      # Number of data points
    time_range: Optional[Tuple[str, str]] # Start and end dates if applicable
    raw_values: Optional[List[float]] = None  # Actual values (truncated for large sets)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ComputedMetric:
    """A single computed metric with full evidence."""
    metric_id: str                        # Unique identifier
    label: str                            # Human-readable label
    value: float                          # The computed value
    unit: str                             # currency, percentage, ratio, count, etc.
    evidence: EvidenceChain               # How we computed this
    confidence: float                     # 0-1, based on sample size and data quality
    category: str                         # revenue, labor, cost, trend, volatility, etc.

    # For comparisons
    benchmark: Optional[float] = None     # Industry benchmark if available
    benchmark_source: Optional[str] = None
    gap_to_benchmark: Optional[float] = None
    gap_direction: Optional[str] = None   # "above", "below", "at"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['evidence'] = self.evidence.to_dict()
        return d


@dataclass
class DataAnomaly:
    """Detected anomaly in the data."""
    anomaly_id: str
    description: str
    severity: str                         # "high", "medium", "low"
    affected_metric: str
    evidence: EvidenceChain
    values: List[float]                   # The anomalous values
    expected_range: Tuple[float, float]   # What we expected
    recommendation: str                   # What to investigate

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['evidence'] = self.evidence.to_dict()
        return d


@dataclass
class PatternInsight:
    """Detected pattern in the data."""
    pattern_id: str
    pattern_type: str                     # "seasonality", "trend", "correlation", "cycle"
    description: str
    strength: float                       # 0-1, how strong is the pattern
    evidence: EvidenceChain
    actionable: bool                      # Can we recommend something based on this?
    specifics: Dict[str, Any]             # Pattern-specific details

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['evidence'] = self.evidence.to_dict()
        return d


@dataclass
class CategoryBreakdown:
    """Breakdown by a specific category (vendor, product type, time period, etc.)."""
    category_field: str                   # e.g., "vendor", "category", "day_of_week"
    breakdown: List[Dict[str, Any]]       # [{name: "Vendor A", value: 5000, pct: 0.25}, ...]
    evidence: EvidenceChain
    top_contributor: str                  # Largest category
    concentration: float                  # How concentrated (HHI or top-3 share)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['evidence'] = self.evidence.to_dict()
        return d


class EnhancedAnalyticsEngine:
    """
    Compute deep, evidence-grounded analytics.

    Output structure:
    {
        "mode_info": {...},
        "metrics": [ComputedMetric, ...],
        "anomalies": [DataAnomaly, ...],
        "patterns": [PatternInsight, ...],
        "breakdowns": [CategoryBreakdown, ...],
        "data_quality": {...},
        "time_coverage": {...}
    }
    """

    def __init__(self, benchmarks: Optional[Dict[str, float]] = None):
        """
        Initialize with optional industry benchmarks.

        Args:
            benchmarks: Dict of benchmark values, e.g., {"labor_pct": 0.28, "cogs_pct": 0.30}
        """
        self.benchmarks = benchmarks or {}
        self.metrics: List[ComputedMetric] = []
        self.anomalies: List[DataAnomaly] = []
        self.patterns: List[PatternInsight] = []
        self.breakdowns: List[CategoryBreakdown] = []

    def analyze(
        self,
        normalized_data: Dict[str, pd.DataFrame]
    ) -> Dict[str, Any]:
        """
        Run full analysis on normalized data.

        Args:
            normalized_data: {pack_type: DataFrame} with canonical columns

        Returns:
            Complete analysis results with evidence chains
        """
        # Reset state
        self.metrics = []
        self.anomalies = []
        self.patterns = []
        self.breakdowns = []

        # Build unified monthly panel
        panel = self._build_monthly_panel(normalized_data)

        # Get time coverage
        time_coverage = self._compute_time_coverage(panel, normalized_data)

        # Compute data quality metrics
        data_quality = self._compute_data_quality(panel, normalized_data)

        # Detect operating mode
        mode_info = self._detect_mode(panel, normalized_data, data_quality)

        # === COMPUTE ALL METRICS ===

        # Revenue metrics (if available)
        if 'revenue_total' in panel.columns:
            self._compute_revenue_metrics(panel, normalized_data)

        # Labor metrics (if available)
        if 'labor_total' in panel.columns:
            self._compute_labor_metrics(panel, normalized_data)

        # COGS metrics (if available)
        if 'cogs' in panel.columns:
            self._compute_cogs_metrics(panel)

        # Expense metrics
        self._compute_expense_metrics(panel)

        # Ratio metrics (cross-cutting)
        self._compute_ratio_metrics(panel)

        # Trend analysis
        self._compute_trends(panel)

        # Volatility analysis
        self._compute_volatility(panel)

        # Seasonality detection
        self._detect_seasonality(panel)

        # Correlation analysis
        self._compute_correlations(panel)

        # Anomaly detection
        self._detect_anomalies(panel)

        # Category breakdowns (from transaction data)
        if 'REVENUE' in normalized_data:
            self._compute_category_breakdowns(normalized_data['REVENUE'])

        # Month-over-month analysis
        self._compute_mom_changes(panel)

        # Benchmark comparisons
        self._compute_benchmark_gaps()

        return {
            "mode_info": mode_info,
            "metrics": [m.to_dict() for m in self.metrics],
            "anomalies": [a.to_dict() for a in self.anomalies],
            "patterns": [p.to_dict() for p in self.patterns],
            "breakdowns": [b.to_dict() for b in self.breakdowns],
            "data_quality": data_quality,
            "time_coverage": time_coverage
        }

    # =========================================================================
    # PANEL BUILDING
    # =========================================================================

    def _build_monthly_panel(
        self,
        normalized_data: Dict[str, pd.DataFrame]
    ) -> pd.DataFrame:
        """Build unified monthly panel from all data packs."""
        panels = []

        for pack_type, df in normalized_data.items():
            if df.empty:
                continue
            if 'month' in df.columns:
                df = df.copy()
                df['month'] = pd.to_datetime(df['month']).dt.to_period('M')

                # Aggregate to monthly if not already
                numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
                if 'month' in numeric_cols:
                    numeric_cols.remove('month')

                if len(numeric_cols) > 0:
                    monthly = df.groupby('month')[numeric_cols].sum().reset_index()
                    monthly = monthly.set_index('month')
                    panels.append(monthly)

        if not panels:
            return pd.DataFrame()

        # Merge all panels
        panel = panels[0]
        for p in panels[1:]:
            panel = panel.join(p, how='outer', rsuffix='_dup')

        # Remove duplicate columns
        panel = panel.loc[:, ~panel.columns.str.endswith('_dup')]
        panel = panel.sort_index()

        return panel

    def _compute_time_coverage(
        self,
        panel: pd.DataFrame,
        normalized_data: Dict[str, pd.DataFrame]
    ) -> Dict[str, Any]:
        """Compute time coverage statistics."""
        if panel.empty:
            return {"months": 0, "start": None, "end": None, "gaps": []}

        months = list(panel.index)

        # Detect gaps
        gaps = []
        for i in range(1, len(months)):
            expected = months[i-1] + 1
            if months[i] != expected:
                gaps.append({
                    "after": str(months[i-1]),
                    "before": str(months[i]),
                    "missing_months": int((months[i] - months[i-1]).n) - 1
                })

        return {
            "months": len(months),
            "start": str(months[0]) if months else None,
            "end": str(months[-1]) if months else None,
            "gaps": gaps,
            "packs_available": list(normalized_data.keys())
        }

    def _compute_data_quality(
        self,
        panel: pd.DataFrame,
        normalized_data: Dict[str, pd.DataFrame]
    ) -> Dict[str, Any]:
        """Compute data quality metrics."""
        if panel.empty:
            return {"overall_completeness": 0, "column_completeness": {}}

        # Column-level completeness
        column_completeness = {}
        for col in panel.columns:
            non_null = panel[col].notna().sum()
            total = len(panel)
            column_completeness[col] = round(non_null / total, 3) if total > 0 else 0

        # Overall completeness
        total_cells = panel.size
        non_null_cells = panel.notna().sum().sum()
        overall = round(non_null_cells / total_cells, 3) if total_cells > 0 else 0

        # Pack-level row counts
        pack_rows = {pack: len(df) for pack, df in normalized_data.items()}

        return {
            "overall_completeness": overall,
            "column_completeness": column_completeness,
            "pack_row_counts": pack_rows,
            "panel_rows": len(panel),
            "panel_columns": len(panel.columns)
        }

    def _detect_mode(
        self,
        panel: pd.DataFrame,
        normalized_data: Dict[str, pd.DataFrame],
        data_quality: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Detect operating mode based on data availability and quality."""
        reasons = []

        has_pnl = 'PNL' in normalized_data and not normalized_data['PNL'].empty
        has_revenue = 'REVENUE' in normalized_data and not normalized_data['REVENUE'].empty
        has_labor = 'LABOR' in normalized_data and not normalized_data['LABOR'].empty

        months_count = len(panel)
        completeness = data_quality.get('overall_completeness', 0)

        has_revenue_col = 'revenue_total' in panel.columns and panel['revenue_total'].notna().sum() > 0
        has_labor_col = 'labor_total' in panel.columns and panel['labor_total'].notna().sum() > 0
        has_cogs_col = 'cogs' in panel.columns and panel['cogs'].notna().sum() > 0

        # Scoring
        if has_pnl and months_count >= 3 and has_revenue_col:
            mode = "PNL_MODE"
            confidence = 0.7
            reasons.append(f"P&L data with {months_count} months")

            if has_labor_col:
                confidence += 0.1
                reasons.append("Labor data available")
            if has_cogs_col:
                confidence += 0.05
                reasons.append("COGS data available")
            if months_count >= 6:
                confidence += 0.05
                reasons.append("6+ months enables trend analysis")
            if completeness >= 0.8:
                confidence += 0.05
                reasons.append("High data completeness")

            confidence = min(0.95, confidence)

        elif (has_revenue or has_labor) and months_count >= 2:
            mode = "OPS_MODE"
            confidence = 0.5
            reasons.append("Operational data available")

            if has_revenue and has_labor:
                confidence += 0.15
                reasons.append("Both revenue and labor present")
            if months_count >= 4:
                confidence += 0.1
                reasons.append("4+ months of data")

            confidence = min(0.75, confidence)

        else:
            mode = "DIRECTIONAL_MODE"
            confidence = 0.3
            reasons.append("Limited data - directional insights only")

            if months_count >= 1:
                confidence = 0.4
            if has_revenue_col or has_labor_col:
                confidence = 0.45

        return {
            "mode": mode,
            "confidence": round(confidence, 2),
            "reasons": reasons,
            "months_available": months_count,
            "data_packs": list(normalized_data.keys())
        }

    # =========================================================================
    # REVENUE METRICS
    # =========================================================================

    def _compute_revenue_metrics(
        self,
        panel: pd.DataFrame,
        normalized_data: Dict[str, pd.DataFrame]
    ):
        """Compute all revenue-related metrics."""
        revenue = panel['revenue_total'].dropna()

        if len(revenue) == 0:
            return

        months = [str(m) for m in revenue.index]
        values = revenue.values.tolist()

        # Basic metrics
        self.metrics.append(ComputedMetric(
            metric_id="revenue_avg_monthly",
            label="Average Monthly Revenue",
            value=round(float(revenue.mean()), 2),
            unit="currency",
            evidence=EvidenceChain(
                dataset="PNL/REVENUE",
                columns=["revenue_total"],
                filters=None,
                computation=f"mean({len(revenue)} monthly values)",
                sample_size=len(revenue),
                time_range=(months[0], months[-1]) if months else None,
                raw_values=values[:12]  # Cap at 12 for storage
            ),
            confidence=min(0.9, 0.5 + len(revenue) * 0.05),
            category="revenue"
        ))

        self.metrics.append(ComputedMetric(
            metric_id="revenue_total_period",
            label="Total Revenue (Period)",
            value=round(float(revenue.sum()), 2),
            unit="currency",
            evidence=EvidenceChain(
                dataset="PNL/REVENUE",
                columns=["revenue_total"],
                filters=None,
                computation=f"sum({len(revenue)} monthly values)",
                sample_size=len(revenue),
                time_range=(months[0], months[-1]) if months else None,
                raw_values=values[:12]
            ),
            confidence=min(0.95, 0.6 + len(revenue) * 0.05),
            category="revenue"
        ))

        self.metrics.append(ComputedMetric(
            metric_id="revenue_median_monthly",
            label="Median Monthly Revenue",
            value=round(float(revenue.median()), 2),
            unit="currency",
            evidence=EvidenceChain(
                dataset="PNL/REVENUE",
                columns=["revenue_total"],
                filters=None,
                computation=f"median({len(revenue)} monthly values)",
                sample_size=len(revenue),
                time_range=(months[0], months[-1]) if months else None,
                raw_values=None
            ),
            confidence=min(0.9, 0.5 + len(revenue) * 0.05),
            category="revenue"
        ))

        # Min/Max months
        max_month = revenue.idxmax()
        min_month = revenue.idxmin()

        self.metrics.append(ComputedMetric(
            metric_id="revenue_peak_month",
            label="Peak Revenue Month",
            value=round(float(revenue.max()), 2),
            unit="currency",
            evidence=EvidenceChain(
                dataset="PNL/REVENUE",
                columns=["revenue_total"],
                filters={"month": str(max_month)},
                computation=f"max value in {str(max_month)}",
                sample_size=len(revenue),
                time_range=(months[0], months[-1]) if months else None,
                raw_values=None
            ),
            confidence=0.95,
            category="revenue"
        ))

        self.metrics.append(ComputedMetric(
            metric_id="revenue_trough_month",
            label="Lowest Revenue Month",
            value=round(float(revenue.min()), 2),
            unit="currency",
            evidence=EvidenceChain(
                dataset="PNL/REVENUE",
                columns=["revenue_total"],
                filters={"month": str(min_month)},
                computation=f"min value in {str(min_month)}",
                sample_size=len(revenue),
                time_range=(months[0], months[-1]) if months else None,
                raw_values=None
            ),
            confidence=0.95,
            category="revenue"
        ))

        # Range
        self.metrics.append(ComputedMetric(
            metric_id="revenue_range",
            label="Revenue Range (Max - Min)",
            value=round(float(revenue.max() - revenue.min()), 2),
            unit="currency",
            evidence=EvidenceChain(
                dataset="PNL/REVENUE",
                columns=["revenue_total"],
                filters=None,
                computation=f"max({revenue.max():.0f}) - min({revenue.min():.0f})",
                sample_size=len(revenue),
                time_range=(months[0], months[-1]) if months else None,
                raw_values=None
            ),
            confidence=0.95,
            category="revenue"
        ))

        # Annualized revenue (if we have enough data)
        if len(revenue) >= 3:
            monthly_avg = revenue.mean()
            annualized = monthly_avg * 12

            self.metrics.append(ComputedMetric(
                metric_id="revenue_annualized",
                label="Annualized Revenue (Projected)",
                value=round(float(annualized), 2),
                unit="currency",
                evidence=EvidenceChain(
                    dataset="PNL/REVENUE",
                    columns=["revenue_total"],
                    filters=None,
                    computation=f"monthly_avg({monthly_avg:.0f}) × 12",
                    sample_size=len(revenue),
                    time_range=(months[0], months[-1]) if months else None,
                    raw_values=None
                ),
                confidence=min(0.8, 0.4 + len(revenue) * 0.05),
                category="revenue"
            ))

    # =========================================================================
    # LABOR METRICS
    # =========================================================================

    def _compute_labor_metrics(
        self,
        panel: pd.DataFrame,
        normalized_data: Dict[str, pd.DataFrame]
    ):
        """Compute all labor-related metrics."""
        labor = panel['labor_total'].dropna()

        if len(labor) == 0:
            return

        months = [str(m) for m in labor.index]
        values = labor.values.tolist()

        # Basic metrics
        self.metrics.append(ComputedMetric(
            metric_id="labor_avg_monthly",
            label="Average Monthly Labor Cost",
            value=round(float(labor.mean()), 2),
            unit="currency",
            evidence=EvidenceChain(
                dataset="PNL/LABOR",
                columns=["labor_total"],
                filters=None,
                computation=f"mean({len(labor)} monthly values)",
                sample_size=len(labor),
                time_range=(months[0], months[-1]) if months else None,
                raw_values=values[:12]
            ),
            confidence=min(0.9, 0.5 + len(labor) * 0.05),
            category="labor"
        ))

        self.metrics.append(ComputedMetric(
            metric_id="labor_total_period",
            label="Total Labor Cost (Period)",
            value=round(float(labor.sum()), 2),
            unit="currency",
            evidence=EvidenceChain(
                dataset="PNL/LABOR",
                columns=["labor_total"],
                filters=None,
                computation=f"sum({len(labor)} monthly values)",
                sample_size=len(labor),
                time_range=(months[0], months[-1]) if months else None,
                raw_values=values[:12]
            ),
            confidence=min(0.95, 0.6 + len(labor) * 0.05),
            category="labor"
        ))

        # Peak labor month
        max_month = labor.idxmax()
        min_month = labor.idxmin()

        self.metrics.append(ComputedMetric(
            metric_id="labor_peak_month",
            label="Peak Labor Cost Month",
            value=round(float(labor.max()), 2),
            unit="currency",
            evidence=EvidenceChain(
                dataset="PNL/LABOR",
                columns=["labor_total"],
                filters={"month": str(max_month)},
                computation=f"max value in {str(max_month)}",
                sample_size=len(labor),
                time_range=(months[0], months[-1]) if months else None,
                raw_values=None
            ),
            confidence=0.95,
            category="labor"
        ))

        # Annualized
        if len(labor) >= 3:
            monthly_avg = labor.mean()
            annualized = monthly_avg * 12

            self.metrics.append(ComputedMetric(
                metric_id="labor_annualized",
                label="Annualized Labor Cost (Projected)",
                value=round(float(annualized), 2),
                unit="currency",
                evidence=EvidenceChain(
                    dataset="PNL/LABOR",
                    columns=["labor_total"],
                    filters=None,
                    computation=f"monthly_avg({monthly_avg:.0f}) × 12",
                    sample_size=len(labor),
                    time_range=(months[0], months[-1]) if months else None,
                    raw_values=None
                ),
                confidence=min(0.8, 0.4 + len(labor) * 0.05),
                category="labor"
            ))

    # =========================================================================
    # COGS METRICS
    # =========================================================================

    def _compute_cogs_metrics(self, panel: pd.DataFrame):
        """Compute COGS-related metrics."""
        cogs = panel['cogs'].dropna()

        if len(cogs) == 0:
            return

        months = [str(m) for m in cogs.index]

        self.metrics.append(ComputedMetric(
            metric_id="cogs_avg_monthly",
            label="Average Monthly COGS",
            value=round(float(cogs.mean()), 2),
            unit="currency",
            evidence=EvidenceChain(
                dataset="PNL",
                columns=["cogs"],
                filters=None,
                computation=f"mean({len(cogs)} monthly values)",
                sample_size=len(cogs),
                time_range=(months[0], months[-1]) if months else None,
                raw_values=cogs.values.tolist()[:12]
            ),
            confidence=min(0.9, 0.5 + len(cogs) * 0.05),
            category="cost"
        ))

        if len(cogs) >= 3:
            annualized = cogs.mean() * 12
            self.metrics.append(ComputedMetric(
                metric_id="cogs_annualized",
                label="Annualized COGS (Projected)",
                value=round(float(annualized), 2),
                unit="currency",
                evidence=EvidenceChain(
                    dataset="PNL",
                    columns=["cogs"],
                    filters=None,
                    computation=f"monthly_avg({cogs.mean():.0f}) × 12",
                    sample_size=len(cogs),
                    time_range=(months[0], months[-1]) if months else None,
                    raw_values=None
                ),
                confidence=min(0.8, 0.4 + len(cogs) * 0.05),
                category="cost"
            ))

    # =========================================================================
    # EXPENSE METRICS
    # =========================================================================

    def _compute_expense_metrics(self, panel: pd.DataFrame):
        """Compute expense metrics for all expense columns."""
        expense_cols = ['rent', 'utilities', 'marketing', 'other_expenses']

        for col in expense_cols:
            if col not in panel.columns:
                continue

            data = panel[col].dropna()
            if len(data) == 0:
                continue

            months = [str(m) for m in data.index]

            self.metrics.append(ComputedMetric(
                metric_id=f"{col}_avg_monthly",
                label=f"Average Monthly {col.replace('_', ' ').title()}",
                value=round(float(data.mean()), 2),
                unit="currency",
                evidence=EvidenceChain(
                    dataset="PNL",
                    columns=[col],
                    filters=None,
                    computation=f"mean({len(data)} monthly values)",
                    sample_size=len(data),
                    time_range=(months[0], months[-1]) if months else None,
                    raw_values=data.values.tolist()[:12]
                ),
                confidence=min(0.85, 0.5 + len(data) * 0.05),
                category="expense"
            ))

    # =========================================================================
    # RATIO METRICS
    # =========================================================================

    def _compute_ratio_metrics(self, panel: pd.DataFrame):
        """Compute cross-cutting ratio metrics."""

        # Labor as % of Revenue
        if 'labor_total' in panel.columns and 'revenue_total' in panel.columns:
            labor = panel['labor_total'].dropna()
            revenue = panel['revenue_total'].dropna()

            # Align indices
            common_idx = labor.index.intersection(revenue.index)
            if len(common_idx) > 0:
                labor_aligned = labor.loc[common_idx]
                revenue_aligned = revenue.loc[common_idx]

                # Avoid division by zero
                valid_mask = revenue_aligned > 0
                if valid_mask.sum() > 0:
                    ratios = (labor_aligned[valid_mask] / revenue_aligned[valid_mask]) * 100
                    avg_ratio = ratios.mean()

                    months = [str(m) for m in common_idx]

                    self.metrics.append(ComputedMetric(
                        metric_id="labor_pct",
                        label="Labor as % of Revenue",
                        value=round(float(avg_ratio), 2),
                        unit="percentage",
                        evidence=EvidenceChain(
                            dataset="PNL",
                            columns=["labor_total", "revenue_total"],
                            filters=None,
                            computation=f"avg(labor/revenue × 100) over {len(common_idx)} months",
                            sample_size=len(common_idx),
                            time_range=(months[0], months[-1]) if months else None,
                            raw_values=[round(r, 2) for r in ratios.values.tolist()[:12]]
                        ),
                        confidence=min(0.9, 0.5 + len(common_idx) * 0.05),
                        category="ratio",
                        benchmark=self.benchmarks.get("labor_pct"),
                        benchmark_source="industry_average" if "labor_pct" in self.benchmarks else None
                    ))

                    # Also compute per-month labor %
                    for month, ratio in ratios.items():
                        self.metrics.append(ComputedMetric(
                            metric_id=f"labor_pct_{str(month).replace('-', '_')}",
                            label=f"Labor % in {str(month)}",
                            value=round(float(ratio), 2),
                            unit="percentage",
                            evidence=EvidenceChain(
                                dataset="PNL",
                                columns=["labor_total", "revenue_total"],
                                filters={"month": str(month)},
                                computation=f"labor({labor_aligned.loc[month]:.0f}) / revenue({revenue_aligned.loc[month]:.0f}) × 100",
                                sample_size=1,
                                time_range=(str(month), str(month)),
                                raw_values=None
                            ),
                            confidence=0.95,
                            category="ratio_monthly"
                        ))

        # COGS as % of Revenue
        if 'cogs' in panel.columns and 'revenue_total' in panel.columns:
            cogs = panel['cogs'].dropna()
            revenue = panel['revenue_total'].dropna()

            common_idx = cogs.index.intersection(revenue.index)
            if len(common_idx) > 0:
                cogs_aligned = cogs.loc[common_idx]
                revenue_aligned = revenue.loc[common_idx]

                valid_mask = revenue_aligned > 0
                if valid_mask.sum() > 0:
                    ratios = (cogs_aligned[valid_mask] / revenue_aligned[valid_mask]) * 100
                    avg_ratio = ratios.mean()

                    months = [str(m) for m in common_idx]

                    self.metrics.append(ComputedMetric(
                        metric_id="cogs_pct",
                        label="COGS as % of Revenue",
                        value=round(float(avg_ratio), 2),
                        unit="percentage",
                        evidence=EvidenceChain(
                            dataset="PNL",
                            columns=["cogs", "revenue_total"],
                            filters=None,
                            computation=f"avg(cogs/revenue × 100) over {len(common_idx)} months",
                            sample_size=len(common_idx),
                            time_range=(months[0], months[-1]) if months else None,
                            raw_values=[round(r, 2) for r in ratios.values.tolist()[:12]]
                        ),
                        confidence=min(0.9, 0.5 + len(common_idx) * 0.05),
                        category="ratio",
                        benchmark=self.benchmarks.get("cogs_pct"),
                        benchmark_source="industry_average" if "cogs_pct" in self.benchmarks else None
                    ))

        # Gross margin (if we have revenue and COGS)
        if 'cogs' in panel.columns and 'revenue_total' in panel.columns:
            cogs = panel['cogs'].dropna()
            revenue = panel['revenue_total'].dropna()

            common_idx = cogs.index.intersection(revenue.index)
            if len(common_idx) > 0:
                cogs_aligned = cogs.loc[common_idx]
                revenue_aligned = revenue.loc[common_idx]

                valid_mask = revenue_aligned > 0
                if valid_mask.sum() > 0:
                    gross_profit = revenue_aligned[valid_mask] - cogs_aligned[valid_mask]
                    gross_margin = (gross_profit / revenue_aligned[valid_mask]) * 100
                    avg_margin = gross_margin.mean()

                    months = [str(m) for m in common_idx]

                    self.metrics.append(ComputedMetric(
                        metric_id="gross_margin_pct",
                        label="Gross Margin %",
                        value=round(float(avg_margin), 2),
                        unit="percentage",
                        evidence=EvidenceChain(
                            dataset="PNL",
                            columns=["revenue_total", "cogs"],
                            filters=None,
                            computation=f"avg((revenue - cogs) / revenue × 100) over {len(common_idx)} months",
                            sample_size=len(common_idx),
                            time_range=(months[0], months[-1]) if months else None,
                            raw_values=[round(m, 2) for m in gross_margin.values.tolist()[:12]]
                        ),
                        confidence=min(0.9, 0.5 + len(common_idx) * 0.05),
                        category="ratio",
                        benchmark=self.benchmarks.get("gross_margin_pct"),
                        benchmark_source="industry_average" if "gross_margin_pct" in self.benchmarks else None
                    ))

    # =========================================================================
    # TREND ANALYSIS
    # =========================================================================

    def _compute_trends(self, panel: pd.DataFrame):
        """Compute trend metrics using linear regression."""

        trend_cols = ['revenue_total', 'labor_total', 'cogs']

        for col in trend_cols:
            if col not in panel.columns:
                continue

            data = panel[col].dropna()
            if len(data) < 3:
                continue

            x = np.arange(len(data))
            y = data.values

            try:
                slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)

                # Convert to % change per month
                mean_value = y.mean()
                if mean_value != 0:
                    pct_change_per_month = (slope / mean_value) * 100
                else:
                    pct_change_per_month = 0

                months = [str(m) for m in data.index]

                # Determine trend direction
                if pct_change_per_month > 1:
                    direction = "increasing"
                elif pct_change_per_month < -1:
                    direction = "decreasing"
                else:
                    direction = "stable"

                self.metrics.append(ComputedMetric(
                    metric_id=f"{col}_trend",
                    label=f"{col.replace('_', ' ').title()} Monthly Trend",
                    value=round(float(pct_change_per_month), 2),
                    unit="pct_per_month",
                    evidence=EvidenceChain(
                        dataset="PNL",
                        columns=[col],
                        filters=None,
                        computation=f"linear_regression(slope={slope:.2f}, r²={r_value**2:.3f}, direction={direction})",
                        sample_size=len(data),
                        time_range=(months[0], months[-1]) if months else None,
                        raw_values=y.tolist()[:12]
                    ),
                    confidence=round(min(0.9, r_value**2 + 0.3), 2),  # Higher R² = higher confidence
                    category="trend"
                ))

                # Add pattern insight
                if abs(pct_change_per_month) > 2 and r_value**2 > 0.5:
                    self.patterns.append(PatternInsight(
                        pattern_id=f"{col}_trend_pattern",
                        pattern_type="trend",
                        description=f"{col.replace('_', ' ').title()} is {direction} at {abs(pct_change_per_month):.1f}% per month",
                        strength=round(r_value**2, 2),
                        evidence=EvidenceChain(
                            dataset="PNL",
                            columns=[col],
                            filters=None,
                            computation=f"linear_regression over {len(data)} months",
                            sample_size=len(data),
                            time_range=(months[0], months[-1]) if months else None,
                            raw_values=None
                        ),
                        actionable=True,
                        specifics={
                            "direction": direction,
                            "rate_pct": round(pct_change_per_month, 2),
                            "r_squared": round(r_value**2, 3),
                            "p_value": round(p_value, 4)
                        }
                    ))

            except Exception:
                pass

    # =========================================================================
    # VOLATILITY ANALYSIS
    # =========================================================================

    def _compute_volatility(self, panel: pd.DataFrame):
        """Compute volatility metrics (coefficient of variation)."""

        vol_cols = ['revenue_total', 'labor_total', 'cogs']

        for col in vol_cols:
            if col not in panel.columns:
                continue

            data = panel[col].dropna()
            if len(data) < 4:  # Need at least 4 points for meaningful volatility
                continue

            mean_val = data.mean()
            std_val = data.std()

            if mean_val != 0:
                cv = std_val / mean_val
            else:
                cv = 0

            months = [str(m) for m in data.index]

            # Interpret volatility
            if cv < 0.1:
                interpretation = "very_stable"
            elif cv < 0.2:
                interpretation = "stable"
            elif cv < 0.3:
                interpretation = "moderate"
            else:
                interpretation = "volatile"

            self.metrics.append(ComputedMetric(
                metric_id=f"{col}_volatility",
                label=f"{col.replace('_', ' ').title()} Volatility (CV)",
                value=round(float(cv), 3),
                unit="coefficient_of_variation",
                evidence=EvidenceChain(
                    dataset="PNL",
                    columns=[col],
                    filters=None,
                    computation=f"std({std_val:.0f}) / mean({mean_val:.0f}) = {cv:.3f} ({interpretation})",
                    sample_size=len(data),
                    time_range=(months[0], months[-1]) if months else None,
                    raw_values=data.values.tolist()[:12]
                ),
                confidence=min(0.9, 0.4 + len(data) * 0.05),
                category="volatility"
            ))

            # High volatility pattern
            if cv > 0.2:
                self.patterns.append(PatternInsight(
                    pattern_id=f"{col}_high_volatility",
                    pattern_type="volatility",
                    description=f"{col.replace('_', ' ').title()} shows high month-to-month volatility (CV={cv:.2f})",
                    strength=round(min(1.0, cv), 2),
                    evidence=EvidenceChain(
                        dataset="PNL",
                        columns=[col],
                        filters=None,
                        computation=f"coefficient_of_variation = {cv:.3f}",
                        sample_size=len(data),
                        time_range=(months[0], months[-1]) if months else None,
                        raw_values=None
                    ),
                    actionable=True,
                    specifics={
                        "cv": round(cv, 3),
                        "mean": round(mean_val, 2),
                        "std": round(std_val, 2),
                        "interpretation": interpretation
                    }
                ))

    # =========================================================================
    # SEASONALITY DETECTION
    # =========================================================================

    def _detect_seasonality(self, panel: pd.DataFrame):
        """Detect seasonal patterns in the data."""

        if 'revenue_total' not in panel.columns:
            return

        revenue = panel['revenue_total'].dropna()

        if len(revenue) < 6:  # Need at least 6 months for seasonality
            return

        # Extract month numbers
        try:
            month_nums = [m.month for m in revenue.index]
            values = revenue.values

            # Group by month of year
            monthly_avgs = {}
            for m, v in zip(month_nums, values):
                if m not in monthly_avgs:
                    monthly_avgs[m] = []
                monthly_avgs[m].append(v)

            # Calculate average by month
            month_means = {m: np.mean(vals) for m, vals in monthly_avgs.items()}

            if len(month_means) < 3:
                return

            overall_mean = np.mean(list(month_means.values()))

            # Find best and worst months
            best_month = max(month_means, key=month_means.get)
            worst_month = min(month_means, key=month_means.get)

            best_value = month_means[best_month]
            worst_value = month_means[worst_month]

            # Seasonality strength = range / mean
            if overall_mean > 0:
                seasonality_strength = (best_value - worst_value) / overall_mean
            else:
                seasonality_strength = 0

            months = [str(m) for m in revenue.index]
            month_names = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

            if seasonality_strength > 0.15:  # Meaningful seasonality
                self.patterns.append(PatternInsight(
                    pattern_id="revenue_seasonality",
                    pattern_type="seasonality",
                    description=f"Revenue shows seasonality: {month_names[best_month]} is strongest (+{((best_value/overall_mean)-1)*100:.0f}%), {month_names[worst_month]} is weakest ({((worst_value/overall_mean)-1)*100:.0f}%)",
                    strength=round(min(1.0, seasonality_strength), 2),
                    evidence=EvidenceChain(
                        dataset="PNL/REVENUE",
                        columns=["revenue_total"],
                        filters=None,
                        computation=f"monthly_avg comparison over {len(revenue)} months",
                        sample_size=len(revenue),
                        time_range=(months[0], months[-1]) if months else None,
                        raw_values=None
                    ),
                    actionable=True,
                    specifics={
                        "best_month": month_names[best_month],
                        "best_month_avg": round(best_value, 2),
                        "worst_month": month_names[worst_month],
                        "worst_month_avg": round(worst_value, 2),
                        "overall_avg": round(overall_mean, 2),
                        "seasonality_strength": round(seasonality_strength, 3)
                    }
                ))

        except Exception:
            pass

    # =========================================================================
    # CORRELATION ANALYSIS
    # =========================================================================

    def _compute_correlations(self, panel: pd.DataFrame):
        """Compute correlations between key metrics."""

        # Labor vs Revenue correlation
        if 'labor_total' in panel.columns and 'revenue_total' in panel.columns:
            labor = panel['labor_total'].dropna()
            revenue = panel['revenue_total'].dropna()

            common_idx = labor.index.intersection(revenue.index)
            if len(common_idx) >= 4:
                labor_aligned = labor.loc[common_idx]
                revenue_aligned = revenue.loc[common_idx]

                corr, p_value = stats.pearsonr(labor_aligned, revenue_aligned)

                months = [str(m) for m in common_idx]

                self.metrics.append(ComputedMetric(
                    metric_id="labor_revenue_correlation",
                    label="Labor-Revenue Correlation",
                    value=round(float(corr), 3),
                    unit="correlation",
                    evidence=EvidenceChain(
                        dataset="PNL",
                        columns=["labor_total", "revenue_total"],
                        filters=None,
                        computation=f"pearson_correlation(r={corr:.3f}, p={p_value:.4f})",
                        sample_size=len(common_idx),
                        time_range=(months[0], months[-1]) if months else None,
                        raw_values=None
                    ),
                    confidence=round(1 - p_value, 2) if p_value < 1 else 0.5,
                    category="correlation"
                ))

                # Low correlation = potential scheduling inefficiency
                if corr < 0.7 and len(common_idx) >= 6:
                    self.patterns.append(PatternInsight(
                        pattern_id="labor_revenue_weak_correlation",
                        pattern_type="correlation",
                        description=f"Labor costs don't track revenue well (r={corr:.2f}). This may indicate scheduling inefficiency.",
                        strength=round(1 - corr, 2),
                        evidence=EvidenceChain(
                            dataset="PNL",
                            columns=["labor_total", "revenue_total"],
                            filters=None,
                            computation=f"pearson_correlation over {len(common_idx)} months",
                            sample_size=len(common_idx),
                            time_range=(months[0], months[-1]) if months else None,
                            raw_values=None
                        ),
                        actionable=True,
                        specifics={
                            "correlation": round(corr, 3),
                            "p_value": round(p_value, 4),
                            "interpretation": "Labor should generally track revenue. Low correlation suggests fixed staffing regardless of demand."
                        }
                    ))

    # =========================================================================
    # ANOMALY DETECTION
    # =========================================================================

    def _detect_anomalies(self, panel: pd.DataFrame):
        """Detect anomalies using statistical methods."""

        anomaly_cols = ['revenue_total', 'labor_total', 'cogs']

        for col in anomaly_cols:
            if col not in panel.columns:
                continue

            data = panel[col].dropna()
            if len(data) < 4:
                continue

            mean_val = data.mean()
            std_val = data.std()

            if std_val == 0:
                continue

            # Z-score based anomaly detection (threshold = 2)
            z_scores = (data - mean_val) / std_val
            anomalies = data[np.abs(z_scores) > 2]

            months = [str(m) for m in data.index]

            for month, value in anomalies.items():
                z = z_scores.loc[month]
                direction = "above" if z > 0 else "below"
                severity = "high" if abs(z) > 3 else "medium"

                expected_low = mean_val - 2 * std_val
                expected_high = mean_val + 2 * std_val

                self.anomalies.append(DataAnomaly(
                    anomaly_id=f"{col}_anomaly_{str(month).replace('-', '_')}",
                    description=f"{col.replace('_', ' ').title()} in {str(month)} was {direction} normal range (z-score: {z:.2f})",
                    severity=severity,
                    affected_metric=col,
                    evidence=EvidenceChain(
                        dataset="PNL",
                        columns=[col],
                        filters={"month": str(month)},
                        computation=f"z_score = ({value:.0f} - {mean_val:.0f}) / {std_val:.0f} = {z:.2f}",
                        sample_size=len(data),
                        time_range=(months[0], months[-1]) if months else None,
                        raw_values=None
                    ),
                    values=[round(value, 2)],
                    expected_range=(round(expected_low, 2), round(expected_high, 2)),
                    recommendation=f"Investigate what happened in {str(month)} that caused {col.replace('_', ' ')} to be {abs(value - mean_val):.0f} {direction} average"
                ))

    # =========================================================================
    # CATEGORY BREAKDOWNS
    # =========================================================================

    def _compute_category_breakdowns(self, revenue_df: pd.DataFrame):
        """Compute breakdowns by category fields in transaction data."""

        if revenue_df.empty:
            return

        # Check for category column
        if 'category' in revenue_df.columns and 'amount' in revenue_df.columns:
            category_totals = revenue_df.groupby('category')['amount'].sum().sort_values(ascending=False)

            if len(category_totals) > 0:
                total = category_totals.sum()

                breakdown = []
                for cat, val in category_totals.items():
                    breakdown.append({
                        "name": str(cat),
                        "value": round(float(val), 2),
                        "pct": round(float(val / total), 3) if total > 0 else 0
                    })

                # Concentration (top 3 share)
                top_3_share = category_totals.head(3).sum() / total if total > 0 else 0

                self.breakdowns.append(CategoryBreakdown(
                    category_field="category",
                    breakdown=breakdown,
                    evidence=EvidenceChain(
                        dataset="REVENUE",
                        columns=["category", "amount"],
                        filters=None,
                        computation=f"sum(amount) grouped by category ({len(category_totals)} categories)",
                        sample_size=len(revenue_df),
                        time_range=None,
                        raw_values=None
                    ),
                    top_contributor=str(category_totals.index[0]) if len(category_totals) > 0 else "unknown",
                    concentration=round(float(top_3_share), 3)
                ))

        # Day of week breakdown (if date available)
        if 'transaction_date' in revenue_df.columns and 'amount' in revenue_df.columns:
            try:
                revenue_df = revenue_df.copy()
                revenue_df['transaction_date'] = pd.to_datetime(revenue_df['transaction_date'])
                revenue_df['day_of_week'] = revenue_df['transaction_date'].dt.day_name()

                dow_totals = revenue_df.groupby('day_of_week')['amount'].sum()

                # Reorder by day
                day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                dow_totals = dow_totals.reindex([d for d in day_order if d in dow_totals.index])

                if len(dow_totals) > 0:
                    total = dow_totals.sum()

                    breakdown = []
                    for day, val in dow_totals.items():
                        breakdown.append({
                            "name": str(day),
                            "value": round(float(val), 2),
                            "pct": round(float(val / total), 3) if total > 0 else 0
                        })

                    best_day = dow_totals.idxmax()
                    worst_day = dow_totals.idxmin()

                    self.breakdowns.append(CategoryBreakdown(
                        category_field="day_of_week",
                        breakdown=breakdown,
                        evidence=EvidenceChain(
                            dataset="REVENUE",
                            columns=["transaction_date", "amount"],
                            filters=None,
                            computation=f"sum(amount) grouped by day_of_week",
                            sample_size=len(revenue_df),
                            time_range=None,
                            raw_values=None
                        ),
                        top_contributor=str(best_day),
                        concentration=0  # Not applicable for days
                    ))

                    # Pattern insight
                    if len(dow_totals) >= 5:
                        range_pct = (dow_totals.max() - dow_totals.min()) / dow_totals.mean() if dow_totals.mean() > 0 else 0
                        if range_pct > 0.3:
                            self.patterns.append(PatternInsight(
                                pattern_id="day_of_week_pattern",
                                pattern_type="cycle",
                                description=f"{best_day} is the strongest day, {worst_day} is the weakest. Consider day-specific strategies.",
                                strength=round(min(1.0, range_pct), 2),
                                evidence=EvidenceChain(
                                    dataset="REVENUE",
                                    columns=["transaction_date", "amount"],
                                    filters=None,
                                    computation=f"day_of_week aggregation over {len(revenue_df)} transactions",
                                    sample_size=len(revenue_df),
                                    time_range=None,
                                    raw_values=None
                                ),
                                actionable=True,
                                specifics={
                                    "best_day": str(best_day),
                                    "best_day_total": round(float(dow_totals.max()), 2),
                                    "worst_day": str(worst_day),
                                    "worst_day_total": round(float(dow_totals.min()), 2)
                                }
                            ))

            except Exception:
                pass

    # =========================================================================
    # MONTH-OVER-MONTH CHANGES
    # =========================================================================

    def _compute_mom_changes(self, panel: pd.DataFrame):
        """Compute month-over-month changes."""

        mom_cols = ['revenue_total', 'labor_total']

        for col in mom_cols:
            if col not in panel.columns:
                continue

            data = panel[col].dropna()
            if len(data) < 2:
                continue

            # Compute MoM change
            mom_change = data.pct_change() * 100
            mom_change = mom_change.dropna()

            if len(mom_change) == 0:
                continue

            months = [str(m) for m in mom_change.index]

            # Average MoM change
            avg_mom = mom_change.mean()

            self.metrics.append(ComputedMetric(
                metric_id=f"{col}_avg_mom_change",
                label=f"{col.replace('_', ' ').title()} Avg Month-over-Month Change",
                value=round(float(avg_mom), 2),
                unit="pct_change",
                evidence=EvidenceChain(
                    dataset="PNL",
                    columns=[col],
                    filters=None,
                    computation=f"avg(pct_change) over {len(mom_change)} month transitions",
                    sample_size=len(mom_change),
                    time_range=(months[0], months[-1]) if months else None,
                    raw_values=[round(v, 2) for v in mom_change.values.tolist()[:12]]
                ),
                confidence=min(0.85, 0.4 + len(mom_change) * 0.05),
                category="change"
            ))

            # Largest single-month changes
            if len(mom_change) >= 3:
                max_increase_month = mom_change.idxmax()
                max_decrease_month = mom_change.idxmin()

                self.metrics.append(ComputedMetric(
                    metric_id=f"{col}_max_mom_increase",
                    label=f"{col.replace('_', ' ').title()} Largest Monthly Increase",
                    value=round(float(mom_change.max()), 2),
                    unit="pct_change",
                    evidence=EvidenceChain(
                        dataset="PNL",
                        columns=[col],
                        filters={"month": str(max_increase_month)},
                        computation=f"max MoM increase in {str(max_increase_month)}",
                        sample_size=len(mom_change),
                        time_range=(months[0], months[-1]) if months else None,
                        raw_values=None
                    ),
                    confidence=0.95,
                    category="change"
                ))

    # =========================================================================
    # BENCHMARK COMPARISONS
    # =========================================================================

    def _compute_benchmark_gaps(self):
        """Compute gaps to benchmarks for all metrics that have them."""

        for metric in self.metrics:
            if metric.benchmark is not None and metric.value is not None:
                gap = metric.value - metric.benchmark

                if metric.benchmark != 0:
                    gap_pct = (gap / metric.benchmark) * 100
                else:
                    gap_pct = 0

                metric.gap_to_benchmark = round(gap, 2)

                if gap > 0.5:  # Meaningful positive gap
                    metric.gap_direction = "above"
                elif gap < -0.5:  # Meaningful negative gap
                    metric.gap_direction = "below"
                else:
                    metric.gap_direction = "at"
