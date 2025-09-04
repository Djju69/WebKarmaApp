"""
Application configuration settings.
"""
from functools import lru_cache
from pydantic import HttpUrl, PostgresDsn, validator
from pydantic_settings import BaseSettings
from typing import Optional, List, Dict, Any, Union

class Settings(BaseSettings):
    # Application settings
    PROJECT_NAME: str = "KarmaSystem Bot"
    DEBUG: bool = True  # Set to False in production
    ENVIRONMENT: str = "development"  # 'production', 'staging', 'development'
    VERSION: str = "1.0.0"
    
    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RELOAD: bool = True  # Auto-reload in development
    API_V1_STR: str = "/api/v1"
    
    # Logging settings
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"
    
    # Error tracking
    SENTRY_DSN: Optional[str] = None
    
    # OpenTelemetry settings
    OTEL_SERVICE_NAME: str = "karmasystem-bot"
    OTEL_EXPORTER_OTLP_ENDPOINT: Optional[str] = None
    OTEL_EXPORTER_OTLP_INSECURE: bool = True
    OTEL_PYTHON_EXCLUDED_URLS: str = "/health,/metrics,/health/liveness,/health/readiness"
    OTEL_TRACES_SAMPLER: str = "parentbased_always_on"
    OTEL_PYTHON_LOG_CORRELATION: bool = True
    
    # CORS settings
    BACKEND_CORS_ORIGINS: List[str] = ["*"]  # In production, specify exact origins
    
    # Database settings
    SQLITE_DB: str = "sqlite:///./karmasystem.db"
    DATABASE_URI: str = SQLITE_DB
    
    # Redis settings
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    REDIS_CACHE_EXPIRE: int = 300  # 5 минут по умолчанию
    
    # Request validation settings
    ENABLE_REQUEST_VALIDATION: bool = True  # Включить/выключить валидацию запросов
    VALIDATION_ERROR_DETAIL: str = "Ошибка валидации запроса"  # Сообщение об ошибке валидации
    
    @validator("DATABASE_URI", pre=True)
    def assemble_db_connection(cls, v: Optional[str], values: Dict[str, Any]) -> Any:
        if isinstance(v, str):
            return v
        return cls.SQLITE_DB
        
    @property
    def redis_url(self) -> str:
        """Возвращает URL для подключения к Redis"""
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    # JWT settings
    SECRET_KEY: str = "your-secret-key-here"  # Change this in production
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30  # 30 days
    EMAIL_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # Security settings
    REQUIRE_EMAIL_VERIFICATION: bool = True
    MAX_AUTH_ATTEMPTS: int = 5  # Max login attempts before temporary lockout
    ACCOUNT_LOCKOUT_MINUTES: int = 15  # Lockout duration in minutes
    
    # Email settings (for verification and password reset)
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = "noreply@karmasystem.app"
    
    # Rate limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD: int = 300  # 5 minutes in seconds
    
    # Telegram settings
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_WEBHOOK_URL: Optional[HttpUrl] = None
    TELEGRAM_WEBHOOK_SECRET: Optional[str] = None
    
    # Internationalization settings
    DEFAULT_LANGUAGE: str = "ru"
    SUPPORTED_LANGUAGES: List[str] = ["ru", "en", "es", "fr"]
    LANGUAGE_COOKIE_NAME: str = "lang"
    LANGUAGE_HEADER_NAME: str = "Accept-Language"
    
    # Authentication settings
    SECRET_KEY: str = "your-secret-key-here"  # Change this in production!
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    TOKEN_URL: str = "/auth/login"
    
    # Password hashing
    PWD_CONTEXT_SCHEMES: List[str] = ["bcrypt"]
    PWD_DEPRECATED: str = "auto"
    
    # Security
    SECURITY_BCRYPT_ROUNDS: int = 12
    
    # Translation settings
    TRANSLATION_CACHE_TTL: int = 3600  # 1 hour in seconds
    FALLBACK_LANGUAGE: str = "en"
    TELEGRAM_WEBHOOK_ENABLED: bool = True
    TELEGRAM_ADMIN_IDS: List[int] = []
    
    # Telegram bot settings
    TELEGRAM_RETRY_ATTEMPTS: int = 3
    TELEGRAM_RETRY_DELAY: int = 5  # seconds
    
    # Telegram bot commands
    TELEGRAM_BOT_COMMANDS: Dict[str, str] = {
        "start": "Начать работу с ботом",
        "help": "Показать справку по командам",
        "balance": "Показать баланс бонусов",
        "earn": "Начислить бонусы (админ)",
        "spend": "Потратить бонусы",
        "history": "История операций",
        "profile": "Мой профиль"
    }
    
    # Redis settings (for rate limiting, caching, etc.)
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Sentry settings
    SENTRY_DSN: Optional[HttpUrl] = None
    
    # Security
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    
    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache()
def get_settings() -> Settings:
    return Settings()

# Global settings instance
settings = get_settings()
