from app.entities.activity import Activity
from app.entities.database import AsyncSessionLocal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import Optional, Dict, Any

from app.entities.qr_code import QRCode
from aiocache import cached, Cache, RedisCache

async def get_activity_from_qr(
        qr_code_value: str
) -> Optional[QRCode]:
    """
    Get QRCode entity with its related Activity, only if both have status = 1

    Args:
        db: Async database session
        qr_code_value: The QR code string value to search for

    Returns:
        QRCode entity with activity relationship loaded if found and both active, None otherwise
    """
    async with AsyncSessionLocal() as db:
        try:
            # Build query to select only the activity data we need
            query = (
                select(Activity)
                .join(QRCode, QRCode.activity_id == Activity.id)
                .where(
                    QRCode.qr_code == qr_code_value,
                    QRCode.status == 1,
                    Activity.status == 1
                )
            )
            
            # Execute query
            result = await db.execute(query)
            row = result.first()
            
            if row is None:
                return None
            
            # Extract the data - row[0] is the JSONB data field
            activity_data:Activity = row[0]
            
            return activity_data.as_dict()
        
        except Exception as e:
            print(f"Error retrieving activity data from QR code: {e}")
            return None
