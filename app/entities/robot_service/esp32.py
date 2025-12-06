import uuid
from sqlalchemy.dialects.postgresql.base import UUID
from app.entities.robot_service.database_robot import Base
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON


class ESP32(Base):
    __tablename__ = 'esp_32'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(UUID(as_uuid=True), nullable=False)
    firmware_version = Column(Integer, nullable=True)
    metadata = Column(JSON, nullable=True)
    name = Column(String(255), nullable=False)
    status = Column(Integer, nullable=False)
    topic_pub = Column(String(255), nullable=True)
    topic_sub = Column(String(255), nullable=False)
    message = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False)
    last_updated = Column(DateTime, nullable=True)