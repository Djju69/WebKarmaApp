"""
Тесты для проверки настройки тестового окружения.
"""
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings

def test_testing_environment():
    """Проверяем, что тесты запускаются в тестовом окружении."""
    assert settings.ENVIRONMENT == "testing"
    assert settings.DEBUG is True
    assert "test.db" in settings.DATABASE_URI

def test_test_endpoint(test_client):
    """Проверяем работу тестового эндпоинта."""
    response = test_client.get("/test")
    assert response.status_code == 200
    assert response.json() == {"message": "Test endpoint is working"}

from sqlalchemy import text

def test_database_creation(db_session):
    """Проверяем, что тестовая база данных создана и доступна."""
    # Простой запрос к базе данных с использованием text()
    result = db_session.execute(text("SELECT 1"))
    assert result.scalar() == 1
