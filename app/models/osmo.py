from pydantic import BaseModel
from typing import List, Optional
from fastapi.responses import JSONResponse
from datetime import datetime
from uuid import UUID

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
    direction: Optional[OsmoCard] = None
    step: Optional[OsmoCard] = None    # step card (yellow, value)

class ActionCardList(BaseModel):
    action_cards: List[ActionCard]

class AlphaMiniAction(BaseModel):
    action: str
    value: Optional[int] = None

class AlphaMiniActionList(BaseModel):
    actions: List[AlphaMiniAction]


class OsmoCardRead(BaseModel):
    id: UUID
    color: str
    name: str
    status: int
    expression_id: Optional[UUID]
    action_id: Optional[UUID]
    dance_id: Optional[UUID]
    skill_id: Optional[UUID]
    extended_action_id: Optional[UUID]
    created_date: datetime
    last_updated: Optional[datetime]

    class Config:
        orm_mode = True