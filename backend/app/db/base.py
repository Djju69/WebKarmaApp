"""
Base database configuration and session management.
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from app.core.config import settings

# Create database engine
engine = create_engine(
    settings.DATABASE_URI,
    connect_args={"check_same_thread": False} if settings.DATABASE_URI.startswith("sqlite") else {},
    pool_pre_ping=True if not settings.DATABASE_URI.startswith("sqlite") else False,
    pool_size=20 if not settings.DATABASE_URI.startswith("sqlite") else 1,
    max_overflow=10 if not settings.DATABASE_URI.startswith("sqlite") else 0,
    pool_recycle=3600 if not settings.DATABASE_URI.startswith("sqlite") else -1
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all models
Base = declarative_base()

def get_db():
    """Dependency function that yields database sessions."""
    db = scoped_session(SessionLocal)
    try:
        yield db
    finally:
        db.close()
