"""Generic normalization engine for transforming data to monthly panels."""
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple
from datetime import datetime
import calendar


class NormalizationEngine:
    """Transform raw data into normalized monthly facts."""
    
    def normalize(
        self,
        df: pd.DataFrame,
        mappings: List[Dict[str, Any]],
        pack_type: str
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Normalize data based on mappings.
        
        Args:
            df: Raw dataframe
            mappings: List of confirmed mappings
            pack_type: PNL, REVENUE, or LABOR
        
        Returns:
            (normalized_df, metadata)
            metadata includes: warnings, completeness_score, preview_rows
        """
        warnings = []
        normalized = pd.DataFrame()
        
        # Apply each mapping
        for mapping in mappings:
            canonical_field = mapping["canonical_field"]
            source_cols = mapping["source_columns"]
            transform = mapping["transform"]
            
            try:
                normalized[canonical_field] = self._apply_transform(
                    df, source_cols, transform
                )
            except Exception as e:
                warnings.append(f"Failed to map {canonical_field}: {str(e)}")
        
        # Pack-specific normalization
        if pack_type == "PNL":
            normalized, pack_warnings = self._normalize_pnl(normalized)
            warnings.extend(pack_warnings)
        elif pack_type == "REVENUE":
            normalized, pack_warnings = self._normalize_revenue(normalized)
            warnings.extend(pack_warnings)
        elif pack_type == "LABOR":
            normalized, pack_warnings = self._normalize_labor(normalized)
            warnings.extend(pack_warnings)
        
        # Calculate completeness
        completeness = self._calculate_completeness(normalized)
        
        # Get preview
        preview = normalized.head(10).to_dict('records')
        
        metadata = {
            "warnings": warnings,
            "completeness_score": completeness,
            "preview_rows": preview,
            "row_count": len(normalized)
        }
        
        return normalized, metadata
    
    def _apply_transform(
        self,
        df: pd.DataFrame,
        source_cols: List[str],
        transform: str
    ) -> pd.Series:
        """Apply transformation to source columns."""
        if transform == "to_number":
            return pd.to_numeric(df[source_cols[0]], errors='coerce')
        
        elif transform == "parse_date":
            return pd.to_datetime(df[source_cols[0]], errors='coerce')
        
        elif transform == "parse_month":
            dates = pd.to_datetime(df[source_cols[0]], errors='coerce')
            return dates.dt.to_period('M').astype(str)
        
        elif transform == "sum_columns":
            result = df[source_cols[0]].fillna(0)
            for col in source_cols[1:]:
                result = result + df[col].fillna(0)
            return result
        
        elif transform == "coalesce_columns":
            result = df[source_cols[0]].copy()
            for col in source_cols[1:]:
                result = result.fillna(df[col])
            return result
        
        elif transform == "infer_month_from_date":
            dates = pd.to_datetime(df[source_cols[0]], errors='coerce')
            return dates.dt.to_period('M').astype(str)
        
        else:  # "none" or unknown
            return df[source_cols[0]]
    
    def _normalize_pnl(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
        """Normalize P&L data to monthly format."""
        warnings = []
        
        # Ensure month is in standard format
        if 'month' in df.columns:
            try:
                df['month'] = pd.to_datetime(df['month']).dt.to_period('M').astype(str)
            except Exception as e:
                warnings.append(f"Could not parse month column: {e}")
        
        # P&L is already monthly, so just validate
        required_fields = ['month', 'revenue_total']
        for field in required_fields:
            if field not in df.columns or df[field].isna().all():
                warnings.append(f"Missing or empty required field: {field}")
        
        return df, warnings
    
    def _normalize_revenue(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
        """Normalize revenue transactions to monthly aggregates."""
        warnings = []
        
        if 'transaction_date' not in df.columns:
            warnings.append("Missing transaction_date, cannot aggregate")
            return df, warnings
        
        # Convert to datetime
        df['transaction_date'] = pd.to_datetime(df['transaction_date'], errors='coerce')
        df['month'] = df['transaction_date'].dt.to_period('M').astype(str)
        
        # Aggregate by month
        agg_dict = {}
        if 'amount' in df.columns:
            agg_dict['amount'] = 'sum'
        if 'discount' in df.columns:
            agg_dict['discount'] = 'sum'
        if 'transaction_count' in df.columns:
            agg_dict['transaction_count'] = 'sum'
        
        if not agg_dict:
            warnings.append("No numeric fields to aggregate")
            return df, warnings
        
        monthly = df.groupby('month').agg(agg_dict).reset_index()
        
        # Rename to canonical
        if 'amount' in monthly.columns:
            monthly['revenue_total'] = monthly['amount']
        
        return monthly, warnings
    
    def _normalize_labor(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
        """Normalize labor data to monthly allocation."""
        warnings = []
        
        required = ['pay_period_start', 'pay_period_end', 'total_pay']
        for field in required:
            if field not in df.columns:
                warnings.append(f"Missing required field: {field}")
                return df, warnings
        
        # Convert dates
        df['pay_period_start'] = pd.to_datetime(df['pay_period_start'], errors='coerce')
        df['pay_period_end'] = pd.to_datetime(df['pay_period_end'], errors='coerce')
        
        # Prorate pay across months
        monthly_records = []
        for _, row in df.iterrows():
            if pd.isna(row['pay_period_start']) or pd.isna(row['pay_period_end']):
                continue
            
            start = row['pay_period_start']
            end = row['pay_period_end']
            total_pay = row['total_pay']
            
            # Get months covered
            months = pd.period_range(start.to_period('M'), end.to_period('M'), freq='M')
            
            # Prorate based on days in each month
            total_days = (end - start).days + 1
            for month in months:
                month_start = max(start, datetime(month.year, month.month, 1))
                month_end = min(end, datetime(month.year, month.month, calendar.monthrange(month.year, month.month)[1]))
                month_days = (month_end - month_start).days + 1
                
                prorated_pay = total_pay * (month_days / total_days)
                
                monthly_records.append({
                    'month': str(month),
                    'labor_total': prorated_pay
                })
        
        if not monthly_records:
            warnings.append("Could not prorate any pay periods to months")
            return df, warnings
        
        # Aggregate by month
        monthly = pd.DataFrame(monthly_records)
        monthly = monthly.groupby('month').agg({'labor_total': 'sum'}).reset_index()
        
        return monthly, warnings
    
    def _calculate_completeness(self, df: pd.DataFrame) -> float:
        """Calculate data completeness score (0-1)."""
        if df.empty:
            return 0.0
        
        # Calculate non-null percentage across all cells
        total_cells = df.size
        non_null_cells = df.count().sum()
        
        return non_null_cells / total_cells if total_cells > 0 else 0.0
