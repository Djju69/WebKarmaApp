# WebKarmaApp

Веб-приложение для системы лояльности KarmaSystem с тремя типами кабинетов: пользовательский, партнерский и административный.

## 🚀 Технологии

- **Бэкенд**: FastAPI (Python 3.11+), SQLAlchemy 2.x, Alembic, Pydantic v2
- **Фронтенд**: Next.js 14, TypeScript, React 18, Tailwind CSS
- **База данных**: PostgreSQL (общая с ботом KarmaSystem)
- **Кэш и сессии**: Redis 6+
- **Аутентификация**: JWT, сессии в Redis, Telegram OAuth (опционально)
- **Мониторинг**: Sentry, Prometheus метрики, health checks

## 📦 Установка

1. Клонируйте репозиторий:
   ```bash
   git clone https://github.com/Djju69/WebKarmaApp.git
   cd WebKarmaApp
   ```

2. Установите зависимости:
   ```bash
   # Установка зависимостей бэкенда
   cd backend
   python -m venv venv
   source venv/bin/activate  # для Linux/Mac
   # или
   .\venv\Scripts\activate  # для Windows
   pip install -r requirements.txt
   
   # Установка зависимостей фронтенда
   cd ../frontend
   npm install
   ```

3. Настройте переменные окружения (скопируйте и отредактируйте .env.example)
   ```bash
   cp .env.example .env
   ```

## 🏃 Запуск в разработке

1. Запустите Redis и PostgreSQL

2. Запустите бэкенд:
   ```bash
   cd backend
   uvicorn app.main:app --reload
   ```

3. Запустите фронтенд:
   ```bash
   cd frontend
   npm run dev
   ```

4. Откройте http://localhost:3000 в браузере

## 🏗️ Структура проекта

```
WebKarmaApp/
├── backend/                 # FastAPI приложение
│   ├── app/
│   │   ├── api/            # API эндпоинты
│   │   ├── core/           # Основная логика
│   │   ├── db/             # Модели и миграции
│   │   ├── schemas/        # Pydantic схемы
│   │   ├── services/       # Бизнес-логика
│   │   └── main.py         # Точка входа
│   ├── alembic/            # Миграции БД
│   └── requirements.txt    # Зависимости Python
│
├── frontend/               # Next.js приложение
│   ├── public/             # Статические файлы
│   ├── src/
│   │   ├── app/           # Страницы и маршруты
│   │   ├── components/     # Переиспользуемые компоненты
│   │   ├── lib/           # Вспомогательные функции
│   │   └── styles/        # Глобальные стили
│   └── package.json       # Зависимости Node.js
│
├── .github/               # GitHub Actions
├── .env.example          # Пример переменных окружения
└── docker-compose.yml    # Конфигурация Docker
```

## 🔒 Аутентификация и роли

- **Пользователь**: просмотр каталога, личный кабинет, бонусная программа
- **Партнер**: управление карточками заведений, статистика
- **Администратор**: модерация контента, управление пользователями

## 📝 API Документация

После запуска бэкенда откройте:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🚀 Деплой

### Railway

1. Установите [Railway CLI](https://railway.app/cli)
2. Авторизуйтесь: `railway login`
3. Свяжите проект: `railway link`
4. Запустите деплой: `railway up`

### Переменные окружения

См. `.env.example` для полного списка обязательных переменных.

## 📄 Лицензия

MIT
