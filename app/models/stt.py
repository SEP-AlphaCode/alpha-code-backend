from typing import List
from pydantic import BaseModel


class ASRData(BaseModel):
    arr: List[int]

class STTResponse(BaseModel):
    text: str