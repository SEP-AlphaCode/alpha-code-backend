"""Durations configuration for music planner.

All values are in milliseconds (ms) as provided. The planner will convert to seconds.
"""
# durations.py

from typing import Dict, Set
from app.repositories.dance_repository import load_dance_durations, load_dance_with_types
from app.repositories.action_repository import load_action_durations, load_action_with_types
from app.repositories.expression_repository import load_expression_durations
import json
import os
import fnmatch

# Biến lưu trữ pattern
EXCLUDE_PATTERNS: Dict[str, Set[str]] = {}


def load_exclude_patterns():
    """Load patterns từ file JSON"""
    global EXCLUDE_PATTERNS
    EXCLUDE_PATTERNS = {}
    
    json_path = os.path.join(os.path.dirname(__file__), "exclude_actions.json")
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for item in data:
            model_id = item["modelId"]
            patterns = set(item["excludePattern"])
            EXCLUDE_PATTERNS[model_id] = patterns
        
        print(f"✅ Loaded exclude patterns for {len(EXCLUDE_PATTERNS)} models")
    
    except FileNotFoundError:
        print(f"⚠️ File exclude_actions.json not found at {json_path}")
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing JSON: {e}")
    except Exception as e:
        print(f"❌ Error loading exclude patterns: {e}")


def should_exclude_action(model_id: str, action_key: str) -> bool:
    """Kiểm tra action có cần loại bỏ không"""
    if model_id not in EXCLUDE_PATTERNS:
        return False
    
    for pattern in EXCLUDE_PATTERNS[model_id]:
        if fnmatch.fnmatch(action_key, pattern):
            return True
    
    return False

# Biến global để cache
DANCE_DURATIONS_MS: Dict[str, int] = {}
ACTION_DURATIONS_MS: Dict[str, int] = {}
EXPRESSION_DURATIONS_MS: Dict[str, int] = {}

# Biến global để cache type info
DANCE_TYPES: Dict[str, int] = {}  # {code: type (1|2|3)}
ACTION_TYPES: Dict[str, int] = {}  # {code: type (1|2|3)}


async def load_all_durations_with_exclusion(robot_model_id: str) -> Dict[str, Dict[str, int]]:
    """Load toàn bộ durations từ DB cho một robot model cụ thể."""
    global DANCE_DURATIONS_MS, ACTION_DURATIONS_MS, EXPRESSION_DURATIONS_MS
    global DANCE_TYPES, ACTION_TYPES

    # Đảm bảo đã load patterns
    if not EXCLUDE_PATTERNS:
        load_exclude_patterns()
    
    # ⚙️ Gọi hàm async lấy dữ liệu với type
    dance_with_types = await load_dance_with_types(robot_model_id)
    action_with_types = await load_action_with_types(robot_model_id)
    EXPRESSION_DURATIONS_MS = await load_expression_durations(robot_model_id)
    
    # Tách duration và type
    DANCE_DURATIONS_MS = {code: data['duration'] for code, data in dance_with_types.items()}
    DANCE_TYPES = {code: data['type'] for code, data in dance_with_types.items()}

    ACTION_DURATIONS_MS = {code: data['duration'] for code, data in action_with_types.items()}
    ACTION_TYPES = {code: data['type'] for code, data in action_with_types.items()}

    # Lọc action durations dựa trên pattern
    if robot_model_id in EXCLUDE_PATTERNS:
        original_count = len(ACTION_DURATIONS_MS)
        # Tạo dict mới chỉ với các action không bị exclude
        filtered_actions = {
            key: value for key, value in ACTION_DURATIONS_MS.items()
            if not should_exclude_action(robot_model_id, key)
        }
        filtered_types = {
            key: value for key, value in ACTION_TYPES.items()
            if not should_exclude_action(robot_model_id, key)
        }
        ACTION_DURATIONS_MS = filtered_actions
        ACTION_TYPES = filtered_types

        excluded_count = original_count - len(ACTION_DURATIONS_MS)
        if excluded_count > 0:
            print(f" - Excluded {excluded_count} actions based on patterns")
    
    print(f"✅ Loaded durations for robot_model_id={robot_model_id}")
    print(f" - Dances: {len(DANCE_DURATIONS_MS)} items")
    print(f" - Actions: {len(ACTION_DURATIONS_MS)} items")
    print(f" - Expressions: {len(EXPRESSION_DURATIONS_MS)} items")
    
    return {
        "dance": DANCE_DURATIONS_MS or {},
        "action": ACTION_DURATIONS_MS or {},
        "expression": EXPRESSION_DURATIONS_MS or {},
        "dance_types": DANCE_TYPES or {},
        "action_types": ACTION_TYPES or {},
    }

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