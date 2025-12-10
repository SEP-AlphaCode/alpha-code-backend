import uuid
from sqlalchemy.dialects.postgresql.base import UUID
from app.entities.robot_service.database_robot import Base
from sqlalchemy import Column, String, Integer, DateTime, Boolean, ForeignKey

class VideoCapture(Base):
    __tablename__ = "video_capture"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    created_date = Column(DateTime(timezone=False), nullable=False)
    last_updated = Column(DateTime(timezone=False), nullable=True)
    status = Column(Integer, nullable=False)
    image = Column(String, nullable=False)
    video_url = Column(String, nullable=True)
    account_id = Column(UUID(as_uuid=True), nullable=False)
    is_created = Column(Boolean, nullable=False, default=False)
    description = Column(String, nullable=True)

