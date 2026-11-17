from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db
from app.routes import router

app = FastAPI(title="Payment Service")
app.include_router(router, prefix="/api/v1")


@app.get("/health")
def health():
    return {"service": "payment", "status": "ok"}


@app.get("/health/db")
def database_health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Database unavailable") from None
    return {"service": "payment", "database": "connected"}
