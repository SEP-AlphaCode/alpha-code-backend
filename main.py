from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.routers.osmo_router import router as osmo_router
from app.routers.audio_router import router as audio_router
from app.routers.websocket_router import router as websocket_router
from app.routers.music_router import router as music_router
from app.routers.nlp_router import router as nlp_router
from app.routers.stt_router import router as stt_router
from app.routers.marker_router import router as marker_router
from app.routers.object_detect import router as object_router
from app.routers.robot_info_router import router as robot_info_router
from app.services.socket.connection_manager import connection_manager
from config.config import settings

# Build FastAPI kwargs dynamically to avoid invalid empty URL in license
fastapi_kwargs = dict(
    title=settings.TITLE,
    description=settings.DESCRIPTION,
    version=settings.VERSION,
)
contact = {"name": settings.CONTACT_NAME, "email": settings.CONTACT_EMAIL}
if any(contact.values()):
    fastapi_kwargs["contact"] = contact
if settings.LICENSE_NAME and settings.LICENSE_URL:
    fastapi_kwargs["license_info"] = {"name": settings.LICENSE_NAME, "url": settings.LICENSE_URL}

app = FastAPI(**fastapi_kwargs)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cho phép tất cả origin, có thể chỉnh lại domain cụ thể nếu cần
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(audio_router, prefix="/audio", tags=["Audio"])
app.include_router(osmo_router, prefix="/osmo", tags=["Osmo"])
app.include_router(websocket_router, prefix="/websocket", tags=["WebSocket"])
app.include_router(music_router, prefix="/music", tags=["Music"])
app.include_router(stt_router, prefix="/stt", tags=["STT"])
app.include_router(nlp_router, prefix="/nlp", tags=["NLP"])
app.include_router(marker_router, prefix="/marker", tags=["Marker"])
app.include_router(object_router, prefix="/object", tags=["Object Detection"])
app.include_router(robot_info_router, prefix="/robot", tags=["Robot Info"])

# Backward-compatible alias path for websocket without /websocket prefix
@app.websocket("/ws/{serial}")
async def websocket_alias(websocket: WebSocket, serial: str):
    await connection_manager.connect(websocket, serial)
    try:
        while True:
            data = await websocket.receive_text()
            print(f"[Alias /ws] Client said: {data}")
    except WebSocketDisconnect:
        connection_manager.disconnect(serial)
    except Exception as e:
        print(f"WebSocket alias error: {e}")
        connection_manager.disconnect(serial)


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")

"""Main application entrypoint. WebSocket logic moved to routers.websocket_router."""