import replicate
import os
from fastapi import UploadFile, HTTPException
from dotenv import load_dotenv
from typing import Dict, Any
import base64
import logging

load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Replicate API Configuration
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")

# Default prompt template in Vietnamese
DEFAULT_PROMPT_TEMPLATE = "Hãy biến bức ảnh này thành một đoạn video sinh động và giàu cảm xúc, với chuyển động mềm mại, tự nhiên và hoàn toàn mượt. Biến bản vẽ tĩnh thành một hoạt cảnh đẹp mắt giống như một đoạn phim hoạt hình chất lượng cao dành cho trẻ em. Hãy thêm các hiệu ứng nhẹ nhàng, màu sắc tươi sáng, ánh sáng mềm, hoạt họa đáng yêu và nhịp điệu vui tươi. Giữ nguyên phong cách gốc của bức vẽ nhưng làm cho mọi thứ sống động, đáng yêu và thu hút như một clip hoạt hình chuyên nghiệp. {description}"

async def generate_video_from_image(
    file: UploadFile,
    description: str = "",
    use_default_template: bool = True
) -> Dict[str, Any]:
    """
    Generate video from image using Replicate's Wan Video API
    Returns video URL and metadata
    """
    try:
        logger.info(f"Starting video generation for file: {file.filename}")
        logger.info(f"Description: {description}")
        logger.info(f"Use default template: {use_default_template}")

        # Set Replicate API token
        if not REPLICATE_API_TOKEN:
            logger.error("REPLICATE_API_TOKEN not configured")
            raise HTTPException(status_code=500, detail="REPLICATE_API_TOKEN not configured")

        os.environ["REPLICATE_API_TOKEN"] = REPLICATE_API_TOKEN
        logger.info("Replicate API token configured")

        # Read image file
        logger.info("Reading image file...")
        image_content = await file.read()
        await file.seek(0)  # Reset file pointer
        logger.info(f"Image file read successfully, size: {len(image_content)} bytes")

        # Convert image to base64 data URI
        logger.info("Converting image to base64...")
        image_base64 = base64.b64encode(image_content).decode('utf-8')
        image_data_uri = f"data:{file.content_type};base64,{image_base64}"
        logger.info(f"Image converted to base64 data URI, content type: {file.content_type}")

        # Apply default template if requested
        final_prompt = DEFAULT_PROMPT_TEMPLATE.format(description=description) if use_default_template else description
        logger.info(f"Final prompt: {final_prompt}")

        # Prepare input for Replicate
        input_data = {
            "image": image_data_uri,
            "prompt": final_prompt
        }
        logger.info("Input data prepared for Replicate API")

        # Run the model
        logger.info("Calling Replicate API to generate video...")
        output = replicate.run(
            "wan-video/wan-2.2-i2v-fast",
            input=input_data
        )
        logger.info(f"Replicate API call completed. Output type: {type(output)}")
        logger.info(f"Output value: {output}")

        # Get video URL - output is already a string URL
        video_url = str(output) if output else None

        if not video_url:
            logger.error("No video URL returned from Replicate")
            raise HTTPException(status_code=500, detail="No video URL returned from Replicate")

        logger.info(f"Video URL obtained: {video_url}")

        result = {
            "video_url": video_url,
            "prompt": final_prompt,
            "original_filename": file.filename
        }
        logger.info(f"Video generation completed successfully: {result}")
        return result

    except Exception as e:
        logger.error(f"Failed to generate video: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate video: {str(e)}")

