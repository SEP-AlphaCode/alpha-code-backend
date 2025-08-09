from fastapi import FastAPI, File, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import uvicorn
import os
import asyncio
from typing import List

from app.api.endpoints import music, choreography, robot, ai_music
from app.core.config import settings
from app.services.websocket_manager import ConnectionManager

# Tạo FastAPI app
app = FastAPI(
    title="Alpha Mini AI Music Choreographer API",
    description="Backend API cho robot Alpha Mini với AI tự động phân tích nhạc và tạo vũ đạo thông minh",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files cho uploads
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/data", StaticFiles(directory="data"), name="data")

# WebSocket manager cho giao tiếp real-time với robot
manager = ConnectionManager()

# Include routers
app.include_router(music.router, prefix="/api/v1/music", tags=["Music Analysis"])
app.include_router(choreography.router, prefix="/api/v1/choreography", tags=["Choreography"])
app.include_router(robot.router, prefix="/api/v1/robot", tags=["Robot Control"])
app.include_router(ai_music.router, prefix="/api/v1/ai-music", tags=["AI Music Choreographer"])

@app.get("/")
async def root():
    return {
        "message": "Alpha Mini AI Music Choreographer API",
        "version": "2.0.0", 
        "status": "running",
        "features": [
            "Automatic music analysis",
            "AI-powered choreography generation",
            "Built-in Alpha Mini actions & expressions",
            "Real-time robot control",
            "WebSocket support"
        ],
        "endpoints": {
            "ai_music": "/api/v1/ai-music",
            "music": "/api/v1/music", 
            "choreography": "/api/v1/choreography",
            "robot": "/api/v1/robot",
            "docs": "/docs"
        }
    }

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket endpoint cho giao tiếp real-time với robot"""
    await manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.send_personal_message(f"Echo: {data}", client_id)
    except WebSocketDisconnect:
        manager.disconnect(client_id)
        await manager.broadcast(f"Robot {client_id} disconnected")

@app.on_event("startup")
async def startup_event():
    """Khởi tạo khi server start"""
    # Tạo thư mục cần thiết
    os.makedirs("uploads/music", exist_ok=True)
    os.makedirs("uploads/ubx", exist_ok=True)
    os.makedirs("data/analysis", exist_ok=True)
    os.makedirs("data/choreography", exist_ok=True)
    print("✅ Alpha Mini Backend Server started successfully!")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup khi server shutdown"""
    print("🔌 Alpha Mini Backend Server shutting down...")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )
