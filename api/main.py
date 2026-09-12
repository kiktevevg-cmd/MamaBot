from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.routes import router
from database import init_db

WEBAPP_DIST = Path(__file__).resolve().parent.parent / "webapp" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="MamaBot API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
async def root():
    index = WEBAPP_DIST / "index.html"
    if index.exists():
        return FileResponse(index)
    return {"status": "ok", "webapp": "not built — run npm run build in webapp/"}


if WEBAPP_DIST.exists():
    assets = WEBAPP_DIST / "assets"
    if assets.exists():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/webapp")
    @app.get("/webapp/")
    async def webapp_index():
        return FileResponse(WEBAPP_DIST / "index.html")
