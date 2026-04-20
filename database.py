# database.py
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set. Create a .env file from .env.example or export DATABASE_URL before starting the app."
    )

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def sync_user_schema() -> None:
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("users")}
    if "password_hash" in columns:
        return

    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE users ADD COLUMN password_hash VARCHAR(255)"))



def create_db_and_tables() -> None:
    Base.metadata.create_all(bind=engine)
    sync_user_schema()
