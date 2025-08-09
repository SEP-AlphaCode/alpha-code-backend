"""
Audio Player Service - Phát nhạc đồng bộ với choreography
"""
import asyncio
import pygame
import threading
import time
from typing import Optional, Callable
import os
from pathlib import Path

class AudioPlayerService:
    """Service để phát nhạc và đồng bộ với robot choreography"""

    def __init__(self):
        self.current_music_file: Optional[str] = None
        self.is_playing = False
        self.is_paused = False
        self.start_time = 0
        self.current_position = 0
        self.duration = 0
        self.volume = 0.7
        self.music_thread = None

        # Callback functions
        self.on_music_start: Optional[Callable] = None
        self.on_music_end: Optional[Callable] = None
        self.on_position_update: Optional[Callable[[float], None]] = None

        # Initialize pygame mixer
        self._init_pygame()

    def _init_pygame(self):
        """Initialize pygame mixer for audio playback"""
        try:
            pygame.mixer.pre_init(frequency=22050, size=-16, channels=2, buffer=512)
            pygame.mixer.init()
            self.mixer_initialized = True
            print("✅ Audio system initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize audio system: {e}")
            self.mixer_initialized = False

    def load_music(self, file_path: str) -> bool:
        """Load music file"""
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Music file not found: {file_path}")

            # Stop current music if playing
            if self.is_playing:
                self.stop_music()

            # Load the music file
            pygame.mixer.music.load(file_path)
            self.current_music_file = file_path

            print(f"🎵 Music loaded: {os.path.basename(file_path)}")
            return True

        except Exception as e:
            print(f"❌ Failed to load music {file_path}: {e}")
            return False

    async def play_music_file(self, file_path: str) -> bool:
        """Load and play music file"""
        try:
            if not self.load_music(file_path):
                return False

            if not self.play_music():
                return False

            # Wait for music to finish
            await self._wait_for_music_completion()
            return True

        except Exception as e:
            print(f"❌ Error playing music file: {e}")
            return False

    def play_music(self) -> bool:
        """Start playing loaded music"""
        try:
            if not self.current_music_file:
                print("❌ No music file loaded")
                return False

            if not self.mixer_initialized:
                print("❌ Audio system not initialized")
                return False

            self.start_time = time.time()
            self.is_playing = True
            self.is_paused = False

            # Start playing
            pygame.mixer.music.play()

            if self.on_music_start:
                self.on_music_start()

            print(f"🎵 Playing: {os.path.basename(self.current_music_file)}")
            return True

        except Exception as e:
            print(f"❌ Failed to play music: {e}")
            self.is_playing = False
            return False

    async def _wait_for_music_completion(self):
        """Wait for music to complete playing"""
        try:
            while self.is_playing:
                if not pygame.mixer.music.get_busy():
                    self.is_playing = False
                    if self.on_music_end:
                        self.on_music_end()
                    break

                # Update position
                if self.is_playing and not self.is_paused:
                    self.current_position = time.time() - self.start_time
                    if self.on_position_update:
                        self.on_position_update(self.current_position)

                await asyncio.sleep(0.1)  # Check every 100ms

        except Exception as e:
            print(f"❌ Error waiting for music completion: {e}")
            self.is_playing = False

    def stop_music(self):
        """Stop playing music"""
        try:
            if self.is_playing:
                pygame.mixer.music.stop()
                self.is_playing = False
                self.is_paused = False
                self.current_position = 0
                print("⏹️ Music stopped")

        except Exception as e:
            print(f"❌ Error stopping music: {e}")

    def pause_music(self):
        """Pause music playback"""
        try:
            if self.is_playing and not self.is_paused:
                pygame.mixer.music.pause()
                self.is_paused = True
                print("⏸️ Music paused")

        except Exception as e:
            print(f"❌ Error pausing music: {e}")

    def resume_music(self):
        """Resume paused music"""
        try:
            if self.is_playing and self.is_paused:
                pygame.mixer.music.unpause()
                self.is_paused = False
                print("▶️ Music resumed")

        except Exception as e:
            print(f"❌ Error resuming music: {e}")

    def set_volume(self, volume: float):
        """Set music volume (0.0 to 1.0)"""
        try:
            self.volume = max(0.0, min(1.0, volume))
            pygame.mixer.music.set_volume(self.volume)
            print(f"🔊 Volume set to {self.volume:.1f}")

        except Exception as e:
            print(f"❌ Error setting volume: {e}")

    def get_position(self) -> float:
        """Get current playback position in seconds"""
        if self.is_playing and not self.is_paused:
            return time.time() - self.start_time
        return self.current_position

    def is_music_playing(self) -> bool:
        """Check if music is currently playing"""
        return self.is_playing and not self.is_paused

    def cleanup(self):
        """Cleanup audio resources"""
        try:
            self.stop_music()
            if self.mixer_initialized:
                pygame.mixer.quit()
            print("🧹 Audio player cleaned up")

        except Exception as e:
            print(f"❌ Error during cleanup: {e}")

# Create singleton instance
audio_player_service = AudioPlayerService()
