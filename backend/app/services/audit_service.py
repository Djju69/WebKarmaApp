"""
Audit logging service for tracking user actions.
"""
from typing import Optional, Dict, Any
from uuid import UUID
from fastapi import Request, Depends
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.models.audit_log import AuditLog, ActionType
from app.models.user import User
from app.api.deps import get_current_user

class AuditService:
    """Service for handling audit logging."""
    
    @staticmethod
    async def log(
        action: ActionType,
        request: Request = None,
        user: Optional[User] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        db: Session = Depends(get_db)
    ) -> AuditLog:
        """
        Log a user action to the audit log.
        
        Args:
            action: Type of action being logged
            request: FastAPI request object for getting client info
            user: User performing the action (if not provided, will try to get from request)
            resource_type: Type of resource being acted upon
            resource_id: ID of the resource being acted upon
            details: Additional details about the action
            db: Database session
            
        Returns:
            AuditLog: The created audit log entry
        """
        # Try to get user from request if not provided
        if not user and hasattr(request, 'user') and request.user:
            user = request.user
        
        # Get client info from request
        ip_address = None
        user_agent = None
        
        if request:
            ip_address = request.client.host if request.client else None
            user_agent = request.headers.get('user-agent')
        
        # Create the audit log entry
        log_entry = AuditLog.create_log(
            db=db,
            action=action,
            user_id=user.id if user else None,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        return log_entry
    
    @classmethod
    async def log_user_action(
        cls,
        action: ActionType,
        request: Request,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        db: Session = Depends(get_db)
    ) -> AuditLog:
        """
        Log an action for the current authenticated user.
        
        Args:
            action: Type of action being logged
            request: FastAPI request object
            resource_type: Type of resource being acted upon
            resource_id: ID of the resource being acted upon
            details: Additional details about the action
            db: Database session
            
        Returns:
            AuditLog: The created audit log entry
        """
        # Get current user from request
        current_user = await get_current_user(request)
        
        return await cls.log(
            action=action,
            request=request,
            user=current_user,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            db=db
        )

# Helper function to get the audit service
def get_audit_service() -> AuditService:
    """Dependency to get the audit service."""
    return AuditService()
