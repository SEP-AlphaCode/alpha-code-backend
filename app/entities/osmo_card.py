# app/db/models/osmo_card.py
import uuid
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from app.entities.database import Base

class OsmoCard(Base):
    __tablename__ = "osmo_card"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    color = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    status = Column(Integer, nullable=False, default=1)

    last_update = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())
    created_date = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    expression_id = Column(PG_UUID(as_uuid=True), ForeignKey("expressions.id"), nullable=True)
    action_id = Column(PG_UUID(as_uuid=True), ForeignKey("actions.id"), nullable=True)
    dance_id = Column(PG_UUID(as_uuid=True), ForeignKey("dances.id"), nullable=True)

    # Relationships (Expression/Action/Dance model phải tồn tại ở Python)
    expression = relationship("Expression", back_populates="osmo_cards", lazy="selectin")
    action = relationship("Action", back_populates="osmo_cards", lazy="selectin")
    dance = relationship("Dance", back_populates="osmo_cards", lazy="selectin")
    skill = relationship("Skill", back_populates="osmo_card", lazy="selectin")
    extended_action = relationship("ExtendedAction", back_populates="osmo_card", lazy="selectin")
