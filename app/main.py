from contextlib import asynccontextmanager
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app import models
from app.auth import hash_password
from app.database import SessionLocal, create_db_and_tables
from app.routers import auth, users

_FRONTEND_DIST = Path(__file__).resolve().parents[1] / "frontend" / "dist"


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is not set. Add it to .env before starting the app.")
    return value


DEFAULT_ADMIN_NAME = _required_env("DEFAULT_ADMIN_NAME")
DEFAULT_ADMIN_EMAIL = _required_env("DEFAULT_ADMIN_EMAIL")
DEFAULT_ADMIN_PASSWORD = _required_env("DEFAULT_ADMIN_PASSWORD")


def ensure_default_admin() -> None:
    db = SessionLocal()
    try:
        has_users = db.query(models.User.id).first() is not None
        if has_users:
            return

        db.add(
            models.User(
                name=DEFAULT_ADMIN_NAME,
                email=DEFAULT_ADMIN_EMAIL,
                password_hash=hash_password(DEFAULT_ADMIN_PASSWORD),
                role="admin",
            )
        )
        db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_: FastAPI):
    create_db_and_tables()
    ensure_default_admin()
    yield


app = FastAPI(
    title="User Management API",
    description="JWT-authenticated CRUD API for managing users.",
    version="1.0.0",
    lifespan=lifespan,
)

if (_FRONTEND_DIST / "assets").exists():
    app.mount(
        "/assets",
        StaticFiles(directory=_FRONTEND_DIST / "assets"),
        name="assets",
    )

app.include_router(auth.router)
app.include_router(users.router)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def dashboard():
    dist_index = _FRONTEND_DIST / "index.html"
    if dist_index.exists():
        return HTMLResponse(dist_index.read_text(encoding="utf-8"))

    return HTMLResponse("""
        <!doctype html>
        <html lang="en">
          <head>
            <meta charset="UTF-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1.0" />
            <title>Frontend Not Built</title>
          </head>
          <body style="font-family:sans-serif;padding:2rem;line-height:1.6">
            <h1>React frontend build not found</h1>
            <p>Run <code>cd frontend &amp;&amp; npm install &amp;&amp; npm run build</code>.</p>
            <p>For development, run <code>npm run dev</code> and open the Vite URL.</p>
          </body>
        </html>
    """)
