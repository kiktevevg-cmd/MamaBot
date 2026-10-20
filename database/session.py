from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import DATA_DIR, DATABASE_URL
from database.models import Base

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Columns added after initial schema — SQLite create_all won't alter existing tables
_USER_SETTINGS_MIGRATIONS = [
    ("enable_reactions", "BOOLEAN DEFAULT 1"),
    ("allow_multiple_reactions", "BOOLEAN DEFAULT 1"),
    ("reaction_style", "TEXT DEFAULT 'живой'"),
    ("reaction_sensitivity", "INTEGER DEFAULT 3"),
    ("persona_json", "TEXT DEFAULT '{}'"),
    ("relationship_json", "TEXT DEFAULT '{}'"),
    ("mama_status", "TEXT"),
    ("mama_status_updated_at", "DATETIME"),
    # DEFAULT 1: существующие пользователи не сбрасываются в онбординг
    ("onboarding_completed", "BOOLEAN DEFAULT 1"),
    ("onboarding_step", "INTEGER DEFAULT 0"),
]


async def _migrate_sqlite(conn) -> None:
    result = await conn.execute(text("PRAGMA table_info(user_settings)"))
    existing = {row[1] for row in result.fetchall()}
    for column, col_type in _USER_SETTINGS_MIGRATIONS:
        if column not in existing:
            await conn.execute(
                text(f"ALTER TABLE user_settings ADD COLUMN {column} {col_type}")
            )


async def init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if DATABASE_URL.startswith("sqlite"):
            await _migrate_sqlite(conn)
