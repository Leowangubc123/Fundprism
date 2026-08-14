from datetime import date
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


class LoginRequest(BaseModel):
    username: str
    password: str


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


class FundUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    category: Optional[str] = Field(None, min_length=1, max_length=32)
    risk_level: Optional[str] = Field(None, min_length=1, max_length=8)
    manager: Optional[str] = Field(None, max_length=64)
    establish_date: Optional[date] = None
    reason: Optional[str] = Field(None, max_length=2000)
    target_clients: Optional[str] = Field(None, max_length=500)


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

    class Config:
        from_attributes = True


class SyncResponse(BaseModel):
    fund_id: UUID
    status: str
    records_count: int
    message: Optional[str] = None


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

    class Config:
        from_attributes = True


class FundDetail(BaseModel):
    id: UUID
    name: str
    code: str
    category: str
    nav: Optional[float]
    daily_return: Optional[float]

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
