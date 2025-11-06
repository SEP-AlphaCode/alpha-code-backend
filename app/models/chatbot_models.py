"""
Pydantic models for Chatbot API
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class ChatbotQuery(BaseModel):
    """Request model for chatbot query"""
    question: str = Field(..., description="User's question", min_length=1, max_length=1000)
    top_k: Optional[int] = Field(default=5, description="Number of documents to retrieve", ge=1, le=20)
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Metadata filters for retrieval (optional)")
    

class RetrievedDocumentResponse(BaseModel):
    """Model for a retrieved document"""
    id: str
    content: str
    metadata: Dict[str, Any]
    score: float


class ChatbotResponse(BaseModel):
    """Response model for chatbot"""
    question: str
    answer: str
    has_answer: bool
    documents_used: int
    documents: List[RetrievedDocumentResponse] = []
    model: Optional[str] = None
    provider: Optional[str] = None
    tokens_used: Optional[Dict[str, int]] = None
    retrieval_stats: Optional[Dict[str, Any]] = None
