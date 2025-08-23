import io
import logging
import soundfile as sf
import numpy as np
import whisper
from fastapi import UploadFile

from app.models.stt import ASRData, STTResponse

model = whisper.load_model('base')


async def transcribe_audio(audio_file: UploadFile) -> str:
    """
    Transcribe text from an uploaded .wav file using Whisper

    Args:
        audio_file: UploadFile object containing the .wav file

    Returns:
        str: Transcribed text from the audio file

    Raises:
        HTTPException: If file is not .wav format or transcription fails
    """
    # Check if the file is a .wav file
    if not audio_file.filename.lower().endswith('.wav'):
        raise RuntimeError("Only .wav files are supported")

    # Create a temporary file to save the uploaded audio
    try:
        content = await audio_file.read()

        # Convert bytes to numpy array using soundfile
        audio_data = sf.read(io.BytesIO(content))

        # Ensure audio is in float32 format (Whisper expects this)
        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)

        # Transcribe the audio array
        result = model.transcribe(audio_data)
        return result["text"]
    except Exception as e:
        raise RuntimeError(f"Transcription failed: {str(e)}")


async def transcribe_bytes(data: ASRData):
    if whisper is None or model is None:
        raise RuntimeError("Whisper STT not available (package not installed or model failed to load)")
    try:
        logging.debug(f"Full original data array: {data.arr}")

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
    except Exception as e:
        raise RuntimeError(e)