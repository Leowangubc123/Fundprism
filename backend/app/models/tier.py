import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, ForeignKey, Date, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base

# Use JSON for portability across PostgreSQL and SQLite.
MetricsJSON = JSON()


class FundCurrentTier(Base):
    __tablename__ = "fund_current_tiers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fund_id = Column(UUID(as_uuid=True), ForeignKey("funds.id"), nullable=False, unique=True, index=True)

    current_tier = Column(String(16), nullable=False, default="观察")
    suggested_tier = Column(String(16), nullable=True)
    suggested_at = Column(DateTime, nullable=True)
    adjusted_at = Column(DateTime, nullable=True)
    manual_lock_until = Column(Date, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    fund = relationship("Fund", back_populates="tier")


class FundTierHistory(Base):
    __tablename__ = "fund_tier_histories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fund_id = Column(UUID(as_uuid=True), ForeignKey("funds.id"), nullable=False, index=True)
    operator_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    previous_tier = Column(String(16), nullable=False)
    new_tier = Column(String(16), nullable=False)
    reason = Column(String(1000), nullable=False)
    ip_address = Column(String(64), nullable=True)
    metrics_snapshot = Column(MetricsJSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    fund = relationship("Fund", back_populates="tier_histories")
    operator = relationship("User", back_populates="tier_histories")
