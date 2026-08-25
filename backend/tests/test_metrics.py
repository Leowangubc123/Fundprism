from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.services.metrics import (
    calculate_metrics_for_fund_code,
    compute_inception_return,
    compute_rolling_return,
)


def test_rolling_return_uses_trailing_window():
    values = [Decimal("1.0")] + [Decimal(str(1.0 + i * 0.01)) for i in range(1, 11)]
    # Last 5 values: 1.06, 1.07, 1.08, 1.09, 1.10
    assert float(compute_rolling_return(values, 5)) == pytest.approx(0.037735849, rel=1e-4)


def test_inception_return_uses_full_history():
    values = [Decimal("1.0"), Decimal("1.5"), Decimal("2.0")]
    assert float(compute_inception_return(values)) == pytest.approx(1.0, rel=1e-4)


def test_calculate_metrics_produces_different_1y_3y_inception():
    # Build 1000 days of NAV with a small positive daily return.
    rows = []
    nav = Decimal("1.0")
    base_date = date(2026, 8, 1)
    for i in range(1000):
        d = base_date - timedelta(days=1000 - i - 1)
        nav = nav * Decimal("1.001")
        rows.append((d, nav, Decimal("0.001")))

    return_1y, return_3y, sharpe, max_drawdown = calculate_metrics_for_fund_code(
        type("Perf", (), {"date": r[0], "nav": r[1], "daily_return": r[2]})()
        for r in rows
    )

    assert return_1y is not None
    assert return_3y is not None
    # Inception (full 1000 days) must be larger than 3-year (last 756 days)
    assert return_3y > return_1y
    assert sharpe is not None
    assert max_drawdown is not None
