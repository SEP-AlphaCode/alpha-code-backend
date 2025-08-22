import io
import soundfile as sf
import numpy as np
import whisper
from fastapi import UploadFile

model = whisper.load_model('base')


async def stt(audio_file: UploadFile) -> str:
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
        audio_data, sample_rate = sf.read(io.BytesIO(content))

        # Ensure audio is in float32 format (Whisper expects this)
        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)

        # Transcribe the audio array
        result = model.transcribe(audio_data)
        return result["text"]
    except Exception as e:
        raise RuntimeError(f"Transcription failed: {str(e)}")