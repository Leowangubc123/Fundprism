import uuid
from datetime import datetime

from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Tag(Base):
    __tablename__ = "tags"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(64), nullable=False, unique=True)
    category = Column(String(32), nullable=False, index=True)
    sort_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    fund_tags = relationship("FundTag", back_populates="tag", cascade="all, delete-orphan")


class FundTag(Base):
    __tablename__ = "fund_tags"

    fund_id = Column(UUID(as_uuid=True), ForeignKey("funds.id"), primary_key=True)
    tag_id = Column(UUID(as_uuid=True), ForeignKey("tags.id"), primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    fund = relationship("Fund", back_populates="tags")
    tag = relationship("Tag", back_populates="fund_tags")

    __table_args__ = (
        UniqueConstraint("fund_id", "tag_id", name="uq_fund_tag"),
    )
