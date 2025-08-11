from typing import Literal, List
import numpy as np
from pydantic import BaseModel

from models.audio_parse import MusicInfo


class DanceDefinition(BaseModel):
    id: str
    durationMs: int


class ActionBlock(BaseModel):
    action_id: str
    start_time: float
    duration: float
    action_type: str = Literal['dance', 'expression'],
    r: int
    g: int
    b: int
    a: int

    @staticmethod
    def create(action_id, start_time, duration, action_type):
        color = np.random.randint(low=0, high=256, size=4)
        return ActionBlock(action_id=action_id,
                           start_time=start_time,
                           duration=duration,
                           action_type=action_type,
                           r=int(color[0]),
                           g=int(color[1]),
                           b=int(color[2]),
                           a=int(color[3]))



class Activity(BaseModel):
    actions: List[ActionBlock]

class DanceResponse(BaseModel):
    music_info: MusicInfo
    activity: Activity