# app/db/models/dance.py
import uuid
from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.entities.database import Base

class Dance(Base):
    __tablename__ = "dances"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(100), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    description = Column(String(255), nullable=True)
    status = Column(Integer, nullable=False)
    last_update = Column(DateTime(timezone=True), onupdate=func.now())
    created_date = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    duration = Column(Integer, nullable=False)

    # Relationships
    osmo_cards = relationship("OsmoCard", back_populates="dance", lazy="selectin")
