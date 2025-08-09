"""
Robot Audio Service - Phát âm thanh qua robot Alpha Mini
"""
import asyncio
import os
import logging
from typing import Optional
from mini.apis.api_sound import StartPlayTTS, StopPlayTTS, ControlTTSResponse
from mini.apis.base_api import MiniApiResultType

logger = logging.getLogger(__name__)

class RobotAudioService:
    """Service để phát âm thanh qua robot Alpha Mini"""

    def __init__(self):
        self.is_playing = False
        self.current_audio = None

    async def play_text_to_speech(self, text: str, robot_service) -> bool:
        """Phát text-to-speech qua robot"""
        if not robot_service.is_connected or not robot_service.is_in_program_mode:
            logger.error("Robot not connected or not in program mode")
            return False

        try:
            print(f"🗣️ Robot speaking: {text}")

            block = StartPlayTTS(text=text)
            result_type, response = await block.execute()

            if result_type == MiniApiResultType.Success and response and response.isSuccess:
                self.is_playing = True
                print(f"✅ TTS playing successfully")
                return True
            else:
                print(f"⚠️ Failed to play TTS: {response.resultCode if response else 'No response'}")
                return False

        except Exception as e:
            logger.error(f"Error playing TTS: {e}")
            return False

    async def announce_music_info(self, filename: str, tempo: float, robot_service) -> bool:
        """Thông báo thông tin bài nhạc"""
        try:
            # Tạo thông báo tiếng Việt
            announcement = f"Bắt đầu nhảy theo bài nhạc {filename}. Nhịp độ {tempo:.0f} BPM"
            return await self.play_text_to_speech(announcement, robot_service)
        except Exception as e:
            logger.error(f"Error announcing music info: {e}")
            return False

    async def stop_audio(self, robot_service) -> bool:
        """Dừng phát âm thanh"""
        try:
            if self.is_playing and robot_service.is_connected:
                block = StopPlayTTS()
                result_type, response = await block.execute()

                if result_type == MiniApiResultType.Success:
                    self.is_playing = False
                    self.current_audio = None
                    print("🔇 Audio stopped")
                    return True

        except Exception as e:
            logger.error(f"Error stopping audio: {e}")

        return False

# Global instance
robot_audio_service = RobotAudioService()
