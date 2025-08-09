"""
AI Music Choreographer API Endpoints
Upload nhạc và tạo choreography tự động
"""

from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import os
import shutil
import uuid
import asyncio
from typing import Optional, Dict, Any
from pathlib import Path

from app.services.music_analysis import MusicAnalysisService
from app.services.ai_choreographer import ai_choreographer_service
from app.services.alpha_mini_robot import alpha_mini_robot_service
from app.core.config import settings

router = APIRouter()

# Services
music_analysis_service = MusicAnalysisService()

@router.post("/upload-and-analyze")
async def upload_and_analyze_music(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    auto_choreograph: bool = True,
    style_preferences: Optional[str] = None
):
    """
    Upload file nhạc và tự động phân tích + tạo choreography
    """
    try:
        # Kiểm tra file type
        allowed_extensions = {'.mp3', '.wav', '.m4a', '.flac', '.aac'}
        file_extension = Path(file.filename).suffix.lower()
        
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"File type không được hỗ trợ. Chỉ chấp nhận: {', '.join(allowed_extensions)}"
            )
        
        # Tạo unique filename
        unique_id = str(uuid.uuid4())
        filename = f"{unique_id}_{file.filename}"
        
        # Tạo thư mục uploads nếu chưa có
        uploads_dir = Path("uploads/music")
        uploads_dir.mkdir(parents=True, exist_ok=True)
        
        # Lưu file
        file_path = uploads_dir / filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        print(f"📁 File đã lưu: {file_path}")
        
        # Phân tích nhạc
        print(f"🎵 Đang phân tích nhạc: {file.filename}")
        music_analysis = await music_analysis_service.analyze_audio_file(
            str(file_path), file.filename
        )
        
        response_data = {
            "success": True,
            "message": "Upload và phân tích thành công",
            "music_analysis": {
                "id": music_analysis.id,
                "filename": music_analysis.filename,
                "duration": music_analysis.duration,
                "tempo": music_analysis.tempo,
                "beats_count": len(music_analysis.beats),
                "spectral_features": music_analysis.spectral_features,
                "energy_analysis": music_analysis.energy_analysis
            },
            "file_path": str(file_path),
            "choreography": None
        }
        
        # Tạo choreography nếu được yêu cầu
        if auto_choreograph:
            print(f"🤖 Đang tạo choreography AI...")
            
            preferences = {}
            if style_preferences:
                try:
                    import json
                    preferences = json.loads(style_preferences)
                except:
                    preferences = {"style": style_preferences}
            
            choreography = await ai_choreographer_service.create_intelligent_choreography(
                music_analysis, preferences
            )
            
            # Lưu choreography
            choreography_dir = Path("data/choreography")
            choreography_dir.mkdir(parents=True, exist_ok=True)
            
            choreography_file = choreography_dir / f"{choreography.id}.json"
            
            # Convert choreography to dict for JSON
            choreography_dict = _choreography_to_dict(choreography)
            
            import json
            with open(choreography_file, 'w', encoding='utf-8') as f:
                json.dump(choreography_dict, f, indent=2, ensure_ascii=False)
            
            response_data["choreography"] = {
                "id": choreography.id,
                "segments_count": len(choreography.segments),
                "total_actions": sum(len(seg.actions) for seg in choreography.segments),
                "primary_emotion": choreography.metadata["emotion_analysis"]["primary_emotion"],
                "file_path": str(choreography_file),
                "preview": _get_choreography_preview(choreography)
            }
            
            print(f"✅ Choreography đã tạo với {len(choreography.segments)} segments")
        
        return JSONResponse(content=response_data)
        
    except Exception as e:
        print(f"❌ Lỗi upload và phân tích: {e}")
        import traceback
        traceback.print_exc()
        
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi xử lý file: {str(e)}"
        )

@router.post("/create-choreography/{music_analysis_id}")
async def create_choreography_for_analysis(
    music_analysis_id: str,
    preferences: Optional[Dict[str, Any]] = None
):
    """
    Tạo choreography cho một music analysis có sẵn
    """
    try:
        # Tìm music analysis
        analysis_file = Path(f"data/analysis/{music_analysis_id}.json")
        if not analysis_file.exists():
            raise HTTPException(
                status_code=404,
                detail="Music analysis không tìm thấy"
            )
        
        # Load analysis
        import json
        with open(analysis_file, 'r', encoding='utf-8') as f:
            analysis_data = json.load(f)
        
        # Recreate MusicAnalysisResult object
        from app.models.schemas import MusicAnalysisResult
        music_analysis = MusicAnalysisResult(**analysis_data)
        
        # Tạo choreography
        choreography = await ai_choreographer_service.create_intelligent_choreography(
            music_analysis, preferences
        )
        
        # Lưu choreography
        choreography_dir = Path("data/choreography")
        choreography_dir.mkdir(parents=True, exist_ok=True)
        
        choreography_file = choreography_dir / f"{choreography.id}.json"
        choreography_dict = _choreography_to_dict(choreography)
        
        with open(choreography_file, 'w', encoding='utf-8') as f:
            json.dump(choreography_dict, f, indent=2, ensure_ascii=False)
        
        return {
            "success": True,
            "message": "Choreography tạo thành công",
            "choreography": {
                "id": choreography.id,
                "segments_count": len(choreography.segments),
                "total_actions": sum(len(seg.actions) for seg in choreography.segments),
                "primary_emotion": choreography.metadata["emotion_analysis"]["primary_emotion"],
                "file_path": str(choreography_file),
                "preview": _get_choreography_preview(choreography)
            }
        }
        
    except Exception as e:
        print(f"❌ Lỗi tạo choreography: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi tạo choreography: {str(e)}"
        )

@router.post("/execute-choreography/{choreography_id}")
async def execute_choreography_on_robot(
    choreography_id: str,
    play_music: bool = True,
    preview_only: bool = False
):
    """
    Thực thi choreography trên robot Alpha Mini
    """
    try:
        # Tìm choreography
        choreography_file = Path(f"data/choreography/{choreography_id}.json")
        if not choreography_file.exists():
            raise HTTPException(
                status_code=404,
                detail="Choreography không tìm thấy"
            )
        
        # Load choreography
        import json
        with open(choreography_file, 'r', encoding='utf-8') as f:
            choreography_data = json.load(f)
        
        if preview_only:
            # Chỉ trả về preview
            return {
                "success": True,
                "message": "Preview choreography",
                "choreography": choreography_data,
                "execution_plan": _create_execution_plan(choreography_data)
            }
        
        # Kết nối robot
        if not alpha_mini_robot_service.is_connected():
            connected = await alpha_mini_robot_service.connect()
            if not connected:
                raise HTTPException(
                    status_code=503,
                    detail="Không thể kết nối với robot Alpha Mini"
                )
        
        # Thực thi choreography
        execution_result = await _execute_choreography_on_robot(
            choreography_data, play_music
        )
        
        return {
            "success": True,
            "message": "Choreography đã được thực thi",
            "execution_result": execution_result
        }
        
    except Exception as e:
        print(f"❌ Lỗi thực thi choreography: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi thực thi: {str(e)}"
        )

@router.get("/choreography/{choreography_id}")
async def get_choreography_details(choreography_id: str):
    """
    Lấy chi tiết choreography
    """
    try:
        choreography_file = Path(f"data/choreography/{choreography_id}.json")
        if not choreography_file.exists():
            raise HTTPException(
                status_code=404,
                detail="Choreography không tìm thấy"
            )
        
        import json
        with open(choreography_file, 'r', encoding='utf-8') as f:
            choreography_data = json.load(f)
        
        return {
            "success": True,
            "choreography": choreography_data,
            "summary": {
                "segments_count": len(choreography_data["segments"]),
                "total_actions": sum(len(seg["actions"]) for seg in choreography_data["segments"]),
                "duration": choreography_data["duration"],
                "primary_emotion": choreography_data["metadata"]["emotion_analysis"]["primary_emotion"]
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi lấy choreography: {str(e)}"
        )

@router.get("/available-actions")
async def get_available_actions():
    """
    Lấy danh sách tất cả actions và expressions có sẵn
    """
    try:
        from app.services.alpha_mini_actions import alpha_mini_actions_service
        
        return {
            "success": True,
            "built_in_dances": [
                {
                    "name": action.name,
                    "description": action.description,
                    "duration": action.duration_estimate,
                    "emotion": action.emotion_type,
                    "intensity": action.intensity
                }
                for action in alpha_mini_actions_service.built_in_dances.values()
            ],
            "built_in_actions": [
                {
                    "name": action.name,
                    "description": action.description,
                    "can_interrupt": action.can_interrupt,
                    "duration": action.duration_estimate,
                    "emotion": action.emotion_type,
                    "intensity": action.intensity,
                    "category": action.category
                }
                for action in alpha_mini_actions_service.built_in_actions.values()
            ],
            "built_in_expressions": [
                {
                    "name": expr.name,
                    "description": expr.description,
                    "emotion": expr.emotion_type,
                    "intensity": expr.intensity
                }
                for expr in alpha_mini_actions_service.built_in_expressions.values()
            ]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi lấy danh sách actions: {str(e)}"
        )

# Helper functions

def _choreography_to_dict(choreography) -> Dict[str, Any]:
    """Convert choreography object to dictionary"""
    return {
        "id": choreography.id,
        "music_analysis_id": choreography.music_analysis_id,
        "filename": choreography.filename,
        "duration": choreography.duration,
        "style": choreography.style,
        "created_at": choreography.created_at,
        "metadata": choreography.metadata,
        "segments": [
            {
                "start_time": seg.start_time,
                "end_time": seg.end_time,
                "tempo": seg.tempo,
                "energy_level": seg.energy_level,
                "primary_emotion": seg.primary_emotion,
                "actions": [
                    {
                        "type": action.type,
                        "name": action.name,
                        "start_time": action.start_time,
                        "duration": action.duration,
                        "intensity": action.intensity,
                        "parameters": action.parameters
                    }
                    for action in seg.actions
                ]
            }
            for seg in choreography.segments
        ]
    }

def _get_choreography_preview(choreography) -> Dict[str, Any]:
    """Tạo preview ngắn gọn của choreography"""
    action_types = {}
    total_duration = 0
    
    for segment in choreography.segments:
        for action in segment.actions:
            action_type = action.type
            if action_type not in action_types:
                action_types[action_type] = []
            action_types[action_type].append(action.name)
            total_duration += action.duration
    
    return {
        "total_duration": total_duration,
        "action_types": {k: len(set(v)) for k, v in action_types.items()},
        "sample_actions": {k: list(set(v))[:3] for k, v in action_types.items()},
        "emotion": choreography.metadata["emotion_analysis"]["primary_emotion"]
    }

def _create_execution_plan(choreography_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Tạo execution plan cho choreography"""
    plan = []
    
    for i, segment in enumerate(choreography_data["segments"]):
        segment_plan = {
            "segment": i + 1,
            "start_time": segment["start_time"],
            "duration": segment["end_time"] - segment["start_time"],
            "emotion": segment["primary_emotion"],
            "actions": []
        }
        
        for action in segment["actions"]:
            segment_plan["actions"].append({
                "name": action["name"],
                "type": action["type"],
                "start_time": action["start_time"],
                "duration": action["duration"],
                "description": f"{action['type'].title()}: {action['name']}"
            })
        
        plan.append(segment_plan)
    
    return plan

async def _execute_choreography_on_robot(choreography_data: Dict[str, Any], play_music: bool) -> Dict[str, Any]:
    """Thực thi choreography trên robot với enhanced features"""
    
    execution_log = []
    total_actions = 0
    successful_actions = 0
    
    try:
        # Prepare synchronized actions list from all segments
        all_actions = []
        for segment in choreography_data["segments"]:
            for action in segment["actions"]:
                action_dict = {
                    "type": action["type"],
                    "name": action["name"], 
                    "start_time": action["start_time"],
                    "duration": action["duration"],
                    "params": action.get("parameters", {})
                }
                all_actions.append(action_dict)
        
        total_actions = len(all_actions)
        total_duration = choreography_data["duration"]
        
        print(f"🎪 Executing {total_actions} synchronized actions over {total_duration:.1f}s")
        
        # Use synchronized performance for better coordination
        success = await alpha_mini_robot_service.synchronized_performance(
            all_actions, total_duration
        )
        
        if success:
            successful_actions = total_actions  # Assume all succeeded if sync performance succeeded
            execution_log.append({
                "type": "synchronized_performance",
                "success": True,
                "total_actions": total_actions,
                "duration": total_duration
            })
        else:
            # Fallback to segment-by-segment execution
            print("🔄 Falling back to segment-by-segment execution...")
            
            for i, segment in enumerate(choreography_data["segments"]):
                segment_log = {
                    "segment": i + 1,
                    "start_time": segment["start_time"],
                    "actions": []
                }
                
                # Group actions by type for parallel execution within segment
                actions_by_type = {"dance": [], "action": [], "expression": [], "light": []}
                for action in segment["actions"]:
                    action_type = action["type"]
                    if action_type in actions_by_type:
                        actions_by_type[action_type].append(action)
                
                # Execute continuous performance if we have multiple types
                dances = actions_by_type["dance"]
                expressions = actions_by_type["expression"] 
                lights = actions_by_type["light"]
                
                if len(dances) > 0 and (len(expressions) > 0 or len(lights) > 0):
                    # Use continuous dance method
                    dance_names = [a["name"] for a in dances]
                    expression_names = [a["name"] for a in expressions]
                    light_colors = [a["parameters"].get("color", "green") for a in lights]
                    
                    segment_duration = segment["end_time"] - segment["start_time"]
                    
                    try:
                        success = await alpha_mini_robot_service.continuous_dance_with_expressions_and_lights(
                            dance_names, expression_names, light_colors or ["green"], segment_duration
                        )
                        
                        if success:
                            successful_actions += len(segment["actions"])
                            segment_log["actions"] = [{"name": "continuous_performance", "success": True}]
                        else:
                            segment_log["actions"] = [{"name": "continuous_performance", "success": False}]
                            
                    except Exception as e:
                        print(f"⚠️ Error in continuous performance: {e}")
                        segment_log["actions"] = [{"name": "continuous_performance", "success": False, "error": str(e)}]
                
                else:
                    # Execute individual actions
                    for action in segment["actions"]:
                        action_result = {"name": action["name"], "type": action["type"], "success": False}
                        
                        try:
                            if action["type"] == "dance":
                                await alpha_mini_robot_service.start_dance_behavior(action["name"])
                                await asyncio.sleep(action["duration"] * 0.8)
                                await alpha_mini_robot_service.stop_behavior()
                                action_result["success"] = True
                                successful_actions += 1
                                
                            elif action["type"] == "action":
                                await alpha_mini_robot_service.execute_action(action["name"], action["duration"])
                                action_result["success"] = True
                                successful_actions += 1
                                
                            elif action["type"] == "expression":
                                await alpha_mini_robot_service.play_expression(action["name"])
                                action_result["success"] = True
                                successful_actions += 1
                                
                            elif action["type"] == "light":
                                color = action["parameters"].get("color", "green")
                                mode = action["parameters"].get("mode", "normal")
                                duration = int(action["duration"] * 1000)
                                await alpha_mini_robot_service.set_mouth_lamp(color, mode, duration)
                                action_result["success"] = True
                                successful_actions += 1
                            
                        except Exception as e:
                            action_result["error"] = str(e)
                            print(f"⚠️ Lỗi action {action['name']}: {e}")
                        
                        segment_log["actions"].append(action_result)
                
                execution_log.append(segment_log)
    
    except Exception as e:
        print(f"❌ Lỗi thực thi choreography: {e}")
        execution_log.append({"error": str(e)})
    
    finally:
        # Ensure robot stops all behaviors
        try:
            await alpha_mini_robot_service.stop_behavior()
            await alpha_mini_robot_service.control_mouth_lamp(is_open=False)  # Turn off lights
        except:
            pass
    
    return {
        "total_actions": total_actions,
        "successful_actions": successful_actions,
        "success_rate": (successful_actions / total_actions) * 100 if total_actions > 0 else 0,
        "execution_log": execution_log,
        "features_used": {
            "synchronized_performance": True,
            "mouth_lamp_control": True,
            "continuous_dance": True,
            "expression_integration": True
        }
    }
