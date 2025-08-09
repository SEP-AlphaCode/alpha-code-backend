from fastapi import UploadFile
import os
import tempfile
from pydub import AudioSegment
import shutil

# Explicitly set ffmpeg path for Windows
if os.name == "nt":
    AudioSegment.converter = shutil.which("ffmpeg") or "ffmpeg"

async def convert_audio_to_wav(file: UploadFile):
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg is not installed or not in PATH. Please install ffmpeg.")

    suffix = os.path.splitext(file.filename)[1].lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_in:
        temp_in.write(await file.read())
        temp_in.flush()
        temp_in_path = temp_in.name

    # Đọc file input, với pydub ffmpeg sẽ tự tách audio khi là mp4
    if suffix == ".mp4":
        # pydub sẽ lấy audio track mp4 tự động
        audio = AudioSegment.from_file(temp_in_path, format="mp4")
    else:
        # mp3 hoặc các định dạng khác
        audio = AudioSegment.from_file(temp_in_path)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_out:
        audio.export(temp_out.name, format="wav")
        temp_out_path = temp_out.name

    os.remove(temp_in_path)
    download_name = os.path.splitext(file.filename)[0] + ".wav"
    return temp_out_path, download_name
