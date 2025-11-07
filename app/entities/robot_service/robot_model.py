import uuid
from sqlalchemy import Column, String, Integer, DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from app.entities.robot_service.database_robot import Base
from sqlalchemy import Text

class RobotModel(Base):
    __tablename__ = "robot_model"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    firmware_version = Column(String(255), nullable=False)
    ctrl_version = Column(String(255), nullable=False)
    robot_prompt = Column(Text)

    last_updated = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())
    created_date = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    status = Column(Integer, nullable=False, default=1)
