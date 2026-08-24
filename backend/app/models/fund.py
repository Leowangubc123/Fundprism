import uuid
from datetime import datetime

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Date, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Fund(Base):
    __tablename__ = "funds"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(128), nullable=False)
    category = Column(String(32), nullable=False, index=True)
    risk_level = Column(String(8), nullable=False)
    manager = Column(String(64), nullable=True)
    manager_tenure = Column(String(16), nullable=True)
    manager_start_date = Column(Date, nullable=True)
    is_abnormal = Column(Boolean, default=False, nullable=False)
    establish_date = Column(Date, nullable=True)
    reason = Column(String(2000), nullable=True)
    target_clients = Column(String(500), nullable=True)
    asset_stock_pct = Column(Numeric(5, 2), nullable=True)
    asset_bond_pct = Column(Numeric(5, 2), nullable=True)
    asset_cash_pct = Column(Numeric(5, 2), nullable=True)
    asset_other_pct = Column(Numeric(5, 2), nullable=True)
    status = Column(String(16), default="active", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    codes = relationship("FundCode", back_populates="fund", cascade="all, delete-orphan")
    tags = relationship("FundTag", back_populates="fund", cascade="all, delete-orphan")
    tier = relationship("FundCurrentTier", back_populates="fund", uselist=False, cascade="all, delete-orphan")
    tier_histories = relationship("FundTierHistory", back_populates="fund", cascade="all, delete-orphan")
    materials = relationship("FundMaterial", back_populates="fund", cascade="all, delete-orphan")
    sync_logs = relationship("SyncLog", back_populates="fund")
    daily_tier_suggestions = relationship("DailyTierSuggestion", back_populates="fund", cascade="all, delete-orphan")


class FundCode(Base):
    __tablename__ = "fund_codes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fund_id = Column(UUID(as_uuid=True), ForeignKey("funds.id"), nullable=False, index=True)
    code = Column(String(16), nullable=False, unique=True, index=True)
    code_type = Column(String(8), default="A", nullable=False)
    market = Column(String(8), default="OF", nullable=False)
    is_primary = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    fund = relationship("Fund", back_populates="codes")
    performances = relationship("FundPerformance", back_populates="fund_code", cascade="all, delete-orphan")
