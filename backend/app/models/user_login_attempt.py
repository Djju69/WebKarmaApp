"""
User login attempt model for tracking authentication attempts.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.db.base import Base

class UserLoginAttempt(Base):
    """Tracks user login attempts for security and monitoring."""
    
    __tablename__ = "user_login_attempts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    ip_address = Column(String(45), nullable=False)  # IPv6 can be up to 45 chars
    user_agent = Column(String(500), nullable=True)
    success = Column(Boolean, default=False, nullable=False)
    attempt_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship with User
    user = relationship("User", back_populates="login_attempts")
    
    def __repr__(self):
        return f"<UserLoginAttempt(user_id={self.user_id}, ip={self.ip_address}, success={self.success})>"
