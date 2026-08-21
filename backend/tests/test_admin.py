from datetime import date
from unittest.mock import Mock, patch
from uuid import uuid4

import pandas as pd
import pytest

from app.models.fund import Fund, FundCode
from app.models.performance import FundPerformance
from app.models.sync import SyncLog
from app.models.tier import FundCurrentTier, FundTierHistory


def test_list_funds_requires_admin(client, auth_headers):
    response = client.get("/api/admin/funds", headers=auth_headers)
    assert response.status_code == 403


def test_create_fund(client, admin_headers, db):
    payload = {
        "name": "测试基金",
        "code": "123456",
        "market": "OF",
        "category": "主动权益",
        "risk_level": "中",
        "manager": "测试经理",
    }
    response = client.post("/api/admin/funds", json=payload, headers=admin_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "测试基金"
    assert data["code"] == "123456"
    assert data["market"] == "OF"

    fund = db.query(Fund).filter(Fund.name == "测试基金").first()
    assert fund is not None
    code = db.query(FundCode).filter(FundCode.fund_id == fund.id).first()
    assert code.is_primary is True
    assert code.market == "OF"
    tier = db.query(FundCurrentTier).filter(FundCurrentTier.fund_id == fund.id).first()
    assert tier is not None
    assert tier.current_tier == "观察"


def test_create_fund_duplicate_code(client, admin_headers, db):
    fund = Fund(name="已有基金", category="主动权益", risk_level="高")
    db.add(fund)
    db.flush()
    db.add(FundCode(fund_id=fund.id, code="000001", market="OF", is_primary=True))
    db.commit()

    payload = {
        "name": "重复代码基金",
        "code": "000001",
        "market": "OF",
        "category": "主动权益",
        "risk_level": "中",
    }
    response = client.post("/api/admin/funds", json=payload, headers=admin_headers)
    assert response.status_code == 409


def test_update_fund(client, admin_headers, db):
    fund = Fund(name="旧名字", category="主动权益", risk_level="中")
    db.add(fund)
    db.flush()
    db.add(FundCode(fund_id=fund.id, code="000002", market="OF", is_primary=True))
    db.commit()

    response = client.put(
        f"/api/admin/funds/{fund.id}",
        json={"name": "新名字"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == "新名字"


def test_delete_fund(client, admin_headers, db):
    fund = Fund(name="待删除", category="主动权益", risk_level="中")
    db.add(fund)
    db.flush()
    db.add(FundCode(fund_id=fund.id, code="000003", market="OF", is_primary=True))
    db.commit()

    response = client.delete(f"/api/admin/funds/{fund.id}", headers=admin_headers)
    assert response.status_code == 204
    assert db.query(Fund).filter(Fund.id == fund.id).first() is None


def test_sync_fund_creates_performances(client, admin_headers, db, monkeypatch):
    fund = Fund(name="同步基金", category="主动权益", risk_level="中")
    db.add(fund)
    db.flush()
    db.add(FundCode(fund_id=fund.id, code="000004", market="OF", is_primary=True))
    db.commit()

    monkeypatch.setattr("app.services.tushare_sync.settings.TUSHARE_TOKEN", "test-token")

    mock_df = pd.DataFrame({
        "end_date": ["20260801", "20260802", "20260803"],
        "unit_nav": ["1.1000", "1.1100", "1.1050"],
    })

    mock_pro = Mock()
    mock_pro.fund_nav.return_value = mock_df

    with patch("app.services.tushare_sync.ts.pro_api", return_value=mock_pro):
        response = client.post(f"/api/admin/funds/{fund.id}/sync", headers=admin_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["records_count"] == 3

    perfs = db.query(FundPerformance).join(FundCode).filter(FundCode.fund_id == fund.id).all()
    assert len(perfs) == 3

    sync_log = db.query(SyncLog).filter(SyncLog.sync_type == "fund_nav").first()
    assert sync_log is not None
    assert sync_log.status == "success"
    assert sync_log.records_count == 3


def test_sync_fund_requires_token(client, admin_headers, db):
    fund = Fund(name="无Token基金", category="主动权益", risk_level="中")
    db.add(fund)
    db.flush()
    db.add(FundCode(fund_id=fund.id, code="000005", market="OF", is_primary=True))
    db.commit()

    response = client.post(f"/api/admin/funds/{fund.id}/sync", headers=admin_headers)
    assert response.status_code == 400


def test_lookup_fund_from_tushare(client, admin_headers, monkeypatch):
    monkeypatch.setattr("app.services.tushare_sync.settings.TUSHARE_TOKEN", "test-token")

    mock_df = pd.DataFrame({
        "ts_code": ["000006.OF"],
        "name": ["测试基金"],
        "management": ["测试经理"],
        "fund_type": ["主动权益"],
        "found_date": ["20200101"],
        "market": ["OF"],
    })

    mock_pro = Mock()
    mock_pro.fund_basic.return_value = mock_df

    with patch("app.services.tushare_sync.ts.pro_api", return_value=mock_pro):
        response = client.get("/api/admin/funds/lookup?code=000006&market=OF", headers=admin_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "测试基金"
    assert data["manager"] == "测试经理"
    assert data["category"] == "主动权益"
    assert data["market"] == "OF"


def test_lookup_fund_requires_admin(client, auth_headers):
    response = client.get("/api/admin/funds/lookup?code=000006&market=OF", headers=auth_headers)
    assert response.status_code == 403


def test_get_fund_tier_creates_default(client, admin_headers, db):
    fund = Fund(name="等级基金", category="主动权益", risk_level="中")
    db.add(fund)
    db.flush()
    db.add(FundCode(fund_id=fund.id, code="000007", market="OF", is_primary=True))
    db.commit()

    response = client.get(f"/api/admin/funds/{fund.id}/tier", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["current_tier"] == "观察"


def test_update_fund_tier(client, admin_headers, db, admin_user):
    fund = Fund(name="调整等级基金", category="主动权益", risk_level="中")
    db.add(fund)
    db.flush()
    db.add(FundCode(fund_id=fund.id, code="000008", market="OF", is_primary=True))
    db.commit()

    response = client.put(
        f"/api/admin/funds/{fund.id}/tier",
        json={"current_tier": "主推", "reason": "季度复核结果符合主推标准"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["current_tier"] == "主推"
    assert data["adjusted_reason"] == "季度复核结果符合主推标准"
    assert data["adjusted_by"] == admin_user.username
    assert data["manual_lock_until"] is not None

    history = db.query(FundTierHistory).filter(FundTierHistory.fund_id == fund.id).first()
    assert history is not None
    assert history.previous_tier == "观察"
    assert history.new_tier == "主推"


def test_clear_fund_tier_lock(client, admin_headers, db, admin_user):
    fund = Fund(name="恢复自动评级基金", category="主动权益", risk_level="中")
    db.add(fund)
    db.flush()
    db.add(FundCode(fund_id=fund.id, code="000009", market="OF", is_primary=True))
    db.commit()

    tier = FundCurrentTier(fund_id=fund.id, current_tier="主推", suggested_tier="备选", manual_lock_until=date(2026, 12, 31))
    db.add(tier)
    db.commit()

    response = client.post(
        f"/api/admin/funds/{fund.id}/tier/clear-lock",
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["current_tier"] == "备选"
    assert data["manual_lock_until"] is None
    assert data["adjusted_reason"] == "取消手动锁定，恢复自动评级"

    history = (
        db.query(FundTierHistory)
        .filter(FundTierHistory.fund_id == fund.id, FundTierHistory.new_tier == "备选")
        .first()
    )
    assert history is not None
