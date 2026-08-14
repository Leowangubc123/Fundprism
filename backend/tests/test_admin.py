from datetime import date
from unittest.mock import Mock, patch
from uuid import uuid4

import pandas as pd
import pytest

from app.models.fund import Fund, FundCode
from app.models.performance import FundPerformance
from app.models.sync import SyncLog
from app.models.tier import FundCurrentTier


def test_list_funds_requires_admin(client, auth_headers):
    response = client.get("/api/admin/funds", headers=auth_headers)
    assert response.status_code == 403


def test_create_fund(client, admin_headers, db):
    payload = {
        "name": "测试基金",
        "code": "123456",
        "market": "OF",
        "category": "混合型",
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
    fund = Fund(name="已有基金", category="股票型", risk_level="高")
    db.add(fund)
    db.flush()
    db.add(FundCode(fund_id=fund.id, code="000001", market="OF", is_primary=True))
    db.commit()

    payload = {
        "name": "重复代码基金",
        "code": "000001",
        "market": "OF",
        "category": "混合型",
        "risk_level": "中",
    }
    response = client.post("/api/admin/funds", json=payload, headers=admin_headers)
    assert response.status_code == 409


def test_update_fund(client, admin_headers, db):
    fund = Fund(name="旧名字", category="混合型", risk_level="中")
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
    fund = Fund(name="待删除", category="混合型", risk_level="中")
    db.add(fund)
    db.flush()
    db.add(FundCode(fund_id=fund.id, code="000003", market="OF", is_primary=True))
    db.commit()

    response = client.delete(f"/api/admin/funds/{fund.id}", headers=admin_headers)
    assert response.status_code == 204
    assert db.query(Fund).filter(Fund.id == fund.id).first() is None


def test_sync_fund_creates_performances(client, admin_headers, db, monkeypatch):
    fund = Fund(name="同步基金", category="混合型", risk_level="中")
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
    fund = Fund(name="无Token基金", category="混合型", risk_level="中")
    db.add(fund)
    db.flush()
    db.add(FundCode(fund_id=fund.id, code="000005", market="OF", is_primary=True))
    db.commit()

    response = client.post(f"/api/admin/funds/{fund.id}/sync", headers=admin_headers)
    assert response.status_code == 400
