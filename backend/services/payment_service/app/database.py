import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import HTTPException, status
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

database_url = os.getenv("PAYMENT_DATABASE_URL")
engine = create_engine(database_url, pool_pre_ping=True) if database_url else None
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def get_db():
    if engine is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment database is not configured",
        )
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
