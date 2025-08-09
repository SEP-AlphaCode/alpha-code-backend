import librosa
import numpy as np
from scipy.signal import find_peaks
from typing import List, Dict, Tuple, Any
import json
import os
from datetime import datetime
import uuid

from app.core.config import settings
from app.models.schemas import MusicAnalysisResult, BeatInfo

class MusicAnalysisService:
    """Service chính để phân tích file nhạc và trích xuất đặc trưng âm thanh"""

    def __init__(self):
        self.sample_rate = settings.SAMPLE_RATE if hasattr(settings, 'SAMPLE_RATE') else 22050
        self.hop_length = settings.HOP_LENGTH if hasattr(settings, 'HOP_LENGTH') else 512
        self.frame_length = settings.FRAME_LENGTH if hasattr(settings, 'FRAME_LENGTH') else 2048

    async def analyze_audio_file(self, file_path: str, filename: str) -> MusicAnalysisResult:
        """Phân tích file nhạc và trả về kết quả phân tích"""
        try:
            print(f"Analyzing audio file: {filename}")

            # Load audio file
            y, sr = librosa.load(file_path, sr=self.sample_rate)
            duration = librosa.get_duration(y=y, sr=sr)

            print(f"Audio loaded - Duration: {duration:.2f}s, Sample rate: {sr}")

            # Phân tích tempo và beats
            tempo, beats = self._analyze_tempo_and_beats(y, sr)

            # Phân tích đặc trưng phổ
            spectral_features = self._analyze_spectral_features(y, sr)

            # Phân tích cường độ âm thanh
            energy_analysis = self._analyze_energy_levels(y, sr)

            # Tạo ID unique cho analysis
            analysis_id = str(uuid.uuid4())

            # Lưu kết quả phân tích
            result = MusicAnalysisResult(
                id=analysis_id,
                filename=filename,
                duration=duration,
                tempo=tempo,
                beats=beats.tolist() if beats is not None else [],
                spectral_features=spectral_features,
                energy_analysis=energy_analysis,
                analysis_timestamp=datetime.now(),
                file_path=file_path
            )

            # Lưu kết quả vào file JSON
            await self._save_analysis_result(result)

            print(f"Analysis completed - Tempo: {tempo:.1f} BPM, Beats: {len(beats) if beats is not None else 0}")

            return result

        except Exception as e:
            print(f"Error analyzing audio file: {str(e)}")
            raise

    def _analyze_tempo_and_beats(self, y: np.ndarray, sr: int) -> Tuple[float, np.ndarray]:
        """Phân tích tempo và vị trí các beats"""
        try:
            # Estimate tempo and beat frames
            tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, hop_length=self.hop_length)

            # Convert beat frames to time in seconds
            beat_times = librosa.frames_to_time(beat_frames, sr=sr, hop_length=self.hop_length)

            return float(tempo), beat_times

        except Exception as e:
            print(f"Error in tempo analysis: {e}")
            return 120.0, np.array([])

    def _analyze_spectral_features(self, y: np.ndarray, sr: int) -> Dict[str, Any]:
        """Phân tích đặc trưng phổ của âm thanh"""
        try:
            # Tính MFCC (Mel-frequency cepstral coefficients)
            mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)

            # Tính spectral centroid (tần số trung tâm)
            spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)

            # Tính chroma features
            chroma = librosa.feature.chroma_stft(y=y, sr=sr)

            # Tính zero crossing rate
            zcr = librosa.feature.zero_crossing_rate(y)

            return {
                "mfcc_mean": np.mean(mfccs, axis=1).tolist(),
                "mfcc_std": np.std(mfccs, axis=1).tolist(),
                "spectral_centroid_mean": float(np.mean(spectral_centroids)),
                "spectral_centroid_std": float(np.std(spectral_centroids)),
                "chroma_mean": np.mean(chroma, axis=1).tolist(),
                "chroma_std": np.std(chroma, axis=1).tolist(),
                "zcr_mean": float(np.mean(zcr)),
                "zcr_std": float(np.std(zcr))
            }

        except Exception as e:
            print(f"Error in spectral analysis: {e}")
            return {}

    def _analyze_energy_levels(self, y: np.ndarray, sr: int) -> Dict[str, Any]:
        """Phân tích mức năng lượng âm thanh theo thời gian"""
        try:
            # Tính RMS energy
            rms = librosa.feature.rms(y=y, hop_length=self.hop_length)

            # Tính onset strength
            onset_envelope = librosa.onset.onset_strength(y=y, sr=sr, hop_length=self.hop_length)

            # Tìm peaks trong onset envelope
            peaks, _ = find_peaks(onset_envelope, height=np.mean(onset_envelope))

            # Convert frames to time
            times = librosa.times_like(rms, sr=sr, hop_length=self.hop_length)
            peak_times = librosa.frames_to_time(peaks, sr=sr, hop_length=self.hop_length)

            return {
                "rms_energy": rms[0].tolist(),
                "rms_times": times.tolist(),
                "onset_strength": onset_envelope.tolist(),
                "onset_peaks": peak_times.tolist(),
                "energy_mean": float(np.mean(rms)),
                "energy_std": float(np.std(rms)),
                "peak_count": len(peaks)
            }

        except Exception as e:
            print(f"Error in energy analysis: {e}")
            return {}

    async def _save_analysis_result(self, result: MusicAnalysisResult):
        """Lưu kết quả phân tích vào file JSON"""
        try:
            analysis_dir = "data/analysis"
            os.makedirs(analysis_dir, exist_ok=True)

            filename = f"{result.id}.json"
            filepath = os.path.join(analysis_dir, filename)

            # Convert to dict and save
            result_dict = {
                "id": result.id,
                "filename": result.filename,
                "duration": result.duration,
                "tempo": result.tempo,
                "beats": result.beats,
                "spectral_features": result.spectral_features,
                "energy_analysis": result.energy_analysis,
                "analysis_timestamp": result.analysis_timestamp.isoformat(),
                "file_path": result.file_path
            }

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(result_dict, f, indent=2, ensure_ascii=False)

            print(f"Analysis result saved to: {filepath}")

        except Exception as e:
            print(f"Error saving analysis result: {e}")

    async def load_analysis_result(self, analysis_id: str) -> MusicAnalysisResult:
        """Load kết quả phân tích từ file JSON"""
        try:
            filepath = os.path.join("data/analysis", f"{analysis_id}.json")

            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            return MusicAnalysisResult(
                id=data["id"],
                filename=data["filename"],
                duration=data["duration"],
                tempo=data["tempo"],
                beats=data["beats"],
                spectral_features=data["spectral_features"],
                energy_analysis=data["energy_analysis"],
                analysis_timestamp=datetime.fromisoformat(data["analysis_timestamp"]),
                file_path=data["file_path"]
            )

        except Exception as e:
            print(f"Error loading analysis result: {e}")
            raise

    def get_beat_segments(self, beats: List[float], duration: float, min_segment_length: float = 0.5) -> List[Tuple[float, float]]:
        """Tạo các segments dựa trên beats"""
        print(f"Debug: Creating segments from {len(beats) if beats else 0} beats, duration: {duration}s, min_length: {min_segment_length}s")

        if not beats or len(beats) < 2:
            print("Debug: Not enough beats, using fallback method")
            # Fallback: tạo segments đều
            segments = []
            segment_length = max(min_segment_length, duration / 8)  # Chia làm 8 phần
            for i in range(int(duration / segment_length)):
                start = i * segment_length
                end = min((i + 1) * segment_length, duration)
                segments.append((start, end))
            print(f"Debug: Created {len(segments)} fallback segments")
            return segments

        segments = []
        # Tạo segments từ beats, nhóm beats lại nếu cần
        i = 0
        while i < len(beats) - 1:
            start_time = beats[i]

            # Tìm beat tiếp theo tạo segment đủ dài
            j = i + 1
            while j < len(beats) and (beats[j] - start_time) < min_segment_length:
                j += 1

            if j < len(beats):
                end_time = beats[j]
                segments.append((start_time, end_time))
                i = j
            else:
                # Nếu không tìm được beat phù hợp, tạo segment cuối
                end_time = min(start_time + min_segment_length * 2, duration)
                segments.append((start_time, end_time))
                break

        # Đảm bảo có ít nhất một vài segments
        if not segments and duration > 0:
            print("Debug: No segments created, adding fallback segments")
            # Tạo ít nhất 3 segments
            segment_duration = duration / 3
            for i in range(3):
                start = i * segment_duration
                end = min((i + 1) * segment_duration, duration)
                segments.append((start, end))

        print(f"Debug: Created {len(segments)} segments: {segments[:5]}")  # Show first 5
        return segments


# Global service instance
music_analysis_service = MusicAnalysisService()
