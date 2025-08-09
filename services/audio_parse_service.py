from fastapi import UploadFile
from typing import Dict
from models.action import DanceSequence
from pathlib import Path

current_dir = Path(__file__).parent  # Gets directory containing service.py
action_file_path = current_dir.parent / "local_files" / "available_actions.txt"

async def generate_sequence(file: UploadFile) -> DanceSequence:
    action_pool = await load_data()
    # Parse file here...
    result = DanceSequence()
    result.actions = []
    result.leds = []
    return result

async def load_data() -> Dict[str, int]:
    file = open(action_file_path)
    rs: Dict[str, int] = dict()
    for line in file:
        comp = line.strip().split()
        rs[comp[0]] = int(comp[1])
    return rs