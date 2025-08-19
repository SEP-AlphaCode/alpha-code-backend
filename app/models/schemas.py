from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class AudioFormat(str, Enum):
    MP3 = "mp3"
    WAV = "wav"
    FLAC = "flac"
    M4A = "m4a"
    AAC = "aac"

class RobotAction(str, Enum):
    DANCE = "dance"
    WALK = "walk"
    ARM_MOVEMENT = "arm_movement"
    HEAD_MOVEMENT = "head_movement"
    POSE = "pose"
    STOP = "stop"

class MusicAnalysisRequest(BaseModel):
    filename: str
    analyze_tempo: bool = True
    analyze_beats: bool = True
    analyze_spectral: bool = True
    generate_choreography: bool = True

class MusicAnalysisResult(BaseModel):
    id: str
    filename: str
    duration: float
    tempo: Optional[float] = None
    beats: Optional[List[float]] = None
    spectral_features: Optional[Dict[str, Any]] = None
    energy_analysis: Optional[Dict[str, Any]] = None
    analysis_timestamp: datetime
    file_path: str

class BeatInfo(BaseModel):
    time: float
    confidence: float
    intensity: float

class ChoreographySegment(BaseModel):
    start_time: float
    end_time: float
    actions: List['RobotActionData'] = []  # Forward reference to RobotActionData
    tempo: Optional[float] = None
    energy_level: Optional[float] = None
    primary_emotion: Optional[str] = None
    parameters: Dict[str, Any] = {}
    notes: Optional[str] = ""

class ChoreographyData(BaseModel):
    id: str
    music_analysis_id: str
    filename: str
    duration: float
    segments: List[ChoreographySegment]
    style: str = "ai_generated"
    created_at: str  # ISO format datetime string
    metadata: Dict[str, Any] = {}

class RobotStatus(BaseModel):
    connected: bool
    battery_level: Optional[int] = None
    current_action: Optional[RobotAction] = None
    position: Optional[Dict[str, float]] = None
    timestamp: datetime

class RobotCommand(BaseModel):
    action: RobotAction
    parameters: Dict[str, Any]
    duration: Optional[float] = None
    ubx_file: Optional[str] = None

class RobotActionData(BaseModel):
    """Data class để đại diện cho robot action với thông tin chi tiết"""
    type: str
    name: str
    start_time: float
    duration: float
    intensity: str  # Changed from float to str to accept 'low', 'medium', 'high'
    parameters: Dict[str, Any] = {}

class UploadResponse(BaseModel):
    success: bool
    message: str
    file_id: Optional[str] = None
    filename: Optional[str] = None
