# WebKarmaApp

Веб-приложение для системы лояльности KarmaSystem с тремя типами кабинетов: пользовательский, партнерский и административный. Полностью синхронизировано с существующим телеграм-ботом через общую базу данных.

## Технологии

### Бэкенд (webkarma-api)
- **Язык**: Python 3.11+
- **Фреймворк**: FastAPI
- **ORM**: SQLAlchemy 2.x, Alembic
- **Валидация**: Pydantic v2
- **Аутентификация**: JWT, 2FA для админов, Telegram OAuth
- **Кэширование**: Redis 7+
- **Мониторинг**: Sentry, Prometheus, health checks

### Фронтенд (webkarma-frontend)
- **Фреймворк**: Next.js 14
- **Язык**: TypeScript
- **UI**: React 18, Tailwind CSS
- **Многоязычность**: Поддержка RU/EN/DE/FR
- **Тема**: Черно-белый минималистичный дизайн

### Инфраструктура (Railway)
- **БД**: PostgreSQL 15+ (общая с ботом)
- **Кэш**: Redis 7+
- **CI/CD**: GitHub Actions
- **Мониторинг**: Встроенный в Railway + Sentry

## Архитектура Railway

Проект развернут на Railway с использованием multi-service подхода:

```
webkarma-project (Railway Project)
├── webkarma-bot         (существующий бокс)
├── webkarma-api         (новый FastAPI бэкенд)
├── webkarma-frontend    (Next.js фронтенд)
├── webkarma-redis       (общий Redis)
└── webkarma-postgres    (общая PostgreSQL БД)
```

## Установка для разработки

1. Клонируйте репозиторий:
   ```bash
   git clone https://github.com/Djju69/WebKarmaApp.git
   cd WebKarmaApp
   ```

2. Настройте бэкенд:
   ```bash
   cd backend
   python -m venv venv
   # Для Linux/Mac:
   source venv/bin/activate
   # Для Windows:
   .\venv\Scripts\activate
   
   pip install -r requirements.txt
   ```

3. Настройте фронтенд:
   ```bash
   cd ../frontend
   npm install
   ```

4. Настройте переменные окружения:
   ```bash
   # backend/.env
   DATABASE_URL=postgresql://user:pass@localhost:5432/webkarma
   REDIS_URL=redis://localhost:6379/0
   JWT_SECRET=your_jwt_secret
   
   # frontend/.env.local
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

## Запуск в разработке

1. Запустите зависимости:
   ```bash
   # Запуск PostgreSQL и Redis (требуется Docker)
   docker-compose up -d postgres redis
   ```

2. Запустите бэкенд:
   ```bash
   cd backend
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

3. Запустите фронтенд:
   ```bash
   cd frontend
   npm run dev
   ```

4. Откройте в браузере:
   - Фронтенд: http://localhost:3000
   - API документация: http://localhost:8000/docs
   - Админка: http://localhost:8000/admin

## Структура проекта

```
WebKarmaApp/
├── backend/                     # FastAPI приложение (webkarma-api)
│   ├── app/
│   │   ├── api/                # API эндпоинты (REST + WebSocket)
│   │   │   ├── v1/             # API v1
│   │   │   └── admin/          # Админские эндпоинты
│   │   ├── core/               # Ядро приложения
│   │   │   ├── config/         # Конфигурация
│   │   │   ├── database/       # Модели и миграции
│   │   │   ├── security/       # Аутентификация и авторизация
│   │   │   └── services/       # Бизнес-логика
│   │   └── schemas/            # Pydantic схемы
│   ├── tests/                  # Тесты
│   └── alembic/                # Миграции БД
│
├── frontend/                   # Next.js приложение (webkarma-frontend)
│   ├── public/                 # Статические файлы
│   ├── src/
│   │   ├── app/               # Страницы (App Router)
│   │   │   ├── [locale]/      # Многоязычные маршруты
│   │   │   ├── api/           # API роуты
│   │   │   └── layout.tsx     # Основной лейаут
│   │   ├── components/        # UI компоненты
│   │   ├── lib/               # Утилиты и хелперы
│   │   └── styles/            # Глобальные стили
│   └── next.config.js         # Конфигурация Next.js
│
├── .github/workflows/         # GitHub Actions
│   └── deploy.yml            # CI/CD пайплайн
├── docker-compose.yml        # Локальная разработка
└── .env.example             # Пример переменных окружения
```

## Роли и права доступа

### Пользователь
- Просмотр каталога с фильтрами
- Личный кабинет
- Бонусная программа и баллы лояльности
- Реферальная система
- История операций

### Партнер
- Управление карточками заведений
- Просмотр статистики
- Управление акциями и скидками
- Аналитика по клиентам

### Администратор
- Модерация контента
- Управление пользователями
- Настройка системы лояльности
- Доступ к аналитике

### SuperAdmin
- Управление дизайном (макеты, темы)
- Настройка многоязычности
- Управление баннерами и промо
- Системные настройки

## Документация

### API
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Postman коллекция: `/docs/postman/WebKarmaAPI.postman_collection.json`

### Разработка
- [Руководство по стилю кода](/docs/CODING_STANDARDS.md)
- [Архитектура приложения](/docs/ARCHITECTURE.md)
- [Многоязычность](/docs/I18N_GUIDE.md)

### Развертывание
- [Деплой на Railway](/docs/RAILWAY_DEPLOYMENT.md)
- [Настройка окружения](/docs/ENV_SETUP.md)
- [Мониторинг и логи](/docs/MONITORING.md)

## Деплой на Railway

### Автоматический деплой из GitHub
1. Форкните репозиторий
2. Подключите к Railway через GitHub интеграцию
3. Настройте переменные окружения в Railway Dashboard
4. Включите автоматический деплой для ветки `main`

### Ручной деплой
```bash
# Установка Railway CLI
npm i -g @railway/cli

# Авторизация
railway login

# Связывание с проектом
railway link

# Деплой
railway up
```

### Переменные окружения
Основные переменные окружения (полный список в `.env.example`):

**Бэкенд:**
```
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
JWT_SECRET=...
SENTRY_DSN=...
```

**Фронтенд:**
```
NEXT_PUBLIC_API_URL=...
NEXT_PUBLIC_SENTRY_DSN=...
NEXTAUTH_SECRET=...
```

## Мониторинг

- **Sentry**: Отслеживание ошибок и производительности
- **Railway Dashboard**: Мониторинг ресурсов и логи
- **Health Checks**: `/health` эндпоинты для проверки состояния сервисов

## 📊 Текущий прогресс (03.09.2025)

### ✅ Выполнено:
1. **Инфраструктура**
   - Настроен multi-service проект на Railway
   - Подключены общие сервисы (PostgreSQL, Redis)
   - Настроен CI/CD через GitHub Actions

2. **Бэкенд**
   - Базовый API на FastAPI
   - Аутентификация и авторизация (JWT + 2FA)
   - Интеграция с существующей БД
   - Health checks и мониторинг

3. **Фронтенд**
   - Базовая структура Next.js 14
   - Черно-белая тема
   - Многоязычная поддержка (RU/EN/DE/FR)
   - Адаптивный дизайн

### 🚧 В процессе:
1. Интеграция с Telegram API
2. Система продвижения карточек
3. Админ-панель SuperAdmin
4. Документация API

### 📅 Планы:
1. Полная интеграция с ботом
2. Система аналитики
3. Мобильное приложение
4. Дополнительные способы оплаты

## Лицензия

MIT 2025 KarmaSystem Team
