# User Management

A full-stack project for learning CRUD, PostgreSQL, password hashing, and JWT authentication — with a React frontend that exercises the same API.

## What This Project Teaches

This app now shows the full flow from registration to login to protected CRUD.

- how FastAPI routes work
- how request validation works with Pydantic
- how SQLAlchemy models map to database tables
- how passwords are hashed before saving
- how JWT tokens are created and checked
- how protected routes use `Authorization: Bearer <token>`
- how a small frontend can call the same backend API

## Best Reading Order

Open these files side by side with the README and study them in this order:

1. `database.py`
2. `models.py`
3. `schemas.py`
4. `auth.py`
5. `main.py`
6. `frontend/src/App.jsx`
7. `frontend/src/styles.css`
8. `tests/test_app.py`

## Project Files

- `database.py` — loads `DATABASE_URL` from `.env`, creates the SQLAlchemy engine and session
- `models.py` — defines the `users` table
- `schemas.py` — validates incoming request data and shapes outgoing responses
- `auth.py` — hashes passwords and builds/verifies JWT tokens using Python stdlib only
- `main.py` — registration, login, current-user, and protected CRUD routes
- `frontend/src/App.jsx` — React UI for register, login, current session, and protected CRUD
- `frontend/src/styles.css` — frontend styles
- `frontend/package.json` — React 18 and Vite 5
- `frontend/vite.config.js` — Vite dev server and API proxy config
- `tests/test_app.py` — unit tests for auth and CRUD (run against SQLite)
- `alembic/` — migration history
- `.env.example` — sample environment variables

## Environment Setup

Install Python dependencies:

```bash
pip install fastapi "uvicorn[standard]" sqlalchemy psycopg2-binary "pydantic[email]" python-dotenv alembic
```

Make sure PostgreSQL is running:

```bash
sudo systemctl start postgresql
```

Create a PostgreSQL user:

```bash
sudo -u postgres psql -c "CREATE USER fastapi_user WITH PASSWORD 'strongpass';"
```

If the user already exists, reset the password:

```bash
sudo -u postgres psql -c "ALTER USER fastapi_user WITH PASSWORD 'strongpass';"
```

Create the database:

```bash
sudo -u postgres psql -c "CREATE DATABASE fastapi_db OWNER fastapi_user;"
```

Create your local env file:

```bash
cp .env.example .env
```

Put values like these in `.env`:

```env
DATABASE_URL=postgresql://fastapi_user:strongpass@localhost/fastapi_db
JWT_SECRET_KEY=replace-this-with-a-long-random-secret
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

Run database migrations:

```bash
alembic upgrade head
```

## Run The App

Start the FastAPI backend:

```bash
uvicorn main:app --reload
```

For React development:

```bash
cd frontend
npm install
npm run dev
```

Open the Vite app at `http://127.0.0.1:5173/`.

For a production-style build that FastAPI can serve at `/`:

```bash
cd frontend
npm install
npm run build
```

Then open:

- `http://127.0.0.1:8000/` for the built React frontend
- `http://127.0.0.1:8000/docs` for FastAPI Swagger docs

## Authentication Concepts In This Code

### 1. Password hashing

When a user registers, the password is never stored directly.

`auth.py` uses `hashlib.pbkdf2_hmac` to turn the password into a derived hash plus salt. The database stores only `password_hash`.

So instead of this unsafe idea:

```text
password = supersecure
```

The database stores something like this:

```text
pbkdf2_sha256$390000$<salt>$<derived_key>
```

### 2. JWT tokens

After login, `main.py` calls `create_access_token()` from `auth.py`.

That token contains claims such as:

- `sub`: the user ID
- `email`: the user email
- `exp`: expiration time

The browser or API client sends the token back using:

```http
Authorization: Bearer <token>
```

### 3. Protected routes

`get_current_user()` in `main.py` is the key auth dependency.

It:

1. reads the bearer token
2. decodes and verifies the JWT
3. gets the `sub` user ID from the token
4. loads that user from the database
5. returns the authenticated user to the route

That dependency is added to routes like:

- `GET /auth/me`
- `GET /users`
- `GET /users/{user_id}`
- `PUT /users/{user_id}`
- `DELETE /users/{user_id}`

## Request Flow To Understand

### Register flow

1. frontend or `/docs` sends `name`, `email`, and `password`
2. `schemas.UserCreate` validates the data
3. `main.py` hashes the password
4. `models.User` stores `name`, `email`, and `password_hash`
5. response returns safe user data without the password

### Login flow

1. client sends `email` and `password`
2. `main.py` finds the user by email
3. `auth.verify_password()` compares the raw password with the stored hash
4. if valid, `auth.create_access_token()` returns a JWT
5. the client saves and uses that JWT for protected routes

### Protected CRUD flow

1. client sends bearer token in the header
2. `get_current_user()` verifies the token
3. route runs only if the token is valid
4. database query returns protected data

## API Endpoints

Public routes:

- `GET /`
- `POST /users`
- `POST /auth/login`

Protected routes:

- `GET /auth/me`
- `GET /users`
- `GET /users/{user_id}`
- `PUT /users/{user_id}`
- `DELETE /users/{user_id}`

## How To Test In `/docs`

1. Open `http://127.0.0.1:8000/docs`
2. Use `POST /users` to create a user
3. Use `POST /auth/login` with the same email and password
4. Copy the `access_token`
5. Click `Authorize` in Swagger
6. Paste the token value into the bearer auth box
7. Call `GET /auth/me` or `GET /users`
8. Try `PUT /users/{user_id}` to change name, email, or password

Example register body:

```json
{
  "name": "Alice",
  "email": "alice@example.com",
  "password": "supersecure"
}
```

Example login body:

```json
{
  "email": "alice@example.com",
  "password": "supersecure"
}
```

Example update body:

```json
{
  "name": "Alice Cooper",
  "email": "acooper@example.com",
  "password": "newsecurepass"
}
```

## Frontend

The React frontend lets you:

- create an account
- log in and store the token in the browser
- verify the session with the backend
- load protected user data
- update user name, email, and password
- delete users

## Notes About Existing Databases

If you already had a `users` table before adding auth, `database.py` now checks whether the `password_hash` column exists and adds it automatically on startup.

That fixes the schema mismatch bug for older local databases.

## Run Tests

Tests use SQLite so no PostgreSQL setup is needed:

```bash
python -m unittest discover -s tests -v
```

## Stack Details

| Layer | Technology |
|---|---|
| Backend | Python 3.11+, FastAPI, SQLAlchemy |
| Database | PostgreSQL (Alembic migrations) |
| Auth | Custom HS256 JWT + PBKDF2-SHA256 (Python stdlib, no third-party auth lib) |
| Frontend | React 18, Vite 5 |
| Tests | Python `unittest` with SQLite |

## Learning Note

The hashing and JWT code in `auth.py` uses only Python's standard library (`hashlib`, `hmac`, `secrets`) so you can see exactly what happens at each step. The frontend demonstrates controlled React forms, `localStorage` token storage, and `fetch`-based API calls. In production systems teams typically use dedicated auth libraries rather than maintaining this logic by hand.
