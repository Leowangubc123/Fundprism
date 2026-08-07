import uuid
from datetime import datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class FundPerformance(Base):
    __tablename__ = "fund_performances"
    __table_args__ = (
        {"comment": "Daily performance metrics for each fund code"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fund_code_id = Column(UUID(as_uuid=True), ForeignKey("fund_codes.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)

    return_1y = Column(Numeric(10, 4), nullable=True)
    return_3y = Column(Numeric(10, 4), nullable=True)
    sharpe = Column(Numeric(10, 4), nullable=True)
    max_drawdown = Column(Numeric(10, 4), nullable=True)
    rank_percentile = Column(Numeric(6, 2), nullable=True)
    aum = Column(Numeric(14, 4), nullable=True)
    nav = Column(Numeric(10, 4), nullable=True)
    daily_return = Column(Numeric(10, 4), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    fund_code = relationship("FundCode", back_populates="performances")

    def __repr__(self):
        return f"<FundPerformance {self.fund_code_id} {self.date}>"
