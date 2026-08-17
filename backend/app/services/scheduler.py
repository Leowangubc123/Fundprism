from datetime import datetime
from typing import List

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers import SchedulerAlreadyRunningError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models.fund import Fund
from app.models.sync import SyncLog
from app.services.tushare_sync import sync_fund_nav


scheduler: BackgroundScheduler = BackgroundScheduler()


def _now() -> datetime:
    return datetime.utcnow()


def run_daily_sync() -> dict:
    """Run NAV sync for all funds. Returns a summary dict."""
    if not settings.TUSHARE_TOKEN:
        return {"status": "skipped", "total": 0, "successful": 0, "failed": 0, "message": "TUSHARE_TOKEN not configured"}

    db = SessionLocal()
    try:
        funds = db.query(Fund).all()
        total = len(funds)
        successful = 0
        failed = 0
        error_messages: List[str] = []

        batch_log = SyncLog(
            sync_type="daily_sync",
            status="running",
            records_count=0,
            failed_records=0,
        )
        db.add(batch_log)
        db.commit()
        db.refresh(batch_log)

        for fund in funds:
            try:
                result = sync_fund_nav(db, fund.id)
                if result.get("status") == "success":
                    successful += 1
                else:
                    failed += 1
            except Exception as exc:
                failed += 1
                error_messages.append(f"{fund.name}: {exc}")

        batch_log.status = "failed" if failed else "success"
        batch_log.records_count = successful
        batch_log.failed_records = failed
        batch_log.error_message = "\n".join(error_messages) if error_messages else None
        batch_log.ended_at = _now()
        db.commit()

        return {
            "status": batch_log.status,
            "total": total,
            "successful": successful,
            "failed": failed,
            "message": f"Synced {successful}/{total} funds" + (f", {failed} failed" if failed else ""),
        }
    finally:
        db.close()


def start_scheduler() -> None:
    global scheduler
    if scheduler.running:
        return

    hour = getattr(settings, "DAILY_SYNC_HOUR", 2)
    minute = getattr(settings, "DAILY_SYNC_MINUTE", 0)

    try:
        scheduler.add_job(
            run_daily_sync,
            trigger="cron",
            hour=hour,
            minute=minute,
            id="daily_sync",
            replace_existing=True,
        )
        scheduler.start()
    except SchedulerAlreadyRunningError:
        scheduler = BackgroundScheduler()
        scheduler.add_job(
            run_daily_sync,
            trigger="cron",
            hour=hour,
            minute=minute,
            id="daily_sync",
            replace_existing=True,
        )
        scheduler.start()


def shutdown_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown()
