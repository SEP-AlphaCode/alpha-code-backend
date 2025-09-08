from pydantic import BaseModel
from typing import List, Optional


class Detection(BaseModel):
    label: str
    confidence: float
    bbox: List[int]
    depth_avg: Optional[float] = None
    depth_min: Optional[float] = None
    depth_median: Optional[float] = None


class DetectResponse(BaseModel):
    objects: List[Detection]


class DetectClosestResponse(BaseModel):
    closest_objects: List[Detection]
    all_objects: List[Detection]
