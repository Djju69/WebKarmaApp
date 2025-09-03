# Руководство по развертыванию

## Требования

- Python 3.10+
- PostgreSQL 13+
- Redis (для кеширования и rate limiting)
- Nginx (рекомендуется для продакшена)
- Docker и Docker Compose (опционально)

## Установка

1. Клонируйте репозиторий:
   ```bash
   git clone https://github.com/yourusername/WebKarmaApp.git
   cd WebKarmaApp/backend
   ```

2. Создайте и активируйте виртуальное окружение:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   # ИЛИ
   .\venv\Scripts\activate  # Windows
   ```

3. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```

4. Создайте файл `.env` на основе `.env.example` и настройте переменные окружения:
   ```bash
   cp .env.example .env
   # Отредактируйте .env файл
   ```

## Настройка базы данных

1. Создайте базу данных в PostgreSQL
2. Примените миграции:
   ```bash
   alembic upgrade head
   ```

3. Создайте суперпользователя (опционально):
   ```bash
   python -m app.scripts.create_admin
   ```

## Запуск приложения

### Для разработки:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Для продакшена с Gunicorn:
```bash
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app
```

### С использованием Docker:
```bash
docker-compose up -d --build
```

## Настройка Nginx (рекомендуется для продакшена)

Пример конфигурации Nginx:

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /path/to/your/static/files/;
    }
}
```

## Мониторинг и логирование

- Логи приложения пишутся в `logs/app.log`
- Для мониторинга рекомендуется настроить Sentry
- Доступ к метрикам Prometheus: `/metrics`

## Резервное копирование

Рекомендуется настроить регулярное резервное копирование базы данных:

```bash
# Пример резервного копирования PostgreSQL
pg_dump -U username -d dbname > backup_$(date +%Y%m%d).sql
```

## Обновление

1. Остановите приложение
2. Получите последние изменения:
   ```bash
   git pull origin main
   ```
3. Обновите зависимости:
   ```bash
   pip install -r requirements.txt
   ```
4. Примените миграции:
   ```bash
   alembic upgrade head
   ```
5. Перезапустите приложение

## Безопасность

- Регулярно обновляйте зависимости
- Используйте HTTPS
- Ограничьте доступ к административным эндпоинтам
- Настройте брандмауэр
- Регулярно проверяйте логи

## Устранение неисправностей

- Проверьте логи: `tail -f logs/app.log`
- Убедитесь, что все сервисы запущены:
  ```bash
  sudo systemctl status postgresql
  sudo systemctl status redis
  ```
- Проверьте доступность портов:
  ```bash
  netstat -tuln | grep -E '8000|5432|6379'
  ```

## Поддержка

По вопросам развертывания и настройки обращайтесь:
- Email: support@yourdomain.com
- Чат: [Ссылка на чат поддержки]
- Документация: [Ссылка на документацию]
