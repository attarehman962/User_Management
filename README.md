# User Management API

A small FastAPI CRUD project for managing users with PostgreSQL.

## Features

- Create user
- Read all users
- Read one user by ID
- Update user
- Delete user
- Duplicate email protection
- Pydantic validation
- Alembic setup

## Project Files

- `main.py`: FastAPI routes
- `schemas.py`: request and response schemas
- `models.py`: SQLAlchemy model
- `database.py`: database connection and session setup
- `tests/test_app.py`: CRUD tests
- `alembic/`: migration setup
- `.env.example`: database URL example
- `requirements.txt`: dependencies

## PostgreSQL Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Make sure PostgreSQL is running:

```bash
sudo systemctl start postgresql
```

3. Create the PostgreSQL user:

```bash
sudo -u postgres psql -c "CREATE USER fastapi_user WITH PASSWORD 'strongpass';"
```

If the user already exists, reset the password:

```bash
sudo -u postgres psql -c "ALTER USER fastapi_user WITH PASSWORD 'strongpass';"
```

4. Create the database:

```bash
sudo -u postgres psql -c "CREATE DATABASE fastapi_db OWNER fastapi_user;"
```

5. Create your local environment file:

```bash
cp .env.example .env
```

6. Put this in `.env`:

```env
DATABASE_URL=postgresql://fastapi_user:strongpass@localhost/fastapi_db
```

## Run The App

```bash
./venv/bin/uvicorn main:app --reload
```

Open:

- `http://127.0.0.1:8000/docs`

## API Endpoints

- `POST /users`
- `GET /users`
- `GET /users/{user_id}`
- `PUT /users/{user_id}`
- `DELETE /users/{user_id}`

## Run Tests

```bash
./venv/bin/python -m unittest discover -s tests -v
```

## Notes

- The app reads the database connection from `.env`.
- `.env` is ignored by Git so your credentials stay local.
- The old SQLite file and generated cache files were removed from the project.
