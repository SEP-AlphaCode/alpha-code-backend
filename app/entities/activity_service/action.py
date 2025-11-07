# app/db/models/action.py
import uuid
from sqlalchemy import Column, String, Integer, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.entities.activity_service.database import Base

class Action(Base):
    __tablename__ = "action"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(100), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    description = Column(String(255), nullable=True)
    duration = Column(Integer, nullable=False)
    status = Column(Integer, nullable=False)
    icon = Column(String(255), nullable=True)
    last_updated = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())
    created_date = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    can_interrupt = Column(Boolean, nullable=False, default=False)
    robot_model_id = Column(PG_UUID(as_uuid=True), nullable=True)

    # - osmo_cards: quan hệ ngược với OsmoCard
    osmo_card = relationship("OsmoCard", back_populates="action", lazy="selectin")
