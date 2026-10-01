"""
Database Session and Engine Management with PostgreSQL connection pooling and SQLite fallback.
"""

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from app.core.config import settings
from app.core.logging import logger

Base = declarative_base()


def get_engine_and_sessionmaker(db_url: str):
    """
    Creates a SQLAlchemy engine and sessionmaker with connection pooling.
    Supports SQLite fallback for development and testing.
    """
    is_sqlite = db_url.startswith("sqlite")

    if is_sqlite:
        engine = create_engine(
            db_url,
            connect_args={"check_same_thread": False},
        )
    else:
        engine = create_engine(
            db_url,
            pool_pre_ping=True,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
        )

    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine, session_factory


# Initialize Engine and Session
try:
    engine, SessionLocal = get_engine_and_sessionmaker(settings.DATABASE_URL)
except Exception as exc:
    logger.warning(f"Could not connect to database '{settings.DATABASE_URL}': {exc}. Falling back to SQLite in-memory.")
    engine, SessionLocal = get_engine_and_sessionmaker("sqlite:///:memory:")


def init_db(target_engine=None):
    """
    Initializes database tables.
    """
    eng = target_engine or engine
    Base.metadata.create_all(bind=eng)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a transactional database session per request.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
