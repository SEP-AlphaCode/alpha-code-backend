from typing import Literal, List

from pydantic import BaseModel

class DanceDefinition(BaseModel):
    id: str
    durationMs: int


class ActionBlock(BaseModel):
    action_id: str
    start_time: float
    duration: float
    action_type: str = Literal['action', 'face']


class MouthLedBlock(BaseModel):
    red: int
    green: int
    blue: int
    alpha: float
    start_time: float
    duration: float
    # Duration / beat speed
    delay: float


class DanceSequence:
    actions: List[ActionBlock]
    leds: List[MouthLedBlock]