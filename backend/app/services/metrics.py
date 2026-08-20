from datetime import date, timedelta
from decimal import Decimal
from math import sqrt
from typing import List, Optional, Tuple

from app.config import settings

TRADING_DAYS_PER_YEAR = 252
RISK_FREE_RATE = Decimal(str(getattr(settings, "RISK_FREE_RATE", 0.025)))


def _to_decimal(value) -> Optional[Decimal]:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


def compute_rolling_return(nav_values: List[Decimal], window: int) -> Optional[Decimal]:
    """Compute (latest / first - 1) for a window of NAV values."""
    if len(nav_values) < window or nav_values[0] == 0:
        return None
    return (nav_values[-1] - nav_values[0]) / nav_values[0]


def compute_max_drawdown(nav_values: List[Decimal]) -> Optional[Decimal]:
    """Compute maximum drawdown from a series of NAV values."""
    if len(nav_values) < 2:
        return None
    max_dd = Decimal("0")
    peak = nav_values[0]
    for nav in nav_values[1:]:
        if nav > peak:
            peak = nav
        dd = (nav - peak) / peak
        if dd < max_dd:
            max_dd = dd
    return max_dd


def compute_sharpe(daily_returns: List[Decimal]) -> Optional[Decimal]:
    """Compute annualized Sharpe ratio from daily returns."""
    if len(daily_returns) < 2:
        return None
    n = len(daily_returns)
    mean = sum(daily_returns, Decimal("0")) / n
    variance = sum((r - mean) ** 2 for r in daily_returns) / n
    std = variance.sqrt()
    if std == 0:
        return Decimal("0")
    rf_daily = RISK_FREE_RATE / TRADING_DAYS_PER_YEAR
    return (mean - rf_daily) / std * Decimal(sqrt(TRADING_DAYS_PER_YEAR))


def calculate_metrics_for_rows(rows: List[Tuple[date, Decimal, Optional[Decimal]]]) -> Tuple[Optional[Decimal], Optional[Decimal], Optional[Decimal], Optional[Decimal]]:
    """Given rows of (date, nav, daily_return), return (return_1y, return_3y, sharpe, max_drawdown)."""
    if not rows:
        return None, None, None, None

    sorted_rows = sorted(rows, key=lambda x: x[0])
    nav_values = [r[1] for r in sorted_rows]
    daily_returns = [r[2] for r in sorted_rows if r[2] is not None]

    return_1y = compute_rolling_return(nav_values, TRADING_DAYS_PER_YEAR) if len(nav_values) >= TRADING_DAYS_PER_YEAR else None
    return_3y = compute_rolling_return(nav_values, TRADING_DAYS_PER_YEAR * 3) if len(nav_values) >= TRADING_DAYS_PER_YEAR * 3 else None
    sharpe = compute_sharpe(daily_returns) if len(daily_returns) >= 2 else None
    max_drawdown = compute_max_drawdown(nav_values)

    return return_1y, return_3y, sharpe, max_drawdown


def calculate_metrics_for_fund_code(performances) -> Tuple[Optional[Decimal], Optional[Decimal], Optional[Decimal], Optional[Decimal]]:
    """Helper that accepts a list of FundPerformance objects."""
    rows = [
        (p.date, _to_decimal(p.nav), _to_decimal(p.daily_return))
        for p in performances
        if p.nav is not None
    ]
    return calculate_metrics_for_rows(rows)
