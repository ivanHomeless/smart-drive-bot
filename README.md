# CarQuery AI Bot

Telegram-бот для автодилера с интеграцией AmoCRM и AI-модулем OpenAI.

Бот собирает структурированные заявки через пошаговые диалоги (продажа, покупка, подбор, проверка, юридическая помощь) и автоматически передает квалифицированные лиды в AmoCRM. AI-модуль на базе OpenAI классифицирует свободные текстовые запросы и направляет клиентов в нужную ветку.

## Стек

- **Python 3.12**, aiogram 3.x (long polling)
- **PostgreSQL 16** -- пользователи, лиды, токены AmoCRM, логи AI
- **Redis 7** -- FSM-хранилище (state_ttl=30 мин)
- **AmoCRM REST API v4** -- контакты, сделки, примечания
- **OpenAI API** -- gpt-4o-mini (основная) + gpt-4o (smart fallback)
- **Docker Compose** -- бот + PostgreSQL + Redis

## Возможности

- 5 веток опроса: продажа, покупка, подбор, проверка авто, юридическая помощь
- AI-классификация свободного текста с автоматическим предложением нужной ветки
- AI pre-fill -- извлеченные сущности (марка, год, бюджет) подставляются в форму
- Smart fallback: если gpt-4o-mini дает низкий confidence (<0.65), автоматически запрашивается gpt-4o
- Экран подтверждения с возможностью редактирования отдельных полей
- Навигация: назад / в начало / пропустить (для необязательных шагов)
- Валидация телефона (международный формат, phonenumbers)
- Загрузка фото (Telegram file_id)
- Дедупликация контактов в AmoCRM по номеру телефона
- Фоновый retry неотправленных лидов (каждые 5 мин)
- Уведомление администратора об ошибках CRM
- Rate limiting (throttling middleware)
- Health check endpoint (`:8080/health`)
- Mock-режим AmoCRM для разработки

## Быстрый старт

### Предварительные требования

- Docker и Docker Compose
- Telegram Bot Token (от [@BotFather](https://t.me/BotFather))
- OpenAI API Key
- AmoCRM аккаунт с внешней интеграцией (для продакшена)

### Локальная разработка

```bash
# Клонировать репозиторий
git clone <repo-url>
cd carquery-ai-bot

# Создать виртуальное окружение
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Настроить переменные окружения
cp .env.example .env
# Заполнить TELEGRAM_BOT_TOKEN, OPENAI_API_KEY, ADMIN_CHAT_ID
# AMOCRM_MOCK_MODE=true для разработки без AmoCRM

# Запустить PostgreSQL и Redis
docker compose up -d db redis

# Применить миграции
.venv/bin/alembic upgrade head

# Запустить бота
.venv/bin/python -m src.main
```

### Docker (полный стек)

```bash
cp .env.example .env
# Заполнить .env

docker compose up -d --build
```

Бот автоматически применяет миграции при запуске.

### Тесты

```bash
.venv/bin/pytest tests/
```

## Настройка AmoCRM

1. Создать внешнюю интеграцию в AmoCRM (Настройки -> Интеграции)
2. Получить Integration ID, Secret Key и Authorization Code
3. Заполнить `AMOCRM_*` переменные в `.env`
4. Запустить однократную авторизацию:

```bash
.venv/bin/python -m scripts.setup_amocrm <AUTHORIZATION_CODE>
```

5. Создать кастомные поля в AmoCRM и заполнить `AMOCRM_FIELD_*` в `.env`

## Настройка BotFather

Команды для регистрации в BotFather (`/setcommands`):

```
start - Главное меню
help - Помощь
menu - Показать меню услуг
```

## Структура проекта

```
src/
├── main.py                  # Точка входа
├── config.py                # Pydantic Settings
├── bot/
│   ├── handlers/            # start, base_dialog, sell, buy, find, check, legal, freetext, common, errors
│   ├── states/              # StatesGroup для каждой ветки
│   ├── keyboards/           # InlineKeyboard builders
│   ├── middlewares/         # DB session, throttling, logging
│   └── filters/             # PhoneFilter
├── services/
│   ├── amocrm/              # OAuth, client, contacts, leads, notes, mock
│   ├── openai_client/       # classify, prompts, models, smart fallback
│   └── lead_processor.py    # Оркестрация: данные -> CRM
├── db/
│   ├── engine.py            # async engine + session factory
│   ├── models.py            # User, Lead, AmoToken, AiLog
│   └── repositories/        # Data access layer
└── utils/                   # phone, retry, formatters, admin
```

## Переменные окружения

Все переменные документированы в `.env.example`. Ключевые:

| Переменная | Описание |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Токен бота от BotFather |
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string |
| `OPENAI_API_KEY` | Ключ OpenAI API |
| `OPENAI_MODEL` | Основная модель (default: gpt-4o-mini) |
| `OPENAI_FALLBACK_MODEL` | Fallback модель (default: gpt-4o) |
| `AMOCRM_MOCK_MODE` | `true` для разработки без AmoCRM |
| `ADMIN_CHAT_ID` | Telegram ID для уведомлений об ошибках |

## Документация

- `PRD_SmartDrive_Bot.md` -- Product Requirements Document
- `IMPLEMENTATION_PLAN.md` -- Phased implementation plan

## Лицензия

Proprietary.
