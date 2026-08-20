from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional
from uuid import UUID

import tushare as ts
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.models.fund import Fund, FundCode
from app.models.performance import FundPerformance
from app.models.sync import SyncLog
from app.services.metrics import calculate_metrics_for_fund_code


def _str(value) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip()
    return s if s else None


def _today_str() -> str:
    return datetime.utcnow().strftime("%Y%m%d")


def _date_str(d: date) -> str:
    return d.strftime("%Y%m%d")


def _parse_date(value) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    # Tushare returns YYYYMMDD strings or pandas Timestamp
    s = str(value).replace("-", "").split(" ")[0]
    if len(s) >= 8 and s.isdigit():
        return date(int(s[:4]), int(s[4:6]), int(s[6:8]))
    return None


def _parse_nav(row) -> Optional[Decimal]:
    for key in ("unit_nav", "nav", "adj_nav"):
        value = row.get(key)
        if value is not None:
            try:
                return Decimal(str(value))
            except Exception:
                continue
    return None


def _get_start_date(db: Session, fund_code_id: UUID) -> date:
    latest = (
        db.query(FundPerformance)
        .filter(FundPerformance.fund_code_id == fund_code_id)
        .order_by(FundPerformance.date.desc())
        .first()
    )
    if latest and latest.date:
        return latest.date + timedelta(days=1)
    return datetime.utcnow().date() - timedelta(days=365)


def sync_fund_nav(db: Session, fund_id: UUID) -> dict:
    if not settings.TUSHARE_TOKEN:
        raise HTTPException(status_code=400, detail="TUSHARE_TOKEN not configured")

    fund = db.query(Fund).filter(Fund.id == fund_id).first()
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")

    primary_code = (
        db.query(FundCode)
        .filter(FundCode.fund_id == fund_id, FundCode.is_primary.is_(True))
        .first()
    )
    if not primary_code:
        raise HTTPException(status_code=400, detail="Fund has no primary code")

    ts_code = f"{primary_code.code}.{primary_code.market}"
    start_date = _get_start_date(db, primary_code.id)
    end_date = datetime.utcnow().date()

    sync_log = SyncLog(
        sync_type="fund_nav",
        status="running",
        records_count=0,
        fund_id=fund_id,
    )
    db.add(sync_log)
    db.commit()
    db.refresh(sync_log)

    try:
        pro = ts.pro_api(settings.TUSHARE_TOKEN)
        df = pro.fund_nav(
            ts_code=ts_code,
            start_date=_date_str(start_date),
            end_date=_date_str(end_date),
        )
    except Exception as exc:
        sync_log.status = "failed"
        sync_log.error_message = str(exc)
        sync_log.ended_at = datetime.utcnow()
        db.commit()
        raise HTTPException(status_code=502, detail=f"Tushare request failed: {exc}")

    if df is None or df.empty:
        sync_log.status = "success"
        sync_log.ended_at = datetime.utcnow()
        db.commit()
        return {
            "fund_id": fund_id,
            "status": "success",
            "records_count": 0,
            "message": "No new NAV data from Tushare",
        }

    # Sort ascending by date so daily_return can be computed from previous row
    date_col = None
    for candidate in ("end_date", "nav_date", "trade_date", "date"):
        if candidate in df.columns:
            date_col = candidate
            break
    if date_col is None:
        sync_log.status = "failed"
        sync_log.error_message = "No date column in Tushare response"
        sync_log.ended_at = datetime.utcnow()
        db.commit()
        raise HTTPException(status_code=502, detail="No date column in Tushare response")

    df = df.sort_values(by=date_col, ascending=True).reset_index(drop=True)

    existing = {
        (r.fund_code_id, r.date): r
        for r in db.query(FundPerformance).filter(
            FundPerformance.fund_code_id == primary_code.id
        ).all()
    }

    records_created = 0
    records_updated = 0
    prev_nav: Optional[Decimal] = None

    for _, row in df.iterrows():
        nav_date = _parse_date(row[date_col])
        nav = _parse_nav(row)
        if nav_date is None or nav is None:
            continue

        daily_return = None
        if prev_nav is not None and prev_nav != 0:
            daily_return = (nav - prev_nav) / prev_nav
        prev_nav = nav

        key = (primary_code.id, nav_date)
        perf = existing.get(key)
        if perf:
            perf.nav = nav
            if daily_return is not None:
                perf.daily_return = daily_return
            records_updated += 1
        else:
            perf = FundPerformance(
                fund_code_id=primary_code.id,
                date=nav_date,
                nav=nav,
                daily_return=daily_return,
            )
            db.add(perf)
            records_created += 1
            existing[key] = perf

    db.commit()

    _update_fund_metrics(db, primary_code.id)

    total = records_created + records_updated
    sync_log.status = "success"
    sync_log.records_count = total
    sync_log.ended_at = datetime.utcnow()
    db.commit()

    return {
        "fund_id": fund_id,
        "status": "success",
        "records_count": total,
        "message": f"Created {records_created}, updated {records_updated} NAV records",
    }


def _update_fund_metrics(db: Session, fund_code_id: UUID) -> None:
    performances = (
        db.query(FundPerformance)
        .filter(FundPerformance.fund_code_id == fund_code_id)
        .order_by(FundPerformance.date.asc())
        .all()
    )
    if not performances:
        return

    return_1y, return_3y, sharpe, max_drawdown = calculate_metrics_for_fund_code(performances)
    latest = performances[-1]
    latest.return_1y = return_1y
    latest.return_3y = return_3y
    latest.sharpe = sharpe
    latest.max_drawdown = max_drawdown
    db.commit()


def lookup_fund_basic(code: str, market: str) -> dict:
    if not settings.TUSHARE_TOKEN:
        raise HTTPException(status_code=400, detail="TUSHARE_TOKEN not configured")

    ts_code = f"{code}.{market}"
    try:
        pro = ts.pro_api(settings.TUSHARE_TOKEN)
        df = pro.fund_basic(ts_code=ts_code)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Tushare request failed: {exc}")

    if df is None or df.empty:
        raise HTTPException(status_code=404, detail="Fund not found in Tushare")

    row = df.iloc[0]
    return {
        "ts_code": _str(row.get("ts_code")),
        "name": _str(row.get("name")),
        "management": _str(row.get("management")),
        "fund_type": _str(row.get("fund_type")),
        "found_date": _parse_date(row.get("found_date")),
        "market": _str(row.get("market")),
    }
