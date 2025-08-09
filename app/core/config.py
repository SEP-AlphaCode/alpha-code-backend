from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Server settings
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "sqlite:///./alpha_mini.db"

    # File upload settings
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB
    ALLOWED_AUDIO_EXTENSIONS: list = [".mp3", ".wav", ".flac", ".m4a", ".aac"]
    ALLOWED_UBX_EXTENSIONS: list = [".ubx"]

    # Audio analysis settings
    SAMPLE_RATE: int = 22050
    HOP_LENGTH: int = 512
    FRAME_LENGTH: int = 2048

    # Robot settings
    ROBOT_IP: Optional[str] = None
    ROBOT_PORT: int = 20001
    ROBOT_TIMEOUT: int = 30

    # Choreography settings
    MIN_BPM: int = 60
    MAX_BPM: int = 180
    BEAT_THRESHOLD: float = 0.3

    class Config:
        env_file = ".env"

settings = Settings()
