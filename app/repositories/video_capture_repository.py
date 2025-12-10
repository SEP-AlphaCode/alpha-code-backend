from app.entities.robot_service.video_capture import VideoCapture
from app.entities.robot_service.database_robot import AsyncSessionLocal
from typing import Optional
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)



async def create_video_capture(
    image_url: str,
    account_id: uuid.UUID,
    description: Optional[str] = None
) -> Optional[VideoCapture]:
    """
    Create new video capture record

    Args:
        image_url: S3 URL of uploaded image
        account_id: Account UUID
        description: Optional description for video generation

    Returns:
        Created VideoCapture entity if successful, None otherwise
    """
    async with AsyncSessionLocal() as db:
        try:
            now = datetime.utcnow()

            video_capture = VideoCapture(
                id=uuid.uuid4(),
                created_date=now,
                last_updated=now,
                status=1,  # Active status
                image=image_url,
                video_url=None,  # Will be updated later when video is generated
                account_id=account_id,
                is_created=False,  # Not yet generated
                description=description or "Hãy biến bức ảnh này thành video sinh động"
            )

            db.add(video_capture)
            await db.commit()
            await db.refresh(video_capture)

            logger.info(f"Created video_capture record: {video_capture.id}")
            return video_capture

        except Exception as e:
            logger.error(f"Error creating video_capture: {e}")
            await db.rollback()
            return None

