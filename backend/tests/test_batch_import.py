from io import BytesIO

import openpyxl
import pytest

from app.models.fund import Fund, FundCode
from app.models.tag import Tag


def _make_xlsx(rows):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append([
        "基金代码",
        "市场",
        "基金名称",
        "分类",
        "风险等级",
        "基金经理",
        "成立日期",
        "入选理由",
        "目标客户",
        "标签",
    ])
    for row in rows:
        ws.append(row)
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer.read()


def test_batch_import_requires_admin(client, auth_headers):
    response = client.post("/api/admin/funds/import", headers=auth_headers)
    assert response.status_code == 403


def test_batch_import_create_and_update(client, admin_headers, db):
    rows = [
        ["123456", "OF", "新基金", "混合型", "中", "张三", "2020-01-01", "理由1", "客户1", "红利主题"],
        ["123456", "OF", "更新基金", "股票型", "高", "李四", "", "", "", "量化策略"],
        ["abc", "OF", "无效代码", "混合型", "中", "", "", "", "", ""],
    ]
    files = {"file": ("test.xlsx", BytesIO(_make_xlsx(rows)), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}

    response = client.post("/api/admin/funds/import", files=files, headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["created"] == 1
    assert data["updated"] == 1
    assert data["skipped"] == 1
    assert any("abc" in err for err in data["errors"])

    fund = db.query(Fund).filter(Fund.name == "更新基金").first()
    assert fund is not None
    assert fund.category == "股票型"
    assert fund.risk_level == "高"

    code = db.query(FundCode).filter(FundCode.code == "123456").first()
    assert code is not None
    assert code.market == "OF"

    tag_names = {t.name for t in db.query(Tag).all()}
    assert "红利主题" in tag_names
    assert "量化策略" in tag_names


def test_batch_import_invalid_file_type(client, admin_headers):
    files = {"file": ("test.txt", BytesIO(b"not excel"), "text/plain")}
    response = client.post("/api/admin/funds/import", files=files, headers=admin_headers)
    assert response.status_code == 400
