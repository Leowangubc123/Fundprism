from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.daily_tier_suggestion import DailyTierSuggestion
from app.models.fund import Fund
from app.models.tier import FundCurrentTier, FundTierHistory, TIER_OPTIONS


def _record_change(
    db: Session,
    fund_id: UUID,
    tier: FundCurrentTier,
    new_tier: str,
    reason: str,
) -> None:
    """Record an automatic tier change in both FundCurrentTier and FundTierHistory."""
    previous_tier = tier.current_tier
    now = datetime.utcnow()

    tier.current_tier = new_tier
    tier.adjusted_at = now
    tier.adjusted_by_id = None
    tier.adjusted_reason = reason

    history = FundTierHistory(
        fund_id=fund_id,
        operator_id=None,
        previous_tier=previous_tier,
        new_tier=new_tier,
        reason=reason,
        ip_address=None,
    )
    db.add(history)


def apply_stable_tier_changes(db: Session) -> dict:
    """
    Apply automatic tier changes based on red lines and 5-day stable suggestions.

    Rules:
    - Red line funds are immediately downgraded to 观察, bypassing any manual lock.
    - Non-red-line funds with an active manual lock are skipped.
    - Otherwise, if the latest 5 daily suggestions all agree and differ from the
      current tier, update the current tier.
    """
    today = datetime.utcnow().date()
    funds = db.query(Fund).filter(Fund.status == "active").all()

    applied = 0
    red_line_downgrades = 0
    locked_skipped = 0

    for fund in funds:
        tier = (
            db.query(FundCurrentTier)
            .filter(FundCurrentTier.fund_id == fund.id)
            .first()
        )
        if not tier:
            continue

        latest_suggestion = (
            db.query(DailyTierSuggestion)
            .filter(DailyTierSuggestion.fund_id == fund.id)
            .order_by(DailyTierSuggestion.date.desc())
            .first()
        )
        if not latest_suggestion:
            continue

        # Red line: immediate downgrade, bypass lock.
        if latest_suggestion.reason and latest_suggestion.reason.startswith("red_line_"):
            if tier.current_tier != "观察":
                _record_change(
                    db,
                    fund.id,
                    tier,
                    "观察",
                    f"触发降级红线：{latest_suggestion.reason}",
                )
                red_line_downgrades += 1
            continue

        # Active manual lock prevents automatic non-red-line changes.
        if tier.manual_lock_until and tier.manual_lock_until >= today:
            locked_skipped += 1
            continue

        # Require 5 consecutive daily suggestions with the same tier.
        recent = (
            db.query(DailyTierSuggestion)
            .filter(DailyTierSuggestion.fund_id == fund.id)
            .order_by(DailyTierSuggestion.date.desc())
            .limit(5)
            .all()
        )
        if len(recent) < 5:
            continue

        target_tier = recent[0].suggested_tier
        if target_tier not in TIER_OPTIONS:
            continue

        if all(s.suggested_tier == target_tier for s in recent) and target_tier != tier.current_tier:
            _record_change(
                db,
                fund.id,
                tier,
                target_tier,
                "连续 5 个交易日系统建议等级一致，自动生效",
            )
            applied += 1

    db.commit()
    return {
        "applied": applied,
        "red_line_downgrades": red_line_downgrades,
        "locked_skipped": locked_skipped,
    }
