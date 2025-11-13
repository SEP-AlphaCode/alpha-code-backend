from sqlalchemy import Column, Integer, DateTime, ForeignKey, text, String
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.entities.payment_service.database_payment import Base


class TokenRule(Base):
    __tablename__ = 'token_rule'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    created_date = Column(DateTime, nullable=False)
    last_updated = Column(DateTime, nullable=True)
    status = Column(Integer, nullable=False)
    code = Column(String(255), nullable=False)
    cost = Column(Integer, nullable=False)
    note = Column(String(255), nullable=True)