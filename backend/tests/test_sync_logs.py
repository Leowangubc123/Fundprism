from app.models.fund import Fund
from app.models.sync import SyncLog


def test_list_sync_logs_requires_admin(client, auth_headers):
    response = client.get("/api/admin/sync-logs", headers=auth_headers)
    assert response.status_code == 403


def test_list_sync_logs(client, admin_headers, db):
    fund = Fund(name="日志基金", category="主动权益", risk_level="中")
    db.add(fund)
    db.commit()

    log = SyncLog(
        sync_type="fund_nav",
        status="success",
        records_count=5,
        failed_records=0,
        fund_id=fund.id,
    )
    db.add(log)
    db.commit()

    response = client.get("/api/admin/sync-logs", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["sync_type"] == "fund_nav"
    assert data[0]["records_count"] == 5
    assert data[0]["fund_name"] == "日志基金"


def test_trigger_daily_sync_without_token(client, admin_headers):
    response = client.post("/api/admin/sync/run", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "skipped"
    assert data["total"] == 0
