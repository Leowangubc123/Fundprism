from datetime import date, timedelta
from decimal import Decimal

from app.models.daily_tier_suggestion import DailyTierSuggestion
from app.models.fund import Fund, FundCode
from app.models.performance import FundPerformance
from app.models.tier import FundCurrentTier, FundTierHistory
from app.services.scoring import run_scoring
from app.services.tier_stability import apply_stable_tier_changes


def _add_performances(db, code_id, days=95):
    base_date = date(2026, 8, 1)
    nav = Decimal("1.0")
    for i in range(days):
        d = base_date - timedelta(days=days - 1 - i)
        nav = nav * Decimal("1.0005")
        db.add(
            FundPerformance(
                fund_code_id=code_id,
                date=d,
                nav=nav,
                daily_return=Decimal("0.0005"),
            )
        )
    db.commit()


def test_red_line_abnormal_bypasses_lock(client, admin_headers, db):
    fund = Fund(
        name="红线基金",
        category="主动权益",
        risk_level="高",
        establish_date=date(2020, 1, 1),
        is_abnormal=True,
    )
    db.add(fund)
    db.flush()
    code = FundCode(fund_id=fund.id, code="000010", market="OF", is_primary=True)
    db.add(code)
    db.commit()

    _add_performances(db, code.id)

    tier = FundCurrentTier(
        fund_id=fund.id,
        current_tier="主推",
        manual_lock_until=date(2030, 1, 1),
    )
    db.add(tier)
    db.commit()

    run_scoring(db)
    summary = apply_stable_tier_changes(db)

    assert summary["red_line_downgrades"] == 1
    assert summary["applied"] == 0

    db.refresh(tier)
    assert tier.current_tier == "观察"
    # Manual lock should remain untouched for non-red-line changes.
    assert tier.manual_lock_until == date(2030, 1, 1)

    history = (
        db.query(FundTierHistory)
        .filter(FundTierHistory.fund_id == fund.id)
        .order_by(FundTierHistory.created_at.desc())
        .first()
    )
    assert history is not None
    assert history.new_tier == "观察"
    assert "红线" in history.reason


def test_stable_5_day_applies_tier(client, admin_headers, db):
    fund = Fund(name="稳定基金", category="主动权益", risk_level="中", establish_date=date(2020, 1, 1))
    db.add(fund)
    db.flush()
    code = FundCode(fund_id=fund.id, code="000011", market="OF", is_primary=True)
    db.add(code)
    db.commit()

    tier = FundCurrentTier(fund_id=fund.id, current_tier="观察")
    db.add(tier)
    db.commit()

    today = date(2026, 8, 10)
    for i in range(5):
        db.add(
            DailyTierSuggestion(
                fund_id=fund.id,
                date=today - timedelta(days=i),
                suggested_tier="备选",
                reason="ok",
            )
        )
    db.commit()

    summary = apply_stable_tier_changes(db)
    assert summary["applied"] == 1

    db.refresh(tier)
    assert tier.current_tier == "备选"


def test_active_lock_blocks_stable_change(client, admin_headers, db):
    fund = Fund(name="锁定基金", category="主动权益", risk_level="中", establish_date=date(2020, 1, 1))
    db.add(fund)
    db.flush()
    code = FundCode(fund_id=fund.id, code="000012", market="OF", is_primary=True)
    db.add(code)
    db.commit()

    tier = FundCurrentTier(
        fund_id=fund.id,
        current_tier="观察",
        manual_lock_until=date(2030, 1, 1),
    )
    db.add(tier)
    db.commit()

    today = date(2026, 8, 10)
    for i in range(5):
        db.add(
            DailyTierSuggestion(
                fund_id=fund.id,
                date=today - timedelta(days=i),
                suggested_tier="备选",
                reason="ok",
            )
        )
    db.commit()

    summary = apply_stable_tier_changes(db)
    assert summary["applied"] == 0
    assert summary["locked_skipped"] == 1

    db.refresh(tier)
    assert tier.current_tier == "观察"


def test_fewer_than_5_suggestions_no_change(client, admin_headers, db):
    fund = Fund(name="不足5日基金", category="主动权益", risk_level="中", establish_date=date(2020, 1, 1))
    db.add(fund)
    db.flush()
    code = FundCode(fund_id=fund.id, code="000013", market="OF", is_primary=True)
    db.add(code)
    db.commit()

    tier = FundCurrentTier(fund_id=fund.id, current_tier="观察")
    db.add(tier)
    db.commit()

    today = date(2026, 8, 10)
    for i in range(4):
        db.add(
            DailyTierSuggestion(
                fund_id=fund.id,
                date=today - timedelta(days=i),
                suggested_tier="备选",
                reason="ok",
            )
        )
    db.commit()

    summary = apply_stable_tier_changes(db)
    assert summary["applied"] == 0

    db.refresh(tier)
    assert tier.current_tier == "观察"


def test_scoring_red_line_abnormal(db):
    from app.services.scoring import score_fund

    fund = Fund(name="异常基金", category="主动权益", risk_level="高", is_abnormal=True, establish_date=date(2020, 1, 1))
    db.add(fund)
    db.flush()
    code = FundCode(fund_id=fund.id, code="000014", market="OF", is_primary=True)
    db.add(code)
    db.commit()

    _add_performances(db, code.id)
    performances = db.query(FundPerformance).filter(FundPerformance.fund_code_id == code.id).order_by(FundPerformance.date.asc()).all()

    suggested_tier, score, reason = score_fund(fund, performances, {fund.id: Decimal("0")})
    assert suggested_tier == "观察"
    assert reason == "red_line_abnormal"
    assert score is not None
