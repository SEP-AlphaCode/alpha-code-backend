import boto3
from fastapi import UploadFile
import os
import tempfile
from pydub import AudioSegment
import shutil
from botocore.exceptions import NoCredentialsError, BotoCoreError, ClientError
from dotenv import load_dotenv
import time
import io
from typing import List, Optional

# Explicitly set ffmpeg path for Windows
if os.name == "nt":
    AudioSegment.converter = shutil.which("ffmpeg") or "ffmpeg"

load_dotenv()

AWS_ACCESS_KEY_ID = os.getenv("CLOUD_AWS_CREDENTIALS_ACCESS_KEY")
AWS_SECRET_ACCESS_KEY = os.getenv("CLOUD_AWS_CREDENTIALS_SECRET_KEY")
AWS_REGION = os.getenv("CLOUD_AWS_REGION_STATIC")
S3_BUCKET_NAME = os.getenv("APPLICATION_BUCKET_NAME")

s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)

# Separate Polly client (can reuse same credentials)
polly_client = boto3.client(
    "polly",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)

async def convert_audio_to_wav_and_upload(file: UploadFile):
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg is not installed or not in PATH. Please install ffmpeg.")

    suffix = os.path.splitext(file.filename)[1].lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_in:
        temp_in.write(await file.read())
        temp_in.flush()
        temp_in_path = temp_in.name

    # Đọc file input
    if suffix == ".mp4":
        audio = AudioSegment.from_file(temp_in_path, format="mp4")
    else:
        audio = AudioSegment.from_file(temp_in_path)

    # Lấy duration (giây)
    duration_seconds = round(len(audio) / 1000.0, 2)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_out:
        audio.export(temp_out.name, format="wav")
        temp_out_path = temp_out.name

    os.remove(temp_in_path)

    # Tên file khi upload lên S3 (nằm trong folder music/)
    timestamp = int(time.time() * 1000)
    download_name = os.path.splitext(file.filename)[0] + "_" + str(timestamp) + ".wav"
    s3_key = f"music/{download_name}"  # Thêm folder music

    try:
        s3_client.upload_file(
            temp_out_path,
            S3_BUCKET_NAME,
            s3_key,
            ExtraArgs={'ContentType': 'audio/wav'}
        )
        file_url = f"https://{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"
    except NoCredentialsError:
        raise RuntimeError("AWS credentials not found. Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY.")
    finally:
        os.remove(temp_out_path)

    return {
        "file_name": download_name,
        "url": file_url,
        "duration": duration_seconds
    }


# ==============================
# Text -> Speech (WAV) via Polly (S3 upload)
# ==============================
POLLY_DEFAULT_VOICE = os.getenv("AWS_POLLY_VOICE", "Joanna")  # Common English female voice
POLLY_TEXT_LIMIT = 3000  # Polly max chars per request (approx)

def _split_text(text: str, limit: int) -> List[str]:
    """Split text into chunks <= limit, trying to cut at sentence boundaries."""
    if len(text) <= limit:
        return [text]
    parts: List[str] = []
    current = []
    current_len = 0
    for sentence in text.replace('\n', ' ').split('. '):
        piece = sentence.strip()
        if not piece:
            continue
        # add the period back if it was there originally
        if not piece.endswith('.'):
            piece += '.'
        if current_len + len(piece) + 1 > limit and current:
            parts.append(' '.join(current).strip())
            current = [piece]
            current_len = len(piece)
        else:
            current.append(piece)
            current_len += len(piece) + 1
    if current:
        parts.append(' '.join(current).strip())
    return parts

async def text_to_wav_and_upload(text: str, voice: Optional[str] = None):
    """
    Convert input text to speech (WAV) using AWS Polly, upload to S3, return metadata.

    Returns: { file_name, url, duration, voice, text_length }
    """
    if not text or not text.strip():
        raise RuntimeError("Text is empty")
    if not AWS_ACCESS_KEY_ID or not AWS_SECRET_ACCESS_KEY:
        raise RuntimeError("Missing AWS credentials for Polly")

    use_voice = voice or POLLY_DEFAULT_VOICE

    # Chunk text if longer than limit
    chunks = _split_text(text.strip(), POLLY_TEXT_LIMIT)
    segments: List[AudioSegment] = []
    try:
        for chunk in chunks:
            try:
                resp = polly_client.synthesize_speech(
                    Text=chunk,
                    VoiceId=use_voice,
                    OutputFormat='mp3'
                )
            except ClientError as e:
                code = e.response.get('Error', {}).get('Code')
                if code == 'AccessDeniedException':
                    raise RuntimeError(
                        "Access denied for Polly SynthesizeSpeech. Ensure the IAM user/role has a policy allowing polly:SynthesizeSpeech and polly:ListVoices."
                    ) from e
                raise RuntimeError(f"Polly synthesize_speech failed: {e}")
            except BotoCoreError as e:
                raise RuntimeError(f"Polly synthesize_speech core error: {e}")
            audio_stream = resp.get('AudioStream')
            if not audio_stream:
                raise RuntimeError("Polly returned no AudioStream")
            mp3_bytes = audio_stream.read()
            segments.append(AudioSegment.from_file(io.BytesIO(mp3_bytes), format='mp3'))

        if not segments:
            raise RuntimeError("No audio segments generated")

        final_audio = segments[0]
        for seg in segments[1:]:
            final_audio += seg

        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_out:
            final_audio.export(temp_out.name, format='wav')
            wav_path = temp_out.name

        duration_seconds = round(len(final_audio) / 1000.0, 2)

        # Naming: tts_<timestamp>.wav
        timestamp = int(time.time() * 1000)
        download_name = f"tts_{timestamp}.wav"
        s3_key = f"tts/{download_name}"

        try:
            s3_client.upload_file(
                wav_path,
                S3_BUCKET_NAME,
                s3_key,
                ExtraArgs={'ContentType': 'audio/wav'}
            )
            file_url = f"https://{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"
        except NoCredentialsError:
            raise RuntimeError("AWS credentials not found for S3 upload")
        finally:
            if os.path.exists(wav_path):
                os.remove(wav_path)

        return {
            "file_name": download_name,
            "url": file_url,
            "duration": duration_seconds,
            "voice": use_voice,
            "text_length": len(text)
        }
    finally:
        # Ensure any opened AudioStream objects are closed
        for seg in segments:
            pass  # pydub handles memory cleanup; nothing explicit required


# ==============================
# Simple local TTS (using Polly) - no S3, just save to /tmp or configurable folder
# ==============================
LOCAL_TTS_OUTPUT_DIR = os.getenv("LOCAL_TTS_OUTPUT_DIR", os.path.join(tempfile.gettempdir(), "alpha_tts"))
os.makedirs(LOCAL_TTS_OUTPUT_DIR, exist_ok=True)

async def text_to_wav_local(text: str, voice: Optional[str] = None):
    """Generate WAV from text and save locally. Return local file path & metadata.

    This reuses AWS Polly but skips S3 upload. Caller can serve or move the file.
    """
    if not text or not text.strip():
        raise RuntimeError("Text is empty")
    use_voice = voice or POLLY_DEFAULT_VOICE

    chunks = _split_text(text.strip(), POLLY_TEXT_LIMIT)
    segments: List[AudioSegment] = []
    for chunk in chunks:
        try:
            resp = polly_client.synthesize_speech(Text=chunk, VoiceId=use_voice, OutputFormat='mp3')
        except ClientError as e:
            code = e.response.get('Error', {}).get('Code')
            if code == 'AccessDeniedException':
                raise RuntimeError(
                    "Access denied for Polly SynthesizeSpeech. Grant IAM permission polly:SynthesizeSpeech (and optionally polly:ListVoices)."
                ) from e
            raise
        except BotoCoreError as e:
            raise RuntimeError(f"Polly core error: {e}")
        audio_stream = resp.get('AudioStream')
        if not audio_stream:
            raise RuntimeError("Polly returned no AudioStream")
        mp3_bytes = audio_stream.read()
        segments.append(AudioSegment.from_file(io.BytesIO(mp3_bytes), format='mp3'))
    if not segments:
        raise RuntimeError("No audio produced")
    final_audio = segments[0]
    for seg in segments[1:]:
        final_audio += seg

    timestamp = int(time.time() * 1000)
    file_name = f"tts_local_{timestamp}.wav"
    out_path = os.path.join(LOCAL_TTS_OUTPUT_DIR, file_name)
    final_audio.export(out_path, format='wav')
    duration_seconds = round(len(final_audio) / 1000.0, 2)
    return {
        "file_name": file_name,
        "path": out_path,
        "duration": duration_seconds,
        "voice": use_voice,
        "text_length": len(text)
    }

