import uuid
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import relationship
from app.entities.database import Base

class QRCode(Base):
    __tablename__ = "qr_code"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    qr_code = Column(String(255), nullable=False)
    image_url = Column(String(255), nullable=False)
    color = Column(String(100), nullable=True)
    status = Column(Integer, nullable=False, default=1)
    account_id = Column(PG_UUID(as_uuid=True), nullable=False)
    activity_id = Column(PG_UUID(as_uuid=True), ForeignKey("activity.id"), nullable=False)

    last_updated = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())
    created_date = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    activity = relationship("Activity", back_populates="qr_codes", lazy="selectin")