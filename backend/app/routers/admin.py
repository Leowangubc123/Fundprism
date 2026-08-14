from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.fund import Fund, FundCode
from app.models.performance import FundPerformance
from app.models.tier import FundCurrentTier
from app.models.user import User
from app.schemas import (
    AdminFundListItem,
    FundCreateRequest,
    FundUpdateRequest,
    SyncResponse,
)
from app.security import get_current_admin
from app.services.tushare_sync import sync_fund_nav

router = APIRouter(prefix="/admin", tags=["admin"])


def _to_float(value) -> Optional[float]:
    return float(value) if value is not None else None


def _build_admin_item(fund: Fund, code: FundCode, perf: Optional[FundPerformance], latest_date) -> AdminFundListItem:
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
        _build_admin_item(fund, code, perf, latest_date)
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
    db.commit()
    db.refresh(fund)
    db.refresh(code)

    return _build_admin_item(fund, code, None, None)


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
    for field, value in update_data.items():
        setattr(fund, field, value)

    db.commit()
    db.refresh(fund)

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
