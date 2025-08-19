from pydantic import BaseModel

class NLPRequest(BaseModel):
    text: str