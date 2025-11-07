# app/db/models/expression.py
import uuid
from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.entities.activity_service.database import Base

class Expression(Base):
    __tablename__ = "expression"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(100), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    image_url = Column(String(255), nullable=False)
    status = Column(Integer, nullable=False)
    robot_model_id = Column(PG_UUID(as_uuid=True), nullable=True)

    created_date = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_updated = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    osmo_card = relationship("OsmoCard", back_populates="expression", lazy="selectin")