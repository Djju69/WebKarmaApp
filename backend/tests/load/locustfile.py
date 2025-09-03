"""
Нагрузочное тестирование приложения с использованием Locust.

Тестирует производительность API при различных уровнях нагрузки.
"""
import os
import random
import time
from datetime import datetime
from typing import Dict, Optional

from locust import HttpUser, task, between, TaskSet, constant
from locust.env import Environment
from locust.log import setup_logging

# Настройка логирования
setup_logging("INFO")

class UserBehavior(TaskSet):
    """Поведение пользователя при нагрузочном тестировании."""
    
    def on_start(self):
        """Вызывается при запуске каждого виртуального пользователя."""
        self.token = self.login()
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        } if self.token else {}
    
    def login(self) -> Optional[str]:
        """Аутентификация пользователя."""
        credentials = {
            "username": os.getenv("TEST_USER", "test@example.com"),
            "password": os.getenv("TEST_PASSWORD", "testpassword123")
        }
        
        with self.client.post(
            "/api/v1/auth/login",
            json=credentials,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                return response.json().get("access_token")
        return None

    @task(3)
    def get_public_data(self):
        """Получение публичных данных (высокая частота)."""
        self.client.get("/api/v1/public/data", headers=self.headers)

    @task(2)
    def get_user_profile(self):
        """Получение профиля пользователя (средняя частота)."""
        self.client.get("/api/v1/users/me", headers=self.headers)

    @task(1)
    def create_item(self):
        """Создание нового элемента (низкая частота)."""
        item_data = {
            "name": f"Item {random.randint(1, 1000)}",
            "description": "Test item",
            "price": random.uniform(10, 1000)
        }
        self.client.post(
            "/api/v1/items",
            json=item_data,
            headers=self.headers
        )

    @task(1)
    def list_items(self):
        """Получение списка элементов с пагинацией."""
        page = random.randint(1, 5)
        self.client.get(
            f"/api/v1/items?page={page}&size=10",
            headers=self.headers
        )

class WebsiteUser(HttpUser):
    """Определение пользовательских сценариев тестирования."""
    
    tasks = [UserBehavior]
    wait_time = between(1, 3)  # Случайная задержка между запросами 1-3 секунды
    host = os.getenv("TARGET_HOST", "http://localhost:8000")

# Конфигурация для различных сценариев нагрузки
class SmokeTest(WebsiteUser):
    """Дымовое тестирование (проверка работоспособности)."""
    wait_time = constant(1)
    weight = 1  # Вес для выбора сценария

class NormalLoad(WebsiteUser):
    """Нормальная нагрузка."""
    wait_time = between(0.5, 2)
    weight = 3

class HighLoad(WebsiteUser):
    """Высокая нагрузка."""
    wait_time = between(0.1, 1)
    weight = 2

class SpikeTest(WebsiteUser):
    """Пиковая нагрузка."""
    wait_time = between(0.05, 0.5)
    weight = 1

def run_load_test():
    """Запуск нагрузочного тестирования."""
    from locust import events
    import pandas as pd
    import matplotlib.pyplot as plt
    
    # Настройка окружения
    env = Environment(user_classes=[WebsiteUser])
    env.create_local_runner()
    
    # Запуск теста
    print("🚀 Запуск нагрузочного тестирования...")
    env.runner.start(100, spawn_rate=10)  # 100 пользователей, скорость нарастания 10 пользователей/сек
    
    try:
        # Ожидание завершения теста
        env.runner.greenlet.join()
    except KeyboardInterrupt:
        print("\n⏹️ Тестирование прервано пользователем")
    
    # Генерация отчета
    generate_report(env)

def generate_report(env):
    """Генерация отчета по результатам тестирования."""
    import os
    from datetime import datetime
    
    # Создаем директорию для отчетов
    report_dir = "load_test_reports"
    os.makedirs(report_dir, exist_ok=True)
    
    # Сохраняем статистику
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    stats = env.stats.serialize_stats()
    
    # Сохраняем сырые данные
    import json
    with open(f"{report_dir}/stats_{timestamp}.json", "w") as f:
        json.dump(stats, f, indent=2)
    
    # Генерируем HTML отчет
    from locust.env import Environment
    from locust.log import setup_logging
    from locust_plugins import run_single_user
    
    print(f"📊 Отчет сохранен в {report_dir}/report_{timestamp}.html")

if __name__ == "__main__":
    run_load_test()
