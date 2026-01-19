"""Tests for normalization engine."""
import pytest
import pandas as pd
from datetime import datetime
from app.normalization.engine import NormalizationEngine


def test_to_number_transform():
    """Test numeric transformation."""
    engine = NormalizationEngine()
    
    df = pd.DataFrame({
        'value': ['100', '200.50', '300']
    })
    
    result = engine._apply_transform(df, ['value'], 'to_number')
    
    assert result.dtype in [float, 'float64']
    assert result[0] == 100.0
    assert result[1] == 200.5


def test_parse_date_transform():
    """Test date parsing."""
    engine = NormalizationEngine()
    
    df = pd.DataFrame({
        'date': ['2024-01-15', '2024-02-20', '2024-03-10']
    })
    
    result = engine._apply_transform(df, ['date'], 'parse_date')
    
    assert pd.api.types.is_datetime64_any_dtype(result)


def test_sum_columns_transform():
    """Test column summation."""
    engine = NormalizationEngine()
    
    df = pd.DataFrame({
        'col1': [10, 20, 30],
        'col2': [5, 10, 15]
    })
    
    result = engine._apply_transform(df, ['col1', 'col2'], 'sum_columns')
    
    assert result[0] == 15
    assert result[1] == 30
    assert result[2] == 45


def test_normalize_pnl():
    """Test P&L normalization."""
    engine = NormalizationEngine()
    
    df = pd.DataFrame({
        'month': ['2024-01', '2024-02', '2024-03'],
        'revenue_total': [100000, 110000, 105000]
    })
    
    normalized, warnings = engine._normalize_pnl(df)
    
    assert not normalized.empty
    assert 'month' in normalized.columns


def test_normalize_labor_proration():
    """Test labor cost proration across months."""
    engine = NormalizationEngine()
    
    df = pd.DataFrame({
        'pay_period_start': ['2024-01-01', '2024-01-16'],
        'pay_period_end': ['2024-01-15', '2024-01-31'],
        'total_pay': [10000, 10000]
    })
    
    normalized, warnings = engine._normalize_labor(df)
    
    assert not normalized.empty
    assert 'month' in normalized.columns
    assert 'labor_total' in normalized.columns
    
    # Both periods in January should aggregate
    assert normalized['labor_total'].sum() == 20000
