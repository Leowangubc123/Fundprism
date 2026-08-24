from datetime import date
from decimal import Decimal
from uuid import UUID

from app.models.fund import Fund, FundCode
from app.models.material import FundMaterial, MaterialDownloadLog
from app.models.performance import FundPerformance
from app.models.tag import Tag, FundTag
from app.models.tier import FundCurrentTier


def test_get_fund_detail_returns_full_fields(client, auth_headers, db):
    fund = Fund(
        name="测试基金",
        category="主动权益",
        risk_level="中高",
        manager="王五",
        manager_start_date=date(2020, 1, 1),
        establish_date=date(2018, 6, 1),
        reason="长期业绩优秀",
        target_clients="稳健型客户",
        asset_stock_pct=Decimal("75.50"),
        asset_bond_pct=Decimal("15.00"),
        asset_cash_pct=Decimal("5.00"),
        asset_other_pct=Decimal("4.50"),
    )
    db.add(fund)
    db.flush()

    code_a = FundCode(fund_id=fund.id, code="000001", market="OF", is_primary=True)
    code_c = FundCode(fund_id=fund.id, code="000002", market="OF", is_primary=False)
    db.add_all([code_a, code_c])

    tier = FundCurrentTier(fund_id=fund.id, current_tier="主推")
    db.add(tier)

    tag = Tag(name="核心池", category="策略", is_active=True)
    db.add(tag)
    db.flush()
    db.add(FundTag(fund_id=fund.id, tag_id=tag.id))

    perf = FundPerformance(
        fund_code_id=code_a.id,
        date=date(2026, 8, 10),
        nav=Decimal("1.2345"),
        daily_return=Decimal("0.0123"),
        return_1y=Decimal("0.15"),
        return_3y=Decimal("0.45"),
        sharpe=Decimal("1.23"),
        max_drawdown=Decimal("-0.20"),
        aum=Decimal("1234567890.1234"),
        rank_percentile=Decimal("0.25"),
    )
    db.add(perf)
    db.commit()

    res = client.get(f"/api/funds/{fund.id}", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()

    assert data["name"] == "测试基金"
    assert data["code"] == "000001"
    assert len(data["codes"]) == 2
    assert data["risk_level"] == "中高"
    assert data["manager"] == "王五"
    assert data["manager_start_date"] == "2020-01-01"
    assert data["establish_date"] == "2018-06-01"
    assert data["reason"] == "长期业绩优秀"
    assert data["target_clients"] == "稳健型客户"
    assert data["current_tier"] == "主推"
    assert data["nav"] == 1.2345
    assert data["daily_return"] == 0.0123
    assert data["return_1y"] == 0.15
    assert data["return_3y"] == 0.45
    assert data["sharpe"] == 1.23
    assert data["max_drawdown"] == -0.20
    assert data["aum"] == 1234567890.1234
    assert data["rank_percentile"] == 0.25
    assert data["asset_stock_pct"] == 75.5
    assert data["asset_bond_pct"] == 15.0
    assert data["asset_cash_pct"] == 5.0
    assert data["asset_other_pct"] == 4.5
    assert len(data["tags"]) == 1
    assert data["tags"][0]["name"] == "核心池"


def test_list_fund_materials(client, auth_headers, admin_headers, db):
    fund = Fund(name="物料基金", category="固收+", risk_level="中")
    db.add(fund)
    db.flush()
    code = FundCode(fund_id=fund.id, code="000003", market="OF", is_primary=True)
    db.add(code)
    db.commit()

    res = client.post(
        f"/api/admin/funds/{fund.id}/materials",
        headers=admin_headers,
        json={
            "name": "产品一页通",
            "material_type": "PDF",
            "url": "https://example.com/factsheet.pdf",
            "size": "2.5MB",
        },
    )
    assert res.status_code == 201

    res = client.get(f"/api/funds/{fund.id}/materials", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["name"] == "产品一页通"
    assert data[0]["material_type"] == "PDF"
    assert data[0]["url"] == "https://example.com/factsheet.pdf"
    assert data[0]["size"] == "2.5MB"


def test_download_material_records_log(client, auth_headers, db):
    fund = Fund(name="下载基金", category="主动权益", risk_level="高")
    db.add(fund)
    db.flush()
    material = FundMaterial(
        fund_id=fund.id,
        name="路演PPT",
        material_type="PPT",
        url="https://example.com/roadshow.pptx",
    )
    db.add(material)
    db.commit()

    before = db.query(MaterialDownloadLog).count()
    res = client.post(f"/api/funds/materials/{material.id}/download", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["download_url"] == "https://example.com/roadshow.pptx"
    assert db.query(MaterialDownloadLog).count() == before + 1


def test_admin_create_and_delete_material(client, admin_headers, db):
    fund = Fund(name="管理物料基金", category="QDII", risk_level="高")
    db.add(fund)
    db.flush()
    code = FundCode(fund_id=fund.id, code="000004", market="OF", is_primary=True)
    db.add(code)
    db.commit()

    res = client.post(
        f"/api/admin/funds/{fund.id}/materials",
        headers=admin_headers,
        json={
            "name": "营销话术包",
            "material_type": "DOCX",
            "url": "https://example.com/script.docx",
        },
    )
    assert res.status_code == 201
    material_id = UUID(res.json()["id"])

    assert db.query(FundMaterial).filter(FundMaterial.id == material_id).first() is not None

    res = client.delete(f"/api/admin/funds/{fund.id}/materials/{material_id}", headers=admin_headers)
    assert res.status_code == 204
    assert db.query(FundMaterial).filter(FundMaterial.id == material_id).first() is None


def test_admin_update_asset_allocation(client, admin_headers, db):
    fund = Fund(name="资产配置基金", category="固收", risk_level="低")
    db.add(fund)
    db.flush()
    code = FundCode(fund_id=fund.id, code="000005", market="OF", is_primary=True)
    db.add(code)
    db.commit()

    res = client.put(
        f"/api/admin/funds/{fund.id}",
        headers=admin_headers,
        json={
            "asset_stock_pct": 20,
            "asset_bond_pct": 70,
            "asset_cash_pct": 10,
            "asset_other_pct": 0,
        },
    )
    assert res.status_code == 200

    db.refresh(fund)
    assert float(fund.asset_stock_pct) == 20.0
    assert float(fund.asset_bond_pct) == 70.0
    assert float(fund.asset_cash_pct) == 10.0
    assert float(fund.asset_other_pct) == 0.0

    res = client.get(f"/api/funds/{fund.id}", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["asset_stock_pct"] == 20.0
    assert data["asset_bond_pct"] == 70.0
