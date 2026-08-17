from decimal import Decimal
from typing import List, Optional, Union
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, aliased, joinedload

from app.database import get_db
from app.models.fund import Fund, FundCode
from app.models.performance import FundPerformance
from app.models.tag import FundTag, Tag
from app.models.tier import FundCurrentTier
from app.models.user import User
from app.schemas import (
    FundCompareItem,
    FundCompareResponse,
    FundDetail,
    FundListItem,
    NavHistoryItem,
    TagSummary,
)
from app.security import get_current_user

router = APIRouter(prefix="/funds", tags=["funds"])

COMPARE_HISTORY_DAYS = 90


def _to_float(value: Optional[Union[int, float, Decimal]]) -> Optional[float]:
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


def _latest_performance_subquery(db: Session):
    return (
        db.query(
            FundPerformance.fund_code_id,
            func.max(FundPerformance.date).label("max_date"),
        )
        .group_by(FundPerformance.fund_code_id)
        .subquery()
    )


def _base_fund_query(db: Session):
    latest = _latest_performance_subquery(db)
    return (
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


@router.get("", response_model=List[FundListItem])
def list_funds(
    q: str = "",
    tag: str = "",
    tier: str = "",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = _base_fund_query(db)
    if q:
        query = query.filter(
            (Fund.name.ilike(f"%{q}%")) | (FundCode.code.ilike(f"%{q}%"))
        )
    if tag:
        # tag can be a tag id or tag name; filter funds that have this active tag.
        tag_obj = db.query(Tag).filter(Tag.is_active.is_(True)).filter(
            (Tag.id == tag) | (Tag.name == tag)
        ).first()
        if tag_obj:
            fund_ids = (
                db.query(FundTag.fund_id)
                .filter(FundTag.tag_id == tag_obj.id)
                .subquery()
            )
            query = query.filter(Fund.id.in_(fund_ids))
    if tier:
        query = query.join(
            FundCurrentTier, FundCurrentTier.fund_id == Fund.id
        ).filter(FundCurrentTier.current_tier == tier)
    results = query.order_by(Fund.name).all()
    out = []
    for fund, code, perf in results:
        out.append(
            FundListItem(
                id=fund.id,
                name=fund.name,
                code=code.code,
                category=fund.category,
                nav=_to_float(perf.nav) if perf else None,
                daily_return=_to_float(perf.daily_return) if perf else None,
                current_tier=fund.tier.current_tier if fund.tier else None,
                tags=_tag_summaries(db, fund.id),
            )
        )
    return out


@router.get("/compare", response_model=FundCompareResponse)
def compare_funds(
    ids: str = Query(default=""),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    parsed_ids = []
    if ids:
        for id_str in ids.split(","):
            id_str = id_str.strip()
            if not id_str:
                continue
            try:
                parsed_ids.append(UUID(id_str))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid fund ID")

    if not parsed_ids:
        raise HTTPException(status_code=400, detail="At least one fund is required")
    if len(parsed_ids) > 5:
        raise HTTPException(status_code=400, detail="Up to 5 funds can be compared")
    if len(parsed_ids) != len(set(parsed_ids)):
        raise HTTPException(status_code=400, detail="Duplicate fund IDs are not allowed")

    rows = _base_fund_query(db).filter(Fund.id.in_(parsed_ids)).all()

    found_ids = {fund.id for fund, _, _ in rows}
    missing_ids = set(parsed_ids) - found_ids
    if missing_ids:
        raise HTTPException(status_code=404, detail="One or more funds not found")

    fund_by_id = {}
    code_by_id = {}
    perf_by_id = {}
    for fund, code, perf in rows:
        fund_by_id[fund.id] = fund
        code_by_id[fund.id] = code
        perf_by_id[fund.id] = perf

    code_ids = [code.id for code in code_by_id.values()]
    ranked = (
        db.query(
            FundPerformance,
            func.row_number()
            .over(
                partition_by=FundPerformance.fund_code_id,
                order_by=FundPerformance.date.desc(),
            )
            .label("rn"),
        )
        .filter(FundPerformance.fund_code_id.in_(code_ids))
        .subquery()
    )
    fund_performance_alias = aliased(FundPerformance, ranked)
    history_rows = (
        db.query(fund_performance_alias)
        .filter(ranked.c.rn <= COMPARE_HISTORY_DAYS)
        .order_by(fund_performance_alias.fund_code_id, fund_performance_alias.date)
        .all()
    )

    history_by_code = {}
    for row in history_rows:
        history_by_code.setdefault(row.fund_code_id, []).append(row)

    result = []
    for fund_id in parsed_ids:
        fund = fund_by_id[fund_id]
        code = code_by_id[fund_id]
        perf = perf_by_id[fund_id]
        nav_history = [
            NavHistoryItem(date=r.date, nav=float(r.nav))
            for r in history_by_code.get(code.id, [])
            if r.nav is not None
        ]
        result.append(
            FundCompareItem(
                id=fund.id,
                name=fund.name,
                code=code.code,
                category=fund.category,
                nav=_to_float(perf.nav) if perf else None,
                daily_return=_to_float(perf.daily_return) if perf else None,
                current_tier=fund.tier.current_tier if fund.tier else None,
                manager=fund.manager,
                nav_history=nav_history,
                tags=_tag_summaries(db, fund.id),
            )
        )

    return {"funds": result}


@router.get("/{fund_id}", response_model=FundDetail)
def get_fund(
    fund_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = _base_fund_query(db).filter(Fund.id == fund_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Fund not found")
    fund, code, perf = row
    return FundDetail(
        id=fund.id,
        name=fund.name,
        code=code.code,
        category=fund.category,
        nav=_to_float(perf.nav) if perf else None,
        daily_return=_to_float(perf.daily_return) if perf else None,
        current_tier=fund.tier.current_tier if fund.tier else None,
        tags=_tag_summaries(db, fund.id),
    )


@router.get("/{fund_id}/nav", response_model=List[NavHistoryItem])
def get_nav_history(
    fund_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
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
