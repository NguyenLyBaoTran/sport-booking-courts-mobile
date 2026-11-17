from fastapi import FastAPI

from app.core.config import settings
from app.routers.health import router as health_router

app = FastAPI(title=settings.app_name)
app.include_router(health_router, prefix="/api/v1", tags=["health"])


@app.get("/")
def root() -> dict[str, str]:
    return {
        "status": "ok",
        "message": f"{settings.app_name} is running",
    }
