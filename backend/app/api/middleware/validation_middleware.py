"""
Request validation middleware for FastAPI.
"""
from typing import Any, Callable, Dict, Optional, Type, TypeVar, Union, List, Tuple
from functools import wraps
import logging

from fastapi import Request, HTTPException, status, Response
from fastapi.routing import APIRoute
from fastapi.types import DecoratedCallable
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError

from app.core.validators import validate_request_data
from app.core.config import settings

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)

def validate_request(
    model: Type[T],
    body_param: Optional[str] = None,
    query_param: Optional[str] = None,
    path_param: Optional[str] = None,
    exclude_unset: bool = False,
    exclude_defaults: bool = False,
    exclude_none: bool = False,
) -> Callable:
    """
    Decorator factory for request validation.
    
    Args:
        model: Pydantic model to validate against
        body_param: Name of the body parameter in the function signature
        query_param: Name of the query parameter in the function signature
        path_param: Name of the path parameter in the function signature
        exclude_unset: Whether to exclude unset fields
        exclude_defaults: Whether to exclude fields with default values
        exclude_none: Whether to exclude None values
        
    Returns:
        Decorated function with validation
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Skip validation if disabled in settings
            if not settings.ENABLE_REQUEST_VALIDATION:
                return await func(*args, **kwargs)
                
            request = None
            
            # Find the request object in the function arguments
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if request is None:
                for arg in kwargs.values():
                    if isinstance(arg, Request):
                        request = arg
                        break
            
            if request is None:
                raise RuntimeError("Request object not found in function arguments")
            
            # Get data to validate based on the parameter types
            data_to_validate = {}
            
            if body_param:
                if body_param in kwargs:
                    data_to_validate = kwargs[body_param]
                else:
                    try:
                        data_to_validate = await request.json()
                    except Exception:
                        pass
            
            if query_param:
                if query_param in kwargs:
                    data_to_validate.update(kwargs[query_param])
                else:
                    data_to_validate.update(dict(request.query_params))
            
            if path_param and path_param in kwargs:
                if isinstance(kwargs[path_param], dict):
                    data_to_validate.update(kwargs[path_param])
                else:
                    data_to_validate[path_param] = kwargs[path_param]
            
            try:
                # Validate the data
                validated_data = validate_request_data(
                    model=model,
                    data=data_to_validate,
                    exclude_unset=exclude_unset,
                    exclude_defaults=exclude_defaults,
                    exclude_none=exclude_none,
                )
                
                # Update the kwargs with the validated data
                if body_param:
                    kwargs[body_param] = validated_data
                
                # Call the original function with validated data
                return await func(*args, **kwargs)
                
            except HTTPException as e:
                # Re-raise HTTP exceptions
                raise e
                
            except ValidationError as e:
                # Log validation error
                logger.warning(f"Validation error: {e}")
                
                # Convert validation errors to HTTP 422 response
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail={
                        "detail": settings.VALIDATION_ERROR_DETAIL,
                        "errors": e.errors()
                    }
                )
                
            except HTTPException:
                # Re-raise HTTP exceptions
                raise
                
            except Exception as e:
                # Log the error
                logger.error(f"Unexpected error in request validation: {str(e)}", exc_info=True)
                
                # Handle other exceptions
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail={"detail": "Internal server error during request validation"}
                )
        
        return wrapper
    
    return decorator

# Example usage:
# @router.post("/users/")
# @validate_request(UserCreate, body_param="user")
# async def create_user(user: UserCreate):
#     # user is already validated here
#     return {"id": 1, **user.dict()}

class ValidatedRoute(APIRoute):
    """
    Custom route class that automatically validates request data.
    
    This route class extends FastAPI's APIRoute to provide automatic
    request validation using Pydantic models.
    """
    
    def get_route_handler(self) -> Callable[[Request], Any]:
        original_route_handler = super().get_route_handler()
        
        async def custom_route_handler(request: Request) -> Any:
            # Skip validation if disabled in settings
            if not settings.ENABLE_REQUEST_VALIDATION:
                return await original_route_handler(request)
            
            try:
                # Get the request body if it's a JSON request
                body = {}
                content_type = request.headers.get("content-type", "")
                
                if request.method in ("POST", "PUT", "PATCH", "DELETE"):
                    if "application/json" in content_type:
                        try:
                            body = await request.json()
                            if not isinstance(body, dict):
                                body = {"data": body}
                        except Exception as e:
                            logger.warning(f"Failed to parse JSON body: {str(e)}")
                    elif "form-data" in content_type or "x-www-form-urlencoded" in content_type:
                        try:
                            form_data = await request.form()
                            body = dict(form_data)
                            # Convert file uploads to a more usable format
                            for key, value in form_data.items():
                                if hasattr(value, "filename"):
                                    body[key] = {
                                        "filename": value.filename,
                                        "content_type": value.content_type,
                                        "size": len(await value.read())
                                    }
                        except Exception as e:
                            logger.warning(f"Failed to parse form data: {str(e)}")
                
                # Get query parameters
                query_params = dict(request.query_params)
                
                # Get path parameters
                path_params = dict(request.path_params)
                
                try:
                    # Let FastAPI handle the request and validation
                    response = await original_route_handler(request)
                except HTTPException as http_exc:
                    # Re-raise HTTP exceptions as they're already properly formatted
                    raise http_exc
                except ValidationError as e:
                    # Handle validation errors from FastAPI
                    logger.warning(f"Request validation error: {e}")
                    if settings.DEBUG:
                        return JSONResponse(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            content={
                                "detail": settings.VALIDATION_ERROR_DETAIL,
                                "errors": e.errors(),
                            }
                        )
                    else:
                        return JSONResponse(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            content={"detail": settings.VALIDATION_ERROR_DETAIL}
                        )
                
                # If the response is a Response object, return it as is
                if isinstance(response, Response):
                    return response
                
                # Get the response model
                response_model = None
                if hasattr(self, 'response_model'):
                    response_model = self.response_model
                elif hasattr(self, 'response_class') and hasattr(self.response_class, '__model__'):
                    response_model = self.response_class.__model__
                
                # If no response model, return the response as is
                if response_model is None:
                    return response
                
                # If the response is already a Pydantic model, validate it
                if isinstance(response, BaseModel):
                    return response
                
                # Validate the response data if it's a dictionary
                if isinstance(response, dict):
                    try:
                        # Create an instance of the response model to validate the data
                        validated = response_model.model_validate(response)
                        return validated.model_dump()
                    except Exception as e:
                        logger.error(f"Response validation error: {e}")
                        if settings.DEBUG:
                            return JSONResponse(
                                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                content={
                                    "detail": "Response validation error",
                                    "error": str(e),
                                    "response": response
                                }
                            )
                        else:
                            return JSONResponse(
                                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                content={"detail": "Internal server error"}
                            )
                
                return response
                
            except Exception as e:
                # Log the error
                logger.error(f"Unexpected error in request handling: {str(e)}", exc_info=True)
                
                # Return a 500 response
                if settings.DEBUG:
                    return JSONResponse(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        content={
                            "detail": "Internal server error",
                            "error": str(e)
                        }
                    )
                else:
                    return JSONResponse(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        content={"detail": "Internal server error"}
                    )
        
        return custom_route_handler
