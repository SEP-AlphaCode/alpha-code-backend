import uuid
from sqlalchemy import Column, String, Integer, DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import relationship
from app.entities.databases.database import Base

class Activity(Base):
    __tablename__ = "activity"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    type = Column(String(255), nullable=False)
    status = Column(Integer, nullable=False, default=1)
    data = Column(JSONB, nullable=False)
    account_id = Column(PG_UUID(as_uuid=True), nullable=False)
    robot_model_id = Column(PG_UUID(as_uuid=True), nullable=False)

    last_updated = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())
    created_date = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    qr_codes = relationship("QRCode", back_populates="activity", lazy="selectin")
    
    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
