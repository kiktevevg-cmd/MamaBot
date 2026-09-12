import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import init_db


async def main():
    await init_db()
    print("Database initialized successfully.")


if __name__ == "__main__":
    asyncio.run(main())
