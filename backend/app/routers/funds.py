from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.fund import Fund, FundCode
from app.models.performance import FundPerformance
from app.schemas import FundCompareItem, FundCompareResponse, FundDetail, FundListItem, NavHistoryItem
from app.security import get_current_user

router = APIRouter(prefix="/funds", tags=["funds"])


def _latest_performance_subquery(db: Session):
    return (
        db.query(
            FundPerformance.fund_code_id,
            func.max(FundPerformance.date).label("max_date"),
        )
        .group_by(FundPerformance.fund_code_id)
        .subquery()
    )


@router.get("", response_model=List[FundListItem])
def list_funds(q: str = "", db: Session = Depends(get_db), user=Depends(get_current_user)):
    latest = _latest_performance_subquery(db)
    query = (
        db.query(Fund, FundCode, FundPerformance)
        .join(FundCode, FundCode.fund_id == Fund.id)
        .filter(FundCode.is_primary.is_(True))
        .outerjoin(
            latest,
            latest.c.fund_code_id == FundCode.id,
        )
        .outerjoin(
            FundPerformance,
            (FundPerformance.fund_code_id == FundCode.id)
            & (FundPerformance.date == latest.c.max_date),
        )
    )
    if q:
        query = query.filter(
            (Fund.name.ilike(f"%{q}%")) | (FundCode.code.ilike(f"%{q}%"))
        )
    results = query.order_by(Fund.name).all()
    out = []
    for fund, code, perf in results:
        out.append(
            FundListItem(
                id=fund.id,
                name=fund.name,
                code=code.code,
                category=fund.category,
                nav=float(perf.nav) if perf and perf.nav is not None else None,
                daily_return=float(perf.daily_return) if perf and perf.daily_return is not None else None,
            )
        )
    return out


@router.get("/{fund_id}", response_model=FundDetail)
def get_fund(fund_id: UUID, db: Session = Depends(get_db), user=Depends(get_current_user)):
    latest = _latest_performance_subquery(db)
    row = (
        db.query(Fund, FundCode, FundPerformance)
        .join(FundCode, FundCode.fund_id == Fund.id)
        .filter(FundCode.is_primary.is_(True))
        .filter(Fund.id == fund_id)
        .outerjoin(
            latest,
            latest.c.fund_code_id == FundCode.id,
        )
        .outerjoin(
            FundPerformance,
            (FundPerformance.fund_code_id == FundCode.id)
            & (FundPerformance.date == latest.c.max_date),
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Fund not found")
    fund, code, perf = row
    return FundDetail(
        id=fund.id,
        name=fund.name,
        code=code.code,
        category=fund.category,
        nav=float(perf.nav) if perf and perf.nav is not None else None,
        daily_return=float(perf.daily_return) if perf and perf.daily_return is not None else None,
    )


@router.get("/{fund_id}/nav", response_model=List[NavHistoryItem])
def get_nav_history(fund_id: UUID, db: Session = Depends(get_db), user=Depends(get_current_user)):
    fund = db.query(Fund).filter(Fund.id == fund_id).first()
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")
    primary_code = (
        db.query(FundCode)
        .filter(FundCode.fund_id == fund_id, FundCode.is_primary.is_(True))
        .first()
    )
    if not primary_code:
        return []
    rows = (
        db.query(FundPerformance)
        .filter(FundPerformance.fund_code_id == primary_code.id)
        .order_by(FundPerformance.date)
        .all()
    )
    return [NavHistoryItem(date=r.date, nav=float(r.nav)) for r in rows if r.nav is not None]


@router.get("/compare", response_model=FundCompareResponse)
def compare_funds(
    ids: List[UUID] = Query(default_factory=list),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    if not ids:
        raise HTTPException(status_code=400, detail="至少需要选择一只基金")
    if len(ids) > 5:
        raise HTTPException(status_code=400, detail="最多只能选择 5 只基金进行对比")

    latest = _latest_performance_subquery(db)
    rows = (
        db.query(Fund, FundCode, FundPerformance)
        .join(FundCode, FundCode.fund_id == Fund.id)
        .filter(FundCode.is_primary.is_(True))
        .filter(Fund.id.in_(ids))
        .outerjoin(
            latest,
            latest.c.fund_code_id == FundCode.id,
        )
        .outerjoin(
            FundPerformance,
            (FundPerformance.fund_code_id == FundCode.id)
            & (FundPerformance.date == latest.c.max_date),
        )
        .all()
    )

    result = []
    for fund, code, perf in rows:
        history_rows = (
            db.query(FundPerformance)
            .filter(FundPerformance.fund_code_id == code.id)
            .order_by(FundPerformance.date)
            .limit(90)
            .all()
        )
        nav_history = [
            NavHistoryItem(date=r.date, nav=float(r.nav))
            for r in history_rows
            if r.nav is not None
        ]
        result.append(
            FundCompareItem(
                id=fund.id,
                name=fund.name,
                code=code.code,
                category=fund.category,
                nav=float(perf.nav) if perf and perf.nav is not None else None,
                daily_return=float(perf.daily_return) if perf and perf.daily_return is not None else None,
                manager=fund.manager,
                nav_history=nav_history,
            )
        )

    return {"funds": result}
