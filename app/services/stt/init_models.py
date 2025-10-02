# app/services/stt/models.py
import logging
import whisper
from typing import Tuple, Optional, Dict, Any
import torch

# Try to import Vietnamese model dependencies
try:
    from transformers import Wav2Vec2Processor, Wav2Vec2ForCTC
    
    VIETNAMESE_AVAILABLE = True
except ImportError:
    logging.warning(
        "Vietnamese model dependencies not installed. Install transformers and torch for Vietnamese support.")
    VIETNAMESE_AVAILABLE = False
    torch = None
    Wav2Vec2Processor = None
    Wav2Vec2ForCTC = None

device = "cuda" if torch.cuda.is_available() else "cpu"
print(device)

class STTModels:
    """Class to manage all STT model instances"""
    
    def __init__(self):
        self.base_model = None
        self.english_model = None
        self.vietnamese_processor = None
        self.vietnamese_model = None
        self.models_loaded = False  # This was missing!
    
    def load_models(self):
        """Load all STT models"""
        try:
            logging.info("Loading Whisper base model...")
            self.base_model = whisper.load_model('small', device)
            
            logging.info("Loading Whisper English model...")
            self.english_model = whisper.load_model('base.en', device)  # or 'large' for best accuracy
            model_name = "nguyenvulebinh/wav2vec2-base-vi-vlsp2020"
            if VIETNAMESE_AVAILABLE:
                logging.info("Loading Vietnamese model...")
                self.vietnamese_processor = Wav2Vec2Processor.from_pretrained(
                    model_name
                )
                self.vietnamese_model = Wav2Vec2ForCTC.from_pretrained(
                    model_name
                )
            
            self.models_loaded = True
            logging.info("All STT models loaded successfully")
        
        except Exception as e:
            logging.error(f"Failed to load STT models: {e}")
            self.models_loaded = False
            raise
    
    def get_model_status(self) -> Dict[str, Any]:
        """Get status of all models"""
        return {
            "models_loaded": self.models_loaded,
            "base_model_loaded": self.base_model is not None,
            "english_model_loaded": self.english_model is not None,
            "vietnamese_model_loaded": self.vietnamese_model is not None,
            "vietnamese_available": VIETNAMESE_AVAILABLE
        }


# Global instance
stt_models = STTModels()