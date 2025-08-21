from fastapi import APIRouter, HTTPException
try:
    import whisper  # type: ignore
except ImportError:
    whisper = None  # Fallback if package missing
import numpy as np
from app.models.stt import ASRData, STTResponse

router = APIRouter()
model = None
if whisper is not None:
    try:
        model = whisper.load_model('tiny', device='cpu')
    except Exception:
        model = None

@router.post('')
async def transcribe_audio(data: ASRData):
    if whisper is None or model is None:
        raise HTTPException(status_code=501, detail="Whisper STT not available (package not installed or model failed to load)")
    # 1. Convert list of ints -> raw bytes
    byte_array = np.array(data.arr, dtype=np.int8).tobytes()

    # 2. Convert raw bytes -> int16 samples (little-endian PCM 16-bit)
    audio_array = np.frombuffer(byte_array, dtype="<i2")
    # 4. Run Whisper transcription (requires file path or numpy)
    # Use numpy directly (float32 normalized)
    float_audio = audio_array.astype(np.float32) / 32768.0
    result = model.transcribe(float_audio, fp16=False)
    transcript = result["text"].strip()
    return STTResponse(text=transcript)