from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db
from app.routes import router as user_router
from app.security import get_jwt_settings


@asynccontextmanager
async def lifespan(_: FastAPI):
    get_jwt_settings()
    yield


app = FastAPI(title="User Service", lifespan=lifespan)
app.include_router(user_router, prefix="/api/v1")


@app.get("/health")
def health():
    return {"service": "user", "status": "ok"}


@app.get("/health/db")
def database_health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Database unavailable") from None
    return {"service": "user", "database": "connected"}
