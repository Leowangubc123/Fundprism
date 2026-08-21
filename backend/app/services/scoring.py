from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from app.config import settings
from app.constants import (
    BOND_CATEGORIES,
    CATEGORY_ALIASES,
    CATEGORY_SET,
    EQUITY_CATEGORIES,
    NON_RATED_CATEGORIES,
    normalize_category,
)
from app.models.daily_tier_suggestion import DailyTierSuggestion
from app.models.fund import Fund, FundCode
from app.models.performance import FundPerformance
from app.models.tier import FundCurrentTier
from app.services.metrics import calculate_metrics_for_fund_code

TRADING_DAYS_PER_YEAR = 252
MIN_HISTORY_DAYS = 90

EQUITY_WEIGHTS = {
    "rank": Decimal("0.30"),
    "rank_3y": Decimal("0.10"),
    "sharpe": Decimal("0.15"),
    "max_drawdown": Decimal("0.15"),
    "return_1y": Decimal("0.10"),
    "scale": Decimal("0.10"),
    "manager": Decimal("0.10"),
}

BOND_WEIGHTS = {
    "return_1y": Decimal("0.25"),
    "max_drawdown": Decimal("0.30"),
    "sharpe": Decimal("0.20"),
    "rank": Decimal("0.15"),
    "scale": Decimal("0.10"),
}

MAX_DD_BOUNDS = {
    "主动权益": Decimal("0.30"),
    "指增": Decimal("0.25"),
    "QDII": Decimal("0.35"),
    "固收+": Decimal("0.08"),
    "固收": Decimal("0.03"),
}

SCALE_BOUNDS = {
    "主动权益": (Decimal("5"), Decimal("100")),
    "指增": (Decimal("3"), Decimal("50")),
    "被动指数": (Decimal("5"), None),
    "固收+": (Decimal("5"), Decimal("200")),
    "固收": (Decimal("10"), Decimal("500")),
    "QDII": (Decimal("3"), Decimal("100")),
}


def _to_float(value) -> Optional[float]:
    return float(value) if value is not None else None


def _score_rank_percentile(percentile: Optional[Decimal]) -> Optional[Decimal]:
    if percentile is None:
        return None
    p = max(Decimal("0"), min(Decimal("1"), percentile))
    return (Decimal("1") - p) * Decimal("100")


def _score_sharpe(sharpe: Optional[Decimal]) -> Optional[Decimal]:
    if sharpe is None:
        return None
    if sharpe < 0:
        return Decimal("0")
    if sharpe >= 2:
        return Decimal("100")
    return sharpe / Decimal("2") * Decimal("100")


def _score_max_drawdown(max_drawdown: Optional[Decimal], category: str) -> Optional[Decimal]:
    if max_drawdown is None:
        return None
    bound = MAX_DD_BOUNDS.get(category, Decimal("0.30"))
    dd = abs(max_drawdown)
    if dd <= 0:
        return Decimal("100")
    if dd >= bound:
        return Decimal("0")
    return (Decimal("1") - dd / bound) * Decimal("100")


def _score_manager_tenure(tenure: Optional[Decimal]) -> Optional[Decimal]:
    if tenure is None:
        return None
    if tenure >= 3:
        return Decimal("100")
    if tenure >= 1:
        return Decimal("70")
    return Decimal("40")


def _score_scale(aum: Optional[Decimal], category: str) -> Optional[Decimal]:
    if aum is None:
        return None
    lower, upper = SCALE_BOUNDS.get(category, (Decimal("5"), Decimal("100")))
    if upper is None:
        return Decimal("100") if aum >= lower else Decimal("0")
    if aum >= lower and aum <= upper:
        return Decimal("100")
    if aum < lower * Decimal("0.5"):
        return Decimal("0")
    if aum > upper * Decimal("2"):
        return Decimal("60")
    if aum < lower:
        return (aum - lower * Decimal("0.5")) / (lower * Decimal("0.5")) * Decimal("100")
    return (Decimal("100") - (aum - upper) / upper * Decimal("40"))


def _annualized_return(performances: List[FundPerformance]) -> Optional[Decimal]:
    """Annualized return from available NAV history, requiring at least MIN_HISTORY_DAYS."""
    if len(performances) < 2:
        return None
    first = performances[0]
    last = performances[-1]
    if first.nav is None or last.nav is None or first.nav == 0:
        return None
    days = (last.date - first.date).days
    if days < MIN_HISTORY_DAYS:
        return None
    total_return = (last.nav - first.nav) / first.nav
    return (Decimal("1") + total_return) ** (Decimal("365") / Decimal(days)) - Decimal("1")


def _effective_return(perf: Optional[FundPerformance], performances: List[FundPerformance]) -> Optional[Decimal]:
    if perf is not None and perf.return_1y is not None:
        return perf.return_1y
    return _annualized_return(performances)


def _fallback_sharpe(performances: List[FundPerformance]) -> Optional[Decimal]:
    perf = performances[-1] if performances else None
    if perf is not None and perf.sharpe is not None:
        return perf.sharpe
    _, _, sharpe, _ = calculate_metrics_for_fund_code(performances)
    return sharpe


def _fallback_max_drawdown(performances: List[FundPerformance]) -> Optional[Decimal]:
    perf = performances[-1] if performances else None
    if perf is not None and perf.max_drawdown is not None:
        return perf.max_drawdown
    _, _, _, max_dd = calculate_metrics_for_fund_code(performances)
    return max_dd


def _compute_category_percentiles(funds: List[Fund], metric_getter) -> Dict[UUID, Decimal]:
    """Compute percentile (0=best, 1=worst) for each fund within its category."""
    by_category: Dict[str, List[Tuple[Fund, Decimal]]] = {}
    for fund in funds:
        value = metric_getter(fund)
        if value is None:
            continue
        by_category.setdefault(fund.category, []).append((fund, value))

    percentiles: Dict[UUID, Decimal] = {}
    for category, items in by_category.items():
        items.sort(key=lambda x: x[1], reverse=True)
        n = len(items)
        for rank, (fund, _) in enumerate(items, start=1):
            if n == 1:
                percentiles[fund.id] = Decimal("0")
            else:
                percentiles[fund.id] = Decimal(str((rank - 1) / (n - 1)))
    return percentiles


def score_fund(
    fund: Fund,
    performances: List[FundPerformance],
    category_percentiles: Dict[UUID, Decimal],
) -> Tuple[Optional[str], Optional[Decimal], str]:
    """Return (suggested_tier, score, reason) for a single fund."""
    category = normalize_category(fund.category)
    if category is None:
        return None, None, "unknown_category"
    if category in NON_RATED_CATEGORIES:
        return None, None, "non_rated"

    establish_cutoff = datetime.utcnow().date() - timedelta(days=180)
    if fund.establish_date and fund.establish_date > establish_cutoff:
        return None, None, "too_new"

    if not performances:
        return None, None, "no_data"

    perf = performances[-1]
    effective_return = _effective_return(perf, performances)
    if effective_return is None:
        return None, None, "insufficient_metrics"

    # Require a minimum history length to avoid rating funds with just a few days of data.
    first_date = performances[0].date
    last_date = perf.date
    if (last_date - first_date).days < MIN_HISTORY_DAYS:
        return None, None, "history_too_short"

    weights = EQUITY_WEIGHTS if category in EQUITY_CATEGORIES else BOND_WEIGHTS

    scores: Dict[str, Decimal] = {}

    # Rank percentile: prefer Tushare value, fall back to within-category percentile on return.
    rank_percentile = perf.rank_percentile
    if rank_percentile is None and fund.id in category_percentiles:
        rank_percentile = category_percentiles[fund.id]
    s_rank = _score_rank_percentile(rank_percentile)
    if s_rank is not None:
        scores["rank"] = s_rank

    s_sharpe = _score_sharpe(_fallback_sharpe(performances))
    if s_sharpe is not None:
        scores["sharpe"] = s_sharpe

    s_dd = _score_max_drawdown(_fallback_max_drawdown(performances), category)
    if s_dd is not None:
        scores["max_drawdown"] = s_dd

    # Return 1y percentile within category (uses annualized return as fallback).
    return_percentile = category_percentiles.get(fund.id)
    s_return = _score_rank_percentile(return_percentile)
    if s_return is not None:
        scores["return_1y"] = s_return

    s_scale = _score_scale(perf.aum, category)
    if s_scale is not None:
        scores["scale"] = s_scale

    s_manager = _score_manager_tenure(fund.manager_tenure)
    if s_manager is not None:
        scores["manager"] = s_manager

    if not scores:
        return None, None, "insufficient_metrics"

    total_weight = sum(weights[key] for key in scores)
    if total_weight == 0:
        return None, None, "insufficient_metrics"

    composite = sum(scores[key] * weights[key] for key in scores) / total_weight

    # Red line: AUM below 0.5亿 -> 观察
    if perf.aum is not None and perf.aum < Decimal("0.5"):
        return "观察", composite, "red_line_aum"

    if composite >= Decimal("80"):
        tier = "主推"
    elif composite >= Decimal("65"):
        tier = "备选"
    elif composite >= Decimal("45"):
        tier = "替代"
    else:
        tier = "观察"

    return tier, composite, "ok"


def run_scoring(db: Session, fund_id: Optional[UUID] = None) -> Dict:
    """Run scoring for all funds or a single fund. Returns summary."""
    today = datetime.utcnow().date()

    query = db.query(Fund).filter(Fund.status == "active")
    if fund_id:
        query = query.filter(Fund.id == fund_id)
    funds = query.all()

    # Pre-fetch primary codes and full performance history per fund.
    performances_by_fund: Dict[UUID, List[FundPerformance]] = {}
    effective_return_by_fund: Dict[UUID, Decimal] = {}

    for fund in funds:
        primary_code = (
            db.query(FundCode)
            .filter(FundCode.fund_id == fund.id, FundCode.is_primary.is_(True))
            .first()
        )
        if not primary_code:
            continue
        performances = (
            db.query(FundPerformance)
            .filter(FundPerformance.fund_code_id == primary_code.id)
            .order_by(FundPerformance.date.asc())
            .all()
        )
        if performances:
            performances_by_fund[fund.id] = performances
            effective_return = _effective_return(performances[-1], performances)
            if effective_return is not None:
                effective_return_by_fund[fund.id] = effective_return

    category_percentiles = _compute_category_percentiles(
        [f for f in funds if f.id in effective_return_by_fund],
        lambda f: effective_return_by_fund.get(f.id),
    )

    scored = 0
    skipped = 0
    for fund in funds:
        performances = performances_by_fund.get(fund.id, [])
        suggested_tier, score, reason = score_fund(fund, performances, category_percentiles)

        tier = db.query(FundCurrentTier).filter(FundCurrentTier.fund_id == fund.id).first()
        if not tier:
            tier = FundCurrentTier(fund_id=fund.id)
            db.add(tier)
            db.flush()

        if suggested_tier is not None:
            tier.suggested_tier = suggested_tier
            tier.suggested_at = datetime.utcnow()
            scored += 1
        else:
            skipped += 1

        existing = (
            db.query(DailyTierSuggestion)
            .filter(DailyTierSuggestion.fund_id == fund.id, DailyTierSuggestion.date == today)
            .first()
        )
        suggestion_tier = suggested_tier or tier.current_tier or "观察"
        if existing:
            existing.suggested_tier = suggestion_tier
            existing.score = score
            existing.reason = reason
        else:
            db.add(
                DailyTierSuggestion(
                    fund_id=fund.id,
                    date=today,
                    suggested_tier=suggestion_tier,
                    score=score,
                    reason=reason,
                )
            )

    db.commit()
    return {"scored": scored, "skipped": skipped, "date": today.isoformat()}
