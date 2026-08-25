from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

import pandas as pd
import pytest

from app.models.fund import Fund, FundCode
from app.models.performance import FundPerformance
from app.services.tushare_sync import (
    _get_start_date,
    _update_fund_aum,
    _update_fund_manager,
    _update_rank_percentile,
)


pytestmark = pytest.mark.usefixtures("db")


def test_get_start_date_returns_far_past_for_empty_history(db):
    fund = Fund(name="新基金", category="主动权益", risk_level="中")
    db.add(fund)
    db.flush()
    code = FundCode(fund_id=fund.id, code="000001", market="OF", is_primary=True)
    db.add(code)
    db.commit()

    start = _get_start_date(db, code.id)
    # Should be roughly 1100 days ago
    assert (date.today() - start).days >= 1000


def test_get_start_date_uses_establish_date_for_older_fund(db):
    fund = Fund(
        name="老基金",
        category="主动权益",
        risk_level="中",
        establish_date=date(2022, 1, 26),
    )
    db.add(fund)
    db.flush()
    code = FundCode(fund_id=fund.id, code="000002", market="OF", is_primary=True)
    db.add(code)
    db.commit()

    start = _get_start_date(db, code.id, fund.establish_date)
    assert start == date(2022, 1, 26)


def test_get_start_date_backfills_short_history(db):
    fund = Fund(
        name="需回填基金",
        category="主动权益",
        risk_level="中",
        establish_date=date(2022, 1, 26),
    )
    db.add(fund)
    db.flush()
    code = FundCode(fund_id=fund.id, code="000003", market="OF", is_primary=True)
    db.add(code)
    db.commit()

    # Only 30 days of history
    perf = FundPerformance(
        fund_code_id=code.id,
        date=date.today() - timedelta(days=30),
        nav=Decimal("1.0"),
    )
    db.add(perf)
    db.commit()

    start = _get_start_date(db, code.id, fund.establish_date)
    assert start == date(2022, 1, 26)


def test_get_start_date_returns_day_after_latest_record_when_history_complete(db):
    fund = Fund(name="完整历史基金", category="主动权益", risk_level="中")
    db.add(fund)
    db.flush()
    code = FundCode(fund_id=fund.id, code="000004", market="OF", is_primary=True)
    db.add(code)
    db.commit()

    perfs = [
        FundPerformance(fund_code_id=code.id, date=date(2020, 1, 1), nav=Decimal("1.0")),
        FundPerformance(fund_code_id=code.id, date=date(2026, 7, 1), nav=Decimal("1.1")),
    ]
    db.add_all(perfs)
    db.commit()

    start = _get_start_date(db, code.id)
    assert start == date(2026, 7, 2)


def test_update_fund_aum_from_share(db, monkeypatch):
    monkeypatch.setattr("app.services.tushare_sync.settings.TUSHARE_TOKEN", "test-token")

    fund = Fund(name="规模基金", category="主动权益", risk_level="中")
    db.add(fund)
    db.flush()
    code = FundCode(fund_id=fund.id, code="000003", market="OF", is_primary=True)
    db.add(code)
    db.commit()

    perf = FundPerformance(
        fund_code_id=code.id,
        date=date(2026, 8, 10),
        nav=Decimal("2.0000"),
    )
    db.add(perf)
    db.commit()

    share_df = pd.DataFrame({
        "trade_date": ["20260810"],
        "fd_share": ["50000"],  # 50000 万份
    })
    mock_pro = Mock()
    mock_pro.fund_share.return_value = share_df

    with patch("app.services.tushare_sync.ts.pro_api", return_value=mock_pro):
        _update_fund_aum(db, code)

    db.refresh(perf)
    # 50000 万份 * 10000 份/万份 * 2.0 元 = 1_000_000_000 元
    assert perf.aum == Decimal("1000000000")


def test_update_fund_manager_from_tushare(db, monkeypatch):
    monkeypatch.setattr("app.services.tushare_sync.settings.TUSHARE_TOKEN", "test-token")

    fund = Fund(name="经理基金", category="主动权益", risk_level="中")
    db.add(fund)
    db.flush()
    code = FundCode(fund_id=fund.id, code="000004", market="OF", is_primary=True)
    db.add(code)
    db.commit()

    manager_df = pd.DataFrame({
        "name": ["王经理"],
        "begin_date": ["20220101"],
        "end_date": [None],
    })
    mock_pro = Mock()
    mock_pro.fund_manager.return_value = manager_df

    with patch("app.services.tushare_sync.ts.pro_api", return_value=mock_pro):
        _update_fund_manager(db, fund.id)

    db.refresh(fund)
    assert fund.manager == "王经理"
    assert fund.manager_start_date == date(2022, 1, 1)


def test_update_fund_manager_replaces_company_name(db, monkeypatch):
    monkeypatch.setattr("app.services.tushare_sync.settings.TUSHARE_TOKEN", "test-token")

    fund = Fund(name="经理基金2", category="主动权益", risk_level="中", manager="某基金管理有限责任公司")
    db.add(fund)
    db.flush()
    code = FundCode(fund_id=fund.id, code="000007", market="OF", is_primary=True)
    db.add(code)
    db.commit()

    manager_df = pd.DataFrame({
        "name": ["李经理"],
        "begin_date": ["20230101"],
        "end_date": [None],
    })
    mock_pro = Mock()
    mock_pro.fund_manager.return_value = manager_df

    with patch("app.services.tushare_sync.ts.pro_api", return_value=mock_pro):
        _update_fund_manager(db, fund.id)

    db.refresh(fund)
    assert fund.manager == "李经理"


def test_update_fund_manager_preserves_existing_person_name(db, monkeypatch):
    monkeypatch.setattr("app.services.tushare_sync.settings.TUSHARE_TOKEN", "test-token")

    fund = Fund(name="经理基金3", category="主动权益", risk_level="中", manager="张三")
    db.add(fund)
    db.flush()
    code = FundCode(fund_id=fund.id, code="000008", market="OF", is_primary=True)
    db.add(code)
    db.commit()

    manager_df = pd.DataFrame({
        "name": ["李四"],
        "begin_date": ["20230101"],
        "end_date": [None],
    })
    mock_pro = Mock()
    mock_pro.fund_manager.return_value = manager_df

    with patch("app.services.tushare_sync.ts.pro_api", return_value=mock_pro):
        _update_fund_manager(db, fund.id)

    db.refresh(fund)
    assert fund.manager == "张三"


def test_update_rank_percentile_within_category(db):
    fund = Fund(name="排名基金 A", category="主动权益", risk_level="中")
    db.add(fund)
    db.flush()
    code_a = FundCode(fund_id=fund.id, code="000005", market="OF", is_primary=True)
    db.add(code_a)

    peer_fund = Fund(name="排名基金 B", category="主动权益", risk_level="中")
    db.add(peer_fund)
    db.flush()
    code_b = FundCode(fund_id=peer_fund.id, code="000006", market="OF", is_primary=True)
    db.add(code_b)
    db.commit()

    perf_a = FundPerformance(
        fund_code_id=code_a.id,
        date=date(2026, 8, 10),
        nav=Decimal("1.0"),
        return_1y=Decimal("0.20"),
    )
    perf_b = FundPerformance(
        fund_code_id=code_b.id,
        date=date(2026, 8, 10),
        nav=Decimal("1.0"),
        return_1y=Decimal("0.10"),
    )
    db.add_all([perf_a, perf_b])
    db.commit()

    _update_rank_percentile(db, fund.id)

    db.refresh(perf_a)
    # Fund A's return is higher than its only peer -> 100th percentile
    assert float(perf_a.rank_percentile) == 1.0


def test_update_fund_manager_clears_company_name_when_no_person_in_tushare(db, monkeypatch):
    monkeypatch.setattr("app.services.tushare_sync.settings.TUSHARE_TOKEN", "test-token")

    fund = Fund(
        name="经理基金4",
        category="主动权益",
        risk_level="中",
        manager="某基金管理有限责任公司",
    )
    db.add(fund)
    db.flush()
    code = FundCode(fund_id=fund.id, code="000009", market="OF", is_primary=True)
    db.add(code)
    db.commit()

    manager_df = pd.DataFrame({
        "name": ["某基金管理有限责任公司"],
        "begin_date": ["20230101"],
        "end_date": [None],
    })
    mock_pro = Mock()
    mock_pro.fund_manager.return_value = manager_df

    with patch("app.services.tushare_sync.ts.pro_api", return_value=mock_pro):
        result = _update_fund_manager(db, fund.id)

    db.refresh(fund)
    assert fund.manager is None
    assert "cleared" in result


def test_update_fund_manager_prefers_current_person_over_historical_company(db, monkeypatch):
    monkeypatch.setattr("app.services.tushare_sync.settings.TUSHARE_TOKEN", "test-token")

    fund = Fund(name="经理基金5", category="主动权益", risk_level="中")
    db.add(fund)
    db.flush()
    code = FundCode(fund_id=fund.id, code="000010", market="OF", is_primary=True)
    db.add(code)
    db.commit()

    manager_df = pd.DataFrame({
        "name": ["某基金管理有限责任公司", "赵经理"],
        "begin_date": ["20200101", "20240101"],
        "end_date": ["20231231", None],
    })
    mock_pro = Mock()
    mock_pro.fund_manager.return_value = manager_df

    with patch("app.services.tushare_sync.ts.pro_api", return_value=mock_pro):
        _update_fund_manager(db, fund.id)

    db.refresh(fund)
    assert fund.manager == "赵经理"
