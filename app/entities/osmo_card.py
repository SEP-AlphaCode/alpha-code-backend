# app/db/models/osmo_card.py
import uuid
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from app.entities.databases.database import Base

class OsmoCard(Base):
    __tablename__ = "osmo_card"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    color = Column(String(50), nullable=False)
    name = Column(String(255), nullable=False)
    status = Column(Integer, nullable=False, default=1)

    created_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_updated = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    expression_id = Column(PG_UUID(as_uuid=True), ForeignKey("expression.id"), nullable=True)
    action_id = Column(PG_UUID(as_uuid=True), ForeignKey("action.id"), nullable=True)
    dance_id = Column(PG_UUID(as_uuid=True), ForeignKey("dance.id"), nullable=True)
    skill_id = Column(PG_UUID(as_uuid=True), ForeignKey("skill.id"), nullable=True)
    extended_action_id = Column(PG_UUID(as_uuid=True), ForeignKey("extended_action.id"), nullable=True)

    # Relationships
    expression = relationship("Expression", back_populates="osmo_card", lazy="selectin")
    action = relationship("Action", back_populates="osmo_card", lazy="selectin")
    dance = relationship("Dance", back_populates="osmo_card", lazy="selectin")
    skill = relationship("Skill", back_populates="osmo_card", lazy="selectin")
    extended_action = relationship("ExtendedAction", back_populates="osmo_card", lazy="selectin")
