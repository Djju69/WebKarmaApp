"""
Role-Based Access Control (RBAC) utilities.
"""
from typing import List, Set, Callable, Any, Coroutine, TypeVar
from functools import wraps
from fastapi import Depends, HTTPException, status

from app.models.user import User
from app.schemas.user import UserWithRoles
from app.api.deps import get_current_active_user, get_db
from sqlalchemy.orm import Session

T = TypeVar('T')

class RBAC:
    """RBAC handler for permission and role checks."""
    
    @classmethod
    def has_permission(cls, permissions: List[str], require_all: bool = True) -> Callable:
        """Check if user has required permissions."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(
                *args,
                current_user: User = Depends(get_current_active_user),
                db: Session = Depends(get_db),
                **kwargs
            ) -> Any:
                user_perms = set()
                for role in current_user.roles:
                    user_perms.update(p.name for p in role.permissions)
                
                if require_all and not all(p in user_perms for p in permissions):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Insufficient permissions"
                    )
                elif not any(p in user_perms for p in permissions):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="No required permissions found"
                    )
                return await func(*args, current_user=current_user, **kwargs)
            return wrapper
        return decorator
    
    @classmethod
    def has_role(cls, roles: List[str], require_all: bool = False) -> Callable:
        """Check if user has required roles."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(
                *args,
                current_user: User = Depends(get_current_active_user),
                **kwargs
            ) -> Any:
                user_roles = {r.name for r in current_user.roles}
                
                if require_all and not all(r in user_roles for r in roles):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Missing required roles"
                    )
                elif not any(r in user_roles for r in roles):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="No required roles found"
                    )
                return await func(*args, current_user=current_user, **kwargs)
            return wrapper
        return decorator
