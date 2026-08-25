from datetime import date, datetime
from enum import Enum
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


FundCategory = Literal["主动权益", "指增", "被动指数", "固收+", "固收", "QDII", "其他"]


class Market(str, Enum):
    OF = "OF"
    SH = "SH"
    SZ = "SZ"


class TokenResponse(BaseModel):
    token: str
    token_type: str = "bearer"
    role: str
    username: str
    id: UUID


class LoginRequest(BaseModel):
    username: str
    password: str


class UserListItem(BaseModel):
    id: UUID
    username: str
    full_name: Optional[str] = None
    role: str
    is_active: bool
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserCreateRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=64)
    password: str = Field(..., min_length=6, max_length=64)
    full_name: Optional[str] = Field(None, max_length=64)
    role: str = Field(..., pattern="^(sales|admin)$")
    is_active: bool = True


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = Field(None, max_length=64)
    role: Optional[str] = Field(None, pattern="^(sales|admin)$")
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=6, max_length=64)


class TagSummary(BaseModel):
    id: UUID
    name: str
    category: str

    class Config:
        from_attributes = True


class FundCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")
    market: Market = Market.OF
    category: FundCategory
    risk_level: str = Field(..., min_length=1, max_length=8)
    manager: Optional[str] = Field(None, max_length=64)
    manager_start_date: Optional[date] = None
    is_abnormal: bool = False
    establish_date: Optional[date] = None
    reason: Optional[str] = Field(None, max_length=2000)
    target_clients: Optional[str] = Field(None, max_length=500)
    asset_stock_pct: Optional[float] = Field(None, ge=0, le=100)
    asset_bond_pct: Optional[float] = Field(None, ge=0, le=100)
    asset_cash_pct: Optional[float] = Field(None, ge=0, le=100)
    asset_other_pct: Optional[float] = Field(None, ge=0, le=100)
    tag_ids: Optional[List[UUID]] = Field(default_factory=list)


class FundUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    category: Optional[FundCategory] = None
    risk_level: Optional[str] = Field(None, min_length=1, max_length=8)
    manager: Optional[str] = Field(None, max_length=64)
    manager_start_date: Optional[date] = None
    is_abnormal: Optional[bool] = None
    establish_date: Optional[date] = None
    reason: Optional[str] = Field(None, max_length=2000)
    target_clients: Optional[str] = Field(None, max_length=500)
    asset_stock_pct: Optional[float] = Field(None, ge=0, le=100)
    asset_bond_pct: Optional[float] = Field(None, ge=0, le=100)
    asset_cash_pct: Optional[float] = Field(None, ge=0, le=100)
    asset_other_pct: Optional[float] = Field(None, ge=0, le=100)
    tag_ids: Optional[List[UUID]] = None


class AdminFundListItem(BaseModel):
    id: UUID
    name: str
    code: str
    market: str
    category: str
    risk_level: str
    manager: Optional[str]
    manager_start_date: Optional[date] = None
    is_abnormal: bool = False
    nav: Optional[float]
    daily_return: Optional[float]
    latest_nav_date: Optional[date]
    current_tier: Optional[str] = None
    suggested_tier: Optional[str] = None
    scoring_reason: Optional[str] = None
    manual_lock_until: Optional[date] = None
    tags: List[TagSummary] = []

    class Config:
        from_attributes = True


class SyncLogItem(BaseModel):
    id: UUID
    sync_type: str
    status: str
    records_count: int
    failed_records: int
    error_message: Optional[str] = None
    started_at: datetime
    ended_at: Optional[datetime] = None
    fund_id: Optional[UUID] = None
    fund_name: Optional[str] = None

    class Config:
        from_attributes = True


class SyncRunResponse(BaseModel):
    status: str
    total: int
    successful: int
    failed: int
    message: str


class SyncResponse(BaseModel):
    fund_id: UUID
    status: str
    records_count: int
    message: Optional[str] = None


class FundImportRow(BaseModel):
    row_number: int
    code: str
    market: str = "OF"
    name: Optional[str] = None
    category: Optional[str] = None
    risk_level: Optional[str] = None
    manager: Optional[str] = None
    establish_date: Optional[date] = None
    reason: Optional[str] = None
    target_clients: Optional[str] = None
    tags: List[str] = []


class BatchImportResponse(BaseModel):
    created: int
    updated: int
    skipped: int
    errors: List[str]


class ScoreInfo(BaseModel):
    fund_id: UUID
    current_tier: str
    suggested_tier: Optional[str] = None
    score: Optional[float] = None
    reason: Optional[str] = None


class ScoringRunResponse(BaseModel):
    scored: int
    skipped: int
    date: str


class StableApplyResponse(BaseModel):
    applied: int
    red_line_downgrades: int
    locked_skipped: int


class TierInfo(BaseModel):
    fund_id: UUID
    current_tier: str
    suggested_tier: Optional[str] = None
    suggested_at: Optional[datetime] = None
    adjusted_at: Optional[datetime] = None
    adjusted_by: Optional[str] = None
    adjusted_reason: Optional[str] = None
    manual_lock_until: Optional[date] = None
    is_locked: bool = False

    class Config:
        from_attributes = True


class TierUpdateRequest(BaseModel):
    current_tier: str = Field(..., min_length=1, max_length=16)
    reason: str = Field(..., min_length=10, max_length=1000)


class FundBasicLookupResponse(BaseModel):
    ts_code: str
    name: str
    management: Optional[str] = None
    category: Optional[str]
    establish_date: Optional[date]
    market: str


class FundListItem(BaseModel):
    id: UUID
    name: str
    code: str
    category: str
    nav: Optional[float]
    daily_return: Optional[float]
    current_tier: Optional[str] = None
    tags: List[TagSummary] = []

    class Config:
        from_attributes = True


class FundCodeItem(BaseModel):
    id: UUID
    code: str
    market: str
    is_primary: bool

    class Config:
        from_attributes = True


class MaterialItem(BaseModel):
    id: UUID
    name: str
    material_type: str
    url: str
    size: Optional[str] = None

    class Config:
        from_attributes = True


class MaterialCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    material_type: str = Field(..., min_length=1, max_length=32)
    url: str = Field(..., min_length=1, max_length=500)
    size: Optional[str] = Field(None, max_length=32)


class MaterialDownloadResponse(BaseModel):
    download_url: str


class FundDetail(BaseModel):
    id: UUID
    name: str
    code: str
    codes: List[FundCodeItem] = []
    category: str
    risk_level: Optional[str] = None
    manager: Optional[str] = None
    manager_start_date: Optional[date] = None
    establish_date: Optional[date] = None
    nav: Optional[float] = None
    daily_return: Optional[float] = None
    return_1y: Optional[float] = None
    return_3y: Optional[float] = None
    sharpe: Optional[float] = None
    max_drawdown: Optional[float] = None
    aum: Optional[float] = None
    rank_percentile: Optional[float] = None
    current_tier: Optional[str] = None
    reason: Optional[str] = None
    target_clients: Optional[str] = None
    asset_stock_pct: Optional[float] = None
    asset_bond_pct: Optional[float] = None
    asset_cash_pct: Optional[float] = None
    asset_other_pct: Optional[float] = None
    tags: List[TagSummary] = []

    class Config:
        from_attributes = True


class NavHistoryItem(BaseModel):
    date: date
    nav: float

    class Config:
        from_attributes = True


class FundCompareItem(FundDetail):
    manager: Optional[str]
    nav_history: List[NavHistoryItem]

    class Config:
        from_attributes = True


class FundCompareResponse(BaseModel):
    funds: List[FundCompareItem]


class TagCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    category: str = Field(..., min_length=1, max_length=32)
    is_active: bool = True


class TagUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=64)
    category: Optional[str] = Field(None, min_length=1, max_length=32)
    is_active: Optional[bool] = None


class TagItem(BaseModel):
    id: UUID
    name: str
    category: str
    is_active: bool

    class Config:
        from_attributes = True
