from datetime import date, timedelta
from decimal import Decimal

from app.models.daily_tier_suggestion import DailyTierSuggestion
from app.models.fund import Fund, FundCode
from app.models.performance import FundPerformance
from app.models.tier import FundCurrentTier
from app.services.metrics import calculate_metrics_for_fund_code


def _add_perf(db, code_id, d, nav, daily_return):
    db.add(FundPerformance(fund_code_id=code_id, date=d, nav=nav, daily_return=daily_return))
    db.commit()


def _update_metrics(db, code_id):
    perfs = db.query(FundPerformance).filter(FundPerformance.fund_code_id == code_id).order_by(FundPerformance.date.asc()).all()
    return_1y, return_3y, sharpe, max_drawdown = calculate_metrics_for_fund_code(perfs)
    latest = perfs[-1]
    latest.return_1y = return_1y
    latest.return_3y = return_3y
    latest.sharpe = sharpe
    latest.max_drawdown = max_drawdown
    db.commit()


def test_run_scoring_endpoint(client, admin_headers, db):
    fund = Fund(name="评分基金", category="主动权益", risk_level="高")
    db.add(fund)
    db.flush()
    code = FundCode(fund_id=fund.id, code="000010", market="OF", is_primary=True)
    db.add(code)
    db.commit()

    # Add 252 days of NAV with positive daily returns
    base_date = date(2026, 8, 1)
    nav = Decimal("1.0")
    for i in range(252):
        d = base_date - timedelta(days=252 - i)
        nav = nav * Decimal("1.0005")
        _add_perf(db, code.id, d, nav, Decimal("0.0005"))

    _update_metrics(db, code.id)

    response = client.post("/api/admin/scoring/run", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["scored"] >= 1

    tier = db.query(FundCurrentTier).filter(FundCurrentTier.fund_id == fund.id).first()
    assert tier is not None
    assert tier.suggested_tier is not None

    suggestion = (
        db.query(DailyTierSuggestion)
        .filter(DailyTierSuggestion.fund_id == fund.id)
        .first()
    )
    assert suggestion is not None
    assert suggestion.score is not None
