import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class SyncLog(Base):
    __tablename__ = "sync_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sync_type = Column(String(32), nullable=False, index=True)
    status = Column(String(16), nullable=False, index=True)
    records_count = Column(Integer, default=0, nullable=False)
    failed_records = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    ended_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    fund_id = Column(UUID(as_uuid=True), ForeignKey("funds.id", ondelete="SET NULL"), nullable=True, index=True)

    fund = relationship("Fund", back_populates="sync_logs")
