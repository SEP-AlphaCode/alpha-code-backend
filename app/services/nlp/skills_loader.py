# app/nlp/skill_loader.py
from typing import List
from app.repositories.skill_repository import get_skills_by_robot_model_repo

async def load_skills_text(robot_model_id: str) -> str:
    """
    Load all skills from DB for a given robot model and return as CSV-style text.
    This replaces skills.txt.
    """
    skills = await get_skills_by_robot_model_repo(robot_model_id)

    if not skills:
        return "No skills available."

    skill_lines = [f"{s['code']}, {s['name']}" for s in skills]
    return "\n".join(skill_lines)
