import uuid
from sqlalchemy.dialects.postgresql.base import UUID
from app.entities.robot_service.database_robot import Base
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey

class Robot(Base):
    __tablename__ = "robot"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    account_id = Column(UUID(as_uuid=True), ForeignKey("public.account.id"), nullable=False)
    created_date = Column(DateTime(timezone=False), nullable=False)
    last_updated = Column(DateTime(timezone=False), nullable=True)
    robot_model_id = Column(UUID(as_uuid=True), ForeignKey("public.robot_model.id"), nullable=False)
    serial_number = Column(String(255), nullable=False)
    status = Column(Integer, nullable=False)