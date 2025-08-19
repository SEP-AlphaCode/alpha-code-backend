from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
import os

from app.models.schemas import ChoreographyData, ChoreographySegment
from app.services.choreography import ChoreographyService

router = APIRouter()
choreography_service = ChoreographyService()

@router.post("/generate/{analysis_id}", response_model=ChoreographyData)
async def generate_choreography(analysis_id: str):
    """Tạo vũ đạo tự động dựa trên kết quả phân tích nhạc"""

    try:
        choreography = await choreography_service.generate_choreography(analysis_id)
        return choreography

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Music analysis not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating choreography: {str(e)}")

@router.get("/list", response_model=List[Dict[str, Any]])
async def list_choreographies():
    """Liệt kê tất cả vũ đạo đã tạo"""

    try:
        choreographies = await choreography_service.list_choreographies()
        return choreographies
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing choreographies: {str(e)}")

@router.get("/{choreography_id}", response_model=ChoreographyData)
async def get_choreography(choreography_id: str):
    """Lấy thông tin chi tiết vũ đạo"""

    try:
        choreography = await choreography_service.load_choreography(choreography_id)
        return choreography
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Choreography not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading choreography: {str(e)}")

@router.delete("/{choreography_id}")
async def delete_choreography(choreography_id: str):
    """Xóa vũ đạo"""

    try:
        choreography_file = f"data/choreography/{choreography_id}.json"

        if not os.path.exists(choreography_file):
            raise HTTPException(status_code=404, detail="Choreography not found")

        os.remove(choreography_file)

        return {"success": True, "message": "Choreography deleted successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting choreography: {str(e)}")

@router.get("/{choreography_id}/segments", response_model=List[ChoreographySegment])
async def get_choreography_segments(choreography_id: str):
    """Lấy danh sách segments của vũ đạo"""

    try:
        choreography = await choreography_service.load_choreography(choreography_id)
        return choreography.segments
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Choreography not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading segments: {str(e)}")

@router.post("/{choreography_id}/optimize")
async def optimize_choreography(choreography_id: str):
    """Tối ưu hóa vũ đạo (có thể thêm logic tối ưu sau)"""

    try:
        # Load choreography hiện tại
        choreography = await choreography_service.load_choreography(choreography_id)

        # Có thể thêm logic tối ưu hóa ở đây
        # Ví dụ: loại bỏ segments quá ngắn, smooth transitions, etc.

        return {
            "success": True,
            "message": "Choreography optimization completed",
            "choreography_id": choreography_id
        }

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Choreography not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error optimizing choreography: {str(e)}")

@router.get("/stats/overview")
async def get_choreography_stats():
    """Lấy thống kê tổng quan về vũ đạo"""

    try:
        choreographies = await choreography_service.list_choreographies()

        total_count = len(choreographies)
        total_duration = sum(c.get("total_duration", 0) for c in choreographies)
        avg_bpm = sum(c.get("bpm", 0) for c in choreographies) / max(total_count, 1)

        # Thống kê theo BPM range
        bpm_ranges = {
            "slow (60-90)": 0,
            "medium (90-120)": 0,
            "fast (120-150)": 0,
            "very_fast (150+)": 0
        }

        for c in choreographies:
            bpm = c.get("bpm", 0)
            if bpm < 90:
                bpm_ranges["slow (60-90)"] += 1
            elif bpm < 120:
                bpm_ranges["medium (90-120)"] += 1
            elif bpm < 150:
                bpm_ranges["fast (120-150)"] += 1
            else:
                bpm_ranges["very_fast (150+)"] += 1

        return {
            "total_choreographies": total_count,
            "total_duration_minutes": round(total_duration / 60, 2),
            "average_bpm": round(avg_bpm, 2),
            "bpm_distribution": bpm_ranges
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting stats: {str(e)}")
