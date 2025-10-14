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

# DANCE_DURATIONS_MS: Dict[str, int] = {
#     'dance_0001en': 48752,
#     'dance_0002en': 51980,
#     'dance_0003en': 71100,
#     'dance_0004en': 43432,
#     'dance_0005en': 50972,
#     'dance_0006en': 213100,
#     'dance_0007en': 64416,
#     'dance_0008en': 49491,
#     'dance_0009en': 64168,
#     'dance_0010en': 34731,
#     'dance_0011en': 109368,
# }
# 
# ACTION_DURATIONS_MS: Dict[str, int] = {
#     'action_020': 6200,
#     '009': 1700,
#     '010': 2200,
#     'random_short2': 3300,
#     '017': 3500,
#     '015': 3500,
#     '011': 1900,
#     'random_short3': 3300,
#     'random_short4': 3200,
#     '028': 2000,
#     '037': 2300,
#     '038': 3000,
#     'Surveillance_001': 2500,
#     'Surveillance_003': 2200,
#     'Surveillance_004': 2250,
#     'Surveillance_006': 2500,
#     'action_014': 4300,
#     'action_016': 3900,
#     'action_012': 4500,
#     'action_004': 3700,
#     'action_005': 2600,
#     'action_018': 5500,
#     'action_011': 4900,
#     'action_013': 4500,
#     'action_015': 4400,
#     'action_019': 3900,
# }
# 
# EXPRESSION_DURATIONS_MS: Dict[str, int] = {
#     'codemao1': 4599,
#     'codemao2': 2039,
#     'codemao3': 4439,
#     'codemao4': 7999,
#     'codemao5': 2319,
#     'codemao6': 4599,
#     'codemao7': 1159,
#     'codemao8': 1079,
#     'codemao9': 7999,
#     'codemao10': 2039,
#     'codemao11': 2839,
#     'codemao12': 839,
#     'codemao13': 2999,
#     'codemao14': 7279,
#     'codemao15': 1839,
#     'codemao16': 1319,
#     'codemao17': 2039,
#     'codemao18': 2319,
#     'codemao19': 2679,
#     'codemao20': 1039,
#     'w_basic_0007_1': 2999,
#     'w_basic_0003_1': 1999,
#     'w_basic_0005_1': 4999,
#     'w_basic_0010_1': 4999,
#     'w_basic_0011_1': 4999,
#     'w_basic_0012_1': 4999,
#     'emo_007': 3000,
#     'emo_010': 4240,
#     'emo_016': 2040,
#     'emo_028': 2200,
#     'emo_008': 3520,
#     'emo_014': 3440,
#     'emo_009': 4040,
#     'emo_011': 2800,
#     'emo_023': 3120,
#     'emo_013': 2440,
#     'emo_015': 2999,
#     'emo_026': 2999,
#     'emo_022': 3000,
#     'emo_019': 2680,
#     'emo_020': 2999,
#     'emo_027': 6960,
#     'emo_029': 1520,
#     'emo_030': 2999,
#     'emo_031': 3800,
#     'emo_032': 2840,
# }
