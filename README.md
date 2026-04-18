# User Management FastAPI Project Guide

This project is a small FastAPI app that teaches the full path of a backend request:

1. A client sends HTTP data.
2. FastAPI receives it.
3. Pydantic validates it.
4. SQLAlchemy talks to the database.
5. The API returns a response.

This guide is written to help you read the code side by side with the project files.

## What This Project Does

The app manages users with three fields:

- `id`
- `name`
- `email`

It supports these actions:

- Create a user
- List all users
- Get one user by ID
- Delete a user

## Read In This Order

Read the project in this sequence:

1. `main.py`
2. `schemas.py`
3. `models.py`
4. `database.py`
5. `tests/test_app.py`
6. `alembic/env.py`

This order helps because `main.py` shows the app behavior first, then the other files explain the pieces it uses.

## Project Structure

- `main.py`: FastAPI app, routes, dependency injection, error handling
- `schemas.py`: request and response validation using Pydantic
- `models.py`: database table definition using SQLAlchemy ORM
- `database.py`: database connection, engine, session, base model
- `tests/test_app.py`: simple regression tests that prove the CRUD flow works
- `alembic/env.py`: Alembic migration environment
- `alembic.ini`: Alembic configuration

## 1. `main.py`: The API Layer

Open `main.py` first.

This file is the entry point of the application. It contains:

- the FastAPI app
- startup behavior
- database dependency
- route functions

### Imports

`main.py` imports:

- `FastAPI`, `Depends`, `HTTPException`, `status` from FastAPI
- `Session` from SQLAlchemy
- `IntegrityError`, `SQLAlchemyError` for database error handling
- `models` and `schemas`
- `SessionLocal` and `create_db_and_tables` from `database.py`

This shows the main architecture of the app:

- FastAPI handles HTTP
- Pydantic handles validation
- SQLAlchemy handles database work

### Lifespan Function

The `lifespan()` function runs when the app starts.

Its job here is simple:

- create database tables if they do not exist

That means the app can start on a clean machine without crashing because the `users` table is missing.

Concept to learn:

- FastAPI lifespan is a startup and shutdown hook
- it is useful for setup logic like database initialization

### `get_db()` Dependency

`get_db()` creates a database session and then closes it after the request finishes.

This is one of the most important FastAPI ideas in the project.

Why it matters:

- each request gets its own DB session
- cleanup happens automatically
- route functions do not need to manually open and close connections

Concept to learn:

- `Depends(get_db)` is FastAPI dependency injection

When you see this in a route:

```python
db: Session = Depends(get_db)
```

FastAPI says:

"Before running this route, call `get_db()` and give its result to `db`."

### Route: `POST /users`

This route creates a user.

Flow:

1. FastAPI reads incoming JSON.
2. It validates the body using `schemas.UserCreate`.
3. The route checks if the email already exists.
4. If it exists, the API returns `409 Conflict`.
5. Otherwise, it creates a `models.User` object.
6. It adds the object to the session.
7. It commits the transaction.
8. It refreshes the object so generated values like `id` are loaded.
9. It returns the created user.

Important concepts here:

- request body validation
- ORM object creation
- `db.add()`
- `db.commit()`
- `db.refresh()`
- raising `HTTPException`

Why `refresh()` matters:

- the database generates the `id`
- `refresh()` pulls that final saved row back into Python

### Route: `GET /users`

This route returns all users.

Key line idea:

- `db.query(models.User).all()`

Concept to learn:

- SQLAlchemy query API
- ORM query returns Python objects, not raw SQL rows

### Route: `GET /users/{user_id}`

This route gets one user by ID.

Flow:

1. Query for a row where `id == user_id`
2. If nothing is found, raise `404 Not Found`
3. Otherwise return the user

Concept to learn:

- path parameters
- `404` for missing resources

### Route: `DELETE /users/{user_id}`

This route deletes a user.

Flow:

1. Find the user
2. If not found, return `404`
3. Call `db.delete(user)`
4. Commit the transaction
5. Return a small success message

Concept to learn:

- deleting ORM objects
- transaction commit after delete

### Error Handling in `main.py`

The route functions catch database exceptions and convert them into API responses.

Why this is better than letting Python crash:

- the client gets a controlled HTTP response
- the session is rolled back on failure
- the app behaves predictably

Main ideas:

- `IntegrityError` usually means a database rule was broken, like duplicate email
- `SQLAlchemyError` is the general base class for SQLAlchemy-related errors
- `db.rollback()` resets a failed transaction

## 2. `schemas.py`: Data Validation and Serialization

Open `schemas.py` next.

This file defines the shapes of data that enter and leave the API.

These classes are Pydantic models, not database models.

That distinction is very important:

- `schemas.py` is for API data
- `models.py` is for database tables

### `UserBase`

`UserBase` contains the shared fields:

- `name`
- `email`

It also defines validation rules:

- `name` must be between 1 and 100 characters
- `email` must be a valid email
- blank names are rejected after trimming whitespace

Concept to learn:

- Pydantic validates incoming data before your route logic runs

Example:

- `" Alice "` becomes `"Alice"`
- `"   "` becomes a validation error

### `UserCreate`

`UserCreate` inherits from `UserBase`.

This means:

- the create request uses the same validation rules
- you can extend it later if create-specific fields are needed

### `UserResponse`

`UserResponse` is what the API sends back.

It includes:

- `id`
- `name`
- `email`

The important setting is:

```python
model_config = ConfigDict(from_attributes=True)
```

Why it exists:

- route functions return SQLAlchemy model objects
- Pydantic needs permission to read attributes from those ORM objects

Without this, FastAPI may not know how to convert a SQLAlchemy `User` into JSON properly.

### `MessageResponse`

This schema is used for simple success messages like delete responses.

It gives your response a clear structure:

```json
{"message": "User successfully deleted"}
```

## 3. `models.py`: The Database Table

Open `models.py`.

This file defines the SQLAlchemy ORM model for the `users` table.

### `class User(Base)`

This class represents one row in the `users` table.

Important idea:

- one Python object maps to one database row

### `__tablename__ = "users"`

This tells SQLAlchemy the database table name.

### Columns

- `id = Column(Integer, primary_key=True, index=True)`
- `name = Column(String(100), nullable=False, index=True)`
- `email = Column(String(255), unique=True, nullable=False, index=True)`

Concepts to learn:

- `primary_key=True`: unique identity for each row
- `index=True`: database can search this field faster
- `nullable=False`: this field cannot be empty in the database
- `unique=True`: no two users can share the same email

Very important distinction:

- validation in `schemas.py` protects input at the API level
- constraints in `models.py` protect data at the database level

Good backend systems usually use both.

## 4. `database.py`: Engine, Session, and Base

Open `database.py`.

This file sets up SQLAlchemy itself.

### `DATABASE_URL`

The project reads the database URL from the environment:

```python
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_SQLITE_URL)
```

This means:

- if you set `DATABASE_URL`, the app uses it
- if not, it uses a local SQLite file by default

Why this is useful:

- easy local development
- easy deployment with another database later

### Engine

The engine is the main SQLAlchemy connection manager.

Think of it like:

- the app's bridge to the database

For SQLite, this project adds:

```python
connect_args = {"check_same_thread": False}
```

That is needed because SQLite has thread-related restrictions and FastAPI may handle requests across threads.

### SessionLocal

`SessionLocal` is a session factory.

Important idea:

- it is not one session
- it is a way to create sessions

Then `get_db()` in `main.py` creates one session per request from this factory.

### `Base = declarative_base()`

This is the parent class used by ORM models.

When `User(Base)` is declared in `models.py`, SQLAlchemy registers it in metadata.

That metadata is later used to create tables and help Alembic understand the schema.

### `create_db_and_tables()`

This function runs:

```python
Base.metadata.create_all(bind=engine)
```

Meaning:

- look at all models connected to `Base`
- create missing tables in the database

This is simple and useful for learning.

In bigger production apps, teams often rely more on Alembic migrations than `create_all()`.

## 5. Request Flow: End-to-End Example

Here is the full flow for `POST /users`.

### Request

Client sends:

```json
{
  "name": "Alice",
  "email": "alice@example.com"
}
```

### Step by Step

1. FastAPI matches the request to `create_user()` in `main.py`.
2. It validates the JSON using `schemas.UserCreate`.
3. It injects a database session using `Depends(get_db)`.
4. Your code checks if a user with the same email already exists.
5. If not, it creates `models.User(name=..., email=...)`.
6. SQLAlchemy inserts the row into the database on `commit()`.
7. FastAPI converts the returned ORM object into `schemas.UserResponse`.
8. The client receives JSON.

### Response

```json
{
  "id": 1,
  "name": "Alice",
  "email": "alice@example.com"
}
```

## 6. `tests/test_app.py`: How the Project Proves It Works

Open `tests/test_app.py`.

This file is very useful for learning because it shows the expected behavior of the app in executable form.

### Why the tests matter

Tests answer:

- what should happen when creating a user?
- what should happen when email is duplicated?
- what should happen when a user does not exist?

### How the tests work

The tests use a temporary SQLite database file.

This is great for learning because:

- the real project DB is not modified
- each test gets a clean database
- test behavior is repeatable

### `load_app()`

This helper:

- sets `DATABASE_URL`
- reloads the project modules
- creates tables

Concept to learn:

- configuration can change app behavior
- tests often control environment variables to create isolated setups

### Test Cases

The file currently checks:

- full create, list, fetch, delete flow
- duplicate email returns `409`
- missing user returns `404`

This is a very good starting point for understanding backend behavior.

## 7. Alembic: Why `alembic/env.py` Exists

Open `alembic/env.py`.

Alembic is used for database migrations.

A migration is a tracked database change such as:

- create a table
- add a column
- rename a column
- change constraints

### What this file does

- loads project code
- reads the app's `DATABASE_URL`
- exposes model metadata to Alembic
- runs migrations in offline or online mode

### `target_metadata = models.Base.metadata`

This line is important because Alembic needs to know what your models look like.

That metadata comes from SQLAlchemy models that inherit from `Base`.

### Online vs Offline Migrations

Offline mode:

- generates SQL without opening a live database connection

Online mode:

- connects to the database and applies changes directly

You do not need to master Alembic on day one. Just understand that it is the safer long-term way to evolve database schema over time.

## 8. Important Concepts You Should Learn From This Project

Here is the vocabulary behind the code.

### FastAPI

- `FastAPI()`: creates the app
- route decorators like `@app.get(...)`: map URLs to Python functions
- `Depends(...)`: dependency injection
- `HTTPException`: return controlled error responses
- `response_model=...`: shape and filter outgoing responses

### Pydantic

- validates request data
- converts Python objects to JSON-friendly output
- enforces types like `EmailStr`
- supports custom validators

### SQLAlchemy

- `engine`: connection manager
- `Session`: unit of work for database operations
- ORM model: Python class mapped to a table
- `query()`: fetch rows
- `add()`, `delete()`, `commit()`, `refresh()`

### Database Constraints

- `primary_key`
- `unique`
- `nullable=False`
- indexes

### API Design

- `201 Created` for successful create
- `404 Not Found` for missing user
- `409 Conflict` for duplicate email
- structured JSON responses

## 9. How To Run the App

From the project folder:

```bash
./venv/bin/uvicorn main:app --reload
```

Then open:

- `http://127.0.0.1:8000/docs`

The `/docs` page is Swagger UI, generated automatically by FastAPI.

This page is excellent for learning because you can:

- inspect endpoints
- see request models
- see response models
- try API calls from the browser

## 10. Good Things To Try While Learning

Read the code and test these cases in `/docs`:

1. Create a valid user.
2. Create another user with the same email.
3. Get all users.
4. Get one existing user.
5. Get a user ID that does not exist.
6. Delete a user.
7. Try creating a user with an invalid email.
8. Try creating a user with a blank name.

For each test, ask:

- which file handled this?
- which validation rule stopped bad data?
- did the check happen in FastAPI, Pydantic, or the database?

## 11. How To Think About The Architecture

A clean mental model for this project is:

- `main.py` is the controller layer
- `schemas.py` is the API contract layer
- `models.py` is the database table layer
- `database.py` is the infrastructure layer
- `tests/test_app.py` is the behavior proof

This separation is one of the most important backend design ideas to learn.

## 12. Common Beginner Questions

### Why do we need both schemas and models?

Because they solve different problems.

- schemas define API input and output
- models define database structure

If you mix them together, the app becomes harder to maintain.

### Why not return raw dictionaries everywhere?

Because schemas give:

- validation
- clear structure
- documentation
- type safety

### Why do we commit after add or delete?

Because until `commit()` happens, the transaction is not permanently saved in the database.

### Why do we still check duplicate email in code if the database already has `unique=True`?

Because:

- app-side checking gives a friendly error earlier
- database constraint is the final safety net

Using both is more reliable.

## 13. Next Steps To Grow This Project

Once you understand the current version, good next features are:

1. Add `PUT /users/{id}` to update a user.
2. Add timestamps like `created_at`.
3. Split routes into a separate router file.
4. Add a service layer between routes and DB code.
5. Add real Alembic migration files.
6. Add pagination for `GET /users`.
7. Add password hashing and authentication.

## 14. Best Way To Study This Project

Use this pattern:

1. Read one section of this guide.
2. Open the related file.
3. Trace one request from start to finish.
4. Change one small thing.
5. run the app or tests again.

A good first exercise:

- add a new field like `age`
- update schema
- update model
- update test
- observe what breaks and why

That is one of the fastest ways to actually understand FastAPI and SQLAlchemy.

## 15. Final Summary

This project teaches five core backend ideas:

1. How an API endpoint is defined
2. How request and response data are validated
3. How Python classes map to database tables
4. How database sessions are managed safely
5. How tests verify behavior

If you can explain how `POST /users` works from `main.py` through `schemas.py`, `models.py`, and `database.py`, you already understand the backbone of this entire project.
