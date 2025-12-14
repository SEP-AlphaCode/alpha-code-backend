from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, Body, BackgroundTasks
from pydantic import BaseModel

from app.services.audio.audio_service import convert_audio_to_wav_and_upload
from app.services.music.planner import build_activity_json
from app.services.music.progress_tracker import progress_tracker

router = APIRouter()


class MusicRequest(BaseModel):
    music_name: str
    music_url: str
    duration: float  # seconds
    robot_model_id: str


async def _generate_dance_plan_task(
    task_id: str,
    music_name: str,
    music_url: str,
    duration: float,
    robot_model_id: str,
    start_time: Optional[float] = None,
    end_time: Optional[float] = None
):
    """Background task to generate dance plan with progress tracking"""
    try:
        # Generate the activity
        result = await build_activity_json(
            music_name,
            music_url,
            duration,
            robot_model_id,
            task_id=task_id
        )

        # Extract data and add trimming info if needed
        result_data = result.get('data', result)

        if start_time is not None or end_time is not None:
            if 'music_info' not in result_data:
                result_data['music_info'] = {}
            result_data['music_info']['start_time'] = start_time
            result_data['music_info']['end_time'] = end_time

        # Mark as completed
        await progress_tracker.complete_task(task_id, result_data)

    except Exception as e:
        # Mark as failed
        await progress_tracker.fail_task(task_id, str(e))


@router.post('/generate-dance-plan')
async def generate_dance_plan(req: MusicRequest, background_tasks: BackgroundTasks):
    """
    Generate dance plan asynchronously with progress tracking.
    Returns task_id to check progress.
    """
    # Create task
    task_id = await progress_tracker.create_task()

    # Start background task
    background_tasks.add_task(
        _generate_dance_plan_task,
        task_id,
        req.music_name,
        req.music_url,
        req.duration,
        req.robot_model_id
    )

    return {
        "task_id": task_id,
        "message": "Task created. Use GET /music/task/{task_id} to check progress."
    }


@router.get('/task/{task_id}')
async def get_task_status(task_id: str):
    """Get status and progress of a music generation task"""
    status = await progress_tracker.get_task_status(task_id)

    if not status:
        raise HTTPException(status_code=404, detail="Task not found or expired")

    return status


@router.delete('/task/{task_id}')
async def delete_task(task_id: str):
    """Delete a task from tracking"""
    await progress_tracker.delete_task(task_id)
    return {"message": "Task deleted"}


# Legacy endpoint - synchronous (kept for backward compatibility)
@router.post('/generate-dance-plan-sync')
async def generate_dance_plan_sync(req: MusicRequest):
    """Generate dance plan synchronously (blocks until complete)"""
    return await build_activity_json(req.music_name, req.music_url, req.duration, req.robot_model_id)


@router.post('/upload-music-and-generate-plan')
async def upload_music_and_generate_plan(
        background_tasks: BackgroundTasks,
        file: UploadFile = File(...),
        start_time: Optional[float] = Body(None, description="Start time in seconds (optional)", ge=0),
        end_time: Optional[float] = Body(None, description="End time in seconds (optional)", ge=0),
        robot_model_id: str = Body(..., description="Robot model ID"),
        async_mode: bool = Body(True, description="Whether to process asynchronously")):
    """
    Upload music file and generate dance plan.

    Args:
        file: MP3 or MP4 file
        start_time: Optional start time for trimming
        end_time: Optional end time for trimming
        robot_model_id: Robot model ID
        async_mode: If True, returns task_id for progress tracking. If False, blocks until complete.
    """
    # Chỉ cho phép mp3 và mp4
    if not (file.filename.lower().endswith(".mp3") or file.filename.lower().endswith(".mp4")):
        raise HTTPException(status_code=400, detail="Only .mp3 or .mp4 files are supported.")

    # Validate time parameters
    if start_time is not None and end_time is not None and start_time >= end_time:
        raise HTTPException(status_code=400, detail="start_time must be less than end_time")

    try:
        # Convert and upload audio (this is fast, so do it synchronously)
        result = await convert_audio_to_wav_and_upload(file, start_time=start_time, end_time=end_time)

        if async_mode:
            # Create task for async processing
            task_id = await progress_tracker.create_task()

            # Start background task
            background_tasks.add_task(
                _generate_dance_plan_task,
                task_id,
                result["file_name"],
                result["url"],
                result["duration"],
                robot_model_id,
                start_time,
                end_time
            )

            return {
                "task_id": task_id,
                "message": "Task created. Use GET /music/task/{task_id} to check progress.",
                "music_info": {
                    "name": result["file_name"],
                    "url": result["url"],
                    "duration": result["duration"]
                }
            }
        else:
            # Process synchronously
            response_data = await build_activity_json(
                result["file_name"],
                result["url"],
                result["duration"],
                robot_model_id
            )

            # Extract data and add trimming info
            new_res_data = response_data['data'].copy()

            if start_time is not None or end_time is not None:
                new_res_data['music_info']['start_time'] = start_time
                new_res_data['music_info']['end_time'] = end_time

            return new_res_data

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Conversion or upload failed: {str(e)}")
