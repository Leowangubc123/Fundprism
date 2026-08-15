from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.tag import Tag
from app.models.user import User
from app.schemas import TagCreateRequest, TagItem, TagUpdateRequest
from app.security import get_current_admin

router = APIRouter(prefix="/admin/tags", tags=["admin-tags"])


@router.get("", response_model=List[TagItem])
def list_tags(
    category: Optional[str] = None,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    query = db.query(Tag)
    if category:
        query = query.filter(Tag.category == category)
    if not include_inactive:
        query = query.filter(Tag.is_active.is_(True))
    return query.order_by(Tag.category, Tag.sort_order, Tag.name).all()


@router.post("", response_model=TagItem, status_code=status.HTTP_201_CREATED)
def create_tag(
    payload: TagCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    existing = db.query(Tag).filter(Tag.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=409, detail="Tag name already exists")

    tag = Tag(**payload.model_dump())
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


@router.put("/{tag_id}", response_model=TagItem)
def update_tag(
    tag_id: UUID,
    payload: TagUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    update_data = payload.model_dump(exclude_unset=True)
    if "name" in update_data:
        existing = (
            db.query(Tag)
            .filter(Tag.name == update_data["name"], Tag.id != tag_id)
            .first()
        )
        if existing:
            raise HTTPException(status_code=409, detail="Tag name already exists")

    for field, value in update_data.items():
        setattr(tag, field, value)

    db.commit()
    db.refresh(tag)
    return tag


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tag(
    tag_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    # Soft delete: mark inactive instead of removing, preserving historical data.
    tag.is_active = False
    db.commit()
    return None
