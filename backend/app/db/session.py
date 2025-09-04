"""
Database session management.
"""
from sqlalchemy.orm import scoped_session
from .base import SessionLocal

# Create a scoped session
SessionScoped = scoped_session(SessionLocal)

def get_db():
    """Dependency function that yields database sessions."""
    db = SessionScoped()
    try:
        yield db
    finally:
        db.close()

# Export SessionLocal for backward compatibility
SessionLocal = SessionLocal
