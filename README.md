# User Management FastAPI Project Guide

This project is a small FastAPI app for learning how a backend request moves through an API, validation layer, ORM, and database.

It is a great beginner project because the codebase is small, but it still shows the most important backend building blocks:

- FastAPI routes
- Pydantic schemas
- SQLAlchemy models
- database sessions
- error handling
- tests
- Alembic configuration

## What This Project Currently Does

The app manages users with these fields:

- `id`
- `name`
- `email`

The current code implements full CRUD:

- `Create` a user
- `Read` all users
- `Read` one user by ID
- `Update` a user
- `Delete` a user

## Main Goal Of This Project

This project teaches the full path of an API request:

1. A client sends HTTP data.
2. FastAPI receives the request.
3. Pydantic validates the data.
4. SQLAlchemy converts Python objects into database actions.
5. The database stores or returns data.
6. FastAPI sends a JSON response back.

## Project Files

- `main.py`: FastAPI app and route logic
- `schemas.py`: Pydantic request and response models
- `models.py`: SQLAlchemy ORM model
- `database.py`: engine, session, and base setup
- `tests/test_app.py`: tests for the app behavior
- `alembic/env.py`: Alembic migration environment
- `alembic.ini`: Alembic config file
- `README.md`: learning guide for the project
- `requirements.txt`: installable Python dependencies for the backend

## Quick Setup

If you are starting this project on a fresh machine, install the dependencies first:

```bash
pip install -r requirements.txt
```

Then run the app with:

```bash
./venv/bin/uvicorn main:app --reload
```

If you want to use PostgreSQL instead of the default SQLite file, set `DATABASE_URL` before starting the app.

## Best Reading Order

To understand the project smoothly, read the files in this order:

1. `main.py`
2. `schemas.py`
3. `models.py`
4. `database.py`
5. `tests/test_app.py`
6. `alembic/env.py`

This order works well because `main.py` shows behavior first, and the other files explain the pieces that behavior depends on.

## 1. `main.py`: The API Layer

`main.py` is the center of the application.

It contains:

- the FastAPI app object
- startup setup
- the database dependency
- all route handlers

### Main concepts used in `main.py`

- `FastAPI()`: creates the web application
- route decorators like `@app.post()` and `@app.get()`
- dependency injection with `Depends()`
- `HTTPException` for error responses
- SQLAlchemy sessions for database work

### Lifespan function

The app uses a lifespan function:

- it runs when the application starts
- it calls `create_db_and_tables()`

This means the app can create missing tables automatically on startup.

Why this matters:

- easier local development
- less setup friction for beginners
- the app can run without manually creating the table first

### `get_db()` dependency

`get_db()` creates one database session for a request and closes it afterward.

That is a key FastAPI idea.

When you see this:

```python
db: Session = Depends(get_db)
```

it means FastAPI will:

- call `get_db()`
- inject the returned session into the route
- make sure cleanup happens after the request finishes

This pattern keeps the route functions clean and reusable.

## 2. Current Routes

### `POST /users`

This route creates a user.

Flow:

1. FastAPI receives JSON.
2. Pydantic validates it with `schemas.UserCreate`.
3. The route checks whether the email already exists.
4. If the email exists, it returns `409 Conflict`.
5. If not, it creates a `models.User` object.
6. The object is added to the session.
7. `commit()` saves it.
8. `refresh()` reloads the saved row.
9. The created user is returned.

Important ideas:

- request body validation
- uniqueness checks
- SQLAlchemy ORM object creation
- transaction commit
- converting database objects into API responses

### `GET /users`

This route returns all users.

Main line concept:

```python
db.query(models.User).all()
```

This means:

- ask SQLAlchemy for all rows in the `users` table
- return them as Python ORM objects
- let FastAPI serialize them using the response schema

### `GET /users/{user_id}`

This route gets one user by ID.

Flow:

1. Read the `user_id` from the URL path
2. Query the database for a matching user
3. If none exists, return `404 Not Found`
4. Otherwise return the user

Important ideas:

- path parameters
- searching by primary key value
- `404` for missing resources

### `PUT /users/{user_id}`

This route updates one existing user.

Flow:

1. Find the user by ID
2. If not found, return `404`
3. Accept a new `name`, a new `email`, or both
4. If the new email belongs to another user, return `409`
5. Apply only the fields sent in the request
6. Commit the transaction
7. Refresh and return the updated user

Important ideas:

- update-specific request schema
- partial field updates with `model_dump(exclude_unset=True, exclude_none=True)`
- duplicate email protection during update
- using `setattr()` to apply changed values

### `DELETE /users/{user_id}`

This route deletes one user.

Flow:

1. Find the user by ID
2. If not found, return `404`
3. Call `db.delete(user)`
4. Commit the transaction
5. Return a success message

Important ideas:

- ORM deletion
- committing destructive changes
- returning simple structured JSON

## 3. Error Handling In `main.py`

The app catches database errors and turns them into API responses.

Why this is useful:

- the server does not crash with a raw traceback for the client
- failed transactions can be rolled back safely
- the API returns predictable HTTP errors

Important classes:

- `IntegrityError`: often means a database rule was broken, like duplicate email
- `SQLAlchemyError`: broader SQLAlchemy-related failure

Important action:

- `db.rollback()` resets a broken transaction before continuing

## 4. `schemas.py`: The Validation Layer

`schemas.py` defines the shapes of data that enter and leave the API.

These are Pydantic models.

This file is not about database tables. It is about API data.

That difference is very important:

- `schemas.py` controls request and response validation
- `models.py` controls the database table structure

### `UserBase`

`UserBase` contains:

- `name`
- `email`

Validation rules:

- `name` must not be blank
- `name` is trimmed
- `name` must stay between 1 and 100 characters
- `email` must be a valid email address

So if a client sends invalid data, FastAPI and Pydantic block it before your database logic runs.

### `UserCreate`

`UserCreate` inherits from `UserBase`.

This is the schema used when creating a user.

Why inheritance is helpful:

- less repeated code
- shared validation stays in one place
- future create-only fields can be added easily

### `UserUpdate`

`UserUpdate` is the schema used by the `PUT /users/{user_id}` endpoint.

Why it is different from `UserCreate`:

- both fields are optional
- the client can send only the values that should change
- the schema still validates email format and trims `name`
- the schema rejects completely empty update requests

### `UserResponse`

This is the schema used when sending user data back to the client.

It contains:

- `id`
- `name`
- `email`

This line is very important:

```python
model_config = ConfigDict(from_attributes=True)
```

Why it matters:

- route functions return SQLAlchemy model objects
- Pydantic needs permission to read attributes from ORM objects
- this makes conversion to JSON work cleanly

### `MessageResponse`

This schema is used for responses like delete success messages.

Example:

```json
{
  "message": "User successfully deleted"
}
```

## 5. `models.py`: The Database Model

`models.py` defines the SQLAlchemy ORM model.

The `User` class maps to the `users` database table.

Important parts:

- `__tablename__ = "users"`
- `id` is the primary key
- `name` is required
- `email` is required and unique

Concepts to learn:

- `primary_key=True`: uniquely identifies each row
- `nullable=False`: the database will reject missing values
- `unique=True`: duplicate emails are not allowed
- `index=True`: helps database lookups run faster

A very important lesson here is that the project protects data in two places:

- Pydantic validation at the API level
- database constraints at the database level

That combination is good backend practice.

## 6. `database.py`: Database Setup

`database.py` configures SQLAlchemy.

It defines:

- `DATABASE_URL`
- the SQLAlchemy `engine`
- `SessionLocal`
- `Base`
- `create_db_and_tables()`

### Why the app uses SQLite by default

The project currently uses an environment-based database setup.

If `DATABASE_URL` is not set, it falls back to a local SQLite database file.

Why that is useful:

- the app runs immediately for local learning
- no PostgreSQL server is required just to start studying the code
- the database file lives locally in the project

But the app is not locked to SQLite.

If you set `DATABASE_URL`, the app can use another database such as PostgreSQL.

### Engine

The engine is SQLAlchemy's connection manager.

Think of it as the bridge between Python and the database.

### SessionLocal

`SessionLocal` is a session factory.

It is not one database session by itself.

Instead, it is used to create sessions when needed.

That is why `get_db()` calls it for each request.

### Base

`Base = declarative_base()` is the parent class for ORM models.

When `models.User` inherits from `Base`, SQLAlchemy registers it in metadata.

That metadata is used for:

- table creation
- schema tracking
- Alembic migration support

## 7. Request Flow Example

Here is the full request flow for `POST /users`.

### Request body

```json
{
  "name": "Alice",
  "email": "alice@example.com"
}
```

### What happens step by step

1. FastAPI matches the request to `create_user()`.
2. Pydantic validates the request using `UserCreate`.
3. FastAPI injects a database session using `Depends(get_db)`.
4. The route checks whether the email already exists.
5. If valid, a SQLAlchemy `User` object is created.
6. The session saves it with `commit()`.
7. The object is refreshed to load the final stored data.
8. FastAPI serializes it using `UserResponse`.
9. JSON is sent back to the client.

### Response body

```json
{
  "id": 1,
  "name": "Alice",
  "email": "alice@example.com"
}
```

## 8. `tests/test_app.py`: Behavior Proof

The tests are especially useful for learning because they show what the project is expected to do.

The current tests check:

- create a user
- list users
- fetch a user
- update a user
- reject duplicate emails on create or update with `409`
- delete a user
- missing user returns `404`

The tests use a temporary SQLite database.

Why that is good:

- real data is not affected
- every test starts clean
- results are repeatable

## 9. Alembic Files

`alembic/env.py` and `alembic.ini` are part of the migration system.

Alembic helps manage schema changes over time.

Examples of schema changes:

- creating a table
- adding a column
- changing constraints

Important idea:

- `models.Base.metadata` tells Alembic what your current SQLAlchemy models look like

You do not need deep Alembic knowledge to understand the current app, but it is good to know why those files exist.

## 10. HTTP Status Codes Used Here

This project already shows some useful API design choices:

- `201 Created`: user successfully created
- `404 Not Found`: requested user does not exist
- `409 Conflict`: duplicate email
- `500 Internal Server Error`: unexpected database problem

These status codes help clients understand what happened.

## 11. How To Run The App

From the project directory, make sure the dependencies are installed:

```bash
pip install -r requirements.txt
```

Then start the server:

```bash
./venv/bin/uvicorn main:app --reload
```

Then open:

- `http://127.0.0.1:8000/docs`

The `/docs` page is FastAPI's automatic Swagger UI.

That page is very helpful for learning because you can:

- inspect endpoints
- see request schemas
- see response schemas
- test API calls interactively

## 12. Good Practice Exercises

If you want to understand this project deeply, try these exercises:

1. Create a valid user from `/docs`.
2. Try a duplicate email.
3. Try an invalid email.
4. Try a blank name.
5. Fetch a user that does not exist.
6. Update only a user's name with `PUT /users/{user_id}`.
7. Update only a user's email with `PUT /users/{user_id}`.
8. Try updating a user with another user's email and observe the `409`.
9. Delete an existing user.
10. Add a new field like `age` and follow what files must change.

For each experiment, ask yourself:

- which file handled this?
- was validation done by FastAPI, Pydantic, or the database?
- what response model shaped the output?

## 13. How Full CRUD Works Here

This project now includes all four CRUD operations:

- Create: `POST /users`
- Read: `GET /users` and `GET /users/{user_id}`
- Update: `PUT /users/{user_id}`
- Delete: `DELETE /users/{user_id}`

The most interesting one to study is usually `Update`, because it combines:

- request validation
- lookup by ID
- duplicate email protection
- selective field updates
- transaction commit and refresh

If you can explain the update flow clearly, you probably understand the whole project very well.

## 14. Final Summary

This project is a strong beginner backend example because it teaches:

- how FastAPI routes work
- how dependency injection works
- how Pydantic validates request data
- how SQLAlchemy maps classes to database tables
- how sessions and transactions work
- how errors become HTTP responses
- how tests verify behavior

Right now, the project is a complete small CRUD backend and a strong learning example for FastAPI, Pydantic, and SQLAlchemy.
