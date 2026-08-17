from datetime import date, datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


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
    category: str = Field(..., min_length=1, max_length=32)
    risk_level: str = Field(..., min_length=1, max_length=8)
    manager: Optional[str] = Field(None, max_length=64)
    establish_date: Optional[date] = None
    reason: Optional[str] = Field(None, max_length=2000)
    target_clients: Optional[str] = Field(None, max_length=500)
    tag_ids: Optional[List[UUID]] = Field(default_factory=list)


class FundUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    category: Optional[str] = Field(None, min_length=1, max_length=32)
    risk_level: Optional[str] = Field(None, min_length=1, max_length=8)
    manager: Optional[str] = Field(None, max_length=64)
    establish_date: Optional[date] = None
    reason: Optional[str] = Field(None, max_length=2000)
    target_clients: Optional[str] = Field(None, max_length=500)
    tag_ids: Optional[List[UUID]] = None


class AdminFundListItem(BaseModel):
    id: UUID
    name: str
    code: str
    market: str
    category: str
    risk_level: str
    manager: Optional[str]
    nav: Optional[float]
    daily_return: Optional[float]
    latest_nav_date: Optional[date]
    current_tier: Optional[str] = None
    tags: List[TagSummary] = []

    class Config:
        from_attributes = True


class SyncResponse(BaseModel):
    fund_id: UUID
    status: str
    records_count: int
    message: Optional[str] = None


class TierInfo(BaseModel):
    fund_id: UUID
    current_tier: str
    suggested_tier: Optional[str] = None
    suggested_at: Optional[datetime] = None
    adjusted_at: Optional[datetime] = None
    adjusted_by: Optional[str] = None
    adjusted_reason: Optional[str] = None
    manual_lock_until: Optional[date] = None

    class Config:
        from_attributes = True


class TierUpdateRequest(BaseModel):
    current_tier: str = Field(..., min_length=1, max_length=16)
    reason: str = Field(..., min_length=10, max_length=1000)


class FundBasicLookupResponse(BaseModel):
    ts_code: str
    name: str
    manager: Optional[str]
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


class FundDetail(BaseModel):
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
