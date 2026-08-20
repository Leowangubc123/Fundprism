import uuid
from datetime import datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class DailyTierSuggestion(Base):
    __tablename__ = "daily_tier_suggestions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fund_id = Column(UUID(as_uuid=True), ForeignKey("funds.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    suggested_tier = Column(String(16), nullable=False)
    reason = Column(String(50), nullable=True)
    score = Column(Numeric(6, 2), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    fund = relationship("Fund", back_populates="daily_tier_suggestions")

    __table_args__ = (
        UniqueConstraint("fund_id", "date", name="uq_daily_tier_suggestion_fund_date"),
    )
