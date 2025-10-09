import uuid
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from app.entities.database import Base

class ExtendedAction(Base):
    __tablename__ = "extended_actions"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    code = Column(String(100), nullable=False)
    status = Column(Integer, nullable=False)
    icon = Column(String(255), nullable=True)
    robotModelId = Column(PG_UUID(as_uuid=True), nullable=True)

    last_update = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())
    created_date = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


    # Relationships
    osmo_card = relationship("OsmoCard", back_populates="extended_action", lazy="selectin")