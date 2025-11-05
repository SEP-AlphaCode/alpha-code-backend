import json
import logging

# from redis import asyncio as aioredis
from aiocache import caches
from config.config import settings
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from aiocache import cached, Cache, RedisCache
from starlette.responses import Response
from app.routers.osmo_router import router as osmo_router
from app.routers.audio_router import router as audio_router
from app.routers.websocket_router import router as websocket_router
from app.routers.music_router import router as music_router
from app.routers.nlp_router import router as nlp_router
from app.routers.stt_router import router as stt_router
from app.routers.marker_router import router as marker_router
from app.routers.object_detect import router as object_router
from app.routers.robot_info_router import router as robot_info_router
from app.routers.chatbot_router import router as chatbot_router
from app.services.socket.handlers.binary_handler import handle_binary_message
from app.services.socket.connection_manager import connection_manager, signaling_manager
from app.services.socket.handlers.text_handler import handle_text_message
# from app.services.music.durations import load_all_durations
# from config.config import settings
from aiocache.serializers import StringSerializer, JsonSerializer

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


# @app.on_event("startup")
# async def startup_event():
#     try:
#         redis = aioredis.from_url(
#             f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}",
#             password=settings.REDIS_PASSWORD,
#             encoding="utf-8",
#             decode_responses=True,
#         )
#         await redis.ping()
#         logging.info("✅ Connected to Redis successfully")
#         print(f"🚀 Redis config: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
# 
#         caches.set_config({
#             'default': {
#                 'cache': RedisCache,
#                 'endpoint': settings.REDIS_HOST,
#                 'port': settings.REDIS_PORT,
#                 'password': settings.REDIS_PASSWORD,
#                 'timeout': 5,
#                 'serializer':JsonSerializer(),
#             }
#         })
#     except Exception as e:
#         logging.error(f"❌ Redis connection failed: {e}")

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
app.include_router(chatbot_router, prefix="/chatbot", tags=["RAG Chatbot"])


# Backward-compatible alias path for websocket without /websocket prefix
@app.websocket("/ws/{serial}")
async def websocket_alias(websocket: WebSocket, serial: str):
    model_id = websocket.headers.get('x-robot-model-id', None)
    
    if not model_id:
        r: Response = Response('No robot model id', 401)
        await websocket.send_denial_response(r)
        return
    
    websocket.max_message_size = 10 * 1024 * 1024
    success = await connection_manager.connect(websocket, serial)
    if not success:
        return  # Connection was rejected
    print(model_id)
    try:
        while True:
            # Accept both text and binary messages
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                break
                
            if message["type"] == "websocket.receive":
                if "text" in message:
                    await handle_text_message(message["text"], serial)
                elif "bytes" in message:
                    await handle_binary_message(websocket, message["bytes"], serial, model_id)
            # print('Done process message')
    except WebSocketDisconnect:
        print(f"WebSocket disconnected: {websocket.client}")
        await connection_manager.disconnect(serial)
    except Exception as e:
        print(f"WebSocket error: {websocket.client}, {e}")
        await connection_manager.disconnect(serial)


# Add signaling endpoint directly to main app (without /websocket prefix)
@app.websocket("/ws/signaling/{serial}/{client_type}")
async def signaling_main(ws: WebSocket, serial: str, client_type: str):
    ws.max_message_size = 10 * 1024 * 1024
    """
    WebSocket signaling giữa robot và web client - Direct route
    client_type: "robot" hoặc "web"
    """
    import logging
    logging.info(f"=== MAIN APP signaling connection attempt ===")
    logging.info(f"Serial: {serial}, Client type: {client_type}")

    # Accept connection immediately
    await ws.accept()
    logging.info(f"Signaling accepted: {serial}/{client_type}")

    try:
        # Validate
        if client_type not in ["robot", "web"]:
            await ws.close(code=1008, reason="Invalid client_type")
            return

        # Add to connection manager
        if serial not in signaling_manager.clients:
            signaling_manager.clients[serial] = {}

        # Close old connection of same type
        if client_type in signaling_manager.clients[serial]:
            try:
                old_ws = signaling_manager.clients[serial][client_type].websocket
                if old_ws.client_state.name != "DISCONNECTED":
                    await old_ws.close(reason=f"New {client_type} connection")
            except:
                pass

        from app.services.socket.connection_manager import WSMapEntry
        signaling_manager.clients[serial][client_type] = WSMapEntry(ws, ws.headers.get("client_id"))
        logging.info(f"✅ Signaling connection established: {serial}/{client_type}")

        # Message loop
        while True:
            data = await ws.receive_json()
            logging.info(f"Signaling data from {client_type}: {data}")

            # Relay to other side
            target_type = "web" if client_type == "robot" else "robot"
            if signaling_manager.is_connected(serial, target_type):
                await signaling_manager.send_to_client(serial, json.dumps(data), target_type)

    except WebSocketDisconnect:
        logging.info(f"Signaling disconnected: {serial}/{client_type}")
    except Exception as e:
        logging.error(f"Signaling error: {e}")
    finally:
        try:
            await signaling_manager.disconnect(serial, client_type)
        except:
            pass


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")


"""Main application entrypoint. WebSocket logic moved to routers.websocket_router."""
