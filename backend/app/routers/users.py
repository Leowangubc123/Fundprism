from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas import UserCreateRequest, UserListItem, UserUpdateRequest
from app.security import get_current_admin, get_password_hash

router = APIRouter(prefix="/admin/users", tags=["admin-users"])


def _user_list_item(user: User) -> UserListItem:
    return UserListItem(
        id=user.id,
        username=user.username,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        last_login_at=user.last_login_at,
    )


@router.get("", response_model=List[UserListItem])
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    users = db.query(User).order_by(User.username).all()
    return [_user_list_item(u) for u in users]


@router.post("", response_model=UserListItem, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    existing = db.query(User).filter(User.username == payload.username).first()
    if existing:
        raise HTTPException(status_code=409, detail="Username already exists")

    user = User(
        username=payload.username,
        full_name=payload.full_name,
        hashed_password=get_password_hash(payload.password),
        role=payload.role,
        is_active=payload.is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _user_list_item(user)


@router.put("/{user_id}", response_model=UserListItem)
def update_user(
    user_id: UUID,
    payload: UserUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if current_user.id == user_id:
        if payload.role is not None and payload.role != user.role:
            raise HTTPException(status_code=400, detail="Cannot change your own role")
        if payload.is_active is not None and not payload.is_active:
            raise HTTPException(status_code=400, detail="Cannot deactivate yourself")

    update_data = payload.model_dump(exclude_unset=True)
    if "password" in update_data:
        user.hashed_password = get_password_hash(update_data.pop("password"))
    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return _user_list_item(user)


@router.post("/{user_id}/reset-password", response_model=UserListItem)
def reset_password(
    user_id: UUID,
    payload: UserUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not payload.password:
        raise HTTPException(status_code=400, detail="Password is required")

    user.hashed_password = get_password_hash(payload.password)
    db.commit()
    db.refresh(user)
    return _user_list_item(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    db.delete(user)
    db.commit()
    return None
