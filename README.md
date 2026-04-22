# User Management

A full-stack user management application with a **FastAPI** backend and **React + Vite** frontend. Covers registration, JWT authentication, and protected CRUD operations on users.

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+, FastAPI, SQLAlchemy |
| Database | PostgreSQL (Alembic migrations) |
| Auth | Custom HS256 JWT + PBKDF2-SHA256 (Python stdlib only) |
| Frontend | React 18, Vite 5 |
| Tests | Python `unittest` with SQLite |

## Project Structure

```
User_Management/
├── app/
│   ├── __init__.py
│   ├── main.py            # FastAPI app factory, lifespan, root route
│   ├── database.py        # SQLAlchemy engine, session, Base
│   ├── models.py          # User ORM model
│   ├── schemas.py         # Pydantic request/response schemas
│   ├── auth.py            # Password hashing + JWT (stdlib only)
│   ├── dependencies.py    # Shared FastAPI deps: get_db, get_current_user
│   └── routers/
│       ├── auth.py        # POST /auth/login  GET /auth/me
│       └── users.py       # CRUD /users
├── alembic/
│   ├── env.py
│   └── versions/
├── tests/
│   ├── __init__.py
│   └── test_app.py        # unittest suite (runs against SQLite)
├── frontend/
│   ├── src/
│   │   ├── App.jsx        # React SPA
│   │   ├── main.jsx
│   │   └── styles.css
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
├── .env                   # secrets (git-ignored)
├── .env.example           # template to copy from
├── alembic.ini
└── pyproject.toml         # dependencies + ruff/pytest config
```

## API Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/` | No | Serves the React frontend |
| `POST` | `/users` | No | Register a new user |
| `POST` | `/auth/login` | No | Login — returns a JWT bearer token |
| `GET` | `/auth/me` | Yes | Get the currently authenticated user |
| `GET` | `/users` | Yes | List all users |
| `GET` | `/users/{id}` | Yes | Get a single user by ID |
| `PUT` | `/users/{id}` | Yes | Update name, email, or password |
| `DELETE` | `/users/{id}` | Yes | Delete a user |

Protected endpoints require `Authorization: Bearer <token>`.

## Setup

### 1. Copy and fill the environment file

```bash
cp .env.example .env
```

Edit `.env`:

```env
DATABASE_URL=postgresql://user:password@localhost/user_management
JWT_SECRET_KEY=replace-with-a-long-random-secret
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

Generate a secure secret:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 2. Install Python dependencies

```bash
pip install -e ".[dev]"
```

Or without dev tools:

```bash
pip install -e .
```

### 3. Set up PostgreSQL

```bash
sudo systemctl start postgresql
sudo -u postgres psql -c "CREATE USER your_user WITH PASSWORD 'your_password';"
sudo -u postgres psql -c "CREATE DATABASE user_management OWNER your_user;"
```

### 4. Run database migrations

```bash
alembic upgrade head
```

### 5. Start the backend

```bash
uvicorn app.main:app --reload
```

- API: `http://localhost:8000`
- Swagger docs: `http://localhost:8000/docs`

### 6. Build or run the frontend

**Production build** (served by FastAPI at `/`):

```bash
cd frontend
npm install
npm run build
```

**Development** (hot reload via Vite, API proxied to FastAPI):

```bash
cd frontend
npm run dev
# Open http://localhost:5173
```

## Running Tests

Tests use SQLite — no PostgreSQL setup needed:

```bash
python -m pytest tests/ -v
# or
python -m unittest discover -s tests -v
```

## Authentication Flow

1. **Register** — `POST /users` with `name`, `email`, `password`. Password is hashed with PBKDF2-SHA256 (390,000 iterations) before storage.
2. **Login** — `POST /auth/login` returns a signed HS256 JWT with `sub` (user ID), `email`, and `exp` claims.
3. **Authorize** — Send `Authorization: Bearer <token>` on protected requests.
4. **Verify** — `get_current_user` in `app/dependencies.py` decodes the token, validates the signature, checks expiry, and loads the user from the database.

## How to Test in `/docs`

1. Open `http://localhost:8000/docs`
2. `POST /users` to create an account
3. `POST /auth/login` with the same credentials
4. Copy the `access_token` from the response
5. Click **Authorize** → paste the token
6. Call any protected endpoint

## Best Reading Order

If you are studying the code:

1. `app/database.py` — engine and session setup
2. `app/models.py` — the `users` table
3. `app/schemas.py` — validation and response shapes
4. `app/auth.py` — PBKDF2 hashing and HS256 JWT
5. `app/dependencies.py` — shared FastAPI deps
6. `app/routers/users.py` — CRUD routes
7. `app/routers/auth.py` — login and current-user routes
8. `app/main.py` — app factory, router wiring
9. `frontend/src/App.jsx` — React UI
10. `tests/test_app.py` — test suite

## Learning Note

`app/auth.py` uses only Python's standard library (`hashlib`, `hmac`, `secrets`) so every step of hashing and token signing is visible. The frontend shows controlled React forms, `localStorage` token storage, and `fetch`-based API calls. In production, teams typically use dedicated auth libraries rather than maintaining this logic by hand.
