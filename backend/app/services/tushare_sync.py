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


# Tushare fund_share returns fd_share in 万份 (10,000 shares)
SHARE_UNIT = Decimal("10000")
# Fetch ~3 years + buffer on first sync so 3-year metrics can be computed
INITIAL_SYNC_DAYS = 1100


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


def _parse_share(row) -> Optional[Decimal]:
    for key in ("fd_share", "fd_share_total", "share", "fund_share", "shares", "total_share"):
        value = row.get(key)
        if value is not None:
            try:
                return Decimal(str(value))
            except Exception:
                continue
    return None


def _looks_like_company_name(name: Optional[str]) -> bool:
    if not name:
        return False
    keywords = ("公司", "有限责任", "股份", "资管", "基金", "投资", "资产", "证券", "信托")
    return any(keyword in name for keyword in keywords)


def _get_start_date(db: Session, fund_code_id: UUID) -> date:
    latest = (
        db.query(FundPerformance)
        .filter(FundPerformance.fund_code_id == fund_code_id)
        .order_by(FundPerformance.date.desc())
        .first()
    )
    if latest and latest.date:
        return latest.date + timedelta(days=1)
    # Initial sync: fetch enough history for 3-year metrics.
    return datetime.utcnow().date() - timedelta(days=INITIAL_SYNC_DAYS)


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
    extra_messages = [
        _update_fund_aum(db, primary_code),
        _update_rank_percentile(db, fund_id),
        _update_fund_manager(db, fund_id),
    ]

    total = records_created + records_updated
    sync_log.status = "success"
    sync_log.records_count = total
    sync_log.ended_at = datetime.utcnow()
    db.commit()

    message = f"Created {records_created}, updated {records_updated} NAV records"
    for m in extra_messages:
        if m:
            message += f"; {m}"

    return {
        "fund_id": fund_id,
        "status": "success",
        "records_count": total,
        "message": message,
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


def _update_fund_aum(db: Session, primary_code: FundCode) -> Optional[str]:
    """Fetch latest fund share and estimate AUM = share * latest NAV."""
    if not settings.TUSHARE_TOKEN:
        return "AUM skipped: no TUSHARE_TOKEN"

    ts_code = f"{primary_code.code}.{primary_code.market}"
    try:
        pro = ts.pro_api(settings.TUSHARE_TOKEN)
        df = pro.fund_share(ts_code=ts_code)
    except Exception as exc:
        return f"AUM failed: {exc}"

    if df is None or df.empty:
        return "AUM skipped: no share data"

    date_col = None
    for candidate in ("trade_date", "end_date", "nav_date", "date"):
        if candidate in df.columns:
            date_col = candidate
            break
    if date_col is None:
        return f"AUM skipped: no date column (have {list(df.columns)})"

    df = df.sort_values(by=date_col, ascending=False).reset_index(drop=True)
    latest_row = df.iloc[0]
    share_date = _parse_date(latest_row[date_col])
    share = _parse_share(latest_row)
    if share is None:
        return f"AUM skipped: no share column (have {list(df.columns)})"

    # Use latest NAV on or before the share report date.
    query = (
        db.query(FundPerformance)
        .filter(
            FundPerformance.fund_code_id == primary_code.id,
            FundPerformance.nav.isnot(None),
        )
        .order_by(FundPerformance.date.desc())
    )
    if share_date:
        query = query.filter(FundPerformance.date <= share_date)
    latest_perf = query.first()

    if not latest_perf:
        # Fallback to the most recent NAV regardless of date.
        latest_perf = (
            db.query(FundPerformance)
            .filter(FundPerformance.fund_code_id == primary_code.id)
            .order_by(FundPerformance.date.desc())
            .first()
        )

    if latest_perf and latest_perf.nav:
        # fd_share is in 万份; convert to shares then multiply by NAV.
        latest_perf.aum = share * SHARE_UNIT * latest_perf.nav
        db.commit()
        return "AUM updated"

    return "AUM skipped: no NAV to pair with share"


def _update_rank_percentile(db: Session, fund_id: UUID) -> Optional[str]:
    """Compute 1-year return percentile within the same category."""
    fund = db.query(Fund).filter(Fund.id == fund_id).first()
    if not fund or not fund.category:
        return "rank skipped: no category"

    primary_code = (
        db.query(FundCode)
        .filter(FundCode.fund_id == fund_id, FundCode.is_primary.is_(True))
        .first()
    )
    if not primary_code:
        return "rank skipped: no primary code"

    latest_perf = (
        db.query(FundPerformance)
        .filter(FundPerformance.fund_code_id == primary_code.id)
        .order_by(FundPerformance.date.desc())
        .first()
    )
    if not latest_perf or latest_perf.return_1y is None:
        return "rank skipped: no 1-year return"

    peer_rows = (
        db.query(FundPerformance.return_1y)
        .join(FundCode, FundPerformance.fund_code_id == FundCode.id)
        .join(Fund, FundCode.fund_id == Fund.id)
        .filter(Fund.category == fund.category)
        .filter(Fund.id != fund.id)
        .filter(FundPerformance.return_1y.isnot(None))
        .all()
    )
    values = [float(r.return_1y) for r in peer_rows]
    if len(values) < 1:
        return "rank skipped: no peers"

    target = float(latest_perf.return_1y)
    lower_count = sum(1 for v in values if v < target)
    percentile = Decimal(str(lower_count / len(values)))
    latest_perf.rank_percentile = percentile
    db.commit()
    return f"rank percentile {float(percentile):.0%}"


def _update_fund_manager(db: Session, fund_id: UUID) -> Optional[str]:
    """Fetch current fund manager from Tushare and update Fund fields."""
    fund = db.query(Fund).filter(Fund.id == fund_id).first()
    if not fund:
        return "manager skipped: fund not found"

    primary_code = (
        db.query(FundCode)
        .filter(FundCode.fund_id == fund_id, FundCode.is_primary.is_(True))
        .first()
    )
    if not primary_code:
        return "manager skipped: no primary code"

    ts_code = f"{primary_code.code}.{primary_code.market}"
    try:
        pro = ts.pro_api(settings.TUSHARE_TOKEN)
        df = pro.fund_manager(ts_code=ts_code)
    except Exception as exc:
        return f"manager failed: {exc}"

    if df is None or df.empty:
        return "manager skipped: no manager data"

    name_col = next((c for c in df.columns if c in ("name", "manager_name")), None)
    begin_col = "begin_date" if "begin_date" in df.columns else None
    end_col = "end_date" if "end_date" in df.columns else None
    if not name_col:
        return f"manager skipped: no name column (have {list(df.columns)})"

    # Prefer rows with no end_date (current managers).
    current_rows = []
    for _, row in df.iterrows():
        end_val = row.get(end_col) if end_col else None
        if end_val is None or str(end_val).strip() == "":
            current_rows.append(row)

    if not current_rows:
        # Fall back to the most recent manager by begin_date.
        if begin_col and begin_col in df.columns:
            df = df.sort_values(by=begin_col, ascending=False).reset_index(drop=True)
        current_rows = [df.iloc[0]]

    selected = current_rows[0]
    manager_name = _str(selected.get(name_col))
    begin_date = _parse_date(selected.get(begin_col)) if begin_col else None

    if not manager_name:
        return "manager skipped: empty manager name"

    updated = []
    if not fund.manager or _looks_like_company_name(fund.manager):
        fund.manager = manager_name
        updated.append("manager")
    if begin_date and not fund.manager_start_date:
        fund.manager_start_date = begin_date
        updated.append("manager_start_date")
    db.commit()

    if updated:
        return f"manager updated: {', '.join(updated)}"
    return "manager unchanged"


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
