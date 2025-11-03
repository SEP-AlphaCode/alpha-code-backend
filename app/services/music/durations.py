"""Durations configuration for music planner.

All values are in milliseconds (ms) as provided. The planner will convert to seconds.
"""
# durations.py

from typing import Dict
from app.repositories.dance_repository import load_dance_durations
from app.repositories.action_repository import load_action_durations
from app.repositories.expression_repository import load_expression_durations

# Biến global để cache
DANCE_DURATIONS_MS: Dict[str, int] = {}
ACTION_DURATIONS_MS: Dict[str, int] = {}
EXPRESSION_DURATIONS_MS: Dict[str, int] = {}

async def load_all_durations(robot_model_id: str) -> Dict[str, Dict[str, int]]:
    """Load toàn bộ durations từ DB cho một robot model cụ thể."""
    global DANCE_DURATIONS_MS, ACTION_DURATIONS_MS, EXPRESSION_DURATIONS_MS

    # ⚙️ Gọi 3 hàm async lấy dữ liệu
    DANCE_DURATIONS_MS = await load_dance_durations(robot_model_id)
    ACTION_DURATIONS_MS = await load_action_durations(robot_model_id)
    EXPRESSION_DURATIONS_MS = await load_expression_durations(robot_model_id)

    print(f"✅ Loaded durations for robot_model_id={robot_model_id}")
    print(f" - Dances: {len(DANCE_DURATIONS_MS)} items")
    print(f" - Actions: {len(ACTION_DURATIONS_MS)} items")
    print(f" - Expressions: {len(EXPRESSION_DURATIONS_MS)} items")

    return {
        "dance": DANCE_DURATIONS_MS or {},
        "action": ACTION_DURATIONS_MS or {},
        "expression": EXPRESSION_DURATIONS_MS or {},
    }