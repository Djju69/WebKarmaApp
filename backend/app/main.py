from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from typing import List, Optional
import os

# Инициализация приложения
app = FastAPI(
    title="WebKarmaApp API",
    description="API для системы лояльности KarmaSystem",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене заменить на конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Модели Pydantic (временные, будут вынесены в отдельный файл)
class UserBase(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: Optional[bool] = None

class UserCreate(UserBase):
    password: str

class UserInDB(UserBase):
    hashed_password: str

# Заглушка для аутентификации
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Заглушка для получения текущего пользователя
async def get_current_user(token: str = Depends(oauth2_scheme)):
    # В реальном приложении здесь будет проверка токена
    return {"username": "testuser", "email": "test@example.com"}

# Эндпоинты
@app.get("/api/health")
async def health_check():
    return {"status": "ok"}

@app.get("/api/me", response_model=UserBase)
async def read_users_me(current_user: dict = Depends(get_current_user)):
    return current_user

# Точка входа для приложения
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
