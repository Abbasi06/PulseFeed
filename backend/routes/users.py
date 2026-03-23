from fastapi import APIRouter, Depends, HTTPException, Response

from auth import COOKIE_OPTS, create_access_token, get_current_user_id
from database import get_db
from models import User
from schemas import UserCreate, UserRead
from sqlalchemy.orm import Session

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserRead)
def create_user(
    payload: UserCreate, response: Response, db: Session = Depends(get_db)
) -> User:
    user = User(
        name=payload.name,
        occupation=payload.occupation,
        interests=payload.interests,
        hobbies=payload.hobbies,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    response.set_cookie(value=create_access_token(user.id), **COOKIE_OPTS)
    return user


@router.get("/me", response_model=UserRead)
def get_me(
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> User:
    user = db.get(User, current_user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/logout")
def logout(response: Response) -> dict[str, str]:
    response.delete_cookie("access_token", path="/")
    return {"status": "ok"}


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: int, db: Session = Depends(get_db)) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    payload: UserCreate,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> User:
    if user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    user.name = payload.name
    user.occupation = payload.occupation
    user.interests = payload.interests
    user.hobbies = payload.hobbies
    db.commit()
    db.refresh(user)
    return user
