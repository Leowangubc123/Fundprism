from datetime import date, datetime, timedelta
from typing import List, Optional
import re
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.fund import Fund, FundCode
from app.models.performance import FundPerformance
from app.models.tag import FundTag, Tag
from app.models.tier import FundCurrentTier, FundTierHistory, TIER_OPTIONS
from app.models.user import User
from app.schemas import (
    AdminFundListItem,
    FundBasicLookupResponse,
    FundCreateRequest,
    FundUpdateRequest,
    Market,
    SyncResponse,
    TagSummary,
    TierInfo,
    TierUpdateRequest,
)
from app.security import get_current_admin
from app.services.tushare_sync import lookup_fund_basic, sync_fund_nav

router = APIRouter(prefix="/admin", tags=["admin"])


_CODE_RE = re.compile(r"^\d{6}$")


def _to_float(value) -> Optional[float]:
    return float(value) if value is not None else None


def _tag_summaries(db: Session, fund_id: UUID) -> List[TagSummary]:
    tags = (
        db.query(Tag)
        .join(FundTag, FundTag.tag_id == Tag.id)
        .filter(FundTag.fund_id == fund_id, Tag.is_active.is_(True))
        .order_by(Tag.category, Tag.sort_order, Tag.name)
        .all()
    )
    return [TagSummary(id=t.id, name=t.name, category=t.category) for t in tags]


def _apply_tag_ids(db: Session, fund: Fund, tag_ids: Optional[List[UUID]]) -> None:
    if tag_ids is None:
        return
    db.query(FundTag).filter(FundTag.fund_id == fund.id).delete(synchronize_session=False)
    if tag_ids:
        valid_tags = (
            db.query(Tag)
            .filter(Tag.id.in_(tag_ids), Tag.is_active.is_(True))
            .all()
        )
        valid_ids = {t.id for t in valid_tags}
        if len(valid_ids) != len(set(tag_ids)):
            raise HTTPException(status_code=400, detail="One or more tags are invalid or inactive")
        for tag_id in tag_ids:
            db.add(FundTag(fund_id=fund.id, tag_id=tag_id))


def _build_admin_item(fund: Fund, code: FundCode, perf: Optional[FundPerformance], latest_date, tags: List[TagSummary]) -> AdminFundListItem:
    return AdminFundListItem(
        id=fund.id,
        name=fund.name,
        code=code.code,
        market=code.market,
        category=fund.category,
        risk_level=fund.risk_level,
        manager=fund.manager,
        nav=_to_float(perf.nav) if perf else None,
        daily_return=_to_float(perf.daily_return) if perf else None,
        latest_nav_date=latest_date,
        current_tier=fund.tier.current_tier if fund.tier else None,
        tags=tags,
    )


@router.get("/funds", response_model=List[AdminFundListItem])
def list_funds(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    latest_perf = (
        db.query(
            FundPerformance.fund_code_id,
            func.max(FundPerformance.date).label("latest_date"),
        )
        .group_by(FundPerformance.fund_code_id)
        .subquery()
    )

    results = (
        db.query(Fund, FundCode, FundPerformance, latest_perf.c.latest_date)
        .join(FundCode, FundCode.fund_id == Fund.id)
        .filter(FundCode.is_primary.is_(True))
        .outerjoin(
            latest_perf,
            latest_perf.c.fund_code_id == FundCode.id,
        )
        .outerjoin(
            FundPerformance,
            (FundPerformance.fund_code_id == FundCode.id)
            & (FundPerformance.date == latest_perf.c.latest_date),
        )
        .order_by(Fund.name)
        .all()
    )

    return [
        _build_admin_item(fund, code, perf, latest_date, _tag_summaries(db, fund.id))
        for fund, code, perf, latest_date in results
    ]


@router.post("/funds", response_model=AdminFundListItem, status_code=status.HTTP_201_CREATED)
def create_fund(
    payload: FundCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    existing_code = db.query(FundCode).filter(FundCode.code == payload.code).first()
    if existing_code:
        raise HTTPException(status_code=409, detail="Fund code already exists")

    fund = Fund(
        name=payload.name,
        category=payload.category,
        risk_level=payload.risk_level,
        manager=payload.manager,
        establish_date=payload.establish_date,
        reason=payload.reason,
        target_clients=payload.target_clients,
    )
    db.add(fund)
    db.flush()

    code = FundCode(
        fund_id=fund.id,
        code=payload.code,
        market=payload.market.value,
        is_primary=True,
    )
    tier = FundCurrentTier(fund_id=fund.id)
    db.add_all([code, tier])

    _apply_tag_ids(db, fund, payload.tag_ids)

    db.commit()
    db.refresh(fund)
    db.refresh(code)

    return _build_admin_item(fund, code, None, None, _tag_summaries(db, fund.id))


@router.get("/funds/lookup", response_model=FundBasicLookupResponse)
def lookup_fund(
    code: str,
    market: Market,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    if not _CODE_RE.match(code):
        raise HTTPException(status_code=400, detail="Invalid fund code")
    result = lookup_fund_basic(code, market.value)
    return FundBasicLookupResponse(
        ts_code=result.get("ts_code") or f"{code}.{market.value}",
        name=result.get("name") or "",
        manager=result.get("management"),
        category=result.get("fund_type"),
        establish_date=result.get("found_date"),
        market=market.value,
    )


@router.get("/funds/{fund_id}", response_model=AdminFundListItem)
def get_fund(
    fund_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    fund = db.query(Fund).filter(Fund.id == fund_id).first()
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")

    code = (
        db.query(FundCode)
        .filter(FundCode.fund_id == fund_id, FundCode.is_primary.is_(True))
        .first()
    )
    latest_perf = (
        db.query(FundPerformance)
        .filter(FundPerformance.fund_code_id == code.id)
        .order_by(FundPerformance.date.desc())
        .first()
    ) if code else None

    return _build_admin_item(
        fund,
        code,
        latest_perf,
        latest_perf.date if latest_perf else None,
        _tag_summaries(db, fund.id),
    )


@router.put("/funds/{fund_id}", response_model=AdminFundListItem)
def update_fund(
    fund_id: UUID,
    payload: FundUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    fund = db.query(Fund).filter(Fund.id == fund_id).first()
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")

    update_data = payload.model_dump(exclude_unset=True)
    tag_ids = update_data.pop("tag_ids", None)
    for field, value in update_data.items():
        setattr(fund, field, value)

    db.commit()
    db.refresh(fund)

    _apply_tag_ids(db, fund, tag_ids)
    db.commit()

    code = (
        db.query(FundCode)
        .filter(FundCode.fund_id == fund_id, FundCode.is_primary.is_(True))
        .first()
    )
    latest_perf = (
        db.query(FundPerformance)
        .filter(FundPerformance.fund_code_id == code.id)
        .order_by(FundPerformance.date.desc())
        .first()
    ) if code else None

    return _build_admin_item(
        fund,
        code,
        latest_perf,
        latest_perf.date if latest_perf else None,
        _tag_summaries(db, fund.id),
    )


@router.delete("/funds/{fund_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_fund(
    fund_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    fund = db.query(Fund).filter(Fund.id == fund_id).first()
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")

    db.delete(fund)
    db.commit()
    return None


@router.post("/funds/{fund_id}/sync", response_model=SyncResponse)
def sync_fund(
    fund_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    result = sync_fund_nav(db, fund_id)
    return SyncResponse(**result)


def _tier_info(tier: FundCurrentTier) -> TierInfo:
    return TierInfo(
        fund_id=tier.fund_id,
        current_tier=tier.current_tier,
        suggested_tier=tier.suggested_tier,
        suggested_at=tier.suggested_at,
        adjusted_at=tier.adjusted_at,
        adjusted_by=tier.adjusted_by.username if tier.adjusted_by else None,
        adjusted_reason=tier.adjusted_reason,
        manual_lock_until=tier.manual_lock_until,
    )


@router.get("/funds/{fund_id}/tier", response_model=TierInfo)
def get_fund_tier(
    fund_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    fund = db.query(Fund).filter(Fund.id == fund_id).first()
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")

    tier = db.query(FundCurrentTier).filter(FundCurrentTier.fund_id == fund_id).first()
    if not tier:
        tier = FundCurrentTier(fund_id=fund_id)
        db.add(tier)
        db.commit()
        db.refresh(tier)

    return _tier_info(tier)


@router.put("/funds/{fund_id}/tier", response_model=TierInfo)
def update_fund_tier(
    fund_id: UUID,
    payload: TierUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    fund = db.query(Fund).filter(Fund.id == fund_id).first()
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")

    if payload.current_tier not in TIER_OPTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid tier. Allowed: {', '.join(TIER_OPTIONS)}",
        )

    tier = db.query(FundCurrentTier).filter(FundCurrentTier.fund_id == fund_id).first()
    if not tier:
        tier = FundCurrentTier(fund_id=fund_id)
        db.add(tier)
        db.flush()

    previous_tier = tier.current_tier
    now = datetime.utcnow()
    tier.current_tier = payload.current_tier
    tier.adjusted_at = now
    tier.adjusted_by_id = user.id
    tier.adjusted_reason = payload.reason
    tier.manual_lock_until = (now + timedelta(days=30)).date()

    history = FundTierHistory(
        fund_id=fund_id,
        operator_id=user.id,
        previous_tier=previous_tier,
        new_tier=payload.current_tier,
        reason=payload.reason,
        ip_address=request.client.host if request.client else None,
    )
    db.add(history)

    db.commit()
    db.refresh(tier)

    return _tier_info(tier)


@router.post("/funds/{fund_id}/tier/clear-lock", response_model=TierInfo)
def clear_fund_tier_lock(
    fund_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    fund = db.query(Fund).filter(Fund.id == fund_id).first()
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")

    tier = db.query(FundCurrentTier).filter(FundCurrentTier.fund_id == fund_id).first()
    if not tier:
        tier = FundCurrentTier(fund_id=fund_id)
        db.add(tier)
        db.flush()

    previous_tier = tier.current_tier
    now = datetime.utcnow()
    reason = "取消手动锁定，恢复自动评级"

    if tier.suggested_tier:
        tier.current_tier = tier.suggested_tier

    tier.adjusted_at = now
    tier.adjusted_by_id = user.id
    tier.adjusted_reason = reason
    tier.manual_lock_until = None

    history = FundTierHistory(
        fund_id=fund_id,
        operator_id=user.id,
        previous_tier=previous_tier,
        new_tier=tier.current_tier,
        reason=reason,
        ip_address=request.client.host if request.client else None,
    )
    db.add(history)

    db.commit()
    db.refresh(tier)

    return _tier_info(tier)
