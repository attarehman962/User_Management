from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import create_access_token, verify_password
from app.dependencies import get_current_user, get_db

router = APIRouter(prefix="/auth", tags=["auth"])


def _unauthorized(detail: str = "Not authenticated") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


@router.post("/login", response_model=schemas.TokenResponse)
def login_user(credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    try:
        user = db.query(models.User).filter(models.User.email == credentials.email).first()
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while logging in",
        ) from exc

    if not user or not verify_password(credentials.password, user.password_hash):
        raise _unauthorized("Invalid email or password")

    return schemas.TokenResponse(
        access_token=create_access_token(str(user.id), user.email),
        token_type="bearer",
    )


@router.get("/me", response_model=schemas.UserResponse)
def get_me(current_user: models.User = Depends(get_current_user)):
    return current_user
