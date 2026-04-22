from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import hash_password
from app.dependencies import get_current_user, get_db

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    try:
        existing = db.query(models.User).filter(models.User.email == user.email).first()
        if existing:
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


@router.get("", response_model=list[schemas.UserResponse])
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


@router.get("/{user_id}", response_model=schemas.UserResponse)
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


@router.put("/{user_id}", response_model=schemas.UserResponse)
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
            existing = (
                db.query(models.User)
                .filter(
                    models.User.email == user_update.email,
                    models.User.id != user_id,
                )
                .first()
            )
            if existing:
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


@router.delete("/{user_id}", response_model=schemas.MessageResponse)
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
