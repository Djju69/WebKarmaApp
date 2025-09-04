"""
Script to list all registered API routes in the application.
"""
import uvicorn
from fastapi import FastAPI
from app.core.config import settings
from app.api.api import api_router

def list_routes():
    """List all registered API routes."""
    app = FastAPI(title=settings.PROJECT_NAME, openapi_url=f"{settings.API_V1_STR}/openapi.json")
    app.include_router(api_router, prefix=settings.API_V1_STR)
    
    print("\nRegistered routes:")
    print("-" * 50)
    for route in app.routes:
        if hasattr(route, "path"):
            print(f"{route.methods}: {route.path}")
    print("-" * 50)

if __name__ == "__main__":
    list_routes()
