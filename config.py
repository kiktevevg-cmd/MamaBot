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
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite+aiosqlite:///{BASE_DIR / 'data' / 'mama_bot.db'}",
)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_DIR = BASE_DIR / "logs"
DATA_DIR = BASE_DIR / "data"
PROMPTS_DIR = BASE_DIR / "prompts"

OPENAI_PARAMS = {
    "model": OPENAI_MODEL,
    "temperature": 0.95,
    "presence_penalty": 0.6,
    "max_tokens": 500,
    "top_p": 0.9,
}
