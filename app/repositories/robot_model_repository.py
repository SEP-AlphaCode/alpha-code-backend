from sqlalchemy.future import select
from app.entities.robot_service.robot_model import RobotModel
from app.entities.robot_service.database_robot import AsyncSessionLocal
from typing import Optional
from aiocache import cached, RedisCache
from config.config import settings
from aiocache.serializers import JsonSerializer

PROMPT_TEMPLATE = """You are Alpha Mini, an educational robot.
Analyze the input text and return the result **only as JSON** (no explanation, no extra text).

Input: "$INPUT_TEXT"

Language Rules:
- If the user speaks in Vietnamese, respond in Vietnamese. Set the "lang" field in the JSON as "vi"
- If the user speaks in English, respond in English. Set the "lang" field in the JSON as "en"
- Do not speak in any other languages
- Maintain the same language throughout your response

Task Classification:
Based on semantic analysis, the input likely matches one of these task types (ordered by confidence):
$TASK_PREDICTIONS

Rules:
1. Review the task predictions above. The first prediction is most likely correct.

2. If you believe the prediction is correct, follow the response template in the metadata:
   - Use the exact "type" specified
   - Follow the "response_template" structure
   - Fill in any required fields from the metadata

3. If ALL predictions seem incorrect or confidence is too low, fallback to "talk" intent:
   {
     "type": "talk",
     "lang": "vi" or "en",
     "data": {
       "text": "<your friendly response in the same language as user input>"
     }
   }

4. General guidelines:
   - Be friendly and suitable for students
   - Respond in the same language as the user input
   - Output must be strict JSON (no markdown, no code fences)
   - Extract any required information from the user input (like device names, person names, etc.)

$CONTEXT_BLOCK

Skills:
$SKILL_LIST
"""


@cached(ttl=60 * 10 * 3,
        cache=RedisCache,
        endpoint=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        key_builder=lambda f, robot_model_id: f"robot_model:{robot_model_id}",
        serializer=JsonSerializer(),
        )
async def get_robot_prompt_by_id(robot_model_id: str) -> Optional[str]:
    """
    Load custom prompt template from database for specific robot model

    Args:
        robot_model_id: Robot model identifier

    Returns:
        Custom prompt template string or None if not found
    """
    # TODO: Implement actual database query
    # Example:
    # async with db.session() as session:
    #     result = await session.execute(
    #         select(RobotModel.prompt_template)
    #         .where(RobotModel.id == robot_model_id)
    #     )
    #     return result.scalar_one_or_none()
    
    return PROMPT_TEMPLATE  # Fallback to default PROMPT_TEMPLATE
# async def get_robot_prompt_by_id(robot_model_id: str) -> Optional[str]:
#     async with AsyncSessionLocal() as session:
#         result = await session.execute(
#             select(RobotModel.robot_prompt).where(RobotModel.id == robot_model_id)
#         )
#         row = result.first()
#         return row[0] if row else None
