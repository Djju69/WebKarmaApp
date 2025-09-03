from locust import HttpUser, task, between, TaskSet, constant
from random import randint
import json
import uuid

class UserBehavior(TaskSet):
    def on_start(self):
        """Вызывается при запуске каждого виртуального пользователя"""
        self.login()
    
    def login(self):
        """Аутентификация пользователя"""
        response = self.client.post(
            "/api/v1/auth/login",
            json={"username": "test_user", "password": "test_password"}
        )
        if response.status_code == 200:
            self.token = response.json().get("access_token")
            self.headers = {"Authorization": f"Bearer {self.token}"}
    
    @task(3)
    def get_user_profile(self):
        """Получение профиля пользователя"""
        self.client.get("/api/v1/users/me", headers=getattr(self, 'headers', {}))
    
    @task(2)
    def list_users(self):
        """Получение списка пользователей (только для админов)"""
        self.client.get(
            "/api/v1/users/",
            headers=getattr(self, 'headers', {})
        )
    
    @task(1)
    def create_item(self):
        """Создание нового элемента"""
        item_data = {
            "name": f"Item {uuid.uuid4().hex[:8]}",
            "description": "Test item",
            "price": randint(10, 1000)
        }
        self.client.post(
            "/api/v1/items/",
            json=item_data,
            headers=getattr(self, 'headers', {})
        )

class WebsiteUser(HttpUser):
    tasks = [UserBehavior]
    
    # Время ожидания между задачами (от 1 до 5 секунд)
    wait_time = between(1, 5)
    
    # Хост для тестирования
    host = "http://localhost:8000"

# Конфигурация для распределенного тестирования
class CustomLocust(HttpUser):
    abstract = True
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client.verify = False  # Отключение проверки SSL для тестирования

# Настройки для различных сценариев нагрузки
class NormalLoad(WebsiteUser):
    """Нормальная нагрузка: 100 пользователей, скорость роста 10 пользователей в секунду"""
    wait_time = between(2, 5)
    weight = 1

class HighLoad(WebsiteUser):
    """Высокая нагрузка: 1000 пользователей, скорость роста 50 пользователей в секунду"""
    wait_time = between(1, 3)
    weight = 3
    
    @task(5)
    def get_public_data(self):
        """Запрос публичных данных, которые могут кэшироваться"""
        self.client.get("/api/v1/public/items")

class SpikeLoad(WebsiteUser):
    """Пиковая нагрузка: 5000 пользователей, скорость роста 100 пользователей в секунду"""
    wait_time = between(0.5, 2)
    weight = 1
    
    def on_start(self):
        """Не выполняем аутентификацию для всех пользователей при пиковой нагрузке"""
        if randint(1, 10) > 7:  # 30% пользователей аутентифицируются
            super().on_start()
    
    @task(10)
    def get_public_data(self):
        """В основном запрашиваем публичные данные"""
        self.client.get("/api/v1/public/items")
