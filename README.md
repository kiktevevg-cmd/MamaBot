# Заботливая мама (MamaBot)

Telegram-бот с ИИ, эмулирующий заботливую мать. Поддержка, память, инициативные сообщения и Mini App для настроек.

## Быстрый старт

```bash
# 1. Виртуальное окружение
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/macOS

# 2. Зависимости
pip install -r requirements.txt

# 3. Конфигурация
copy .env.example .env
# Заполните BOT_TOKEN и OPENAI_API_KEY

# 4. База данных
python scripts/init_db.py

# 5. Запуск бота
python bot.py

# 6. API (отдельный терминал)
uvicorn api.main:app --reload --port 8000

# 7. Mini App (отдельный терминал)
cd webapp
npm install
npm run dev
```

## Структура

- `bot.py` — Telegram-бот (Aiogram 3)
- `core/` — GPT, память, кризисный детектор, шедулер
- `database/` — SQLAlchemy модели и CRUD
- `api/` — FastAPI для Mini App
- `webapp/` — React Mini App (Vite)
- `prompts/` — редактируемые промпты
- `tests/` — pytest тесты

## Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Приветствие |
| `/help` | Справка |
| `/settings` | Mini App |
| `/silence 2h` | Режим тишины |
| `/remindme` | Что запомнила |
| `/mood` | Настроение |
| `/forget` | Сброс памяти |
| `/crisis` | Контакты поддержки |

## Тесты

```bash
pytest tests/ -v
```

## Переменные окружения

См. `.env.example`.
