# app/services/stt/models.py
import logging
import whisper
from typing import Tuple, Optional, Dict, Any
import torch
from transformers import pipeline

# device = "cuda" if torch.cuda.is_available() else "cpu"
# print(device)

class STTModels:
    """Class to manage all STT model instances"""
    
    def __init__(self):
        self.base_model = None
        self.english_model = None
        self.vietnamese_model = None
        self.models_loaded = False  # This was missing!
    
    def load_models(self):
        """Load all STT models"""
        try:
            logging.info("Loading Whisper base model...")
            self.base_model = whisper.load_model('base')
            
            logging.info("Loading Whisper English model...")
            self.english_model = whisper.load_model('small.en')  # or 'large' for best accuracy
            model_name = "nguyenvulebinh/wav2vec2-base-vietnamese-250h"
            logging.info("Loading Vietnamese model...")
            self.vietnamese_model = pipeline("automatic-speech-recognition", model=model_name)
            self.models_loaded = True
            logging.info("All STT models loaded successfully")
        
        except Exception as e:
            logging.error(f"Failed to load STT models: {e}")
            self.models_loaded = False
            raise


# Global instance
stt_models = STTModels()