import json
import os
import uuid
from datetime import datetime
from typing import List, Dict, Any, Tuple
import numpy as np
import random

from app.models.schemas import (
    ChoreographyData,
    ChoreographySegment,
    RobotAction,
    MusicAnalysisResult
)
from app.services.music_analysis import music_analysis_service
from app.services.ubx_manager import ubx_manager
from app.core.config import settings

class ChoreographyService:
    """Service tạo vũ đạo tự động dựa trên phân tích nhạc"""

    def __init__(self):
        self.action_mapping_rules = self._create_action_mapping_rules()

    def _create_action_mapping_rules(self) -> Dict[str, Any]:
        """Tạo các quy tắc mapping từ đặc trưng âm thanh sang hành động robot"""
        return {
            "tempo_ranges": {
                "slow": {"min": 60, "max": 90},
                "medium": {"min": 90, "max": 130},
                "fast": {"min": 130, "max": 200}
            },
            "energy_thresholds": {
                "low": 0.3,
                "medium": 0.6,
                "high": 0.8
            }
        }

    async def create_choreography_from_analysis(self, music_analysis: MusicAnalysisResult,
                                               style_preferences: Dict[str, Any] = None) -> ChoreographyData:
        """Tạo vũ đạo tự động từ kết quả phân tích nhạc"""
        try:
            print(f"Creating choreography for: {music_analysis.filename}")

            # Tạo segments dựa trên beats
            segments = music_analysis_service.get_beat_segments(
                music_analysis.beats,
                music_analysis.duration,
                min_segment_length=1.0  # Tăng thời gian tối thiểu để phù hợp với UBX
            )

            print(f"Generated {len(segments)} segments from beats")

            # Tạo choreography segments với UBX actions
            choreography_segments = []

            # Thêm opening action
            if segments:
                opening_segment = self._create_opening_segment(segments[0][0], music_analysis)
                choreography_segments.append(opening_segment)

            # Tạo main segments
            for i, (start_time, end_time) in enumerate(segments):
                segment = self._create_segment_with_ubx(
                    start_time, end_time, music_analysis, i, style_preferences
                )
                choreography_segments.append(segment)

            # Thêm closing action
            if segments:
                closing_segment = self._create_closing_segment(segments[-1][1], music_analysis)
                choreography_segments.append(closing_segment)

            # Tạo choreography data
            choreography_id = str(uuid.uuid4())
            choreography = ChoreographyData(
                id=choreography_id,
                name=f"Auto-generated for {music_analysis.filename}",
                music_file=music_analysis.filename,
                music_analysis_id=music_analysis.id,
                segments=choreography_segments,
                total_duration=music_analysis.duration,
                bpm=music_analysis.tempo,
                created_at=datetime.now(),
                style_preferences=style_preferences or {}
            )

            # Lưu choreography
            await self._save_choreography(choreography)

            print(f"Choreography created successfully with {len(choreography_segments)} segments")
            return choreography

        except Exception as e:
            print(f"Error creating choreography: {str(e)}")
            raise

    def _create_opening_segment(self, start_time: float, music_analysis: MusicAnalysisResult) -> ChoreographySegment:
        """Tạo segment mở đầu"""
        opening_actions = ubx_manager.get_opening_actions()
        selected_action = random.choice(opening_actions)
        action_info = ubx_manager.get_action_info(selected_action)

        return ChoreographySegment(
            start_time=max(0, start_time - 2.0),
            end_time=start_time,
            action=ubx_manager.map_to_robot_action(selected_action),
            parameters={"intensity": 0.7, "ubx_action_id": selected_action},
            ubx_file=f"{selected_action}.ubx",
            energy_level="medium",
            notes=f"Opening: {action_info.get('name', selected_action)}"
        )

    def _create_closing_segment(self, end_time: float, music_analysis: MusicAnalysisResult) -> ChoreographySegment:
        """Tạo segment kết thúc"""
        closing_actions = ubx_manager.get_closing_actions()
        selected_action = random.choice(closing_actions)
        action_info = ubx_manager.get_action_info(selected_action)

        return ChoreographySegment(
            start_time=end_time,
            end_time=min(music_analysis.duration, end_time + 3.0),
            action=ubx_manager.map_to_robot_action(selected_action),
            parameters={"intensity": 0.5, "ubx_action_id": selected_action},
            ubx_file=f"{selected_action}.ubx",
            energy_level="low",
            notes=f"Closing: {action_info.get('name', selected_action)}"
        )

    def _create_segment_with_ubx(self, start_time: float, end_time: float,
                                music_analysis: MusicAnalysisResult,
                                segment_index: int,
                                style_preferences: Dict[str, Any] = None) -> ChoreographySegment:
        """Tạo một segment choreography với UBX action"""

        segment_duration = end_time - start_time

        # Phân tích năng lượng trong segment này
        energy_level = self._get_energy_level_for_segment(
            music_analysis.energy_analysis, start_time, end_time
        )

        # Lấy danh sách UBX actions phù hợp
        suitable_actions = ubx_manager.get_suitable_actions(
            energy_level, segment_duration, music_analysis.tempo
        )

        # Chọn action ngẫu nhiên từ danh sách phù hợp
        selected_ubx_action = random.choice(suitable_actions)
        action_info = ubx_manager.get_action_info(selected_ubx_action)

        # Map sang RobotAction
        robot_action = ubx_manager.map_to_robot_action(selected_ubx_action)

        # Tạo parameters
        parameters = self._generate_ubx_action_parameters(
            selected_ubx_action, energy_level, music_analysis
        )

        return ChoreographySegment(
            start_time=start_time,
            end_time=end_time,
            action=robot_action,
            parameters=parameters,
            ubx_file=f"{selected_ubx_action}.ubx",
            energy_level=energy_level,
            notes=f"UBX Action: {action_info.get('name', selected_ubx_action)}"
        )

    def _generate_ubx_action_parameters(self, ubx_action_id: str, energy_level: str,
                                      music_analysis: MusicAnalysisResult) -> Dict[str, Any]:
        """Tạo parameters cho UBX action"""
        action_info = ubx_manager.get_action_info(ubx_action_id)

        # Base parameters
        intensity_mapping = {
            "low": 0.4,
            "medium": 0.7,
            "high": 1.0
        }

        base_intensity = intensity_mapping.get(energy_level, 0.7)
        tempo_factor = min(music_analysis.tempo / 120.0, 1.5)
        adjusted_intensity = min(base_intensity * tempo_factor, 1.0)

        return {
            "intensity": adjusted_intensity,
            "ubx_action_id": ubx_action_id,
            "action_name": action_info.get("name", ubx_action_id),
            "category": action_info.get("category", "unknown"),
            "expected_duration": action_info.get("duration", 2.0),
            "sync_to_beat": True,
            "tempo": music_analysis.tempo
        }

    def _get_energy_level_for_segment(self, energy_analysis: Dict[str, Any],
                                    start_time: float, end_time: float) -> str:
        """Tính mức năng lượng cho một segment cụ thể"""
        try:
            if not energy_analysis or 'rms_times' not in energy_analysis or 'rms_energy' not in energy_analysis:
                return "medium"

            times = energy_analysis['rms_times']
            energies = energy_analysis['rms_energy']

            # Tìm các index trong khoảng thời gian
            start_idx = next((i for i, t in enumerate(times) if t >= start_time), 0)
            end_idx = next((i for i, t in enumerate(times) if t >= end_time), len(times) - 1)

            if start_idx >= len(energies) or end_idx >= len(energies):
                return "medium"

            # Tính năng lượng trung bình trong segment
            segment_energies = energies[start_idx:end_idx + 1]
            if not segment_energies:
                return "medium"

            avg_energy = np.mean(segment_energies)

            # Phân loại mức năng lượng
            thresholds = self.action_mapping_rules["energy_thresholds"]
            if avg_energy < thresholds["low"]:
                return "low"
            elif avg_energy < thresholds["medium"]:
                return "medium"
            else:
                return "high"

        except Exception as e:
            print(f"Error calculating energy level: {e}")
            return "medium"

    async def _save_choreography(self, choreography: ChoreographyData):
        """Lưu choreography vào file JSON"""
        try:
            choreography_dir = "data/choreography"
            os.makedirs(choreography_dir, exist_ok=True)

            filename = f"{choreography.id}.json"
            filepath = os.path.join(choreography_dir, filename)

            # Convert to dict
            choreography_dict = {
                "id": choreography.id,
                "name": choreography.name,
                "music_file": choreography.music_file,
                "music_analysis_id": choreography.music_analysis_id,
                "segments": [
                    {
                        "start_time": seg.start_time,
                        "end_time": seg.end_time,
                        "action": seg.action.value,
                        "parameters": seg.parameters,
                        "ubx_file": seg.ubx_file,
                        "energy_level": seg.energy_level,
                        "notes": seg.notes
                    } for seg in choreography.segments
                ],
                "total_duration": choreography.total_duration,
                "bpm": choreography.bpm,
                "created_at": choreography.created_at.isoformat(),
                "style_preferences": choreography.style_preferences
            }

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(choreography_dict, f, indent=2, ensure_ascii=False)

            print(f"Choreography saved to: {filepath}")

        except Exception as e:
            print(f"Error saving choreography: {e}")

    async def load_choreography(self, choreography_id: str) -> ChoreographyData:
        """Load choreography từ file JSON"""
        try:
            filepath = os.path.join("data/choreography", f"{choreography_id}.json")

            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Convert segments
            segments = []
            for seg_data in data["segments"]:
                segments.append(ChoreographySegment(
                    start_time=seg_data["start_time"],
                    end_time=seg_data["end_time"],
                    action=RobotAction(seg_data["action"]),
                    parameters=seg_data["parameters"],
                    ubx_file=seg_data["ubx_file"],
                    energy_level=seg_data["energy_level"],
                    notes=seg_data["notes"]
                ))

            return ChoreographyData(
                id=data["id"],
                name=data["name"],
                music_file=data["music_file"],
                music_analysis_id=data["music_analysis_id"],
                segments=segments,
                total_duration=data["total_duration"],
                bpm=data["bpm"],
                created_at=datetime.fromisoformat(data["created_at"]),
                style_preferences=data["style_preferences"]
            )

        except Exception as e:
            print(f"Error loading choreography: {e}")
            raise

    def get_all_choreographies(self) -> List[Dict[str, Any]]:
        """Lấy danh sách tất cả choreography đã lưu"""
        choreographies = []
        choreography_dir = "data/choreography"

        if os.path.exists(choreography_dir):
            for filename in os.listdir(choreography_dir):
                if filename.endswith('.json'):
                    try:
                        filepath = os.path.join(choreography_dir, filename)
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)

                        choreographies.append({
                            "id": data["id"],
                            "name": data["name"],
                            "music_file": data["music_file"],
                            "total_duration": data["total_duration"],
                            "bpm": data["bpm"],
                            "created_at": data["created_at"],
                            "segment_count": len(data["segments"])
                        })
                    except Exception as e:
                        print(f"Error loading choreography {filename}: {e}")

        return sorted(choreographies, key=lambda x: x["created_at"], reverse=True)

    def preview_choreography(self, choreography: ChoreographyData) -> str:
        """Tạo preview text của choreography"""
        preview = []
        preview.append(f"Choreography: {choreography.name}")
        preview.append(f"Music: {choreography.music_file}")
        preview.append(f"Duration: {choreography.total_duration:.1f}s")
        preview.append(f"BPM: {choreography.bpm:.1f}")
        preview.append(f"Total segments: {len(choreography.segments)}")
        preview.append("\nSegment details:")

        for i, segment in enumerate(choreography.segments):
            ubx_action_id = segment.parameters.get('ubx_action_id', 'unknown')
            action_name = segment.parameters.get('action_name', 'Unknown Action')
            preview.append(
                f"  {i+1:2d}. {segment.start_time:5.1f}s - {segment.end_time:5.1f}s: "
                f"{action_name} ({ubx_action_id}) [{segment.energy_level}]"
            )

        return "\n".join(preview)


# Global service instance
choreography_service = ChoreographyService()
