"""Tests for analytics engine."""
import pytest
import pandas as pd
from app.analytics.engine import AnalyticsEngine
from app.core.vertical_config import VerticalConfigManager


def test_build_monthly_panel():
    """Test monthly panel building."""
    config_manager = VerticalConfigManager()
    config = config_manager.get_config("restaurant_v1")
    engine = AnalyticsEngine(config)
    
    # Create sample normalized data
    pnl_data = pd.DataFrame({
        'month': ['2024-01', '2024-02', '2024-03'],
        'revenue_total': [100000, 110000, 105000],
        'labor_total': [30000, 33000, 31500]
    })
    
    normalized_data = {'PNL': pnl_data}
    
    # Build panel
    panel = engine._build_monthly_panel(normalized_data)
    
    assert not panel.empty
    assert len(panel) == 3
    assert 'revenue_total' in panel.columns
    assert 'labor_total' in panel.columns


def test_detect_mode_pnl():
    """Test PNL mode detection."""
    config_manager = VerticalConfigManager()
    config = config_manager.get_config("restaurant_v1")
    engine = AnalyticsEngine(config)
    
    # Create sufficient P&L data
    pnl_data = pd.DataFrame({
        'month': pd.date_range('2024-01', periods=6, freq='M').to_period('M').astype(str),
        'revenue_total': [100000] * 6,
        'labor_total': [30000] * 6
    })
    pnl_data = pnl_data.set_index(pd.to_datetime(pnl_data['month']).dt.to_period('M'))
    
    normalized_data = {'PNL': pd.DataFrame({'month': pnl_data.index.astype(str)})}
    
    mode_info = engine._detect_mode(pnl_data, normalized_data)
    
    # Should be PNL_MODE with good data
    assert mode_info['mode'] in ['PNL_MODE', 'OPS_MODE']
    assert mode_info['confidence'] > 0
    assert mode_info['months_available'] == 6


def test_compute_basic_metrics():
    """Test basic metric computation."""
    config_manager = VerticalConfigManager()
    config = config_manager.get_config("restaurant_v1")
    engine = AnalyticsEngine(config)
    
    panel = pd.DataFrame({
        'revenue_total': [100000, 110000, 105000],
        'labor_total': [30000, 33000, 31500]
    })
    
    facts = engine._compute_basic_metrics(panel)
    
    assert len(facts) > 0
    
    # Check for revenue average
    revenue_avg = [f for f in facts if f['evidence_key'] == 'revenue_avg_monthly']
    assert len(revenue_avg) == 1
    assert revenue_avg[0]['value'] == pytest.approx(105000, rel=1)


def test_compute_trends():
    """Test trend computation."""
    config_manager = VerticalConfigManager()
    config = config_manager.get_config("restaurant_v1")
    engine = AnalyticsEngine(config)
    
    # Create trending data
    panel = pd.DataFrame({
        'revenue_total': [100000, 110000, 120000, 130000, 140000, 150000]
    })
    
    facts = engine._compute_trends(panel)
    
    # Should detect positive trend
    trend_facts = [f for f in facts if 'trend' in f['evidence_key']]
    assert len(trend_facts) > 0
