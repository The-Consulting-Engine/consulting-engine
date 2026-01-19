"""Column profiling for uploaded CSV files."""
import pandas as pd
import numpy as np
from typing import Dict, List, Any
from pathlib import Path


class ColumnProfiler:
    """Profile CSV columns to understand data structure."""
    
    def profile_file(self, file_path: str) -> Dict[str, Any]:
        """
        Profile a CSV file and return column metadata.
        
        Returns:
            {
                "row_count": int,
                "columns": {
                    "col_name": {
                        "inferred_type": str,
                        "null_pct": float,
                        "samples": list,
                        "unique_count": int,
                        "stats": dict (for numeric)
                    }
                }
            }
        """
        df = pd.read_csv(file_path)
        
        profile = {
            "row_count": len(df),
            "columns": {}
        }
        
        for col in df.columns:
            profile["columns"][col] = self._profile_column(df[col])
        
        return profile
    
    def _profile_column(self, series: pd.Series) -> Dict[str, Any]:
        """Profile a single column."""
        col_profile = {
            "inferred_type": self._infer_type(series),
            "null_pct": (series.isna().sum() / len(series) * 100) if len(series) > 0 else 0,
            "unique_count": series.nunique(),
            "samples": self._get_samples(series, n=5)
        }
        
        # Add stats for numeric columns
        if col_profile["inferred_type"] == "numeric":
            numeric_series = pd.to_numeric(series, errors='coerce')
            col_profile["stats"] = {
                "min": float(numeric_series.min()) if not numeric_series.isna().all() else None,
                "max": float(numeric_series.max()) if not numeric_series.isna().all() else None,
                "mean": float(numeric_series.mean()) if not numeric_series.isna().all() else None,
                "median": float(numeric_series.median()) if not numeric_series.isna().all() else None
            }
        
        return col_profile
    
    def _infer_type(self, series: pd.Series) -> str:
        """Infer column type: numeric, date, or text."""
        # Remove nulls for type detection
        non_null = series.dropna()
        if len(non_null) == 0:
            return "text"
        
        # Try numeric
        try:
            pd.to_numeric(non_null, errors='raise')
            return "numeric"
        except (ValueError, TypeError):
            pass
        
        # Try date
        try:
            pd.to_datetime(non_null, errors='raise')
            return "date"
        except (ValueError, TypeError):
            pass
        
        return "text"
    
    def _get_samples(self, series: pd.Series, n: int = 5) -> List[Any]:
        """Get sample values from column."""
        non_null = series.dropna()
        if len(non_null) == 0:
            return []
        
        # Get unique samples up to n
        samples = non_null.unique()[:n].tolist()
        
        # Convert to serializable types
        return [self._make_serializable(x) for x in samples]
    
    def _make_serializable(self, value: Any) -> Any:
        """Convert value to JSON-serializable type."""
        if pd.isna(value):
            return None
        if isinstance(value, (np.integer, np.floating)):
            return float(value)
        if isinstance(value, np.bool_):
            return bool(value)
        if isinstance(value, (pd.Timestamp, np.datetime64)):
            return str(value)
        return str(value)
