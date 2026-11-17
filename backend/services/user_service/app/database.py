from fastapi import HTTPException, status
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.db_config import user_database_url

database_url = user_database_url()
engine = create_engine(database_url, pool_pre_ping=True) if database_url else None
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def get_db():
    if engine is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="User database is not configured",
        )
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
