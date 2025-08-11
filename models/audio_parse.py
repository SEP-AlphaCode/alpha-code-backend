from typing import List

from pydantic import BaseModel

class Section(BaseModel):
    time: int
    bps: float
    duration: int


class AudioInfo(BaseModel):
    duration: float
    sections: List[Section]
    sample_rate: float


class MusicInfo(BaseModel):
    name: str
    music_file_url: str
    duration: float