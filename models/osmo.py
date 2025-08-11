from pydantic import BaseModel
from typing import List, Optional
from fastapi.responses import JSONResponse

# ------------------ Models ------------------

class OsmoCard(BaseModel):
    color: str
    direction: Optional[str] = None
    value: Optional[int] = None

class OsmoAction(BaseModel):
    type: str  # e.g., 'move_forward', 'jump_forward'
    color: str
    step_value: int

class OsmoActionList(BaseModel):
    actions: List[OsmoAction]

class OsmoCardSequence(BaseModel):
    cards: List[OsmoCard]

class ActionCard(BaseModel):
    action: OsmoCard  # action card (blue, red, orange, gray)
    direction: OsmoCard
    step: OsmoCard    # step card (yellow, value)

class ActionCardList(BaseModel):
    action_cards: List[ActionCard]

class AlphaMiniAction(BaseModel):
    action: str
    value: Optional[int] = None

class AlphaMiniActionList(BaseModel):
    actions: List[AlphaMiniAction]
