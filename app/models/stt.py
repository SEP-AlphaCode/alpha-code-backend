from typing import List, Optional, Literal
from pydantic import BaseModel


class ASRData(BaseModel):
    arr: List[int]
    sample_rate: Optional[int] = 16000

class STTResponse(BaseModel):
    """Response model for speech-to-text transcription"""
    text: str
    language: str
    confidence: Optional[float] = None
    model_type: Literal["english", "vietnamese", "base"]


class LanguageDetectionResponse(BaseModel):
    """Response model for language detection"""
    detected_language: str
    language_code: str
    confidence: float
    all_confidences: Optional[dict] = None


class ModelStatusResponse(BaseModel):
    """Response model for model status"""
    models_loaded: bool
    base_model_loaded: bool
    english_model_loaded: bool
    vietnamese_model_loaded: bool
    vietnamese_available: bool