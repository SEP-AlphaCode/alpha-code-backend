import boto3
from fastapi import UploadFile
import os
import tempfile
from pydub import AudioSegment
import shutil
from botocore.exceptions import NoCredentialsError
from dotenv import load_dotenv
import time

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
