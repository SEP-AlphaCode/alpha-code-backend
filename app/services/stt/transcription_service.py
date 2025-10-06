# app/services/stt/transcription_service.py
import io
import logging
import wave

import soundfile as sf
import numpy as np
import librosa
import torch
import whisper
from fastapi import UploadFile
from typing import Tuple, Optional

from app.models.stt import ASRData, STTResponse, LanguageDetectionResponse, ModelStatusResponse
from app.services.stt.init_models import stt_models, VIETNAMESE_AVAILABLE

# Initialize models on import
try:
    stt_models.load_models()
except Exception as e:
    logging.error(f"Failed to initialize STT models: {e}")


async def detect_language(audio_array: np.ndarray, sample_rate: int = 16000) -> LanguageDetectionResponse:
    """
    Detect the primary language in the audio using Whisper's language detection

    Args:
        audio_array: Audio data as numpy array
        sample_rate: Sample rate of the audio

    Returns:
        LanguageDetectionResponse: Language detection results
    """
    if not stt_models.models_loaded or not stt_models.base_model:
        logging.warning("Base model not loaded, defaulting to English")
        return LanguageDetectionResponse(
            detected_language="English",
            language_code="en",
            confidence=1.0
        )
    try:
        if not stt_models.base_model:
            raise RuntimeError("Base model not loaded")
        
        # Ensure audio is at 16kHz for Whisper
        if sample_rate != 16000:
            audio_resampled = librosa.resample(audio_array, orig_sr=sample_rate, target_sr=16000)
        else:
            audio_resampled = audio_array
        
        # Use Whisper to detect language
        audio_for_detect = audio_resampled.astype(np.float32)
        if audio_for_detect.ndim > 1:
            audio_for_detect = audio_for_detect.mean(axis=1)  # Convert to mono
        
        # Pad/trim to 30 seconds as Whisper expects
        if len(audio_for_detect) < 16000 * 30:
            padding = 16000 * 30 - len(audio_for_detect)
            audio_for_detect = np.pad(audio_for_detect, (0, padding))
        else:
            audio_for_detect = audio_for_detect[:16000 * 30]
        
        # Detect language
        mel = whisper.log_mel_spectrogram(audio_for_detect).to(stt_models.base_model.device)
        _, probs = stt_models.base_model.detect_language(mel)
        detected_language = max(probs, key=probs.get)
        confidence = probs[detected_language]
        
        return LanguageDetectionResponse(
            detected_language=detected_language,
            language_code=detected_language,
            confidence=confidence,
            all_confidences=dict(probs)
        )
    
    except Exception as e:
        logging.warning(f"Language detection failed: {e}, defaulting to English")
        return LanguageDetectionResponse(
            detected_language="English",
            language_code="en",
            confidence=1.0
        )


async def transcribe_english(audio_array: np.ndarray, sample_rate: int = 16000) -> Tuple[str, float]:
    """
    Transcribe English audio using specialized English model
    """
    try:
        if not stt_models.english_model:
            raise RuntimeError("English model not loaded")
        
        # Resample to 16kHz if needed
        if sample_rate != 16000:
            audio_array = librosa.resample(audio_array, orig_sr=sample_rate, target_sr=16000)
        
        # Ensure proper format
        audio_float = audio_array.astype(np.float32)
        if audio_float.ndim > 1:
            audio_float = audio_float.mean(axis=1)  # Convert to mono
            
            # Ensure model is on GPU
        stt_models.english_model = stt_models.english_model.to("cuda")
        
        # Transcribe with English-optimized model on GPU
        result = stt_models.english_model.transcribe(
            audio_float,
            language='en',
            fp16=True,  # Use FP16 for faster inference on GPU
            best_of=5,
            beam_size=5
        )
        
        # Safe confidence calculation with multiple fallbacks
        avg_confidence = calculate_confidence(result)
        
        return result["text"].strip(), avg_confidence
    
    except Exception as e:
        logging.error(f"English transcription failed: {e}, falling back to base model")
        # Ensure base model is on GPU
        stt_models.base_model = stt_models.base_model.to("cuda")
        result = stt_models.base_model.transcribe(
            audio_array,
            language='en',
            fp16=True  # Use FP16 on GPU
        )
        avg_confidence = calculate_confidence(result)
        return result["text"].strip(), avg_confidence


def calculate_confidence(result: dict) -> float:
    """
    Safely calculate average confidence from Whisper result with multiple fallbacks
    """
    try:
        # Method 1: Check if segments exist and have confidence
        segments = result.get('segments', [])
        if segments and 'confidence' in segments[0]:
            confidences = [seg.get('confidence', 0.0) for seg in segments]
            return np.mean(confidences) if confidences else 0.0
        
        # Method 2: Check for word-level confidence
        elif segments and 'words' in segments[0] and segments[0]['words']:
            word_confidences = []
            for seg in segments:
                words = seg.get('words', [])
                if words and 'confidence' in words[0]:
                    word_confidences.extend([word.get('confidence', 0.0) for word in words])
            if word_confidences:
                return np.mean(word_confidences)
        
        # Method 3: Return a default confidence based on text length
        text = result.get('text', '').strip()
        if len(text) > 0:
            return 0.8  # Default medium confidence for non-empty text
        else:
            return 0.0  # No text detected
    
    except Exception as e:
        logging.warning(f"Confidence calculation failed: {e}, using default")
        return 0.5  # Fallback confidence


async def transcribe_vietnamese2(audio_array: np.ndarray, sample_rate: int = 16000) -> Tuple[str, float]:
    """
    Transcribe English audio using specialized English model

    Args:
        audio_array: Audio data as numpy array
        sample_rate: Sample rate of the audio

    Returns:
        tuple: (transcribed_text, average_confidence)
    """
    try:
        if not stt_models.base_model:
            raise RuntimeError("English model not loaded")
        
        # Resample to 16kHz if needed
        if sample_rate != 16000:
            audio_array = librosa.resample(audio_array, orig_sr=sample_rate, target_sr=16000)
        
        # Ensure proper format
        audio_float = audio_array.astype(np.float32)
        if audio_float.ndim > 1:
            audio_float = audio_float.mean(axis=1)  # Convert to mono
        
        # Transcribe with English-optimized model
        result = stt_models.base_model.transcribe(
            audio_float,
            language='vi',
            fp16=False,
            best_of=5,
            beam_size=5
        )
        
        # Safe confidence calculation with multiple fallbacks
        avg_confidence = calculate_confidence(result)
        
        return result["text"].strip(), avg_confidence
    
    except Exception as e:
        logging.error(f"English transcription failed: {e}, falling back to base model")
        result = stt_models.base_model.transcribe(audio_array, language='en', fp16=False)
        avg_confidence = calculate_confidence(result)
        return result["text"].strip(), avg_confidence


async def transcribe_vietnamese(audio_array: np.ndarray, sample_rate: int = 16000) -> Tuple[str, float]:
    """
    Transcribe Vietnamese audio using specialized Vietnamese model
    """
    if not VIETNAMESE_AVAILABLE or not stt_models.vietnamese_model:
        logging.warning("Vietnamese model not available, falling back to Whisper")
        result = stt_models.base_model.transcribe(audio_array, language='vi', fp16=False)
        avg_confidence = calculate_confidence(result)
        return result["text"].strip(), avg_confidence
    
    try:
        # Resample to 16kHz for wav2vec2 model
        if sample_rate != 16000:
            audio_array = librosa.resample(audio_array, orig_sr=sample_rate, target_sr=16000)
        
        # Convert to mono if stereo
        if audio_array.ndim > 1:
            audio_array = audio_array.mean(axis=1)
        
        # Normalize audio
        audio_array = audio_array / np.max(np.abs(audio_array))
        
        # Process with Vietnamese model
        input_values = stt_models.vietnamese_processor(
            audio_array,
            sampling_rate=16000,
            return_tensors="pt",
            padding=True
        ).input_values
        
        # Get logits
        with torch.no_grad():
            logits = stt_models.vietnamese_model(input_values).logits
        
        # Get predicted tokens
        predicted_ids = torch.argmax(logits, dim=-1)
        transcription = stt_models.vietnamese_processor.batch_decode(predicted_ids)[0]
        
        # For wav2vec2, we don't get confidence scores easily, so use a default
        confidence = 0.8  # Default confidence for Vietnamese model
        
        return transcription.strip(), confidence
    
    except Exception as e:
        logging.error(f"Vietnamese transcription failed: {e}, falling back to Whisper")
        result = stt_models.base_model.transcribe(audio_array, language='vi', fp16=False)
        avg_confidence = calculate_confidence(result)
        return result["text"].strip(), avg_confidence


async def transcribe_bytes_vip(data: ASRData) -> STTResponse:
    """
    Transcribe audio from byte array with language detection and specialized models
    """
    if not stt_models.models_loaded or not stt_models.base_model:
        raise RuntimeError("STT models not available or not loaded properly")
    
    try:
        # Convert list of ints -> raw bytes -> int16 samples
        byte_array = np.array(data.arr, dtype=np.int8).tobytes()
        audio_array = np.frombuffer(byte_array, dtype="<i2")
        
        # Convert to float32 and normalize
        float_audio = audio_array.astype(np.float32) / 32768.0
        
        # Use provided sample rate or default to 16kHz
        sample_rate = data.sample_rate or 16000
        
        # await save_pcm_as_wav(data, "output.wav")
        # print('Save to wav successfully')
        
        # Detect language
        language_result = await detect_language(float_audio, sample_rate)
        language_code = language_result.language_code
        
        print(language_code)
        # Route to appropriate model
        if language_code == 'vi':
            transcription, confidence = await transcribe_vietnamese2(float_audio, sample_rate)
            model_type = "vietnamese"
        else:
            transcription, confidence = await transcribe_english(float_audio, sample_rate)
            model_type = "english"
        
        return STTResponse(
            text=transcription,
            language=language_code,
            confidence=confidence,
            model_type=model_type
        )
    
    except Exception as e:
        raise RuntimeError(f"Transcription failed: {str(e)}")


async def get_model_status() -> ModelStatusResponse:
    """Get the status of all loaded models"""
    status_dict = stt_models.get_model_status()
    return ModelStatusResponse(**status_dict)


async def force_reload_models():
    """Force reload all models (useful for memory management)"""
    try:
        # Clear existing models
        if stt_models.base_model:
            del stt_models.base_model
        if stt_models.english_model:
            del stt_models.english_model
        if stt_models.vietnamese_model:
            del stt_models.vietnamese_model
        if stt_models.vietnamese_processor:
            del stt_models.vietnamese_processor
        
        # Reload models
        stt_models.load_models()
        logging.info("Models reloaded successfully")
    
    except Exception as e:
        logging.error(f"Failed to reload models: {e}")
        raise


async def save_pcm_as_wav(data: ASRData, filename: str = "output.wav"):
    """
    Reconstruct PCM data and save as WAV file
    """
    try:
        # Convert list of ints -> raw bytes -> int16 samples
        byte_array = np.array(data.arr, dtype=np.int8).tobytes()
        audio_array = np.frombuffer(byte_array, dtype="<i2")
        
        # Use provided sample rate or default to 16kHz
        sample_rate = data.sample_rate or 16000
        
        # Save as WAV file
        with wave.open(filename, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 2 bytes = 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_array.tobytes())
        
        print(f"Audio saved as {filename}")
        return filename
    
    except Exception as e:
        raise RuntimeError(f"Failed to save audio: {str(e)}")
