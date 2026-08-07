from datetime import date
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class TokenResponse(BaseModel):
    token: str
    token_type: str = "bearer"
    role: str
    username: str


class LoginRequest(BaseModel):
    username: str
    password: str


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
