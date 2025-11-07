from sqlalchemy import Column, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.entities.payment_service.database_payment import Base


class AccountQuota(Base):
    __tablename__ = "account_quota"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    created_date = Column(DateTime(timezone=False), nullable=False)
    last_updated = Column(DateTime(timezone=False), nullable=True)
    status = Column(Integer, nullable=False)
    account_id = Column(UUID(as_uuid=True), nullable=False)
    quota = Column(Integer, nullable=False)
