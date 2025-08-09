from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from routers.osmo_router import router as osmo_router
from routers.audio_router import router as audio_router

from config.config import settings

app = FastAPI(
    title=settings.TITLE,
    description=settings.DESCRIPTION,
    version=settings.VERSION,
    contact={
        "name": settings.CONTACT_NAME,
        "email": settings.CONTACT_EMAIL,
    },
    license_info={
        "name": settings.LICENSE_NAME,
        "url": settings.LICENSE_URL,
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cho phép tất cả origin, có thể chỉnh lại domain cụ thể nếu cần
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(osmo_router, prefix="/osmo", tags=["Osmo"])
app.include_router(audio_router, prefix="/audio", tags=["Audio"])

@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")