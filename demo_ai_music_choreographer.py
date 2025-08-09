"""
Alpha Mini AI Music Choreographer Demo
Tự động phân tích nhạc và tạo choreography thông minh
"""

import asyncio
import os
import sys
import json
from pathlib import Path
from typing import Optional

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from app.services.music_analysis import MusicAnalysisService
from app.services.ai_choreographer import ai_choreographer_service
from app.services.alpha_mini_robot import alpha_mini_robot_service
from app.services.audio_player import audio_player_service


class AlphaMiniAIMusicDemo:
    """Demo class cho AI Music Choreographer"""
    
    def __init__(self):
        self.music_analysis_service = MusicAnalysisService()
        self.choreographer = ai_choreographer_service
        self.robot_service = alpha_mini_robot_service
        self.audio_service = audio_player_service
        
    async def process_music_file(self, music_file_path: str) -> Optional[dict]:
        """Xử lý file nhạc từ import đến tạo choreography"""
        
        if not os.path.exists(music_file_path):
            print(f"❌ File không tồn tại: {music_file_path}")
            return None
            
        filename = os.path.basename(music_file_path)
        print(f"🎵 Đang xử lý file nhạc: {filename}")
        
        try:
            # Bước 1: Phân tích nhạc
            print("📊 Bước 1: Phân tích đặc trưng âm nhạc...")
            music_analysis = await self.music_analysis_service.analyze_audio_file(
                music_file_path, filename
            )
            
            print(f"✅ Phân tích hoàn thành:")
            print(f"   - Thời lượng: {music_analysis.duration:.2f}s")
            print(f"   - Tempo: {music_analysis.tempo:.1f} BPM")
            print(f"   - Số beats: {len(music_analysis.beats)}")
            
            # Bước 2: Tạo choreography thông minh
            print("🤖 Bước 2: Tạo choreography AI...")
            choreography = await self.choreographer.create_intelligent_choreography(
                music_analysis
            )
            
            print(f"✅ Choreography tạo thành công:")
            print(f"   - Số segments: {len(choreography.segments)}")
            print(f"   - Tổng số actions: {sum(len(seg.actions) for seg in choreography.segments)}")
            print(f"   - Emotion chính: {choreography.metadata['emotion_analysis']['primary_emotion']}")

            # Bước 3: Hiển thị chi tiết choreography
            print("\n🎭 Chi tiết Choreography:")
            for i, segment in enumerate(choreography.segments):
                print(f"\n  Segment {i+1} ({segment.start_time:.1f}s - {segment.end_time:.1f}s):")
                print(f"    Emotion: {segment.primary_emotion}, Energy: {segment.energy_level:.2f}")
                
                # Group actions by type for better display
                actions_by_type = {"dance": [], "action": [], "expression": [], "light": []}
                for action in segment.actions:
                    action_type = action.type
                    if action_type in actions_by_type:
                        actions_by_type[action_type].append(action)
                
                # Display each type
                for action_type, actions in actions_by_type.items():
                    if actions:
                        type_emoji = {"dance": "💃", "action": "🤸", "expression": "🎭", "light": "💡"}
                        print(f"    {type_emoji.get(action_type, '🎪')} {action_type.upper()}:")
                        for action in actions:
                            if action_type == "light":
                                color = action.parameters.get("color", "unknown")
                                mode = action.parameters.get("mode", "normal") 
                                print(f"      - {color} light ({mode}) ({action.start_time:.1f}s, {action.duration:.1f}s)")
                            else:
                                print(f"      - {action.name} ({action.start_time:.1f}s, {action.duration:.1f}s)")
                    
            return {
                "music_analysis": music_analysis,
                "choreography": choreography,
                "success": True
            }
            
        except Exception as e:
            print(f"❌ Lỗi xử lý: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def execute_choreography(self, choreography_data: dict, play_music: bool = True):
        """Thực thi choreography trên robot"""
        
        print("🎪 Bước 3: Thực thi choreography trên robot...")
        
        try:
            music_analysis = choreography_data["music_analysis"]
            choreography = choreography_data["choreography"]
            
            # Kết nối robot nếu chưa có
            if not self.robot_service.is_connected:
                print("🔌 Đang kết nối robot...")
                if not await self.robot_service.find_and_connect():
                    print("❌ Không thể kết nối robot")
                    return False
            
            print("✅ Robot đã kết nối")
            
            # Thực hiện choreography
            print("💃 Bắt đầu biểu diễn với lights và expressions...")
            
            if len(choreography.segments) > 0:
                # Chuẩn bị danh sách actions đã được đồng bộ hoá theo thời gian
                all_actions = []
                for segment in choreography.segments:
                    for action in segment.actions:
                        all_actions.append({
                            "type": action.type,
                            "name": action.name,
                            "start_time": action.start_time,
                            "duration": action.duration,
                            "params": action.parameters,
                        })
                
                # Khởi chạy performance và phát nhạc input song song
                perf_task = asyncio.create_task(self.robot_service.synchronized_performance(
                    all_actions, choreography.duration
                ))

                if play_music:
                    music_task = asyncio.create_task(self.audio_service.play_music_file(music_analysis.file_path))
                    results = await asyncio.gather(perf_task, music_task, return_exceptions=True)
                else:
                    results = [await perf_task]

                success = bool(results and results[0] is True)
                print("🎉 Synchronized performance completed successfully!" if success else "⚠️ Performance completed with some issues")
            else:
                # Fallback to segment-by-segment execution
                for i, segment in enumerate(choreography.segments):
                    print(f"🎭 Segment {i+1}: {segment.primary_emotion}")
                    
                    # Separate actions by type for parallel execution
                    dances = [a for a in segment.actions if a.type == "dance"]
                    actions = [a for a in segment.actions if a.type == "action"]
                    expressions = [a for a in segment.actions if a.type == "expression"]
                    lights = [a for a in segment.actions if a.type == "light"]
                    
                    # Execute using continuous dance method if we have multiple types
                    if len(dances) > 0 and len(expressions) > 0:
                        dance_names = [a.name for a in dances]
                        expression_names = [a.name for a in expressions]
                        light_colors = [a.parameters.get("color", "green") for a in lights] or ["green"]
                        
                        await self.robot_service.continuous_dance_with_expressions_and_lights(
                            dance_names, expression_names, light_colors, 
                            segment.end_time - segment.start_time
                        )
                    else:
                        # Execute individual actions
                        for action in segment.actions:
                            try:
                                if action.type == "dance":
                                    print(f"  💃 Dance: {action.name}")
                                    await self.robot_service.play_dance(action.name, action.duration)
                                    
                                elif action.type == "action":
                                    print(f"  🤸 Action: {action.name}")
                                    await self.robot_service.play_action(action.name, action.duration)
                                    
                                elif action.type == "expression":
                                    print(f"  🎭 Expression: {action.name}")
                                    await self.robot_service.play_expression(action.name)
                                    
                                elif action.type == "light":
                                    color = action.parameters.get("color", "green")
                                    mode = action.parameters.get("mode", "normal")
                                    print(f"  💡 Light: {color} ({mode})")
                                    await self.robot_service.set_mouth_lamp(
                                        color, mode, int(action.duration * 1000)
                                    )
                                
                                # Small delay between actions
                                await asyncio.sleep(0.2)
                                
                            except Exception as e:
                                print(f"⚠️ Lỗi thực hiện action {action.name}: {e}")
                                continue
            
            print("🎉 Biểu diễn hoàn thành!")
            return True
            
        except Exception as e:
            print(f"❌ Lỗi thực thi: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def save_choreography(self, choreography_data: dict, output_dir: str = "data/choreography"):
        """Lưu choreography vào file"""
        
        try:
            os.makedirs(output_dir, exist_ok=True)
            
            choreography = choreography_data["choreography"]
            filename = f"{choreography.id}.json"
            filepath = os.path.join(output_dir, filename)
            
            # Convert to dict for JSON serialization
            choreography_dict = {
                "id": choreography.id,
                "music_analysis_id": choreography.music_analysis_id,
                "filename": choreography.filename,
                "duration": choreography.duration,
                "style": choreography.style,
                "created_at": choreography.created_at,
                "metadata": choreography.metadata,
                "segments": []
            }
            
            for segment in choreography.segments:
                segment_dict = {
                    "start_time": segment.start_time,
                    "end_time": segment.end_time,
                    "tempo": segment.tempo,
                    "energy_level": segment.energy_level,
                    "primary_emotion": segment.primary_emotion,
                    "actions": []
                }
                
                for action in segment.actions:
                    action_dict = {
                        "type": action.type,
                        "name": action.name,
                        "start_time": action.start_time,
                        "duration": action.duration,
                        "intensity": action.intensity,
                        "parameters": action.parameters
                    }
                    segment_dict["actions"].append(action_dict)
                
                choreography_dict["segments"].append(segment_dict)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(choreography_dict, f, indent=2, ensure_ascii=False)
            
            print(f"💾 Choreography đã lưu: {filepath}")
            return filepath
            
        except Exception as e:
            print(f"❌ Lỗi lưu file: {e}")
            return None

async def main():
    """Main demo function"""
    
    print("🎵 Alpha Mini AI Music Choreographer Demo 🤖")
    print("=" * 50)
    
    demo = AlphaMiniAIMusicDemo()
    
    # Tìm file nhạc trong thư mục uploads
    uploads_dir = "uploads/music"
    if not os.path.exists(uploads_dir):
        print(f"❌ Thư mục {uploads_dir} không tồn tại")
        return
    
    # Lấy danh sách file nhạc
    music_files = []
    for ext in ['.mp3', '.wav', '.m4a', '.flac']:
        music_files.extend([f for f in os.listdir(uploads_dir) if f.lower().endswith(ext)])
    
    if not music_files:
        print("❌ Không tìm thấy file nhạc nào trong uploads/music")
        print("📁 Hãy copy file nhạc vào thư mục uploads/music và chạy lại")
        return
    
    print(f"🎵 Tìm thấy {len(music_files)} file nhạc:")
    for i, filename in enumerate(music_files, 1):
        print(f"   {i}. {filename}")
    
    # Chọn file để xử lý (hoặc xử lý file đầu tiên)
    selected_file = music_files[0]
    music_file_path = os.path.join(uploads_dir, selected_file)
    
    print(f"\n🎯 Đang xử lý: {selected_file}")
    print("-" * 30)
    
    # Xử lý file nhạc
    result = await demo.process_music_file(music_file_path)
    
    if result and result["success"]:
        # Lưu choreography
        await demo.save_choreography(result)
        
        # Hỏi có muốn thực thi trên robot không
        print(f"\n🤖 Choreography đã sẵn sàng!")
        print(f"💡 Để thực thi trên robot thật, hãy:")
        print(f"   1. Đảm bảo robot Alpha Mini đã kết nối")
        print(f"   2. Uncomment phần execute_choreography bên dưới")
        
        # Uncommnt dòng này để thực thi trên robot thật
        await demo.execute_choreography(result, play_music=True)
        
    print(f"\n🎉 Demo hoàn thành!")

if __name__ == "__main__":
    asyncio.run(main())
