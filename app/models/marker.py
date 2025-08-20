from pydantic import BaseModel
from typing import List, Optional

class MarkerResponse(BaseModel):
    page_id: Optional[str]   # gộp thành chuỗi (backward-compatible)
    confidence: float
    method: str
    marker_ids: Optional[List[int]] = None  # list marker thực sự
    dict_used: Optional[str] = None         # dictionary nào detect ra
    debug_image: Optional[str] = None       # đường dẫn ảnh debug
