"""Deterministic analytics engine."""
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple, Optional
from app.core.vertical_config import VerticalConfig


class AnalyticsEngine:
    """Compute deterministic analytics and signals."""
    
    def __init__(self, vertical_config: VerticalConfig):
        self.config = vertical_config
    
    def compute_analytics(
        self,
        normalized_data: Dict[str, pd.DataFrame]
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Compute analytics from normalized data.
        
        Args:
            normalized_data: {pack_type: dataframe}
        
        Returns:
            (mode_info, analytics_facts)
            mode_info: {mode: str, confidence: float, reasons: list}
            analytics_facts: List of evidence-based facts
        """
        # Build monthly panel
        panel = self._build_monthly_panel(normalized_data)
        
        # Detect operating mode
        mode_info = self._detect_mode(panel, normalized_data)
        
        # Compute facts
        facts = []
        
        # Basic metrics
        facts.extend(self._compute_basic_metrics(panel))
        
        # Advanced metrics
        facts.extend(self._compute_advanced_metrics(panel))
        
        # Trends
        facts.extend(self._compute_trends(panel))
        
        # Volatility
        facts.extend(self._compute_volatility(panel))
        
        # Outliers
        facts.extend(self._compute_outliers(panel))
        
        # Month-over-month changes
        facts.extend(self._compute_mom_changes(panel))
        
        # Growth rates
        facts.extend(self._compute_growth_rates(panel))
        
        # Percentiles and distributions
        facts.extend(self._compute_distributions(panel))
        
        # Efficiency metrics
        facts.extend(self._compute_efficiency_metrics(panel))
        
        # Vertical-specific signals
        facts.extend(self._compute_signals(panel))
        
        return mode_info, facts
    
    def _build_monthly_panel(
        self,
        normalized_data: Dict[str, pd.DataFrame]
    ) -> pd.DataFrame:
        """Build unified monthly panel from all data packs."""
        panels = []
        
        for pack_type, df in normalized_data.items():
            if 'month' in df.columns:
                df = df.copy()
                df['month'] = pd.to_datetime(df['month']).dt.to_period('M')
                df = df.set_index('month')
                panels.append(df)
        
        if not panels:
            return pd.DataFrame()
        
        # Merge all panels
        panel = panels[0]
        for p in panels[1:]:
            panel = panel.join(p, how='outer', rsuffix='_dup')
        
        # Remove duplicate columns
        panel = panel.loc[:, ~panel.columns.str.endswith('_dup')]
        
        # Sort by month
        panel = panel.sort_index()
        
        return panel
    
    def _detect_mode(
        self,
        panel: pd.DataFrame,
        normalized_data: Dict[str, pd.DataFrame]
    ) -> Dict[str, Any]:
        """
        Detect operating mode: PNL_MODE, OPS_MODE, or DIRECTIONAL_MODE.
        """
        reasons = []
        confidence_factors = []
        
        # Check data availability
        has_pnl = 'PNL' in normalized_data and not normalized_data['PNL'].empty
        has_revenue = 'REVENUE' in normalized_data and not normalized_data['REVENUE'].empty
        has_labor = 'LABOR' in normalized_data and not normalized_data['LABOR'].empty
        
        # Check panel completeness
        months_count = len(panel)
        
        # Check key fields
        has_revenue_data = 'revenue_total' in panel.columns and panel['revenue_total'].notna().sum() > 0
        has_labor_data = 'labor_total' in panel.columns and panel['labor_total'].notna().sum() > 0
        
        # Determine mode
        if has_pnl and months_count >= 3 and has_revenue_data:
            mode = "PNL_MODE"
            confidence = 0.8
            reasons.append(f"Complete P&L data with {months_count} months")
            
            if has_labor_data:
                confidence += 0.1
                reasons.append("Labor data available")
            
            if months_count >= 6:
                confidence = min(0.95, confidence + 0.05)
                reasons.append("Sufficient history for trends")
        
        elif (has_revenue or has_labor) and months_count >= 2:
            mode = "OPS_MODE"
            confidence = 0.6
            reasons.append("Operational data available")
            
            if has_revenue and has_labor:
                confidence += 0.15
                reasons.append("Both revenue and labor data present")
        
        else:
            mode = "DIRECTIONAL_MODE"
            confidence = 0.4
            reasons.append("Limited data - directional insights only")
        
        # Apply vertical-specific thresholds
        assumptions = self.config.default_assumptions
        min_conf_ops = assumptions.get('min_confidence_for_ops_mode', 0.7)
        min_conf_pnl = assumptions.get('min_confidence_for_pnl_mode', 0.6)
        
        # Downgrade if below threshold
        if mode == "PNL_MODE" and confidence < min_conf_pnl:
            mode = "OPS_MODE"
            reasons.append("Downgraded to OPS_MODE due to low confidence")
        
        if mode == "OPS_MODE" and confidence < min_conf_ops:
            mode = "DIRECTIONAL_MODE"
            reasons.append("Downgraded to DIRECTIONAL_MODE due to low confidence")
        
        return {
            "mode": mode,
            "confidence": round(confidence, 2),
            "reasons": reasons,
            "months_available": months_count
        }
    
    def _compute_basic_metrics(self, panel: pd.DataFrame) -> List[Dict[str, Any]]:
        """Compute basic metrics (totals, averages)."""
        facts = []
        
        if panel.empty:
            return facts
        
        # Revenue metrics
        if 'revenue_total' in panel.columns:
            revenue_data = panel['revenue_total'].dropna()
            if len(revenue_data) > 0:
                facts.append({
                    "evidence_key": "revenue_avg_monthly",
                    "label": "Average Monthly Revenue",
                    "value": float(revenue_data.mean()),
                    "unit": "currency",
                    "period": "average",
                    "source": "PNL/REVENUE"
                })
                
                facts.append({
                    "evidence_key": "revenue_total_period",
                    "label": "Total Revenue (Period)",
                    "value": float(revenue_data.sum()),
                    "unit": "currency",
                    "period": f"{len(revenue_data)} months",
                    "source": "PNL/REVENUE"
                })
        
        # Labor metrics
        if 'labor_total' in panel.columns:
            labor_data = panel['labor_total'].dropna()
            if len(labor_data) > 0:
                facts.append({
                    "evidence_key": "labor_avg_monthly",
                    "label": "Average Monthly Labor Cost",
                    "value": float(labor_data.mean()),
                    "unit": "currency",
                    "period": "average",
                    "source": "PNL/LABOR"
                })
        
        return facts
    
    def _compute_advanced_metrics(self, panel: pd.DataFrame) -> List[Dict[str, Any]]:
        """Compute advanced metrics (min, max, median, std dev, etc.)."""
        facts = []
        
        if panel.empty:
            return facts
        
        metric_cols = ['revenue_total', 'labor_total', 'cogs', 'rent', 'utilities', 'marketing', 'other_expenses']
        
        for col in metric_cols:
            if col in panel.columns:
                data = panel[col].dropna()
                if len(data) > 0:
                    # Min
                    facts.append({
                        "evidence_key": f"{col}_min",
                        "label": f"{col.replace('_', ' ').title()} - Minimum",
                        "value": float(data.min()),
                        "unit": "currency",
                        "period": "period_min",
                        "source": "PNL"
                    })
                    
                    # Max
                    facts.append({
                        "evidence_key": f"{col}_max",
                        "label": f"{col.replace('_', ' ').title()} - Maximum",
                        "value": float(data.max()),
                        "unit": "currency",
                        "period": "period_max",
                        "source": "PNL"
                    })
                    
                    # Median
                    facts.append({
                        "evidence_key": f"{col}_median",
                        "label": f"{col.replace('_', ' ').title()} - Median",
                        "value": float(data.median()),
                        "unit": "currency",
                        "period": "median",
                        "source": "PNL"
                    })
                    
                    # Standard deviation
                    if len(data) > 1:
                        facts.append({
                            "evidence_key": f"{col}_std",
                            "label": f"{col.replace('_', ' ').title()} - Std Deviation",
                            "value": float(data.std()),
                            "unit": "currency",
                            "period": "period",
                            "source": "PNL"
                        })
                    
                    # Range
                    facts.append({
                        "evidence_key": f"{col}_range",
                        "label": f"{col.replace('_', ' ').title()} - Range",
                        "value": float(data.max() - data.min()),
                        "unit": "currency",
                        "period": "period",
                        "source": "PNL"
                    })
        
        return facts
    
    def _compute_trends(self, panel: pd.DataFrame) -> List[Dict[str, Any]]:
        """Compute linear trends."""
        facts = []
        
        if panel.empty or len(panel) < 3:
            return facts
        
        # Revenue trend
        if 'revenue_total' in panel.columns:
            revenue_data = panel['revenue_total'].dropna()
            if len(revenue_data) >= 3:
                trend = self._linear_regression(revenue_data)
                if trend is not None:
                    facts.append({
                        "evidence_key": "revenue_trend",
                        "label": "Revenue Trend",
                        "value": float(trend),
                        "unit": "monthly_change_pct",
                        "period": f"{len(revenue_data)} months",
                        "source": "computed"
                    })
        
        return facts
    
    def _compute_volatility(self, panel: pd.DataFrame) -> List[Dict[str, Any]]:
        """Compute volatility (coefficient of variation)."""
        facts = []
        
        if panel.empty or len(panel) < 6:
            return facts
        
        # Labor volatility
        if 'labor_total' in panel.columns:
            labor_data = panel['labor_total'].dropna()
            if len(labor_data) >= 6:
                cv = labor_data.std() / labor_data.mean() if labor_data.mean() != 0 else 0
                facts.append({
                    "evidence_key": "labor_volatility",
                    "label": "Labor Cost Volatility",
                    "value": float(cv),
                    "unit": "coefficient_of_variation",
                    "period": f"{len(labor_data)} months",
                    "source": "computed"
                })
        
        return facts
    
    def _compute_outliers(self, panel: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect outliers using standard deviation."""
        facts = []
        
        if panel.empty or len(panel) < 4:
            return facts
        
        threshold = self.config.default_assumptions.get('outlier_std_threshold', 2.5)
        
        for col in ['revenue_total', 'labor_total']:
            if col in panel.columns:
                data = panel[col].dropna()
                if len(data) >= 4:
                    mean = data.mean()
                    std = data.std()
                    outliers = data[np.abs(data - mean) > threshold * std]
                    
                    if len(outliers) > 0:
                        facts.append({
                            "evidence_key": f"{col}_outliers",
                            "label": f"{col.replace('_', ' ').title()} Outliers Detected",
                            "value": len(outliers),
                            "unit": "count",
                            "period": "total",
                            "source": "computed"
                        })
        
        return facts
    
    def _compute_mom_changes(self, panel: pd.DataFrame) -> List[Dict[str, Any]]:
        """Compute month-over-month percentage changes."""
        facts = []
        
        if panel.empty or len(panel) < 2:
            return facts
        
        for col in ['revenue_total', 'labor_total', 'cogs']:
            if col in panel.columns:
                data = panel[col].dropna()
                if len(data) >= 2:
                    # Compute MoM changes
                    mom_pct = data.pct_change() * 100
                    mom_pct = mom_pct.dropna()
                    
                    if len(mom_pct) > 0:
                        # Average MoM change
                        facts.append({
                            "evidence_key": f"{col}_avg_mom_change",
                            "label": f"{col.replace('_', ' ').title()} - Avg MoM Change",
                            "value": float(mom_pct.mean()),
                            "unit": "percentage",
                            "period": f"{len(mom_pct)} transitions",
                            "source": "computed"
                        })
                        
                        # Largest increase
                        if len(mom_pct) > 0:
                            facts.append({
                                "evidence_key": f"{col}_max_mom_increase",
                                "label": f"{col.replace('_', ' ').title()} - Largest MoM Increase",
                                "value": float(mom_pct.max()),
                                "unit": "percentage",
                                "period": "single_month",
                                "source": "computed"
                            })
                            
                            # Largest decrease
                            facts.append({
                                "evidence_key": f"{col}_max_mom_decrease",
                                "label": f"{col.replace('_', ' ').title()} - Largest MoM Decrease",
                                "value": float(mom_pct.min()),
                                "unit": "percentage",
                                "period": "single_month",
                                "source": "computed"
                            })
        
        return facts
    
    def _compute_growth_rates(self, panel: pd.DataFrame) -> List[Dict[str, Any]]:
        """Compute compound growth rates."""
        facts = []
        
        if panel.empty or len(panel) < 2:
            return facts
        
        for col in ['revenue_total', 'labor_total']:
            if col in panel.columns:
                data = panel[col].dropna()
                if len(data) >= 2:
                    # Overall growth rate (first to last)
                    first_val = data.iloc[0]
                    last_val = data.iloc[-1]
                    months = len(data) - 1
                    
                    if first_val > 0 and months > 0:
                        # Compound monthly growth rate
                        cagr = ((last_val / first_val) ** (1 / months) - 1) * 100
                        facts.append({
                            "evidence_key": f"{col}_cagr",
                            "label": f"{col.replace('_', ' ').title()} - Compound Monthly Growth Rate",
                            "value": float(cagr),
                            "unit": "percentage",
                            "period": f"{months} months",
                            "source": "computed"
                        })
                        
                        # Total growth
                        total_growth = ((last_val / first_val) - 1) * 100
                        facts.append({
                            "evidence_key": f"{col}_total_growth",
                            "label": f"{col.replace('_', ' ').title()} - Total Growth",
                            "value": float(total_growth),
                            "unit": "percentage",
                            "period": f"{months} months",
                            "source": "computed"
                        })
        
        return facts
    
    def _compute_distributions(self, panel: pd.DataFrame) -> List[Dict[str, Any]]:
        """Compute percentile distributions."""
        facts = []
        
        if panel.empty or len(panel) < 4:
            return facts
        
        for col in ['revenue_total', 'labor_total']:
            if col in panel.columns:
                data = panel[col].dropna()
                if len(data) >= 4:
                    # 25th percentile
                    facts.append({
                        "evidence_key": f"{col}_p25",
                        "label": f"{col.replace('_', ' ').title()} - 25th Percentile",
                        "value": float(data.quantile(0.25)),
                        "unit": "currency",
                        "period": "distribution",
                        "source": "computed"
                    })
                    
                    # 75th percentile
                    facts.append({
                        "evidence_key": f"{col}_p75",
                        "label": f"{col.replace('_', ' ').title()} - 75th Percentile",
                        "value": float(data.quantile(0.75)),
                        "unit": "currency",
                        "period": "distribution",
                        "source": "computed"
                    })
                    
                    # Interquartile range
                    iqr = data.quantile(0.75) - data.quantile(0.25)
                    facts.append({
                        "evidence_key": f"{col}_iqr",
                        "label": f"{col.replace('_', ' ').title()} - Interquartile Range",
                        "value": float(iqr),
                        "unit": "currency",
                        "period": "distribution",
                        "source": "computed"
                    })
        
        return facts
    
    def _compute_efficiency_metrics(self, panel: pd.DataFrame) -> List[Dict[str, Any]]:
        """Compute efficiency and ratio metrics."""
        facts = []
        
        if panel.empty:
            return facts
        
        # Revenue per employee (if we have employee data)
        if 'revenue_total' in panel.columns and 'labor_total' in panel.columns:
            revenue = panel['revenue_total'].dropna()
            labor = panel['labor_total'].dropna()
            
            # Average revenue per dollar of labor
            if len(revenue) > 0 and len(labor) > 0:
                common_months = revenue.index.intersection(labor.index)
                if len(common_months) > 0:
                    rev_per_labor = (revenue.loc[common_months] / labor.loc[common_months]).mean()
                    facts.append({
                        "evidence_key": "revenue_per_labor_dollar",
                        "label": "Revenue per Labor Dollar",
                        "value": float(rev_per_labor),
                        "unit": "ratio",
                        "period": "average",
                        "source": "computed"
                    })
        
        # Operating margin (if we have expenses)
        if 'revenue_total' in panel.columns:
            revenue = panel['revenue_total'].dropna()
            
            # Calculate total expenses if available
            expense_cols = ['labor_total', 'cogs', 'rent', 'utilities', 'marketing', 'other_expenses']
            available_expenses = [col for col in expense_cols if col in panel.columns]
            
            if available_expenses:
                total_expenses = panel[available_expenses].sum(axis=1)
                common_months = revenue.index.intersection(total_expenses.index)
                
                if len(common_months) > 0:
                    revenue_aligned = revenue.loc[common_months]
                    expenses_aligned = total_expenses.loc[common_months]
                    
                    # Operating margin
                    operating_income = revenue_aligned - expenses_aligned
                    margin = (operating_income / revenue_aligned * 100).mean()
                    
                    facts.append({
                        "evidence_key": "operating_margin",
                        "label": "Average Operating Margin",
                        "value": float(margin),
                        "unit": "percentage",
                        "period": "average",
                        "source": "computed"
                    })
        
        # Labor efficiency (if we have both)
        if 'revenue_total' in panel.columns and 'labor_total' in panel.columns:
            revenue = panel['revenue_total'].dropna()
            labor = panel['labor_total'].dropna()
            common_months = revenue.index.intersection(labor.index)
            
            if len(common_months) >= 3:
                # Labor efficiency trend
                labor_pct = (labor.loc[common_months] / revenue.loc[common_months] * 100)
                
                facts.append({
                    "evidence_key": "labor_efficiency_avg",
                    "label": "Average Labor % of Revenue",
                    "value": float(labor_pct.mean()),
                    "unit": "percentage",
                    "period": "average",
                    "source": "computed"
                })
                
                # Labor efficiency trend
                if len(labor_pct) >= 3:
                    trend = self._linear_regression(labor_pct)
                    if trend is not None:
                        facts.append({
                            "evidence_key": "labor_efficiency_trend",
                            "label": "Labor Efficiency Trend",
                            "value": float(trend),
                            "unit": "monthly_change_pct",
                            "period": f"{len(labor_pct)} months",
                            "source": "computed"
                        })
        
        return facts
    
    def _compute_signals(self, panel: pd.DataFrame) -> List[Dict[str, Any]]:
        """Compute vertical-specific signals."""
        facts = []
        
        if panel.empty:
            return facts
        
        for signal in self.config.signals:
            signal_id = signal['signal_id']
            requires = signal.get('requires', [])
            
            # Check if all required fields exist
            if all(field in panel.columns for field in requires):
                if signal.get('formula') == 'linear_regression':
                    continue  # Already handled in trends
                
                elif signal.get('formula') == 'coefficient_of_variation':
                    continue  # Already handled in volatility
                
                else:
                    # Compute ratio-based signals
                    try:
                        # Parse formula (e.g., "labor_total / revenue_total * 100")
                        formula = signal['formula']
                        
                        # Simple evaluation for ratio formulas
                        for _, row in panel.iterrows():
                            values = {field: row[field] for field in requires}
                            if all(pd.notna(v) and v != 0 for v in values.values()):
                                # Evaluate formula with available values
                                result = eval(formula, {"__builtins__": {}}, values)
                                
                                facts.append({
                                    "evidence_key": signal_id,
                                    "label": signal['label'],
                                    "value": float(result),
                                    "unit": "percentage",
                                    "period": str(row.name),
                                    "source": "computed"
                                })
                                break  # Use most recent valid calculation
                    except Exception:
                        pass
        
        return facts
    
    def _linear_regression(self, series: pd.Series) -> Optional[float]:
        """Compute linear trend (% change per month)."""
        if len(series) < 3:
            return None
        
        x = np.arange(len(series))
        y = series.values
        
        try:
            coeffs = np.polyfit(x, y, 1)
            slope = coeffs[0]
            mean_value = y.mean()
            
            if mean_value == 0:
                return 0.0
            
            # Convert slope to percentage change per month
            pct_change = (slope / mean_value) * 100
            return pct_change
        except Exception:
            return None
