import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4-turbo")
WEBAPP_URL = os.getenv("WEBAPP_URL", "http://127.0.0.1:5173")
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")

# Amvera монтирует постоянное хранилище в /data (см. amvera.yaml → persistenceMount)
# Путь в коде: /data/<имя_файла>
if os.getenv("AMVERA") == "1":
    DATA_DIR = Path("/data")
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "sqlite+aiosqlite:////data/mama_bot.db",
    )
    LOG_DIR = Path(os.getenv("LOG_DIR", "/data/logs"))
else:
    DATA_DIR = Path(os.getenv("DATA_DIR", "/data"))
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        f"sqlite+aiosqlite:///{DATA_DIR / 'mama_bot.db'}",
    )
    LOG_DIR = Path(os.getenv("LOG_DIR", str(DATA_DIR / "logs")))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
PROMPTS_DIR = BASE_DIR / "prompts"

OPENAI_PARAMS = {
    "model": OPENAI_MODEL,
    "temperature": 0.95,
    "presence_penalty": 0.6,
    "max_tokens": 500,
    "top_p": 0.9,
}
