from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from app.config import settings
from app.models.fund import Fund, FundCode
from app.models.performance import FundPerformance
from app.models.tier import FundCurrentTier, TIER_OPTIONS
from app.models.daily_tier_suggestion import DailyTierSuggestion

TRADING_DAYS_PER_YEAR = 252

NON_RATED_CATEGORIES = {"被动指数", "其他"}

EQUITY_CATEGORIES = {"主动权益", "指增", "QDII"}
BOND_CATEGORIES = {"固收+", "固收"}

# Weights from PRD section 7.3
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

# Max drawdown upper bounds by category (as positive numbers)
MAX_DD_BOUNDS = {
    "主动权益": Decimal("0.30"),
    "指增": Decimal("0.25"),
    "QDII": Decimal("0.35"),
    "固收+": Decimal("0.08"),
    "固收": Decimal("0.03"),
}

# Scale fit bounds (in 亿元)
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
    # percentile is 0-1 (0 = best). Score 100*(1-percentile)
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


def _score_return_percentile(percentile: Optional[Decimal]) -> Optional[Decimal]:
    # Use same logic as rank percentile: higher return = smaller percentile = better
    return _score_rank_percentile(percentile)


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
        # Passive index: no upper bound, above lower = 100
        return Decimal("100") if aum >= lower else Decimal("0")
    if aum >= lower and aum <= upper:
        return Decimal("100")
    if aum < lower * Decimal("0.5"):
        return Decimal("0")
    if aum > upper * Decimal("2"):
        return Decimal("60")
    if aum < lower:
        # linear from 0 at lower*0.5 to 100 at lower
        return (aum - lower * Decimal("0.5")) / (lower * Decimal("0.5")) * Decimal("100")
    # aum > upper: linear from 100 at upper to 60 at upper*2
    return (Decimal("100") - (aum - upper) / upper * Decimal("40"))


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
        # Sort descending by metric: best first
        items.sort(key=lambda x: x[1], reverse=True)
        n = len(items)
        for rank, (fund, _) in enumerate(items, start=1):
            if n == 1:
                percentiles[fund.id] = Decimal("0")
            else:
                # percentile 0 = rank 1, percentile 1 = rank n
                percentiles[fund.id] = Decimal(str((rank - 1) / (n - 1)))
    return percentiles


def _latest_performance(db: Session, fund_code_id: UUID) -> Optional[FundPerformance]:
    return (
        db.query(FundPerformance)
        .filter(FundPerformance.fund_code_id == fund_code_id)
        .order_by(FundPerformance.date.desc())
        .first()
    )


def score_fund(fund: Fund, perf: FundPerformance, category_percentiles: Dict[UUID, Decimal]) -> Tuple[Optional[str], Optional[Decimal], str]:
    """Return (suggested_tier, score, reason) for a single fund."""
    if fund.category in NON_RATED_CATEGORIES:
        return None, None, "non_rated"

    establish_cutoff = (datetime.utcnow().date() - timedelta(days=180))
    if fund.establish_date and fund.establish_date > establish_cutoff:
        return None, None, "too_new"

    if perf is None:
        return None, None, "no_data"

    weights = EQUITY_WEIGHTS if fund.category in EQUITY_CATEGORIES else BOND_WEIGHTS

    scores: Dict[str, Decimal] = {}

    # Rank percentile: prefer Tushare value, fall back to within-category percentile
    rank_percentile = perf.rank_percentile
    if rank_percentile is None and fund.id in category_percentiles:
        rank_percentile = category_percentiles[fund.id]
    s_rank = _score_rank_percentile(rank_percentile)
    if s_rank is not None:
        scores["rank"] = s_rank

    # 3-year rank: not available in MVP; skip
    s_rank_3y = None
    if s_rank_3y is not None:
        scores["rank_3y"] = s_rank_3y

    s_sharpe = _score_sharpe(perf.sharpe)
    if s_sharpe is not None:
        scores["sharpe"] = s_sharpe

    s_dd = _score_max_drawdown(perf.max_drawdown, fund.category)
    if s_dd is not None:
        scores["max_drawdown"] = s_dd

    # Return 1y percentile within category
    return_1y_percentile = category_percentiles.get(fund.id)
    s_return = _score_return_percentile(return_1y_percentile)
    if s_return is not None:
        scores["return_1y"] = s_return

    s_scale = _score_scale(perf.aum, fund.category)
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

    # Determine tier by score percentile within category
    # For simplicity use absolute composite thresholds
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

    # Pre-compute within-category percentiles based on return_1y
    perf_by_fund: Dict[UUID, FundPerformance] = {}
    return_1y_by_fund: Dict[UUID, Decimal] = {}
    for fund in funds:
        primary_code = (
            db.query(FundCode)
            .filter(FundCode.fund_id == fund.id, FundCode.is_primary.is_(True))
            .first()
        )
        if not primary_code:
            continue
        perf = _latest_performance(db, primary_code.id)
        if perf:
            perf_by_fund[fund.id] = perf
            if perf.return_1y is not None:
                return_1y_by_fund[fund.id] = perf.return_1y

    category_percentiles = _compute_category_percentiles(
        [f for f in funds if f.id in return_1y_by_fund],
        lambda f: return_1y_by_fund.get(f.id),
    )

    scored = 0
    skipped = 0
    for fund in funds:
        perf = perf_by_fund.get(fund.id)
        suggested_tier, score, reason = score_fund(fund, perf, category_percentiles)

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

        # Upsert daily suggestion
        existing = (
            db.query(DailyTierSuggestion)
            .filter(DailyTierSuggestion.fund_id == fund.id, DailyTierSuggestion.date == today)
            .first()
        )
        if existing:
            existing.suggested_tier = suggested_tier or tier.current_tier
            existing.score = score
            existing.reason = reason
        else:
            db.add(
                DailyTierSuggestion(
                    fund_id=fund.id,
                    date=today,
                    suggested_tier=suggested_tier or tier.current_tier,
                    score=score,
                    reason=reason,
                )
            )

    db.commit()
    return {"scored": scored, "skipped": skipped, "date": today.isoformat()}
