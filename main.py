# main.py
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Generator

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

import models, schemas
from auth import AuthError, create_access_token, decode_access_token, hash_password, verify_password
from database import SessionLocal, create_db_and_tables

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_FILE = BASE_DIR / "frontend" / "index.html"
bearer_scheme = HTTPBearer(auto_error=False)


@asynccontextmanager
async def lifespan(_: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def unauthorized_exception(detail: str = "Not authenticated") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthorized_exception()

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload["sub"])
    except (AuthError, KeyError, TypeError, ValueError) as exc:
        raise unauthorized_exception("Invalid or expired token") from exc

    try:
        user = db.query(models.User).filter(models.User.id == user_id).first()
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while fetching the authenticated user",
        ) from exc

    if not user:
        raise unauthorized_exception("User no longer exists")

    return user


@app.get("/", response_class=HTMLResponse)
def dashboard():
    return HTMLResponse(FRONTEND_FILE.read_text(encoding="utf-8"))


@app.post(
    "/users",
    response_model=schemas.UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    try:
        existing_user = (
            db.query(models.User).filter(models.User.email == user.email).first()
        )
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )

        db_user = models.User(
            name=user.name,
            email=user.email,
            password_hash=hash_password(user.password),
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while creating user",
        ) from exc


@app.post("/auth/login", response_model=schemas.TokenResponse)
def login_user(credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    try:
        user = db.query(models.User).filter(models.User.email == credentials.email).first()
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while logging in",
        ) from exc

    if not user or not verify_password(credentials.password, user.password_hash):
        raise unauthorized_exception("Invalid email or password")

    return schemas.TokenResponse(
        access_token=create_access_token(str(user.id), user.email),
        token_type="bearer",
    )


@app.get("/auth/me", response_model=schemas.UserResponse)
def get_me(current_user: models.User = Depends(get_current_user)):
    return current_user


@app.get("/users", response_model=list[schemas.UserResponse])
def get_users(
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    try:
        return db.query(models.User).order_by(models.User.id.asc()).all()
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while fetching users",
        ) from exc


@app.get("/users/{user_id}", response_model=schemas.UserResponse)
def get_single_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    try:
        user = db.query(models.User).filter(models.User.id == user_id).first()
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while fetching the user",
        ) from exc

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@app.put("/users/{user_id}", response_model=schemas.UserResponse)
def update_user(
    user_id: int,
    user_update: schemas.UserUpdate,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    try:
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        if user_update.email and user_update.email != user.email:
            existing_user = (
                db.query(models.User)
                .filter(
                    models.User.email == user_update.email,
                    models.User.id != user_id,
                )
                .first()
            )
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Email already registered",
                )

        update_data = user_update.model_dump(exclude_unset=True, exclude_none=True)
        password = update_data.pop("password", None)
        if password:
            user.password_hash = hash_password(password)

        for field, value in update_data.items():
            setattr(user, field, value)

        db.commit()
        db.refresh(user)
        return user
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while updating the user",
        ) from exc


@app.delete("/users/{user_id}", response_model=schemas.MessageResponse)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    try:
        user = db.query(models.User).filter(models.User.id == user_id).first()
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while fetching the user",
        ) from exc

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    try:
        db.delete(user)
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while deleting the user",
        ) from exc

    return {"message": "User successfully deleted"}
