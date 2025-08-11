from typing import List

from pydantic import BaseModel

class Section(BaseModel):
    time: int
    bps: float
    duration: int


class MusicInfo(BaseModel):
    duration: float
    sections: List[Section]
    sample_rate: float