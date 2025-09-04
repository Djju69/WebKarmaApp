"""
Validation utilities for request data and forms.
"""
import re
from typing import Any, Dict, List, Optional, Type, TypeVar, Union
from pydantic import BaseModel, ValidationError, validator
from fastapi import HTTPException, status

T = TypeVar('T', bound=BaseModel)

def validate_request_data(
    model: Type[T],
    data: Union[Dict[str, Any], Any],
    context: Optional[Dict[str, Any]] = None,
    exclude_unset: bool = False,
    exclude_defaults: bool = False,
    exclude_none: bool = False,
) -> T:
    """
    Validate request data against a Pydantic model.
    
    Args:
        model: Pydantic model class to validate against
        data: Data to validate (dict or Pydantic model)
        context: Additional context for validation
        exclude_unset: Whether to exclude unset fields
        exclude_defaults: Whether to exclude fields with default values
        exclude_none: Whether to exclude None values
        
    Returns:
        Validated model instance
        
    Raises:
        HTTPException: If validation fails
    """
    try:
        if isinstance(data, dict):
            return model(
                **data,
                **({"__root__": data} if hasattr(model, "__root__") else {}),
                **(context or {})
            )
        elif isinstance(data, BaseModel):
            return model.parse_obj(data.dict(
                exclude_unset=exclude_unset,
                exclude_defaults=exclude_defaults,
                exclude_none=exclude_none,
            ))
        else:
            raise ValueError("Invalid data type for validation")
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"detail": e.errors()}
        )

# Common validators
def validate_password_strength(password: str) -> str:
    """
    Validate password strength.
    
    Requirements:
    - At least 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    """
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter")
        
    if not re.search(r"[a-z]", password):
        raise ValueError("Password must contain at least one lowercase letter")
        
    if not re.search(r"\d", password):
        raise ValueError("Password must contain at least one digit")
        
    if not re.search(r"[^A-Za-z0-9]", password):
        raise ValueError("Password must contain at least one special character")
        
    return password

def validate_email_format(email: str) -> str:
    """
    Validate email format using a simple regex.
    For more comprehensive validation, use pydantic.EmailStr.
    """
    if not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email):
        raise ValueError("Invalid email format")
    return email.lower()

def validate_phone_number(phone: str) -> str:
    """
    Validate phone number format.
    
    Requirements:
    - Must start with a plus sign (+)
    - Must contain only digits and optional spaces, dashes, or parentheses
    - Must be between 5 and 20 characters long
    """
    phone = phone.strip()
    if not phone.startswith('+'):
        raise ValueError("Phone number must start with a plus sign (+)")
    
    # Remove all non-digit characters except the leading +
    digits = re.sub(r"[^0-9+]", "", phone)
    
    if len(digits) < 5 or len(digits) > 20:
        raise ValueError("Phone number must be between 5 and 20 digits long")
        
    return digits

def validate_file_extension(filename: str, allowed_extensions: List[str]) -> str:
    """
    Validate file extension.
    
    Args:
        filename: Name of the file to validate
        allowed_extensions: List of allowed file extensions (e.g., ['.jpg', '.png'])
        
    Returns:
        Lowercase file extension with leading dot
        
    Raises:
        ValueError: If file extension is not allowed
    """
    if not filename:
        raise ValueError("No file selected")
        
    ext = filename.rsplit('.', 1)[-1].lower()
    if f".{ext}" not in allowed_extensions:
        raise ValueError(f"File type not allowed. Allowed types: {', '.join(allowed_extensions)}")
        
    return f".{ext}"

# Custom validators for common fields
class ValidatorsMixin:
    """Mixin class with common validators for Pydantic models."""
    
    @validator('email', pre=True, always=True)
    def validate_email(cls, v):
        if v is None:
            return v
        return validate_email_format(v)
    
    @validator('password', pre=True, always=True)
    def validate_password(cls, v):
        if v is None:
            return v
        return validate_password_strength(v)
    
    @validator('phone', pre=True, always=True)
    def validate_phone(cls, v):
        if not v:
            return v
        return validate_phone_number(v)

# Example usage in a Pydantic model:
# class UserCreate(ValidatorsMixin, BaseModel):
#     email: str
#     password: str
#     phone: Optional[str] = None
