import os
import uuid
import json
from typing import Any, Dict
from datetime import datetime
import aiofiles

async def ensure_directories():
    """Đảm bảo tất cả thư mục cần thiết đều tồn tại"""
    directories = [
        "uploads/music",
        "uploads/ubx",
        "data/analysis",
        "data/choreography"
    ]

    for directory in directories:
        os.makedirs(directory, exist_ok=True)

def generate_unique_id() -> str:
    """Tạo ID unique"""
    return str(uuid.uuid4())

async def save_json_file(data: Dict[str, Any], file_path: str):
    """Lưu dữ liệu JSON vào file"""
    async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
        await f.write(json.dumps(data, ensure_ascii=False, indent=2, default=str))

async def load_json_file(file_path: str) -> Dict[str, Any]:
    """Load dữ liệu JSON từ file"""
    async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
        content = await f.read()
        return json.loads(content)

def validate_audio_file(filename: str, allowed_extensions: list) -> bool:
    """Kiểm tra định dạng file audio"""
    return any(filename.lower().endswith(ext) for ext in allowed_extensions)

def format_duration(seconds: float) -> str:
    """Format thời gian từ giây sang mm:ss"""
    minutes = int(seconds // 60)
    seconds = int(seconds % 60)
    return f"{minutes:02d}:{seconds:02d}"

def calculate_file_size_mb(size_bytes: int) -> float:
    """Tính kích thước file theo MB"""
    return round(size_bytes / (1024 * 1024), 2)
