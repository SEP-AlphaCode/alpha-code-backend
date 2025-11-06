from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base
import uuid

from app.entities.databases.database_payment import Base


class Subscription(Base):
    __tablename__ = "subscription"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    created_date = Column(DateTime(timezone=False), nullable=False)
    last_updated = Column(DateTime(timezone=False), nullable=True)
    status = Column(Integer, nullable=False)
    account_id = Column(UUID(as_uuid=True), ForeignKey("public.account.id"), nullable=False)
    end_date = Column(DateTime(timezone=False), nullable=False)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("public.plan.id"), nullable=False)
    start_date = Column(DateTime(timezone=False), nullable=False)
