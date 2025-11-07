# app/db/models/dance.py
import uuid
from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy import Double
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.entities.activity_service.database import Base

class Dance(Base):
    __tablename__ = "dance"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(100), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    description = Column(String(255), nullable=True)
    status = Column(Integer, nullable=False)
    last_updated = Column(DateTime(timezone=True), nullable=True ,onupdate=func.now())
    created_date = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    duration = Column(Double, nullable=True)
    icon = Column(String(255), nullable=False)
    robot_model_id = Column(PG_UUID(as_uuid=True), nullable=True)

    # Relationships
    osmo_card = relationship("OsmoCard", back_populates="dance", lazy="selectin")
