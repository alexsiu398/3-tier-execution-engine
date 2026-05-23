from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.tests import router as tests_router
from app.api.settings import router as settings_router

app = FastAPI(title="3-Tier Execution Engine", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tests_router, prefix="/api/v1")
app.include_router(settings_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok"}
