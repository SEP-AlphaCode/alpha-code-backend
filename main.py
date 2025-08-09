from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.alpha_mini import router as alpha_mini_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cho phép tất cả origin, có thể chỉnh lại domain cụ thể nếu cần
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(alpha_mini_router)
