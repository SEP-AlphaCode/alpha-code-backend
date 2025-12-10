import boto3
import os
import uuid
import logging
from io import BytesIO
from datetime import datetime
from typing import Optional
from PIL import Image

logger = logging.getLogger(__name__)

# AWS Configuration
AWS_ACCESS_KEY_ID = os.getenv("CLOUD_AWS_CREDENTIALS_ACCESS_KEY")
AWS_SECRET_ACCESS_KEY = os.getenv("CLOUD_AWS_CREDENTIALS_SECRET_KEY")
AWS_REGION = os.getenv("CLOUD_AWS_REGION_STATIC")
S3_BUCKET_NAME = os.getenv("APPLICATION_BUCKET_NAME")

s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)


async def upload_image_to_s3(image_bytes: bytes) -> Optional[str]:
    """
    Upload image bytes to S3 and return the URL

    Args:
        image_bytes: Image data as bytes

    Returns:
        S3 URL of uploaded image if successful, None otherwise
    """
    try:
        if not AWS_ACCESS_KEY_ID or not AWS_SECRET_ACCESS_KEY:
            logger.error("AWS credentials not configured")
            raise RuntimeError("AWS credentials not found. Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY.")

        # Validate image
        try:
            image = Image.open(BytesIO(image_bytes))
            image.verify()
            logger.info(f"Image validated: format={image.format}, size={image.size}")
        except Exception as e:
            logger.error(f"Invalid image data: {e}")
            raise ValueError(f"Invalid image data: {e}")

        # Generate unique S3 key
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        s3_key = f"video_captures/{timestamp}_{unique_id}.jpg"

        logger.info(f"Uploading image to S3: {s3_key}")

        # Upload to S3
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=s3_key,
            Body=image_bytes,
            ContentType="image/jpeg"
        )

        # Generate S3 URL
        file_url = f"https://{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"
        logger.info(f"Image uploaded successfully: {file_url}")

        return file_url

    except Exception as e:
        logger.error(f"Failed to upload image to S3: {e}", exc_info=True)
        return None

