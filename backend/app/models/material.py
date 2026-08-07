import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class FundMaterial(Base):
    __tablename__ = "fund_materials"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fund_id = Column(UUID(as_uuid=True), ForeignKey("funds.id"), nullable=False, index=True)

    name = Column(String(128), nullable=False)
    material_type = Column(String(32), nullable=False)
    url = Column(String(500), nullable=False)
    size = Column(String(32), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    fund = relationship("Fund", back_populates="materials")
    download_logs = relationship("MaterialDownloadLog", back_populates="material", cascade="all, delete-orphan")


class MaterialDownloadLog(Base):
    __tablename__ = "material_download_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    material_id = Column(UUID(as_uuid=True), ForeignKey("fund_materials.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    ip_address = Column(String(64), nullable=True)
    downloaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    material = relationship("FundMaterial", back_populates="download_logs")
    user = relationship("User", back_populates="download_logs")
